from __future__ import annotations

from pathlib import Path

from .models import (
    ProfilePackReadinessFinding,
    ProfilePackReadinessProfile,
    ProfilePackReadinessResult,
)
from .profile_lifecycle import generate_profile_lifecycle_ledger, load_profile_lifecycle_ledger
from .profile_promotion import summarize_profile_promotions
from .profile_promotion_apply import generate_profile_promotion_apply_plan, load_profile_promotion_apply_result
from .profile_promotion_revoke import load_profile_promotion_revoke_plan, load_profile_promotion_revoke_result
from .profile_registry import load_project_profile
from .profile_review import generate_profile_review
from .profile_source_fix_plan import generate_profile_source_fix_plan
from .profile_source_fix_review import summarize_profile_source_fix_reviews
from .profile_source_queue import generate_profile_source_queue
from .profile_sources import generate_profile_integrity


def generate_profile_pack_readiness(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfilePackReadinessResult:
    """Aggregate local profile/source operating signals into a scan-friendly readiness dashboard."""

    workspace = Path(root)
    warnings: list[str] = []
    findings: list[ProfilePackReadinessFinding] = []
    profile_ids: set[str] = set()
    profile_statuses: dict[str, str] = {}
    queue_counts: dict[str, int] = {}
    fix_action_counts: dict[str, int] = {}
    fix_review_record_counts: dict[str, int] = {}
    fix_review_unresolved_counts: dict[str, int] = {}

    profile = _load_profile(workspace, warnings)
    if profile is not None:
        profile_ids.add(profile.profile_id)
        profile_statuses[profile.profile_id] = profile.status

    queue = generate_profile_source_queue(workspace)
    for item in queue.items:
        profile_ids.add(item.profile_id)
        if item.profile_status:
            profile_statuses.setdefault(item.profile_id, item.profile_status)
        queue_counts[item.profile_id] = queue_counts.get(item.profile_id, 0) + 1
        findings.append(
            _finding(
                "profile_pack_source_queue_finding",
                item.severity,
                item.message,
                profile_id=item.profile_id,
                path=item.source_record_path or item.source_file or item.profile_path,
                suggested_action=item.suggested_action or "Review profile-source-queue before adding or promoting agency profile packs.",
            )
        )

    fix_plan = generate_profile_source_fix_plan(workspace)
    for action in fix_plan.actions:
        if action.profile_id:
            profile_ids.add(action.profile_id)
            fix_action_counts[action.profile_id] = fix_action_counts.get(action.profile_id, 0) + 1
            if action.severity in {"high", "medium"}:
                findings.append(
                    _finding(
                        "profile_pack_fix_action_open",
                        action.severity,
                        action.rationale,
                        profile_id=action.profile_id,
                        path=action.source_record_path or action.source_file,
                        suggested_action=action.manual_step or action.command or "Review profile-source-fix-plan before changing profile-source metadata.",
                    )
                )
    if fix_plan.status in {"missing_queue", "unreadable_queue"}:
        for profile_id in sorted(queue_counts):
            findings.append(
                _finding(
                    "profile_pack_fix_plan_missing",
                    "medium",
                    "Profile source queue items exist but no current fix-plan artifact is available.",
                    profile_id=profile_id,
                    path=fix_plan.queue_path,
                    suggested_action="Run profile-source-fix-plan before evaluating remediation readiness.",
                )
            )

    action_profile_by_id = {action.action_id: action.profile_id for action in fix_plan.actions if action.profile_id}
    fix_review = summarize_profile_source_fix_reviews(workspace)
    for record in fix_review.records:
        if record.profile_id:
            profile_ids.add(record.profile_id)
            fix_review_record_counts[record.profile_id] = fix_review_record_counts.get(record.profile_id, 0) + 1
    for finding in fix_review.findings:
        profile_id = None
        if finding.action_id:
            profile_id = action_profile_by_id.get(finding.action_id)
        if profile_id:
            profile_ids.add(profile_id)
            if finding.code in {"profile_source_fix_action_unreviewed", "profile_source_fix_action_deferred", "profile_source_fix_action_rejected"}:
                fix_review_unresolved_counts[profile_id] = fix_review_unresolved_counts.get(profile_id, 0) + 1
        findings.append(
            _finding(
                "profile_pack_fix_review_finding",
                finding.severity,
                finding.message,
                profile_id=profile_id,
                path=finding.path,
                suggested_action=finding.suggested_action or "Review profile-source-fix-summary before relying on profile remediation state.",
            )
        )

    integrity = generate_profile_integrity(workspace)
    if integrity.profile_id:
        profile_ids.add(integrity.profile_id)
        if integrity.profile_status:
            profile_statuses[integrity.profile_id] = integrity.profile_status
    for finding in integrity.findings:
        findings.append(
            _finding(
                "profile_pack_integrity_finding",
                finding.severity,
                finding.message,
                profile_id=integrity.profile_id,
                path=finding.path,
                suggested_action=finding.suggested_action or "Review profile-integrity before treating a profile pack as usable.",
            )
        )

    review = generate_profile_review(workspace)
    if review.profile_id:
        profile_ids.add(review.profile_id)
        if review.profile_status:
            profile_statuses[review.profile_id] = review.profile_status
    if review.status != "not_configured" and not review.can_promote:
        findings.append(
            _finding(
                "profile_pack_profile_review_not_ready",
                "high" if review.status == "blocked" else "medium",
                f"Profile review is `{review.status}` with {review.failed_count} failed check(s).",
                profile_id=review.profile_id,
                path=str(workspace / "state" / "profile-review.json"),
                suggested_action="Run profile-review and resolve source-backed promotion blockers.",
            )
        )

    promotion = summarize_profile_promotions(workspace)
    if promotion.profile_id:
        profile_ids.add(promotion.profile_id)
    if review.can_promote and promotion.status != "verified_recorded":
        findings.append(
            _finding(
                "profile_pack_promotion_record_missing",
                "medium",
                f"Profile review can promote, but promotion status is `{promotion.status}`.",
                profile_id=promotion.profile_id or review.profile_id,
                path=str(workspace / "state" / "profile-promotions"),
                suggested_action="Record a supplied profile-promotion decision before any guarded apply.",
            )
        )

    apply_plan = generate_profile_promotion_apply_plan(workspace)
    apply_result = _load_apply_result(workspace)
    if apply_plan.profile_id:
        profile_ids.add(apply_plan.profile_id)
    if apply_plan.can_apply and apply_result is None:
        findings.append(
            _finding(
                "profile_pack_promotion_apply_pending",
                "medium",
                "A profile promotion apply plan is ready, but no guarded apply result has been recorded.",
                profile_id=apply_plan.profile_id,
                path=str(workspace / "state" / "profile-promotion-apply-plan.json"),
                suggested_action="Run guarded profile-promotion-apply only after reviewing the apply-plan hash.",
            )
        )

    revoke_plan = _load_revoke_plan(workspace)
    revoke_result = _load_revoke_result(workspace)
    if revoke_plan and revoke_plan.profile_id:
        profile_ids.add(revoke_plan.profile_id)
    if revoke_plan and revoke_plan.can_revoke and revoke_result is None:
        findings.append(
            _finding(
                "profile_pack_revoke_pending",
                "medium",
                "A profile promotion revocation plan can revoke, but no guarded revoke result has been recorded.",
                profile_id=revoke_plan.profile_id,
                path=str(workspace / "state" / "profile-promotion-revoke-plan.json"),
                suggested_action="Run guarded profile-promotion-revoke only after reviewing the revoke-plan hash.",
            )
        )

    lifecycle = _load_or_generate_lifecycle(workspace)
    if lifecycle.profile_id:
        profile_ids.add(lifecycle.profile_id)
        if lifecycle.current_profile_status:
            profile_statuses[lifecycle.profile_id] = lifecycle.current_profile_status
    for finding in lifecycle.findings:
        findings.append(
            _finding(
                "profile_pack_lifecycle_finding",
                finding.severity,
                finding.message,
                profile_id=lifecycle.profile_id,
                path=finding.path,
                suggested_action=finding.suggested_action or "Review profile-lifecycle-ledger before changing profile pack state.",
            )
        )

    profiles = [
        _profile_summary(
            profile_id,
            profile_statuses.get(profile_id),
            findings,
            queue_counts.get(profile_id, 0),
            fix_action_counts.get(profile_id, 0),
            fix_review_record_counts.get(profile_id, 0),
            fix_review_unresolved_counts.get(profile_id, 0),
            review,
            promotion,
            apply_plan,
            apply_result,
            revoke_plan,
            revoke_result,
            lifecycle,
        )
        for profile_id in sorted(profile_ids)
    ]
    findings = sorted(findings, key=lambda item: (_severity_rank(item.severity), item.profile_id or "", item.code, item.message))
    result = ProfilePackReadinessResult(
        root=str(workspace),
        status=_status_from_findings(findings, profiles),
        profile_count=len(profiles),
        ready_count=sum(1 for item in profiles if item.status == "ready"),
        needs_review_count=sum(1 for item in profiles if item.status in {"needs_review", "ready_with_notes"}),
        blocked_count=sum(1 for item in profiles if item.status == "blocked"),
        profile_without_findings_count=sum(1 for item in profiles if item.finding_count == 0),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        profiles=profiles,
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=sorted(set(warnings + queue.warnings + fix_plan.warnings + fix_review.warnings + integrity.warnings + review.warnings + promotion.warnings + apply_plan.warnings + lifecycle.warnings)),
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_profile_pack_readiness(path: str | Path) -> ProfilePackReadinessResult:
    return ProfilePackReadinessResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_pack_readiness_markdown(result: ProfilePackReadinessResult) -> str:
    lines = [
        "# Profile Pack Readiness",
        "",
        "> Operating projection only. This dashboard summarizes local profile-source, review, promotion, apply/revoke, and lifecycle artifacts; it does not fetch official sources, mutate profile/source records, or certify agency compliance.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Profiles | {result.profile_count} |",
        f"| Ready | {result.ready_count} |",
        f"| Needs review | {result.needs_review_count} |",
        f"| Blocked | {result.blocked_count} |",
        f"| Profiles without findings | {result.profile_without_findings_count} |",
        f"| Findings | {result.finding_count} |",
        f"| High | {result.high_count} |",
        f"| Medium | {result.medium_count} |",
        f"| Low | {result.low_count} |",
        "",
        "## Profiles",
        "",
        "| Status | Profile | Profile Status | Queue | Fix Actions | Fix Reviews | Unresolved Fix Reviews | Promotion | Apply | Revoke | Lifecycle | Blockers |",
        "|---|---|---|---:|---:|---:|---:|---|---|---|---|---|",
    ]
    if not result.profiles:
        lines.append("| missing | - | - | 0 | 0 | 0 | 0 | - | - | - | - | profile_pack_missing |")
    for profile in result.profiles:
        lines.append(
            "| {status} | `{profile}` | {profile_status} | {queue} | {fix_actions} | {fix_reviews} | {unresolved} | {promotion} | {apply} | {revoke} | {lifecycle} | {blockers} |".format(
                status=_escape(profile.status),
                profile=_escape(profile.profile_id),
                profile_status=_escape(profile.profile_status or "-"),
                queue=profile.queue_item_count,
                fix_actions=profile.fix_action_count,
                fix_reviews=profile.fix_review_record_count,
                unresolved=profile.fix_review_unresolved_count,
                promotion=_escape(profile.promotion_status or "-"),
                apply=_escape(profile.apply_status or "-"),
                revoke=_escape(profile.revoke_status or "-"),
                lifecycle=_escape(profile.lifecycle_status or "-"),
                blockers=_escape(", ".join(profile.blockers) or "-"),
            )
        )
    lines.extend(["", "## Findings", "", "| Severity | Code | Profile | Message | Path | Suggested Action |", "|---|---|---|---|---|---|"])
    if not result.findings:
        lines.append("| ok | profile_pack_readiness_ready | - | No readiness findings detected. | - | Continue human review before official use. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {profile} | {message} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                profile=_escape(finding.profile_id or "-"),
                message=_escape(finding.message),
                path=_escape(finding.path or "-"),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Readiness is a local operating projection, not official compliance.",
            "- `accepted_risk` and `ready_with_notes` remain visible review states.",
            "- Official agency profile packs still require current source verification and supplied human decisions.",
            "",
        ]
    )
    return "\n".join(lines)


def _profile_summary(
    profile_id: str,
    profile_status: str | None,
    findings: list[ProfilePackReadinessFinding],
    queue_item_count: int,
    fix_action_count: int,
    fix_review_record_count: int,
    fix_review_unresolved_count: int,
    review,
    promotion,
    apply_plan,
    apply_result,
    revoke_plan,
    revoke_result,
    lifecycle,
) -> ProfilePackReadinessProfile:
    profile_findings = [finding for finding in findings if finding.profile_id == profile_id]
    high = sum(1 for finding in profile_findings if finding.severity == "high")
    medium = sum(1 for finding in profile_findings if finding.severity == "medium")
    low = sum(1 for finding in profile_findings if finding.severity == "low")
    status = "blocked" if high else "needs_review" if medium else "ready_with_notes" if low else "ready"
    blockers = sorted({finding.code for finding in profile_findings if finding.severity in {"high", "medium"}})
    applies_to_profile = _matches_profile(profile_id, getattr(apply_plan, "profile_id", None))
    return ProfilePackReadinessProfile(
        profile_id=profile_id,
        status=status,
        profile_status=profile_status,
        queue_item_count=queue_item_count,
        fix_action_count=fix_action_count,
        fix_review_record_count=fix_review_record_count,
        fix_review_unresolved_count=fix_review_unresolved_count,
        profile_review_status=review.status if _matches_profile(profile_id, review.profile_id) else None,
        profile_review_can_promote=review.can_promote if _matches_profile(profile_id, review.profile_id) else False,
        promotion_status=promotion.status if _matches_profile(profile_id, promotion.profile_id) else None,
        promotion_record_count=promotion.record_count if _matches_profile(profile_id, promotion.profile_id) else 0,
        latest_promotion_decision=promotion.latest_decision if _matches_profile(profile_id, promotion.profile_id) else None,
        apply_status=apply_plan.status if applies_to_profile else None,
        apply_can_apply=apply_plan.can_apply if applies_to_profile else False,
        apply_applied=apply_result.applied if apply_result is not None and _matches_profile(profile_id, apply_result.profile_id) else False,
        revoke_status=revoke_plan.status if revoke_plan is not None and _matches_profile(profile_id, revoke_plan.profile_id) else None,
        revoke_can_revoke=revoke_plan.can_revoke if revoke_plan is not None and _matches_profile(profile_id, revoke_plan.profile_id) else False,
        revoke_revoked=revoke_result.revoked if revoke_result is not None and _matches_profile(profile_id, revoke_result.profile_id) else False,
        lifecycle_status=lifecycle.status if _matches_profile(profile_id, lifecycle.profile_id) else None,
        finding_count=len(profile_findings),
        high_count=high,
        medium_count=medium,
        low_count=low,
        blockers=blockers,
    )


def _load_profile(workspace: Path, warnings: list[str]):
    path = workspace / "state" / "project-profile.json"
    if not path.exists():
        warnings.append("profile_missing")
        return None
    try:
        return load_project_profile(path)
    except Exception as exc:
        warnings.append(f"profile_unreadable:{exc}")
        return None


def _load_apply_result(workspace: Path):
    path = workspace / "state" / "profile-promotion-apply-result.json"
    if not path.exists():
        return None
    try:
        return load_profile_promotion_apply_result(path)
    except Exception:
        return None


def _load_revoke_plan(workspace: Path):
    path = workspace / "state" / "profile-promotion-revoke-plan.json"
    if not path.exists():
        return None
    try:
        return load_profile_promotion_revoke_plan(path)
    except Exception:
        return None


def _load_revoke_result(workspace: Path):
    path = workspace / "state" / "profile-promotion-revoke-result.json"
    if not path.exists():
        return None
    try:
        return load_profile_promotion_revoke_result(path)
    except Exception:
        return None


def _load_or_generate_lifecycle(workspace: Path):
    path = workspace / "state" / "profile-lifecycle-ledger.json"
    if path.exists():
        try:
            return load_profile_lifecycle_ledger(path)
        except Exception:
            pass
    return generate_profile_lifecycle_ledger(workspace)


def _finding(
    code: str,
    severity: str,
    message: str,
    profile_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> ProfilePackReadinessFinding:
    return ProfilePackReadinessFinding(
        code=code,
        severity=severity,
        message=message,
        profile_id=profile_id,
        path=str(path) if path else None,
        suggested_action=suggested_action,
    )


def _status_from_findings(findings: list[ProfilePackReadinessFinding], profiles: list[ProfilePackReadinessProfile]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    if not profiles:
        return "not_configured"
    return "ready"


def _write_outputs(
    result: ProfilePackReadinessResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_pack_readiness_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _matches_profile(profile_id: str, candidate: str | None) -> bool:
    return bool(candidate) and candidate == profile_id


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
