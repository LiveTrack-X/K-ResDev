from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .models import (
    ProfileSourceFixReviewDecision,
    ProfileSourceFixReviewFinding,
    ProfileSourceFixReviewRecord,
    ProfileSourceFixReviewSummaryResult,
)
from .profile_source_fix_plan import load_profile_source_fix_plan


REVIEW_DECISIONS = {"resolved", "accepted_risk", "deferred", "rejected"}


def default_profile_source_fix_reviews_dir(root: str | Path) -> Path:
    return Path(root) / "state" / "profile-source-fix-reviews"


def create_profile_source_fix_review_record(
    root: str | Path,
    action_id: str,
    decision: str | ProfileSourceFixReviewDecision,
    reviewer: str,
    fix_plan_hash: str,
    fix_plan_path: str | Path | None = None,
    reviewed_at: str | None = None,
    notes: str | None = None,
    risk_flags: list[str] | None = None,
) -> ProfileSourceFixReviewRecord:
    """Create a supplied human review record for one profile-source fix-plan action."""

    workspace = Path(root)
    plan_path = _resolve_workspace_path(workspace, fix_plan_path or workspace / "state" / "profile-source-fix-plan.json")
    if not plan_path.exists():
        raise ValueError(f"profile source fix plan not found: {plan_path}")
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer must not be blank")

    normalized_decision = _decision(decision)
    plan = load_profile_source_fix_plan(plan_path)
    actual_hash = _sha256_file(plan_path)
    expected_hash = _normalize_hash(fix_plan_hash)
    if _normalize_hash(actual_hash) != expected_hash:
        raise ValueError("fix_plan_hash does not match the current profile source fix plan")

    action = next((item for item in plan.actions if item.action_id == action_id), None)
    if action is None:
        raise ValueError(f"action_id not found in profile source fix plan: {action_id}")

    reviewed = reviewed_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    review_id = _review_id(action_id, normalized_decision, reviewer.strip(), reviewed, actual_hash)
    return ProfileSourceFixReviewRecord(
        review_id=review_id,
        action_id=action_id,
        decision=normalized_decision,
        reviewer=reviewer.strip(),
        reviewed_at=reviewed,
        fix_plan_path=str(plan_path),
        fix_plan_hash=actual_hash,
        fix_plan_status=plan.status,
        action_issue_code=action.issue_code,
        action_severity=action.severity,
        profile_id=action.profile_id,
        source_id=action.source_id,
        notes=notes,
        risk_flags=risk_flags or [],
    )


