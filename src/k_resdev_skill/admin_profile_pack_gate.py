from __future__ import annotations

import hashlib
from pathlib import Path

from .admin_operating import review_admin_obligation_profile_pack
from .admin_profile_pack_reviews import summarize_admin_profile_pack_reviews
from .models import (
    AdminProfilePackPromotionGateCheck,
    AdminProfilePackPromotionGateResult,
    ProfileReviewResult,
)
from .profile_promotion import summarize_profile_promotions
from .profile_registry import load_project_profile
from .profile_review import generate_profile_review, load_profile_review


def generate_admin_profile_pack_promotion_gate(
    root: str | Path,
    profile_id: str | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    templates_root: str | Path | None = None,
) -> AdminProfilePackPromotionGateResult:
    """Generate a read-only reviewed-seed eligibility gate for admin profile packs."""

    workspace = Path(root)
    checks: list[AdminProfilePackPromotionGateCheck] = []
    warnings: list[str] = []
    workspace_profile_id = _workspace_profile_id(workspace, warnings)
    resolved_profile_id = profile_id or workspace_profile_id
    review_path = workspace / "state" / "profile-review.json"
    review_hash = f"sha256:{_sha256_file(review_path)}" if review_path.exists() else None

    if resolved_profile_id is None:
        checks.append(
            _check(
                "project_profile_present",
                "fail",
                "high",
                "No project profile was found, so no admin profile-pack gate can be evaluated.",
                workspace / "state" / "project-profile.json",
                "Run init-workspace or add state/project-profile.json before evaluating profile-pack seeding.",
            )
        )
        result = _result(
            workspace,
            "not_configured",
            False,
            None,
            None,
            None,
            review_path,
            review_hash,
            None,
            None,
            output_path,
            json_path,
            checks,
            warnings,
        )
        _write_outputs(result, output_path, json_path)
        return result

    if workspace_profile_id is not None and profile_id is not None and workspace_profile_id != profile_id:
        checks.append(
            _check(
                "requested_profile_matches_workspace",
                "fail",
                "high",
                f"Requested profile `{profile_id}` does not match workspace profile `{workspace_profile_id}`.",
                workspace / "state" / "project-profile.json",
                "Run the gate for the workspace profile or switch the workspace profile through the profile promotion flow.",
            )
        )
    else:
        checks.append(
            _check(
                "requested_profile_matches_workspace",
                "pass",
                "high",
                f"Gate profile `{resolved_profile_id}` matches the workspace profile context.",
                workspace / "state" / "project-profile.json",
            )
        )

    profile_review = generate_profile_review(workspace)
    profile_review_artifact = _load_profile_review_artifact(review_path, warnings)
    _append_profile_review_checks(checks, profile_review, profile_review_artifact, review_path)

    profile_promotion = summarize_profile_promotions(workspace)
    _append_profile_promotion_checks(checks, profile_promotion, review_path)

    try:
        admin_pack = review_admin_obligation_profile_pack(resolved_profile_id, templates_root=templates_root)
    except Exception as exc:
        warnings.append(f"admin_profile_pack_gate_pack_unreadable:{exc}")
        admin_pack = None
        checks.append(
            _check(
                "admin_profile_pack_readable",
                "fail",
                "high",
                f"Admin obligation profile pack could not be reviewed: {exc}",
                None,
                "Fix templates/agencies/<profile-id>/admin-obligations.json before evaluating reviewed-seed eligibility.",
            )
        )
    else:
        _append_admin_pack_checks(checks, admin_pack)

    try:
        admin_pack_review = summarize_admin_profile_pack_reviews(workspace, resolved_profile_id, templates_root=templates_root)
    except Exception as exc:
        warnings.append(f"admin_profile_pack_gate_reviews_unreadable:{exc}")
        admin_pack_review = None
        checks.append(
            _check(
                "admin_profile_pack_reviews_readable",
                "fail",
                "medium",
                f"Admin profile-pack human review summary could not be generated: {exc}",
                workspace / "state" / "admin-profile-pack-reviews",
                "Fix state/admin-profile-pack-reviews before evaluating reviewed-seed eligibility.",
            )
        )
    else:
        _append_admin_pack_review_checks(checks, admin_pack_review)

    can_use_reviewed_seed = _can_use_reviewed_seed(checks, profile_review, profile_promotion, admin_pack, admin_pack_review)
    status = _status_from_checks(checks, can_use_reviewed_seed, configured=True)
    result = _result(
        workspace,
        status,
        can_use_reviewed_seed,
        resolved_profile_id,
        profile_review,
        profile_promotion,
        review_path,
        review_hash,
        admin_pack,
        admin_pack_review,
        output_path,
        json_path,
        checks,
        warnings,
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_admin_profile_pack_promotion_gate(path: str | Path) -> AdminProfilePackPromotionGateResult:
    return AdminProfilePackPromotionGateResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_admin_profile_pack_promotion_gate_markdown(result: AdminProfilePackPromotionGateResult) -> str:
    lines = [
        "# Admin Profile Pack Promotion Gate",
        "",
        "> Read-only reviewed-seed gate. This checks local profile review, profile promotion, and admin profile-pack review receipts; it does not certify official agency rules, mutate templates, or create final submissions.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Can use reviewed seed | {result.can_use_reviewed_seed} |",
        f"| Profile | {_escape(result.profile_id or 'missing')} |",
        f"| Profile review | {_escape(result.profile_review_status or '-')} |",
        f"| Profile can promote | {result.profile_review_can_promote} |",
        f"| Profile review hash | `{_escape(result.profile_review_hash or '-')}` |",
        f"| Profile promotion | {_escape(result.profile_promotion_status or '-')} |",
        f"| Latest promotion decision | {_escape(result.latest_profile_promotion_decision or '-')} |",
        f"| Admin profile pack | {_escape(result.admin_profile_pack_status or '-')} |",
        f"| Admin profile pack human reviews | {_escape(result.admin_profile_pack_review_status or '-')} |",
        f"| Reviewed targets | {result.admin_profile_pack_reviewed_target_count}/{result.admin_profile_pack_review_target_count} |",
        f"| Human review records | {result.admin_profile_pack_review_record_count} |",
        f"| Checks | {result.check_count} |",
        f"| High issues | {result.high_count} |",
        f"| Medium issues | {result.medium_count} |",
        f"| Low notes | {result.low_count} |",
        "",
        "## Checks",
        "",
        "| Status | Severity | Check | Message | Path | Suggested Action |",
        "|---|---|---|---|---|---|",
    ]
    if not result.checks:
        lines.append("| fail | high | admin_profile_pack_gate_empty | No gate checks were generated. | - | Re-run admin-profile-pack-gate. |")
    for check in result.checks:
        lines.append(
            "| {status} | {severity} | {check} | {message} | {path} | {action} |".format(
                status=_escape(check.status),
                severity=_escape(check.severity),
                check=_escape(check.check_id),
                message=_escape(check.message),
                path=_escape(check.path or "-"),
                action=_escape(check.suggested_action or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- `can_use_reviewed_seed=true` means the local project has a current profile review, a hash-bound verified profile promotion record, and current hash-bound admin profile-pack review receipts.",
            "- It is still a local candidate state. Agency-specific official rules, IRIS/NTIS/RCMS/Ezbaro fields, and submission readiness remain human-reviewed and profile-driven.",
            "- The gate never changes `state/project-profile.json`, bundled templates, or local admin obligation files.",
            "",
        ]
    )
    return "\n".join(lines)


def _append_profile_review_checks(
    checks: list[AdminProfilePackPromotionGateCheck],
    current: ProfileReviewResult,
    artifact: ProfileReviewResult | None,
    review_path: Path,
) -> None:
    checks.append(
        _check(
            "profile_review_can_promote",
            "pass" if current.can_promote and current.status == "ready_for_human_promotion" else "fail",
            "medium",
            f"Computed profile review status is `{current.status}` with can_promote={current.can_promote}.",
            review_path,
            None if current.can_promote else "Resolve profile source review failures and regenerate profile-review.",
        )
    )
    if artifact is None:
        checks.append(
            _check(
                "profile_review_artifact_present",
                "fail",
                "medium",
                "No state/profile-review.json artifact is present for hash-bound promotion records.",
                review_path,
                "Run profile-review with --json state/profile-review.json before recording or evaluating promotion receipts.",
            )
        )
        return
    checks.append(
        _check(
            "profile_review_artifact_present",
            "pass",
            "medium",
            "A state/profile-review.json artifact is present for hash-bound promotion records.",
            review_path,
        )
    )
    current_signature = _profile_review_signature(current)
    artifact_signature = _profile_review_signature(artifact)
    checks.append(
        _check(
            "profile_review_artifact_matches_current",
            "pass" if current_signature == artifact_signature else "fail",
            "medium",
            "Profile review artifact matches current computed readiness fields." if current_signature == artifact_signature else "Profile review artifact appears stale against current computed readiness fields.",
            review_path,
            None if current_signature == artifact_signature else "Regenerate profile-review and record a fresh profile promotion decision.",
        )
    )


def _append_profile_promotion_checks(checks: list[AdminProfilePackPromotionGateCheck], promotion, review_path: Path) -> None:
    checks.append(
        _check(
            "profile_promotion_verified_current",
            "pass" if promotion.status == "verified_recorded" and promotion.latest_decision == "verified" else "fail",
            "medium",
            f"Profile promotion summary status is `{promotion.status}` with latest decision `{promotion.latest_decision or 'missing'}`.",
            review_path,
            None if promotion.status == "verified_recorded" else "Record a supplied verified profile promotion decision bound to the current profile-review hash.",
        )
    )
    if promotion.hash_mismatch_count:
        checks.append(
            _check(
                "profile_promotion_history_has_stale_hashes",
                "warn",
                "low",
                f"Profile promotion history includes {promotion.hash_mismatch_count} stale review-hash record(s).",
                review_path,
                "Keep stale historical receipts for audit context, but rely only on the latest current verified record.",
            )
        )


def _append_admin_pack_checks(checks: list[AdminProfilePackPromotionGateCheck], admin_pack) -> None:
    if admin_pack.status == "not_configured":
        checks.append(
            _check(
                "admin_profile_pack_configured",
                "fail",
                "high",
                "No admin obligation profile pack is configured for this profile.",
                admin_pack.pack_path,
                "Add templates/agencies/<profile-id>/admin-obligations.json as a needs-review profile pack.",
            )
        )
        return
    checks.append(
        _check(
            "admin_profile_pack_configured",
            "pass",
            "high",
            f"Admin obligation profile pack is configured with {admin_pack.obligation_count} obligation candidate(s).",
            admin_pack.pack_path,
        )
    )
    checks.append(
        _check(
            "admin_profile_pack_no_high_findings",
            "pass" if admin_pack.high_count == 0 else "fail",
            "high",
            f"Admin profile pack review has {admin_pack.high_count} high-severity finding(s).",
            admin_pack.pack_path,
            None if admin_pack.high_count == 0 else "Fix unreadable, missing, or structurally invalid admin profile-pack content before using it.",
        )
    )
    if admin_pack.medium_count or admin_pack.low_count:
        checks.append(
            _check(
                "admin_profile_pack_guarded_needs_review",
                "warn",
                "low",
                f"Admin profile pack remains guarded with {admin_pack.medium_count} medium and {admin_pack.low_count} low finding(s).",
                admin_pack.pack_path,
                "Keep generated obligations needs_review unless the local profile promotion and admin row-review receipts pass this gate.",
            )
        )


def _append_admin_pack_review_checks(checks: list[AdminProfilePackPromotionGateCheck], review) -> None:
    checks.append(
        _check(
            "admin_profile_pack_reviews_configured",
            "pass" if review.status != "not_configured" else "fail",
            "high",
            f"Admin profile-pack human review summary status is `{review.status}`.",
            review.profile_pack_path,
            None if review.status != "not_configured" else "Add an admin-obligations profile pack before recording row reviews.",
        )
    )
    checks.append(
        _check(
            "admin_profile_pack_reviews_current",
            "pass" if review.high_count == 0 and review.stale_record_count == 0 and review.target_mismatch_count == 0 else "fail",
            "high",
            f"Admin profile-pack review summary has {review.high_count} high finding(s), {review.stale_record_count} stale record(s), and {review.target_mismatch_count} target mismatch(es).",
            review.profile_pack_path,
            None if review.high_count == 0 and review.stale_record_count == 0 and review.target_mismatch_count == 0 else "Record fresh hash-bound admin profile-pack review decisions for the current pack.",
        )
    )
    checks.append(
        _check(
            "admin_profile_pack_reviews_resolved",
            "pass" if review.unresolved_count == 0 and review.medium_count == 0 else "fail",
            "medium",
            f"Admin profile-pack review summary has {review.unresolved_count} unresolved and {review.medium_count} medium finding(s).",
            review.profile_pack_path,
            None if review.unresolved_count == 0 and review.medium_count == 0 else "Resolve missing, deferred, rejected, or needs_changes admin profile-pack reviews.",
        )
    )
    coverage_ok = review.target_count > 0 and review.reviewed_target_count == review.target_count
    checks.append(
        _check(
            "admin_profile_pack_review_coverage_complete",
            "pass" if coverage_ok else "fail",
            "medium",
            f"Admin profile-pack reviewed targets are {review.reviewed_target_count}/{review.target_count}.",
            review.profile_pack_path,
            None if coverage_ok else "Record a pack-level accepted review or accepted row-level reviews for all targets.",
        )
    )
    if review.status == "ready_with_notes" or review.low_count:
        checks.append(
            _check(
                "admin_profile_pack_reviews_have_accepted_risk_notes",
                "warn",
                "low",
                f"Admin profile-pack review summary has {review.low_count} low-severity note(s).",
                review.profile_pack_path,
                "Carry accepted-risk notes into local admin obligation initialization and human review.",
            )
        )


def _can_use_reviewed_seed(checks, profile_review, profile_promotion, admin_pack, admin_pack_review) -> bool:
    if any(check.status == "fail" and check.severity in {"high", "medium"} for check in checks):
        return False
    if not (profile_review.can_promote and profile_review.status == "ready_for_human_promotion"):
        return False
    if not (profile_promotion.status == "verified_recorded" and profile_promotion.latest_decision == "verified"):
        return False
    if admin_pack is None or admin_pack.status == "not_configured" or admin_pack.high_count:
        return False
    if admin_pack_review is None or admin_pack_review.status not in {"ready", "ready_with_notes"}:
        return False
    return admin_pack_review.target_count > 0 and admin_pack_review.reviewed_target_count == admin_pack_review.target_count


def _result(
    workspace: Path,
    status: str,
    can_use_reviewed_seed: bool,
    profile_id: str | None,
    profile_review,
    profile_promotion,
    review_path: Path,
    review_hash: str | None,
    admin_pack,
    admin_pack_review,
    output_path: str | Path | None,
    json_path: str | Path | None,
    checks: list[AdminProfilePackPromotionGateCheck],
    warnings: list[str],
) -> AdminProfilePackPromotionGateResult:
    notable_checks = [check for check in checks if check.status != "pass"]
    return AdminProfilePackPromotionGateResult(
        root=str(workspace),
        status=status,
        can_use_reviewed_seed=can_use_reviewed_seed,
        profile_id=profile_id,
        profile_review_status=getattr(profile_review, "status", None),
        profile_review_can_promote=bool(getattr(profile_review, "can_promote", False)),
        profile_review_path=str(review_path),
        profile_review_hash=review_hash,
        profile_promotion_status=getattr(profile_promotion, "status", None),
        latest_profile_promotion_decision=getattr(profile_promotion, "latest_decision", None),
        latest_profile_promotion_id=getattr(profile_promotion, "latest_promotion_id", None),
        admin_profile_pack_status=getattr(admin_pack, "status", None),
        admin_profile_pack_path=getattr(admin_pack, "pack_path", None),
        admin_profile_pack_finding_count=int(getattr(admin_pack, "finding_count", 0) or 0),
        admin_profile_pack_review_status=getattr(admin_pack_review, "status", None),
        admin_profile_pack_review_target_count=int(getattr(admin_pack_review, "target_count", 0) or 0),
        admin_profile_pack_reviewed_target_count=int(getattr(admin_pack_review, "reviewed_target_count", 0) or 0),
        admin_profile_pack_review_record_count=int(getattr(admin_pack_review, "record_count", 0) or 0),
        high_count=sum(1 for check in notable_checks if check.severity == "high"),
        medium_count=sum(1 for check in notable_checks if check.severity == "medium"),
        low_count=sum(1 for check in notable_checks if check.severity == "low"),
        check_count=len(checks),
        checks=_dedupe_checks(checks),
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )


def _write_outputs(result: AdminProfilePackPromotionGateResult, output_path: str | Path | None, json_path: str | Path | None) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_admin_profile_pack_promotion_gate_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _status_from_checks(checks: list[AdminProfilePackPromotionGateCheck], can_use_reviewed_seed: bool, *, configured: bool) -> str:
    if not configured:
        return "not_configured"
    if any(check.status == "fail" and check.severity == "high" for check in checks):
        return "blocked"
    if any(check.status == "fail" and check.severity == "medium" for check in checks):
        return "needs_review"
    if not can_use_reviewed_seed:
        return "needs_review"
    if any(check.status != "pass" for check in checks):
        return "ready_with_notes"
    return "ready"


def _load_profile_review_artifact(path: Path, warnings: list[str]) -> ProfileReviewResult | None:
    if not path.exists():
        return None
    try:
        return load_profile_review(path)
    except Exception as exc:
        warnings.append(f"profile_review_artifact_unreadable:{exc}")
        return None


def _profile_review_signature(review: ProfileReviewResult) -> tuple[object, ...]:
    failed_ids = tuple(sorted(item.check_id for item in review.checklist if item.status == "fail"))
    return (
        review.profile_id,
        review.profile_status,
        review.status,
        review.can_promote,
        review.failed_count,
        review.source_count,
        review.verified_source_count,
        failed_ids,
    )


def _workspace_profile_id(workspace: Path, warnings: list[str]) -> str | None:
    path = workspace / "state" / "project-profile.json"
    if not path.exists():
        return None
    try:
        return load_project_profile(path).profile_id
    except Exception as exc:
        warnings.append(f"project_profile_unreadable:{exc}")
        return None


def _check(
    check_id: str,
    status: str,
    severity: str,
    message: str,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> AdminProfilePackPromotionGateCheck:
    return AdminProfilePackPromotionGateCheck(
        check_id=check_id,
        status=status,
        severity=severity,
        message=message,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _dedupe_checks(checks: list[AdminProfilePackPromotionGateCheck]) -> list[AdminProfilePackPromotionGateCheck]:
    seen: set[tuple[str, str, str]] = set()
    result: list[AdminProfilePackPromotionGateCheck] = []
    for check in checks:
        key = (check.check_id, check.status, check.message)
        if key in seen:
            continue
        seen.add(key)
        result.append(check)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), _status_rank(item.status), item.check_id))


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _status_rank(status: str) -> int:
    return {"fail": 0, "warn": 1, "pass": 2}.get(status, 3)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
