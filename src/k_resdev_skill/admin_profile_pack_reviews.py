from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .admin_operating import load_admin_obligation_profile_pack
from .models import (
    AdminObligationProfilePack,
    AdminProfilePackReviewDecision,
    AdminProfilePackReviewFinding,
    AdminProfilePackReviewRecord,
    AdminProfilePackReviewSummaryResult,
    AdminProfilePackReviewTargetType,
)
from .profile_registry import default_agency_templates_root


REVIEW_DECISIONS = {"accepted", "accepted_risk", "needs_changes", "rejected", "deferred"}
TARGET_TYPES = {"pack", "obligation", "submission", "settlement_requirement"}


def default_admin_profile_pack_reviews_dir(root: str | Path) -> Path:
    return Path(root) / "state" / "admin-profile-pack-reviews"


def create_admin_profile_pack_review_record(
    root: str | Path,
    profile_id: str,
    decision: str | AdminProfilePackReviewDecision,
    reviewer: str,
    profile_pack_hash: str,
    target_type: str | AdminProfilePackReviewTargetType = AdminProfilePackReviewTargetType.PACK,
    target_id: str | None = None,
    profile_pack_path: str | Path | None = None,
    templates_root: str | Path | None = None,
    reviewed_at: str | None = None,
    notes: str | None = None,
    risk_flags: list[str] | None = None,
) -> AdminProfilePackReviewRecord:
    """Create a supplied human review record bound to the current admin obligation profile-pack hash."""

    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer must not be blank")
    normalized_decision = _decision(decision)
    normalized_target_type = _target_type(target_type)
    pack_path = _profile_pack_path(profile_id, templates_root, profile_pack_path)
    if not pack_path.exists():
        raise ValueError(f"admin obligation profile pack not found: {pack_path}")
    actual_hash = _sha256_file(pack_path)
    if _normalize_hash(actual_hash) != _normalize_hash(profile_pack_hash):
        raise ValueError("profile_pack_hash does not match the current admin obligation profile pack")

    pack = load_admin_obligation_profile_pack(profile_id, templates_root=templates_root)
    normalized_target_id = _normalize_target_id(profile_id, normalized_target_type, target_id)
    _validate_target(pack, normalized_target_type, normalized_target_id)

    reviewed = reviewed_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    review_id = _review_id(profile_id, normalized_target_type, normalized_target_id, normalized_decision, reviewer.strip(), reviewed, actual_hash)
    return AdminProfilePackReviewRecord(
        review_id=review_id,
        profile_id=profile_id,
        target_type=normalized_target_type,
        target_id=normalized_target_id,
        profile_pack_path=str(pack_path),
        profile_pack_hash=actual_hash,
        decision=normalized_decision,
        reviewer=reviewer.strip(),
        reviewed_at=reviewed,
        source_record_ids=pack.source_record_ids,
        notes=notes,
        risk_flags=risk_flags or [],
    )