def write_profile_source_fix_review_record(
    record: ProfileSourceFixReviewRecord,
    reviews_dir: str | Path,
) -> Path:
    target_dir = Path(reviews_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{record.review_id}.json"
    target.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


def load_profile_source_fix_review_records(path: str | Path) -> list[ProfileSourceFixReviewRecord]:
    source = Path(path)
    if not source.exists():
        return []
    if source.is_dir():
        records: list[ProfileSourceFixReviewRecord] = []
        for record_path in sorted(source.glob("*.json")):
            records.extend(load_profile_source_fix_review_records(record_path))
        return records
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [ProfileSourceFixReviewRecord.model_validate(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [ProfileSourceFixReviewRecord.model_validate(item) for item in payload["items"]]
    return [ProfileSourceFixReviewRecord.model_validate(payload)]


def summarize_profile_source_fix_reviews(
    root: str | Path,
    fix_plan_path: str | Path | None = None,
    reviews_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfileSourceFixReviewSummaryResult:
    """Compare supplied profile-source fix review records against the current fix plan."""

    workspace = Path(root)
    plan_path = _resolve_workspace_path(workspace, fix_plan_path or workspace / "state" / "profile-source-fix-plan.json")
    source_dir = _resolve_workspace_path(workspace, reviews_dir) if reviews_dir is not None else default_profile_source_fix_reviews_dir(workspace)
    warnings: list[str] = []
    findings: list[ProfileSourceFixReviewFinding] = []
    records: list[ProfileSourceFixReviewRecord] = []
    plan_hash: str | None = None
    plan_status: str | None = None
    action_count = 0

    if not plan_path.exists():
        findings.append(
            _finding(
                "profile_source_fix_plan_missing",
                "medium",
                "Profile source fix plan is missing.",
                path=plan_path,
                suggested_action="Run profile-source-fix-plan before recording fix-action review decisions.",
            )
        )
        result = _summary_result(workspace, plan_path, "not_configured", plan_hash, plan_status, action_count, records, findings, warnings, output_path, json_path)
        _write_outputs(result, output_path, json_path)
        return result

    try:
        plan = load_profile_source_fix_plan(plan_path)
        plan_hash = _sha256_file(plan_path)
        plan_status = plan.status
        action_count = plan.action_count
    except Exception as exc:
        findings.append(
            _finding(
                "profile_source_fix_plan_unreadable",
                "high",
                f"Profile source fix plan could not be read: {exc}",
                path=plan_path,
                suggested_action="Regenerate profile-source-fix-plan before relying on fix review records.",
            )
        )
        result = _summary_result(workspace, plan_path, "blocked", plan_hash, plan_status, action_count, records, findings, warnings, output_path, json_path)
        _write_outputs(result, output_path, json_path)
        return result

    try:
        records = load_profile_source_fix_review_records(source_dir)
    except Exception as exc:
        warnings.append(f"profile_source_fix_reviews_unreadable:{exc}")
        findings.append(
            _finding(
                "profile_source_fix_reviews_unreadable",
                "medium",
                f"Profile source fix review records could not be read: {exc}",
                path=source_dir,
                suggested_action="Fix state/profile-source-fix-reviews before relying on remediation review state.",
            )
        )
        records = []

    action_by_id = {action.action_id: action for action in plan.actions}
    latest_by_action = _latest_records(records)
    stale_count = 0
    missing_action_count = 0

    for record in records:
        if plan_hash is not None and _normalize_hash(record.fix_plan_hash) != _normalize_hash(plan_hash):
            stale_count += 1
            findings.append(
                _finding(
                    "profile_source_fix_review_stale_plan_hash",
                    "high",
                    f"Review record `{record.review_id}` is bound to a stale fix-plan hash.",
                    action_id=record.action_id,
                    review_id=record.review_id,
                    path=record.fix_plan_path,
                    suggested_action="Regenerate profile-source-fix-plan and record a new supplied human decision if the action still applies.",
                )
            )
        if record.action_id not in action_by_id:
            missing_action_count += 1
            findings.append(
                _finding(
                    "profile_source_fix_review_action_missing",
                    "high",
                    f"Review record `{record.review_id}` references action `{record.action_id}`, which is not in the current fix plan.",
                    action_id=record.action_id,
                    review_id=record.review_id,
                    path=record.fix_plan_path,
                    suggested_action="Check whether the action was removed, superseded, or needs a new review record.",
                )
            )

    for action in plan.actions:
        latest = latest_by_action.get(action.action_id)
        if latest is None:
            findings.append(
                _finding(
                    "profile_source_fix_action_unreviewed",
                    action.severity,
                    f"Fix-plan action `{action.action_id}` has no supplied human review record.",
                    action_id=action.action_id,
                    path=action.source_record_path or action.source_file,
                    suggested_action="Record a supplied profile-source-fix-record decision for this action.",
                )
            )
            continue
        if latest.decision in {"deferred", "rejected"}:
            findings.append(
                _finding(
                    f"profile_source_fix_action_{latest.decision}",
                    action.severity,
                    f"Fix-plan action `{action.action_id}` latest decision is `{latest.decision}`.",
                    action_id=action.action_id,
                    review_id=latest.review_id,
                    path=latest.fix_plan_path,
                    suggested_action="Resolve the action or keep the profile/source state in needs_review.",
                )
            )
        elif latest.decision == "accepted_risk":
            severity = "medium" if action.severity == "high" else "low"
            findings.append(
                _finding(
                    "profile_source_fix_action_accepted_risk",
                    severity,
                    f"Fix-plan action `{action.action_id}` was accepted as a known risk.",
                    action_id=action.action_id,
                    review_id=latest.review_id,
                    path=latest.fix_plan_path,
                    suggested_action="Keep the accepted risk visible in review packs and avoid treating it as agency compliance proof.",
                )
            )

    result = _summary_result(
        workspace,
        plan_path,
        _status_from_findings(findings),
        plan_hash,
        plan_status,
        action_count,
        records,
        findings,
        warnings,
        output_path,
        json_path,
        stale_count=stale_count,
        missing_action_count=missing_action_count,
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_profile_source_fix_review_summary(path: str | Path) -> ProfileSourceFixReviewSummaryResult:
    return ProfileSourceFixReviewSummaryResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_source_fix_review_summary_markdown(result: ProfileSourceFixReviewSummaryResult) -> str:
    lines = [
        "# Profile Source Fix Review Summary",
        "",
        "> Human decision log only. This summarizes supplied reviews for profile-source fix-plan actions; it does not mutate source metadata, fetch official documents, or mark sources/profiles verified.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Fix plan | `{_escape(result.fix_plan_path)}` |",
        f"| Fix plan hash | {_escape(result.fix_plan_hash or '-')} |",
        f"| Fix plan status | {_escape(result.fix_plan_status or '-')} |",
        f"| Actions | {result.action_count} |",
        f"| Records | {result.record_count} |",
        f"| Resolved | {result.resolved_count} |",
        f"| Accepted risk | {result.accepted_risk_count} |",
        f"| Deferred | {result.deferred_count} |",
        f"| Rejected | {result.rejected_count} |",
        f"| Unresolved | {result.unresolved_count} |",
        f"| High unresolved | {result.high_unresolved_count} |",
        f"| Stale records | {result.stale_record_count} |",
        f"| Missing action records | {result.missing_action_count} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Action | Review | Message | Suggested Action |",
        "|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | profile_source_fix_reviews_ready | - | - | No profile-source fix review findings detected. | Keep review records current with the fix plan hash. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {action} | {review} | {message} | {suggested} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                action=_escape(finding.action_id or "-"),
                review=_escape(finding.review_id or "-"),
                message=_escape(finding.message),
                suggested=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Records",
            "",
            "| Decision | Review | Action | Reviewer | Reviewed At | Plan Hash | Profile | Source | Risk Flags | Notes |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if not result.records:
        lines.append("| missing | - | - | - | - | - | - | - | profile_source_fix_review_missing | Record supplied human decisions for fix-plan actions. |")
    for record in sorted(result.records, key=lambda item: (item.action_id, item.reviewed_at, item.review_id)):
        lines.append(
            "| {decision} | `{review}` | `{action}` | {reviewer} | {reviewed} | `{plan_hash}` | {profile} | {source} | {risks} | {notes} |".format(
                decision=_escape(str(record.decision)),
                review=_escape(record.review_id),
                action=_escape(record.action_id),
                reviewer=_escape(record.reviewer),
                reviewed=_escape(record.reviewed_at),
                plan_hash=_escape(record.fix_plan_hash),
                profile=_escape(record.profile_id or "-"),
                source=_escape(record.source_id or "-"),
                risks=_escape(", ".join(record.risk_flags) or "-"),
                notes=_escape(record.notes or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Review records document supplied human decisions only.",
            "- A `resolved` record does not edit `state/profile-sources.json` or prove agency compliance.",
            "- `accepted_risk` keeps risk visible rather than converting it into verified source state.",
            "",
        ]
    )
    return "\n".join(lines)


def _summary_result(
    workspace: Path,
    plan_path: Path,
    status: str,
    plan_hash: str | None,
    plan_status: str | None,
    action_count: int,
    records: list[ProfileSourceFixReviewRecord],
    findings: list[ProfileSourceFixReviewFinding],
    warnings: list[str],
    output_path: str | Path | None,
    json_path: str | Path | None,
    stale_count: int = 0,
    missing_action_count: int = 0,
) -> ProfileSourceFixReviewSummaryResult:
    decision_counts = _decision_counts(records)
    unresolved_count = sum(1 for finding in findings if finding.code in {"profile_source_fix_action_unreviewed", "profile_source_fix_action_deferred", "profile_source_fix_action_rejected"})
    high_unresolved_count = sum(
        1
        for finding in findings
        if finding.severity == "high" and finding.code in {"profile_source_fix_action_unreviewed", "profile_source_fix_action_deferred", "profile_source_fix_action_rejected"}
    )
    return ProfileSourceFixReviewSummaryResult(
        root=str(workspace),
        status=status,
        fix_plan_path=str(plan_path),
        fix_plan_hash=plan_hash,
        fix_plan_status=plan_status,
        action_count=action_count,
        record_count=len(records),
        resolved_count=decision_counts.get("resolved", 0),
        accepted_risk_count=decision_counts.get("accepted_risk", 0),
        deferred_count=decision_counts.get("deferred", 0),
        rejected_count=decision_counts.get("rejected", 0),
        unresolved_count=unresolved_count,
        high_unresolved_count=high_unresolved_count,
        stale_record_count=stale_count,
        missing_action_count=missing_action_count,
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        records=sorted(records, key=lambda item: (item.action_id, item.reviewed_at, item.review_id)),
        findings=sorted(findings, key=lambda item: (_severity_rank(item.severity), item.action_id or "", item.code)),
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=sorted(set(warnings)),
    )


def _write_outputs(
    result: ProfileSourceFixReviewSummaryResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_source_fix_review_summary_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _latest_records(records: list[ProfileSourceFixReviewRecord]) -> dict[str, ProfileSourceFixReviewRecord]:
    latest: dict[str, ProfileSourceFixReviewRecord] = {}
    for record in sorted(records, key=lambda item: (item.action_id, item.reviewed_at, item.review_id)):
        latest[record.action_id] = record
    return latest


def _decision_counts(records: list[ProfileSourceFixReviewRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in _latest_records(records).values():
        counts[str(record.decision)] = counts.get(str(record.decision), 0) + 1
    return counts


def _status_from_findings(findings: list[ProfileSourceFixReviewFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.code == "profile_source_fix_action_accepted_risk" for finding in findings):
        return "ready_with_accepted_risk" if not any(finding.severity == "medium" for finding in findings) else "needs_review"
    if findings:
        return "needs_review"
    return "ready"


def _finding(
    code: str,
    severity: str,
    message: str,
    action_id: str | None = None,
    review_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> ProfileSourceFixReviewFinding:
    return ProfileSourceFixReviewFinding(
        code=code,
        severity=severity,
        message=message,
        action_id=action_id,
        review_id=review_id,
        path=str(path) if path else None,
        suggested_action=suggested_action,
    )


def _decision(value: str | ProfileSourceFixReviewDecision) -> str:
    decision = ProfileSourceFixReviewDecision(value).value if isinstance(value, ProfileSourceFixReviewDecision) else str(value).strip()
    if decision not in REVIEW_DECISIONS:
        raise ValueError(f"unknown profile source fix review decision: {value}")
    return decision


def _resolve_workspace_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else workspace / candidate


def _review_id(action_id: str, decision: str, reviewer: str, reviewed_at: str, plan_hash: str) -> str:
    digest = hashlib.sha256(f"{action_id}|{decision}|{reviewer}|{reviewed_at}|{plan_hash}".encode("utf-8")).hexdigest()
    year = reviewed_at[:4] if reviewed_at[:4].isdigit() else datetime.now(UTC).strftime("%Y")
    return f"PSFR-{year}-{digest[:8].upper()}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _normalize_hash(value: str) -> str:
    text = value.strip().lower()
    return text.split(":", 1)[1] if text.startswith("sha256:") else text


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
