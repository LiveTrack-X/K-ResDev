from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import (
    ProfileLifecycleLedgerEntry,
    ProfileLifecycleLedgerFinding,
    ProfileLifecycleLedgerResult,
    ProfilePromotionApplyPlanResult,
    ProfilePromotionApplyResult,
    ProfilePromotionRecord,
    ProfilePromotionRevocationPlanResult,
    ProfilePromotionRevocationResult,
    ProfileReviewResult,
    ProjectProfile,
)
from .profile_registry import load_project_profile


def generate_profile_lifecycle_ledger(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfileLifecycleLedgerResult:
    """Render a local audit-friendly ledger for profile review, promotion, apply, and revoke artifacts."""

    workspace = Path(root)
    entries: list[ProfileLifecycleLedgerEntry] = []
    findings: list[ProfileLifecycleLedgerFinding] = []
    warnings: list[str] = []

    profile_path = workspace / "state" / "project-profile.json"
    if not _has_lifecycle_artifacts(workspace):
        result = ProfileLifecycleLedgerResult(
            root=str(workspace),
            status="not_configured",
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
        )
        _write_outputs(result, output_path, json_path)
        return result

    profile = _load_profile(workspace, findings)
    if profile is not None:
        entries.append(
            _entry(
                "current_profile",
                profile.profile_id,
                profile.status,
                profile_path,
                profile_id=profile.profile_id,
                notes=profile.notes,
            )
        )

    review = _load_model(
        workspace / "state" / "profile-review.json",
        ProfileReviewResult,
        findings,
        "profile_lifecycle_review_unreadable",
        "Profile review could not be read.",
    )
    if review is not None:
        entries.append(
            _entry(
                "profile_review",
                "profile-review",
                review.status,
                workspace / "state" / "profile-review.json",
                profile_id=review.profile_id,
                notes=f"can_promote={review.can_promote}; failed_count={review.failed_count}",
                warnings=review.warnings,
            )
        )

    for record, record_path in _load_promotion_records(workspace, findings):
        entries.append(
            _entry(
                "profile_promotion",
                record.promotion_id,
                record.decision,
                record_path,
                occurred_at=record.reviewed_at,
                profile_id=record.profile_id,
                promotion_id=record.promotion_id,
                reviewer=record.reviewer,
                decision=record.decision,
                related_paths=[record.profile_review_path],
                notes=record.notes,
                warnings=record.risk_flags,
            )
        )

    apply_plan_path = workspace / "state" / "profile-promotion-apply-plan.json"
    apply_plan = _load_model(
        apply_plan_path,
        ProfilePromotionApplyPlanResult,
        findings,
        "profile_lifecycle_apply_plan_unreadable",
        "Profile promotion apply plan could not be read.",
    )
    if apply_plan is not None:
        entries.append(
            _entry(
                "profile_promotion_apply_plan",
                "profile-promotion-apply-plan",
                apply_plan.status,
                apply_plan_path,
                occurred_at=apply_plan.reviewed_at,
                profile_id=apply_plan.profile_id,
                promotion_id=apply_plan.promotion_id,
                reviewer=apply_plan.reviewer,
                decision=apply_plan.promotion_decision,
                related_paths=[apply_plan.profile_review_path],
                notes=f"can_apply={apply_plan.can_apply}; change_count={apply_plan.change_count}",
                warnings=apply_plan.warnings,
            )
        )

    apply_result_path = workspace / "state" / "profile-promotion-apply-result.json"
    apply_result = _load_model(
        apply_result_path,
        ProfilePromotionApplyResult,
        findings,
        "profile_lifecycle_apply_result_unreadable",
        "Profile promotion apply result could not be read.",
    )
    if apply_result is not None:
        entries.append(
            _entry(
                "profile_promotion_apply_result",
                "profile-promotion-apply-result",
                apply_result.status,
                apply_result_path,
                occurred_at=apply_result.applied_at,
                profile_id=apply_result.profile_id,
                promotion_id=apply_result.promotion_id,
                reviewer=apply_result.reviewer,
                backup_path=apply_result.backup_path,
                related_paths=[apply_result.apply_plan_path, apply_result.backup_path],
                notes=f"applied={apply_result.applied}; fields={','.join(apply_result.applied_fields) or '-'}",
                warnings=apply_result.warnings,
            )
        )

    revoke_plan_path = workspace / "state" / "profile-promotion-revoke-plan.json"
    revoke_plan = _load_model(
        revoke_plan_path,
        ProfilePromotionRevocationPlanResult,
        findings,
        "profile_lifecycle_revoke_plan_unreadable",
        "Profile promotion revoke plan could not be read.",
    )
    if revoke_plan is not None:
        entries.append(
            _entry(
                "profile_promotion_revoke_plan",
                "profile-promotion-revoke-plan",
                revoke_plan.status,
                revoke_plan_path,
                occurred_at=revoke_plan.requested_at,
                profile_id=revoke_plan.profile_id,
                promotion_id=revoke_plan.promotion_id,
                reviewer=revoke_plan.reviewer,
                backup_path=revoke_plan.backup_path,
                related_paths=[revoke_plan.apply_result_path, revoke_plan.backup_path],
                notes=f"can_revoke={revoke_plan.can_revoke}; reason={revoke_plan.reason}; change_count={revoke_plan.change_count}",
                warnings=revoke_plan.warnings,
            )
        )

    revoke_result_path = workspace / "state" / "profile-promotion-revoke-result.json"
    revoke_result = _load_model(
        revoke_result_path,
        ProfilePromotionRevocationResult,
        findings,
        "profile_lifecycle_revoke_result_unreadable",
        "Profile promotion revoke result could not be read.",
    )
    if revoke_result is not None:
        entries.append(
            _entry(
                "profile_promotion_revoke_result",
                "profile-promotion-revoke-result",
                revoke_result.status,
                revoke_result_path,
                occurred_at=revoke_result.revoked_at,
                profile_id=revoke_result.profile_id,
                promotion_id=revoke_result.promotion_id,
                reviewer=revoke_result.reviewer,
                backup_path=revoke_result.pre_revoke_backup_path,
                related_paths=[revoke_result.revoke_plan_path, revoke_result.apply_result_path, revoke_result.restore_backup_path],
                notes=f"revoked={revoke_result.revoked}; fields={','.join(revoke_result.revoked_fields) or '-'}",
                warnings=revoke_result.warnings,
            )
        )

    _integrity_findings(workspace, profile, apply_result, revoke_plan, revoke_result, findings)

    entries = sorted(entries, key=lambda item: (item.occurred_at or "", item.entry_type, item.entry_id))
    findings = _dedupe_findings(findings)
    result = ProfileLifecycleLedgerResult(
        root=str(workspace),
        status=_status_from_findings(findings),
        profile_id=profile.profile_id if profile else None,
        current_profile_status=profile.status if profile else None,
        entry_count=len(entries),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        entries=entries,
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=sorted(set(warnings)),
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_profile_lifecycle_ledger(path: str | Path) -> ProfileLifecycleLedgerResult:
    return ProfileLifecycleLedgerResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_lifecycle_ledger_markdown(result: ProfileLifecycleLedgerResult) -> str:
    lines = [
        "# Profile Lifecycle Ledger",
        "",
        "> Operating projection only. This ledger summarizes local profile review, human promotion records, guarded apply artifacts, and guarded revoke artifacts; it does not certify official agency compliance or erase audit history.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Profile | {_escape(result.profile_id or 'missing')} |",
        f"| Current profile status | {_escape(result.current_profile_status or 'missing')} |",
        f"| Entries | {result.entry_count} |",
        f"| Findings | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Message | Path | Suggested Action |",
        "|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | profile_lifecycle_ready | No profile lifecycle findings detected. | - | Continue human review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {message} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                message=_escape(finding.message),
                path=_escape(finding.path or "-"),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Entries",
            "",
            "| Time | Type | Status | Profile | Promotion | Reviewer | Artifact | Backup | Related | Notes | Warnings |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if not result.entries:
        lines.append("| - | - | No profile lifecycle artifacts found. | - | - | - | - | - | - | - | - |")
    for entry in result.entries:
        lines.append(
            "| {time} | {kind} | {status} | {profile} | {promotion} | {reviewer} | {artifact} | {backup} | {related} | {notes} | {warnings} |".format(
                time=_escape(entry.occurred_at or "-"),
                kind=_escape(entry.entry_type),
                status=_escape(entry.status),
                profile=_escape(entry.profile_id or "-"),
                promotion=_escape(entry.promotion_id or "-"),
                reviewer=_escape(entry.reviewer or "-"),
                artifact=_path_cell(entry.artifact_path),
                backup=_path_cell(entry.backup_path),
                related=_format_paths(entry.related_paths),
                notes=_escape(entry.notes or "-"),
                warnings=_escape(", ".join(entry.warnings) or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This command reads local artifacts and writes a projection ledger only.",
            "- Use guarded apply/revoke commands for profile mutations; do not manually edit official-status fields without preserving the lifecycle trail.",
            "- Keep agency profile packs in `needs_review` until official-source metadata and supplied human decisions support promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_outputs(
    result: ProfileLifecycleLedgerResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_lifecycle_ledger_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _has_lifecycle_artifacts(workspace: Path) -> bool:
    paths = [
        workspace / "state" / "project-profile.json",
        workspace / "state" / "profile-review.json",
        workspace / "state" / "profile-promotion-apply-plan.json",
        workspace / "state" / "profile-promotion-apply-result.json",
        workspace / "state" / "profile-promotion-revoke-plan.json",
        workspace / "state" / "profile-promotion-revoke-result.json",
    ]
    promotions = workspace / "state" / "profile-promotions"
    return any(path.exists() for path in paths) or (promotions.exists() and any(promotions.glob("*.json")))


def _load_profile(workspace: Path, findings: list[ProfileLifecycleLedgerFinding]) -> ProjectProfile | None:
    path = workspace / "state" / "project-profile.json"
    if not path.exists():
        return None
    try:
        return load_project_profile(path)
    except Exception as exc:
        findings.append(
            _finding(
                "profile_lifecycle_profile_unreadable",
                "medium",
                f"Project profile could not be read: {exc}",
                path,
                "Fix state/project-profile.json before relying on profile lifecycle status.",
            )
        )
        return None


def _load_model(
    path: Path,
    model_cls,
    findings: list[ProfileLifecycleLedgerFinding],
    code: str,
    message: str,
):
    if not path.exists():
        return None
    try:
        return model_cls.model_validate_json(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        findings.append(_finding(code, "medium", f"{message} {exc}", path, "Regenerate or repair the lifecycle artifact."))
        return None


def _load_promotion_records(
    workspace: Path,
    findings: list[ProfileLifecycleLedgerFinding],
) -> list[tuple[ProfilePromotionRecord, Path]]:
    promotions = workspace / "state" / "profile-promotions"
    if not promotions.exists():
        return []
    paths = sorted(promotions.glob("*.json")) if promotions.is_dir() else [promotions]
    records: list[tuple[ProfilePromotionRecord, Path]] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(payload, list):
                records.extend((ProfilePromotionRecord.model_validate(item), path) for item in payload)
            elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
                records.extend((ProfilePromotionRecord.model_validate(item), path) for item in payload["items"])
            else:
                records.append((ProfilePromotionRecord.model_validate(payload), path))
        except Exception as exc:
            findings.append(
                _finding(
                    "profile_lifecycle_promotion_record_unreadable",
                    "medium",
                    f"Profile promotion record could not be read: {exc}",
                    path,
                    "Fix state/profile-promotions before relying on profile lifecycle history.",
                )
            )
    return records


def _integrity_findings(
    workspace: Path,
    profile: ProjectProfile | None,
    apply_result: ProfilePromotionApplyResult | None,
    revoke_plan: ProfilePromotionRevocationPlanResult | None,
    revoke_result: ProfilePromotionRevocationResult | None,
    findings: list[ProfileLifecycleLedgerFinding],
) -> None:
    profile_path = workspace / "state" / "project-profile.json"
    current_payload = profile.model_dump() if profile is not None else None
    current_matches_revoke = _profile_matches(current_payload, revoke_result.after_profile if revoke_result else None)

    if profile is not None and profile.status == "verified" and apply_result is None:
        findings.append(
            _finding(
                "profile_lifecycle_verified_without_apply_result",
                "high",
                "Current project profile is verified, but no guarded profile promotion apply result was found.",
                workspace / "state" / "profile-promotion-apply-result.json",
                "Restore the profile to needs_review or preserve the status change through profile-promotion-apply.",
            )
        )
    if apply_result is not None:
        if apply_result.backup_path and not _resolve_path(workspace, apply_result.backup_path).exists():
            findings.append(
                _finding(
                    "profile_lifecycle_apply_backup_missing",
                    "medium",
                    "Profile promotion apply result refers to a missing profile backup.",
                    apply_result.backup_path,
                    "Restore the apply backup artifact or review version control before relying on rollback instructions.",
                )
            )
        if current_payload is not None and apply_result.after_profile and not current_matches_revoke:
            if not _profile_matches(current_payload, apply_result.after_profile):
                findings.append(
                    _finding(
                        "profile_lifecycle_apply_result_drift",
                        "high",
                        "Current project profile no longer matches the saved apply result and no later revoke result explains the state.",
                        profile_path,
                        "Regenerate lifecycle artifacts or inspect manual profile edits before relying on the profile status.",
                    )
                )
    if revoke_plan is not None and revoke_result is None and revoke_plan.status == "ready_to_revoke" and revoke_plan.can_revoke:
        findings.append(
            _finding(
                "profile_lifecycle_revoke_pending",
                "medium",
                "A profile promotion revocation plan is ready, but the guarded revoke command has not been run.",
                workspace / "state" / "profile-promotion-revoke-result.json",
                "Run profile-promotion-revoke with the revoke-plan hash or leave the applied profile state unchanged.",
            )
        )
    if revoke_result is not None:
        if revoke_result.pre_revoke_backup_path and not _resolve_path(workspace, revoke_result.pre_revoke_backup_path).exists():
            findings.append(
                _finding(
                    "profile_lifecycle_revoke_pre_backup_missing",
                    "medium",
                    "Profile promotion revoke result refers to a missing pre-revoke backup.",
                    revoke_result.pre_revoke_backup_path,
                    "Restore the pre-revoke backup artifact or review version control before relying on rollback instructions.",
                )
            )
        if revoke_result.restore_backup_path and not _resolve_path(workspace, revoke_result.restore_backup_path).exists():
            findings.append(
                _finding(
                    "profile_lifecycle_revoke_restore_backup_missing",
                    "medium",
                    "Profile promotion revoke result refers to a missing original restore backup.",
                    revoke_result.restore_backup_path,
                    "Restore the original profile backup artifact or review version control before relying on lifecycle history.",
                )
            )
        if current_payload is not None and revoke_result.after_profile:
            if not _profile_matches(current_payload, revoke_result.after_profile):
                findings.append(
                    _finding(
                        "profile_lifecycle_revoke_result_drift",
                        "high",
                        "Current project profile no longer matches the saved revoke result.",
                        profile_path,
                        "Inspect profile changes before relying on reverted profile status.",
                    )
                )


def _profile_matches(current: dict[str, Any] | None, expected: dict[str, Any] | None) -> bool:
    if current is None or not expected:
        return False
    try:
        return ProjectProfile.model_validate(current).model_dump() == ProjectProfile.model_validate(expected).model_dump()
    except Exception:
        return current == expected


def _entry(
    entry_type: str,
    key: str | None,
    status: str,
    artifact_path: str | Path,
    occurred_at: str | None = None,
    profile_id: str | None = None,
    promotion_id: str | None = None,
    reviewer: str | None = None,
    decision: str | None = None,
    backup_path: str | None = None,
    related_paths: list[str | None] | None = None,
    notes: str | None = None,
    warnings: list[str] | None = None,
) -> ProfileLifecycleLedgerEntry:
    path = Path(artifact_path)
    clean_related = [str(path) for path in (related_paths or []) if path]
    return ProfileLifecycleLedgerEntry(
        entry_id=_entry_id(entry_type, key or str(path)),
        entry_type=entry_type,
        status=status,
        artifact_path=str(path),
        artifact_hash=_sha256_file(path) if path.exists() else None,
        occurred_at=occurred_at,
        profile_id=profile_id,
        promotion_id=promotion_id,
        reviewer=reviewer,
        decision=decision,
        backup_path=backup_path,
        related_paths=clean_related,
        notes=notes,
        warnings=warnings or [],
    )


def _entry_id(entry_type: str, key: str) -> str:
    digest = hashlib.sha256(f"{entry_type}|{key}".encode("utf-8")).hexdigest()
    return f"PLC-{digest[:12].upper()}"


def _finding(
    code: str,
    severity: str,
    message: str,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> ProfileLifecycleLedgerFinding:
    return ProfileLifecycleLedgerFinding(
        code=code,
        severity=severity,
        message=message,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _dedupe_findings(findings: list[ProfileLifecycleLedgerFinding]) -> list[ProfileLifecycleLedgerFinding]:
    deduped: dict[tuple[str, str | None, str], ProfileLifecycleLedgerFinding] = {}
    for finding in findings:
        deduped[(finding.code, finding.path, finding.message)] = finding
    return sorted(deduped.values(), key=lambda item: (item.severity, item.code, item.path or ""))


def _status_from_findings(findings: list[ProfileLifecycleLedgerFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if any(finding.severity == "low" for finding in findings):
        return "ready_with_notes"
    return "ready"


def _resolve_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    workspace_candidate = workspace / candidate
    if workspace_candidate.exists() or not candidate.exists():
        return workspace_candidate
    return candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _path_cell(path: str | None) -> str:
    return f"`{_escape(path)}`" if path else "-"


def _format_paths(paths: list[str]) -> str:
    if not paths:
        return "-"
    return "<br>".join(f"`{_escape(path)}`" for path in paths)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
