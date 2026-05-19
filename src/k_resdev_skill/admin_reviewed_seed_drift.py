from __future__ import annotations

import hashlib
from pathlib import Path

from .admin_operating import review_admin_obligations
from .admin_profile_pack_reviews import summarize_admin_profile_pack_reviews
from .models import AdminReviewedSeedDriftDashboardResult, AdminReviewedSeedDriftItem


REVIEWED_SEED_DRIFT_CODES = {
    "admin_reviewed_seed_gate_metadata_missing",
    "admin_reviewed_seed_gate_missing",
    "admin_reviewed_seed_gate_hash_mismatch",
    "admin_reviewed_seed_profile_review_hash_mismatch",
    "admin_reviewed_seed_profile_pack_hash_mismatch",
    "admin_reviewed_seed_review_receipts_missing",
}


def generate_admin_reviewed_seed_drift_dashboard(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> AdminReviewedSeedDriftDashboardResult:
    """Summarize reviewed-seed drift and propose non-destructive repair actions."""

    workspace = Path(root)
    warnings: list[str] = []
    admin = review_admin_obligations(workspace)
    warnings.extend(admin.warnings)

    current_review_receipt_count = 0
    items: list[AdminReviewedSeedDriftItem] = []
    if admin.seed_mode == "reviewed_seed":
        items.extend(_gate_items(workspace, admin.reviewed_seed_gate_path, admin.reviewed_seed_gate_hash))
        items.extend(_profile_review_items(workspace, admin.reviewed_seed_profile_review_hash))
        items.extend(_profile_pack_items(workspace, admin.source_pack_path, admin.reviewed_seed_admin_profile_pack_hash or admin.source_pack_hash))
        receipt_items, current_review_receipt_count = _review_receipt_items(workspace, admin.profile_id, admin.reviewed_seed_review_ids)
        items.extend(receipt_items)
        items.extend(_finding_items(workspace, items, admin.findings))

    items = _dedupe_items(items)
    high_count = sum(1 for item in items if item.severity == "high")
    medium_count = sum(1 for item in items if item.severity == "medium")
    low_count = sum(1 for item in items if item.severity == "low")
    status = _status(admin.seed_mode, high_count, medium_count, bool(items))
    result = AdminReviewedSeedDriftDashboardResult(
        root=str(workspace),
        status=status,
        profile_id=admin.profile_id,
        seed_mode=admin.seed_mode,
        gate_status=admin.reviewed_seed_gate_status,
        gate_path=admin.reviewed_seed_gate_path,
        source_pack_path=admin.source_pack_path,
        recorded_review_receipt_count=len(admin.reviewed_seed_review_ids),
        current_review_receipt_count=current_review_receipt_count,
        drift_count=len(items),
        action_count=sum(1 for item in items if item.repair_command or item.manual_step),
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        items=items,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=warnings,
    )
    _write_outputs(result, output_path, json_path)
    return result


def render_admin_reviewed_seed_drift_markdown(result: AdminReviewedSeedDriftDashboardResult) -> str:
    lines = [
        "# K-ResDev Reviewed-Seed Drift Dashboard",
        "",
        "> Operating projection only. Repair commands refresh local review artifacts; official submissions and seed replacement still require human approval.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | `{_escape(result.status)}` |",
        f"| Profile | {_escape(result.profile_id or '-')} |",
        f"| Seed mode | {_escape(result.seed_mode or '-')} |",
        f"| Gate status | {_escape(result.gate_status or '-')} |",
        f"| Gate path | `{_escape(result.gate_path or '-')}` |",
        f"| Source pack | `{_escape(result.source_pack_path or '-')}` |",
        f"| Drift count | {result.drift_count} |",
        f"| High / medium / low | {result.high_count} / {result.medium_count} / {result.low_count} |",
        f"| Review receipts recorded/current | {result.recorded_review_receipt_count} / {result.current_review_receipt_count} |",
        "",
        "## Repair Actions",
        "",
        "| Severity | Category | Status | Finding | Message | Path | Recorded Hash | Current Hash | Command | Manual Step |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    if not result.items:
        lines.append("| ok | - | ready | - | No reviewed-seed drift detected. | - | - | - | - | Keep reviewed-seed rows in accepted_risk until human-approved for external use. |")
    for item in result.items:
        command = f"`{_escape(item.repair_command)}`" if item.repair_command else "-"
        lines.append(
            "| {severity} | {category} | {status} | {finding} | {message} | {path} | {recorded} | {current} | {command} | {manual} |".format(
                severity=_escape(item.severity),
                category=_escape(item.category),
                status=_escape(item.status),
                finding=_escape(item.finding_code),
                message=_escape(item.message),
                path=f"`{_escape(item.path)}`" if item.path else "-",
                recorded=f"`{_escape(item.recorded_hash)}`" if item.recorded_hash else "-",
                current=f"`{_escape(item.current_hash)}`" if item.current_hash else "-",
                command=command,
                manual=_escape(item.manual_step),
            )
        )
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in result.warnings:
            lines.append(f"- {_escape(warning)}")
    lines.append("")
    return "\n".join(lines)


def _gate_items(workspace: Path, recorded_path: str | None, recorded_hash: str | None) -> list[AdminReviewedSeedDriftItem]:
    path = _resolve_path(workspace, recorded_path)
    command = f'python -m k_resdev_skill admin-profile-pack-gate --root "{workspace}" --output "{workspace / "reports" / "admin-profile-pack-gate.md"}" --json "{workspace / "state" / "admin-profile-pack-gate.json"}"'
    if path is None or not recorded_hash:
        return [
            _item(
                "gate_metadata",
                "gate",
                "medium",
                "metadata_missing",
                "admin_reviewed_seed_gate_metadata_missing",
                "Reviewed-seed metadata is missing the gate path or recorded gate hash.",
                path=str(workspace / "state" / "admin-obligations.json"),
                repair_command=command,
                manual_step="Regenerate the gate, review it, then archive or supersede stale local admin obligations before re-seeding.",
            )
        ]
    if not path.exists():
        return [
            _item(
                "gate_missing",
                "gate",
                "medium",
                "artifact_missing",
                "admin_reviewed_seed_gate_missing",
                "Recorded reviewed-seed gate artifact is missing.",
                path=str(path),
                recorded_hash=recorded_hash,
                repair_command=command,
                manual_step="Restore the gate artifact or regenerate it before relying on reviewed-seed obligations.",
            )
        ]
    current_hash = _sha256_file(path)
    if not _hash_equal(current_hash, recorded_hash):
        return [
            _item(
                "gate_hash",
                "gate",
                "high",
                "hash_mismatch",
                "admin_reviewed_seed_gate_hash_mismatch",
                "Recorded reviewed-seed gate hash differs from the current gate artifact.",
                path=str(path),
                recorded_hash=recorded_hash,
                current_hash=current_hash,
                repair_command=command,
                manual_step="Re-run the gate and reviewed-seed decision flow; do not silently reuse the old seed.",
            )
        ]
    return []


def _profile_review_items(workspace: Path, recorded_hash: str | None) -> list[AdminReviewedSeedDriftItem]:
    path = workspace / "state" / "profile-review.json"
    command = f'python -m k_resdev_skill profile-review --root "{workspace}" --output "{workspace / "reports" / "profile-review.md"}" --json "{path}"'
    if not recorded_hash:
        return [
            _item(
                "profile_review_metadata",
                "profile_review",
                "medium",
                "metadata_missing",
                "admin_reviewed_seed_profile_review_hash_missing",
                "Reviewed-seed metadata has no recorded profile-review hash.",
                path=str(path),
                repair_command=command,
                manual_step="Refresh profile review and promotion evidence before relying on reviewed-seed obligations.",
            )
        ]
    if not path.exists():
        return [
            _item(
                "profile_review_missing",
                "profile_review",
                "high",
                "artifact_missing",
                "admin_reviewed_seed_profile_review_missing",
                "Recorded profile-review artifact is missing.",
                path=str(path),
                recorded_hash=recorded_hash,
                repair_command=command,
                manual_step="Restore or regenerate profile-review.json, then repeat promotion and gate review.",
            )
        ]
    current_hash = _sha256_file(path)
    if not _hash_equal(current_hash, recorded_hash):
        return [
            _item(
                "profile_review_hash",
                "profile_review",
                "high",
                "hash_mismatch",
                "admin_reviewed_seed_profile_review_hash_mismatch",
                "Current profile-review.json hash differs from the reviewed-seed metadata.",
                path=str(path),
                recorded_hash=recorded_hash,
                current_hash=current_hash,
                repair_command=command,
                manual_step="Re-run profile review, record/review promotion, rerun the admin profile-pack gate, then re-seed only after human approval.",
            )
        ]
    return []


def _profile_pack_items(workspace: Path, recorded_path: str | None, recorded_hash: str | None) -> list[AdminReviewedSeedDriftItem]:
    path = _resolve_path(workspace, recorded_path)
    command = f'python -m k_resdev_skill admin-profile-pack-review --profile "<profile-id>" --output "{workspace / "reports" / "admin-profile-pack.md"}" --json "{workspace / "state" / "admin-profile-pack-review.json"}"'
    if path is None or not recorded_hash:
        return [
            _item(
                "admin_profile_pack_metadata",
                "admin_profile_pack",
                "high",
                "metadata_missing",
                "admin_reviewed_seed_profile_pack_metadata_missing",
                "Reviewed-seed metadata is missing source pack path or hash.",
                path=str(workspace / "state" / "admin-obligations.json"),
                repair_command=command,
                manual_step="Review the admin profile pack and record fresh review receipts before any re-seed.",
            )
        ]
    if not path.exists():
        return [
            _item(
                "admin_profile_pack_missing",
                "admin_profile_pack",
                "high",
                "artifact_missing",
                "admin_reviewed_seed_profile_pack_missing",
                "Recorded admin profile-pack artifact is missing.",
                path=str(path),
                recorded_hash=recorded_hash,
                repair_command=command,
                manual_step="Restore the profile pack or rerun review against the current pack before re-seeding.",
            )
        ]
    current_hash = _sha256_file(path)
    if not _hash_equal(current_hash, recorded_hash):
        return [
            _item(
                "admin_profile_pack_hash",
                "admin_profile_pack",
                "high",
                "hash_mismatch",
                "admin_reviewed_seed_profile_pack_hash_mismatch",
                "Current admin profile-pack hash differs from the reviewed-seed metadata.",
                path=str(path),
                recorded_hash=recorded_hash,
                current_hash=current_hash,
                repair_command=command,
                manual_step="Human-review the changed pack, record fresh receipts, rerun the gate, and only then re-seed local obligations.",
            )
        ]
    return []


def _review_receipt_items(workspace: Path, profile_id: str | None, recorded_review_ids: list[str]) -> tuple[list[AdminReviewedSeedDriftItem], int]:
    command = f'python -m k_resdev_skill admin-profile-pack-review-summary --root "{workspace}" --profile "{profile_id or "<profile-id>"}" --output "{workspace / "reports" / "admin-profile-pack-review-summary.md"}" --json "{workspace / "state" / "admin-profile-pack-review-summary.json"}"'
    if not profile_id:
        return (
            [
                _item(
                    "review_receipt_profile_missing",
                    "review_receipt",
                    "medium",
                    "profile_missing",
                    "admin_reviewed_seed_profile_id_missing",
                    "Reviewed-seed metadata has no profile ID for receipt verification.",
                    path=str(workspace / "state" / "admin-obligations.json"),
                    repair_command=command,
                    manual_step="Set or restore profile metadata before relying on admin profile-pack review receipts.",
                )
            ],
            0,
        )
    try:
        summary = summarize_admin_profile_pack_reviews(workspace, profile_id)
    except Exception as exc:
        return (
            [
                _item(
                    "review_receipts_unreadable",
                    "review_receipt",
                    "medium",
                    "unreadable",
                    "admin_reviewed_seed_review_receipts_unreadable",
                    f"Admin profile-pack review receipt summary could not be read: {exc}",
                    path=str(workspace / "state" / "admin-profile-pack-reviews"),
                    repair_command=command,
                    manual_step="Fix receipt JSON files, then rerun the review summary before re-seeding.",
                )
            ],
            0,
        )

    current_ids = {record.review_id for record in summary.records}
    current_accepted_ids = {
        record.review_id
        for record in summary.records
        if summary.profile_pack_hash is not None
        and _hash_equal(record.profile_pack_hash, summary.profile_pack_hash)
        and record.decision in {"accepted", "accepted_risk"}
    }
    items: list[AdminReviewedSeedDriftItem] = []
    if not recorded_review_ids:
        items.append(
            _item(
                "review_receipts_missing_metadata",
                "review_receipt",
                "medium",
                "metadata_missing",
                "admin_reviewed_seed_review_receipts_missing",
                "Reviewed-seed metadata has no admin profile-pack review receipt IDs.",
                path=str(workspace / "state" / "admin-obligations.json"),
                repair_command=command,
                manual_step="Record hash-bound admin profile-pack review receipts and rerun the gate before relying on reviewed-seed obligations.",
            )
        )
    for review_id in recorded_review_ids:
        if review_id not in current_ids:
            items.append(
                _item(
                    f"review_receipt_missing_{_short_id(review_id)}",
                    "review_receipt",
                    "medium",
                    "receipt_missing",
                    "admin_reviewed_seed_review_receipt_missing",
                    f"Recorded admin profile-pack review receipt `{review_id}` is missing from the current workspace.",
                    path=str(workspace / "state" / "admin-profile-pack-reviews"),
                    review_id=review_id,
                    repair_command=command,
                    manual_step="Restore the receipt or record a fresh human review receipt before relying on the seed.",
                )
            )
        elif review_id not in current_accepted_ids:
            items.append(
                _item(
                    f"review_receipt_stale_{_short_id(review_id)}",
                    "review_receipt",
                    "high",
                    "receipt_stale",
                    "admin_reviewed_seed_review_receipt_stale",
                    f"Recorded admin profile-pack review receipt `{review_id}` is no longer current accepted evidence for the pack.",
                    path=str(workspace / "state" / "admin-profile-pack-reviews"),
                    review_id=review_id,
                    repair_command=command,
                    manual_step="Review the current admin profile pack and record a fresh accepted or accepted_risk receipt.",
                )
            )
    return items, len(current_accepted_ids)


def _finding_items(workspace: Path, existing_items: list[AdminReviewedSeedDriftItem], findings) -> list[AdminReviewedSeedDriftItem]:
    existing_codes = {item.finding_code for item in existing_items}
    items: list[AdminReviewedSeedDriftItem] = []
    for finding in findings:
        if finding.code not in REVIEWED_SEED_DRIFT_CODES or finding.code in existing_codes:
            continue
        items.append(
            _item(
                finding.code,
                "metadata",
                finding.severity,
                "review_needed",
                finding.code,
                finding.message,
                path=finding.path,
                repair_command=f'python -m k_resdev_skill admin-obligations-review --root "{workspace}" --output "{workspace / "reports" / "admin-obligations.md"}" --json "{workspace / "state" / "admin-obligations-review.json"}"',
                manual_step=finding.suggested_action or "Review the admin obligation graph before relying on reviewed-seed obligations.",
                related_findings=[finding.code],
            )
        )
    return items


def _item(
    drift_id: str,
    category: str,
    severity: str,
    status: str,
    finding_code: str,
    message: str,
    *,
    path: str | None = None,
    recorded_hash: str | None = None,
    current_hash: str | None = None,
    review_id: str | None = None,
    repair_command: str | None = None,
    manual_step: str,
    related_findings: list[str] | None = None,
) -> AdminReviewedSeedDriftItem:
    return AdminReviewedSeedDriftItem(
        drift_id=drift_id,
        category=category,
        severity=severity,
        status=status,
        finding_code=finding_code,
        message=message,
        path=path,
        recorded_hash=recorded_hash,
        current_hash=current_hash,
        review_id=review_id,
        repair_command=repair_command,
        manual_step=manual_step,
        related_findings=related_findings or [finding_code],
    )


def _write_outputs(result: AdminReviewedSeedDriftDashboardResult, output_path: str | Path | None, json_path: str | Path | None) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_admin_reviewed_seed_drift_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _resolve_path(workspace: Path, value: str | None) -> Path | None:
    if not value:
        return None
    raw = Path(value)
    if raw.is_absolute():
        return raw
    workspace_path = workspace / raw
    if workspace_path.exists():
        return workspace_path
    if raw.exists():
        return raw
    return workspace_path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _hash_equal(left: str | None, right: str | None) -> bool:
    return _normalize_hash(left) == _normalize_hash(right)


def _normalize_hash(value: str | None) -> str:
    if not value:
        return ""
    return value.removeprefix("sha256:").strip().lower()


def _dedupe_items(items: list[AdminReviewedSeedDriftItem]) -> list[AdminReviewedSeedDriftItem]:
    seen: set[tuple[str, str, str | None]] = set()
    result: list[AdminReviewedSeedDriftItem] = []
    for item in items:
        key = (item.finding_code, item.drift_id, item.review_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.category, item.drift_id))


def _severity_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(value, 3)


def _status(seed_mode: str | None, high_count: int, medium_count: int, has_items: bool) -> str:
    if seed_mode != "reviewed_seed":
        return "not_configured"
    if high_count:
        return "blocked"
    if medium_count:
        return "needs_review"
    if has_items:
        return "ready_with_notes"
    return "ready"


def _short_id(value: str) -> str:
    return "".join(character for character in value if character.isalnum())[:16] or "unknown"


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