def write_admin_profile_pack_review_record(
    record: AdminProfilePackReviewRecord,
    reviews_dir: str | Path,
) -> Path:
    target_dir = Path(reviews_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{record.review_id}.json"
    target.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


def load_admin_profile_pack_review_records(path: str | Path) -> list[AdminProfilePackReviewRecord]:
    source = Path(path)
    if not source.exists():
        return []
    if source.is_dir():
        records: list[AdminProfilePackReviewRecord] = []
        for record_path in sorted(source.glob("*.json")):
            records.extend(load_admin_profile_pack_review_records(record_path))
        return records
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [AdminProfilePackReviewRecord.model_validate(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [AdminProfilePackReviewRecord.model_validate(item) for item in payload["records"]]
    return [AdminProfilePackReviewRecord.model_validate(payload)]


def summarize_admin_profile_pack_reviews(
    root: str | Path,
    profile_id: str,
    profile_pack_path: str | Path | None = None,
    templates_root: str | Path | None = None,
    reviews_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> AdminProfilePackReviewSummaryResult:
    """Compare supplied row-level admin profile-pack reviews against the current pack hash."""

    workspace = Path(root)
    pack_path = _profile_pack_path(profile_id, templates_root, profile_pack_path)
    source_dir = _resolve_workspace_path(workspace, reviews_dir) if reviews_dir is not None else default_admin_profile_pack_reviews_dir(workspace)
    findings: list[AdminProfilePackReviewFinding] = []
    warnings: list[str] = []
    records: list[AdminProfilePackReviewRecord] = []
    pack: AdminObligationProfilePack | None = None
    pack_hash: str | None = None
    targets: list[tuple[str, str]] = []

    if not pack_path.exists():
        result = _summary_result(workspace, profile_id, pack_path, "not_configured", None, None, None, targets, records, findings, warnings, output_path, json_path)
        _write_outputs(result, output_path, json_path)
        return result

    try:
        pack = load_admin_obligation_profile_pack(profile_id, templates_root=templates_root)
        pack_hash = _sha256_file(pack_path)
        targets = _pack_targets(profile_id, pack)
    except Exception as exc:
        findings.append(
            _finding(
                "admin_profile_pack_review_pack_unreadable",
                "high",
                f"Admin obligation profile pack could not be read: {exc}",
                profile_id=profile_id,
                path=pack_path,
                suggested_action="Fix templates/agencies/<profile-id>/admin-obligations.json before recording review receipts.",
            )
        )
        result = _summary_result(workspace, profile_id, pack_path, "blocked", pack_hash, None, None, targets, records, findings, warnings, output_path, json_path)
        _write_outputs(result, output_path, json_path)
        return result

    try:
        records = [record for record in load_admin_profile_pack_review_records(source_dir) if record.profile_id == profile_id]
    except Exception as exc:
        warnings.append(f"admin_profile_pack_reviews_unreadable:{exc}")
        findings.append(
            _finding(
                "admin_profile_pack_reviews_unreadable",
                "medium",
                f"Admin profile-pack review records could not be read: {exc}",
                profile_id=profile_id,
                path=source_dir,
                suggested_action="Fix state/admin-profile-pack-reviews before relying on admin profile-pack review state.",
            )
        )
        records = []

    if not records:
        findings.append(
            _finding(
                "admin_profile_pack_review_missing",
                "medium",
                f"Admin obligation profile pack `{profile_id}` has no supplied human review record.",
                profile_id=profile_id,
                target_type="pack",
                target_id=profile_id,
                path=source_dir,
                suggested_action="Run admin-profile-pack-review-record after a human reviews the pack or row candidates.",
            )
        )

    target_set = set(targets)
    valid_target_set = target_set | {("pack", profile_id)}
    for record in records:
        if pack_hash is not None and _normalize_hash(record.profile_pack_hash) != _normalize_hash(pack_hash):
            findings.append(
                _finding(
                    "admin_profile_pack_review_stale_hash",
                    "high",
                    f"Review `{record.review_id}` is bound to a stale admin profile-pack hash.",
                    review_id=record.review_id,
                    profile_id=profile_id,
                    target_type=str(record.target_type),
                    target_id=record.target_id,
                    path=record.profile_pack_path,
                    suggested_action="Review the current profile pack and record a fresh hash-bound decision.",
                )
            )
        record_key = _record_target_key(record)
        if record_key not in valid_target_set:
            findings.append(
                _finding(
                    "admin_profile_pack_review_target_missing",
                    "high",
                    f"Review `{record.review_id}` references missing target `{record.target_type}:{record.target_id}`.",
                    review_id=record.review_id,
                    profile_id=profile_id,
                    target_type=str(record.target_type),
                    target_id=record.target_id,
                    path=record.profile_pack_path,
                    suggested_action="Check whether the review belongs to an older pack or update the target ID.",
                )
            )

    current_hash_records = [record for record in records if pack_hash is not None and _normalize_hash(record.profile_pack_hash) == _normalize_hash(pack_hash)]
    latest_by_target = _latest_records_by_target(current_hash_records)
    for record in latest_by_target.values():
        if record.decision == "rejected":
            findings.append(
                _finding(
                    "admin_profile_pack_review_rejected",
                    "high",
                    f"Latest review `{record.review_id}` rejected `{record.target_type}:{record.target_id}`.",
                    review_id=record.review_id,
                    profile_id=profile_id,
                    target_type=str(record.target_type),
                    target_id=record.target_id,
                    path=record.profile_pack_path,
                    suggested_action="Do not promote or seed this admin profile-pack target until a new review supersedes it.",
                )
            )
        elif record.decision == "needs_changes":
            findings.append(
                _finding(
                    "admin_profile_pack_review_needs_changes",
                    "medium",
                    f"Latest review `{record.review_id}` says `{record.target_type}:{record.target_id}` needs changes.",
                    review_id=record.review_id,
                    profile_id=profile_id,
                    target_type=str(record.target_type),
                    target_id=record.target_id,
                    path=record.profile_pack_path,
                    suggested_action="Revise the profile-pack row and record a fresh human review.",
                )
            )
        elif record.decision == "deferred":
            findings.append(
                _finding(
                    "admin_profile_pack_review_deferred",
                    "medium",
                    f"Latest review `{record.review_id}` deferred `{record.target_type}:{record.target_id}`.",
                    review_id=record.review_id,
                    profile_id=profile_id,
                    target_type=str(record.target_type),
                    target_id=record.target_id,
                    path=record.profile_pack_path,
                    suggested_action="Keep the row as needs_review until the deferred review is resolved.",
                )
            )
        elif record.decision == "accepted_risk":
            findings.append(
                _finding(
                    "admin_profile_pack_review_accepted_risk",
                    "low",
                    f"Latest review `{record.review_id}` accepted `{record.target_type}:{record.target_id}` with risk.",
                    review_id=record.review_id,
                    profile_id=profile_id,
                    target_type=str(record.target_type),
                    target_id=record.target_id,
                    path=record.profile_pack_path,
                    suggested_action="Carry accepted-risk notes into profile promotion and local admin obligation review.",
                )
            )

    missing_targets = _missing_targets(target_set, latest_by_target)
    for target_type, target_id in missing_targets:
        findings.append(
            _finding(
                "admin_profile_pack_target_review_missing",
                "medium",
                f"Admin profile-pack target `{target_type}:{target_id}` has no current accepted human review.",
                profile_id=profile_id,
                target_type=target_type,
                target_id=target_id,
                path=pack_path,
                suggested_action="Record a pack-level accepted review or a row-level accepted/accepted-risk review for this target.",
            )
        )

    result = _summary_result(
        workspace,
        profile_id,
        pack_path,
        _status_from_findings(findings),
        pack_hash,
        pack.status if pack else None,
        pack.profile_status if pack else None,
        targets,
        records,
        findings,
        warnings,
        output_path,
        json_path,
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_admin_profile_pack_review_summary(path: str | Path) -> AdminProfilePackReviewSummaryResult:
    return AdminProfilePackReviewSummaryResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_admin_profile_pack_review_summary_markdown(result: AdminProfilePackReviewSummaryResult) -> str:
    lines = [
        "# Admin Profile Pack Review Summary",
        "",
        "> Supplied human review receipt log only. This records row-level admin profile-pack review metadata; it does not certify official compliance, mutate profile packs, or create final submissions.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Profile | {_escape(result.profile_id)} |",
        f"| Profile status | {_escape(result.profile_status or '-')} |",
        f"| Profile pack path | `{_escape(result.profile_pack_path)}` |",
        f"| Profile pack hash | `{_escape(result.profile_pack_hash or '-')}` |",
        f"| Profile pack status | {_escape(result.profile_pack_status or '-')} |",
        f"| Targets | {result.target_count} |",
        f"| Reviewed targets | {result.reviewed_target_count} |",
        f"| Missing target reviews | {result.missing_target_review_count} |",
        f"| Records | {result.record_count} |",
        f"| Accepted | {result.accepted_count} |",
        f"| Accepted risk | {result.accepted_risk_count} |",
        f"| Needs changes | {result.needs_changes_count} |",
        f"| Rejected | {result.rejected_count} |",
        f"| Deferred | {result.deferred_count} |",
        f"| Unresolved | {result.unresolved_count} |",
        f"| Stale records | {result.stale_record_count} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Review | Target | Message | Suggested Action |",
        "|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | admin_profile_pack_reviews_ready | - | - | No admin profile-pack review findings detected. | Keep reviews current with pack hashes. |")
    for finding in result.findings:
        target = f"{finding.target_type or '-'}:{finding.target_id or '-'}"
        lines.append(
            "| {severity} | {code} | {review} | {target} | {message} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                review=_escape(finding.review_id or "-"),
                target=_escape(target),
                message=_escape(finding.message),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Records",
            "",
            "| Decision | Review | Target | Reviewer | Reviewed At | Pack Hash | Risk Flags | Notes |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    if not result.records:
        lines.append("| missing | - | - | - | - | - | admin_profile_pack_review_missing | Record supplied human review decisions. |")
    for record in sorted(result.records, key=lambda item: (item.profile_id, str(item.target_type), item.target_id or "", item.reviewed_at, item.review_id)):
        target = f"{record.target_type}:{record.target_id or '-'}"
        lines.append(
            "| {decision} | `{review}` | {target} | {reviewer} | {reviewed} | `{pack_hash}` | {risks} | {notes} |".format(
                decision=_escape(str(record.decision)),
                review=_escape(record.review_id),
                target=_escape(target),
                reviewer=_escape(record.reviewer),
                reviewed=_escape(record.reviewed_at),
                pack_hash=_escape(record.profile_pack_hash),
                risks=_escape(", ".join(record.risk_flags) or "-"),
                notes=_escape(record.notes or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Review records are supplied human decisions bound to the current admin profile-pack hash.",
            "- A pack-level `accepted` or `accepted_risk` review covers all current row targets; otherwise each row needs a current accepted row-level review.",
            "- Review records do not mark an agency rule official and do not change profile status by themselves.",
            "",
        ]
    )
    return "\n".join(lines)


def _summary_result(
    workspace: Path,
    profile_id: str,
    pack_path: Path,
    status: str,
    pack_hash: str | None,
    pack_status: str | None,
    profile_status: str | None,
    targets: list[tuple[str, str]],
    records: list[AdminProfilePackReviewRecord],
    findings: list[AdminProfilePackReviewFinding],
    warnings: list[str],
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> AdminProfilePackReviewSummaryResult:
    findings = _dedupe_findings(findings)
    decision_counts = _decision_counts(records)
    current_hash_records = [record for record in records if pack_hash is not None and _normalize_hash(record.profile_pack_hash) == _normalize_hash(pack_hash)]
    latest_by_target = _latest_records_by_target(current_hash_records)
    reviewed_target_count = len(set(targets) - set(_missing_targets(set(targets), latest_by_target))) if targets else 0
    return AdminProfilePackReviewSummaryResult(
        root=str(workspace),
        status=status,
        profile_id=profile_id,
        profile_status=profile_status,
        profile_pack_path=str(pack_path),
        profile_pack_hash=pack_hash,
        profile_pack_status=pack_status,
        target_count=len(targets),
        reviewed_target_count=reviewed_target_count,
        missing_target_review_count=sum(1 for finding in findings if finding.code == "admin_profile_pack_target_review_missing"),
        record_count=len(records),
        accepted_count=decision_counts.get("accepted", 0),
        accepted_risk_count=decision_counts.get("accepted_risk", 0),
        needs_changes_count=decision_counts.get("needs_changes", 0),
        rejected_count=decision_counts.get("rejected", 0),
        deferred_count=decision_counts.get("deferred", 0),
        unresolved_count=sum(1 for finding in findings if finding.code in {"admin_profile_pack_review_missing", "admin_profile_pack_target_review_missing", "admin_profile_pack_review_needs_changes", "admin_profile_pack_review_rejected", "admin_profile_pack_review_deferred"}),
        stale_record_count=sum(1 for finding in findings if finding.code == "admin_profile_pack_review_stale_hash"),
        target_mismatch_count=sum(1 for finding in findings if finding.code == "admin_profile_pack_review_target_missing"),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        records=sorted(records, key=lambda item: (item.profile_id, str(item.target_type), item.target_id or "", item.reviewed_at, item.review_id)),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )


def _write_outputs(
    result: AdminProfilePackReviewSummaryResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_admin_profile_pack_review_summary_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _pack_targets(profile_id: str, pack: AdminObligationProfilePack) -> list[tuple[str, str]]:
    targets = [("obligation", item.obligation_id) for item in pack.obligations]
    targets.extend(("submission", item.submission_id) for item in pack.submissions)
    targets.extend(("settlement_requirement", item.requirement_id) for item in pack.settlement_requirements)
    if not targets:
        targets.append(("pack", profile_id))
    return sorted(set(targets))


def _missing_targets(targets: set[tuple[str, str]], latest_by_target: dict[tuple[str, str], AdminProfilePackReviewRecord]) -> list[tuple[str, str]]:
    if any(key[0] == "pack" and record.decision in {"accepted", "accepted_risk"} for key, record in latest_by_target.items()):
        return []
    missing: list[tuple[str, str]] = []
    for target in sorted(targets):
        record = latest_by_target.get(target)
        if record is None or record.decision not in {"accepted", "accepted_risk"}:
            missing.append(target)
    return missing


def _latest_records_by_target(records: list[AdminProfilePackReviewRecord]) -> dict[tuple[str, str], AdminProfilePackReviewRecord]:
    latest: dict[tuple[str, str], AdminProfilePackReviewRecord] = {}
    for record in sorted(records, key=lambda item: (item.reviewed_at, item.review_id)):
        latest[_record_target_key(record)] = record
    return latest


def _record_target_key(record: AdminProfilePackReviewRecord) -> tuple[str, str]:
    return str(record.target_type), record.target_id or record.profile_id


def _validate_target(pack: AdminObligationProfilePack, target_type: str, target_id: str) -> None:
    if target_type == "pack":
        return
    targets = set(_pack_targets(pack.profile_id, pack))
    if (target_type, target_id) not in targets:
        raise ValueError(f"target not found in admin profile pack: {target_type}:{target_id}")


def _normalize_target_id(profile_id: str, target_type: str, target_id: str | None) -> str:
    if target_type == "pack":
        return target_id or profile_id
    if not target_id or not target_id.strip():
        raise ValueError("target_id is required for row-level admin profile-pack reviews")
    return target_id.strip()


def _profile_pack_path(profile_id: str, templates_root: str | Path | None, profile_pack_path: str | Path | None) -> Path:
    if profile_pack_path is not None:
        return Path(profile_pack_path)
    root = Path(templates_root) if templates_root is not None else default_agency_templates_root()
    return root / profile_id / "admin-obligations.json"


def _decision(value: str | AdminProfilePackReviewDecision) -> str:
    decision = str(getattr(value, "value", value)).strip()
    if decision not in REVIEW_DECISIONS:
        raise ValueError(f"Unsupported admin profile-pack review decision: {decision}")
    return decision


def _target_type(value: str | AdminProfilePackReviewTargetType) -> str:
    target_type = str(getattr(value, "value", value)).strip()
    if target_type not in TARGET_TYPES:
        raise ValueError(f"Unsupported admin profile-pack review target type: {target_type}")
    return target_type


def _decision_counts(records: list[AdminProfilePackReviewRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        key = str(record.decision)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _finding(
    code: str,
    severity: str,
    message: str,
    review_id: str | None = None,
    profile_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> AdminProfilePackReviewFinding:
    return AdminProfilePackReviewFinding(
        code=code,
        severity=severity,
        message=message,
        review_id=review_id,
        profile_id=profile_id,
        target_type=target_type,
        target_id=target_id,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _status_from_findings(findings: list[AdminProfilePackReviewFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    return "ready"


def _dedupe_findings(findings: list[AdminProfilePackReviewFinding]) -> list[AdminProfilePackReviewFinding]:
    seen: set[tuple[str, str, str | None, str | None, str | None]] = set()
    result: list[AdminProfilePackReviewFinding] = []
    for finding in findings:
        key = (finding.code, finding.message, finding.review_id, finding.target_type, finding.target_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.code, item.message))


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _resolve_workspace_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else workspace / candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _normalize_hash(value: str) -> str:
    return value.replace("sha256:", "").strip().lower()


def _review_id(profile_id: str, target_type: str, target_id: str, decision: str, reviewer: str, reviewed_at: str, pack_hash: str) -> str:
    digest = hashlib.sha256("|".join([profile_id, target_type, target_id, decision, reviewer, reviewed_at, pack_hash]).encode("utf-8")).hexdigest()[:10].upper()
    year = reviewed_at[:4] if reviewed_at[:4].isdigit() else datetime.now(UTC).strftime("%Y")
    return f"APRV-{year}-{digest}"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
