from __future__ import annotations

import json
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .models import ProfilePromotionApplyChange, ProfilePromotionApplyPlanResult, ProfilePromotionApplyResult, ProjectProfile
from .profile_promotion import latest_profile_promotion, summarize_profile_promotions
from .profile_registry import load_project_profile


def generate_profile_promotion_apply_plan(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfilePromotionApplyPlanResult:
    """Generate a non-destructive plan for applying a supplied profile promotion decision."""

    workspace = Path(root)
    profile_path = workspace / "state" / "project-profile.json"
    profile: ProjectProfile | None = None
    warnings: list[str] = []

    if profile_path.exists():
        try:
            profile = load_project_profile(profile_path)
        except Exception as exc:
            warnings.append(f"profile_unreadable:{exc}")
    else:
        warnings.append("profile_missing")

    promotion_summary = summarize_profile_promotions(workspace)
    latest = latest_profile_promotion(promotion_summary.records, promotion_summary.profile_id)
    changes: list[ProfilePromotionApplyChange] = []
    proposed_profile = profile.model_dump() if profile is not None else {}
    status = "blocked"
    can_apply = False

    if profile is None:
        status = "missing_profile"
    elif promotion_summary.status != "verified_recorded" or latest is None:
        status = _blocked_status(promotion_summary.status, latest.decision if latest else None)
        warnings.append(f"profile_promotion_not_current:{promotion_summary.status}")
    elif profile.profile_id != latest.profile_id:
        status = "profile_mismatch"
        warnings.append(f"profile_id_mismatch:{profile.profile_id}:{latest.profile_id}")
    elif profile.status == "verified":
        status = "already_applied"
        proposed_profile["status"] = "verified"
    else:
        status = "ready_to_apply"
        can_apply = True
        proposed_profile["status"] = "verified"
        changes.append(
            ProfilePromotionApplyChange(
                field="status",
                before=profile.status,
                after="verified",
                rationale=f"Latest supplied profile promotion record `{latest.promotion_id}` is verified and bound to the current profile-review hash.",
            )
        )
        proposed_notes = _promoted_notes(profile.notes, latest.promotion_id, latest.reviewer, latest.reviewed_at, latest.profile_review_hash)
        if proposed_notes != profile.notes:
            proposed_profile["notes"] = proposed_notes
            changes.append(
                ProfilePromotionApplyChange(
                    field="notes",
                    before=profile.notes,
                    after=proposed_notes,
                    rationale="Record reviewer, review hash, and rollback context inside the profile notes field if a human later chooses to apply this plan.",
                )
            )

    result = ProfilePromotionApplyPlanResult(
        root=str(workspace),
        status=status,
        can_apply=can_apply,
        profile_id=profile.profile_id if profile else promotion_summary.profile_id,
        profile_path=str(profile_path),
        current_profile_status=profile.status if profile else None,
        proposed_profile_status=str(proposed_profile.get("status")) if proposed_profile else None,
        profile_review_path=str(workspace / "state" / "profile-review.json"),
        profile_review_hash=promotion_summary.current_profile_review_hash,
        promotion_id=latest.promotion_id if latest else None,
        promotion_decision=latest.decision if latest else None,
        reviewer=latest.reviewer if latest else None,
        reviewed_at=latest.reviewed_at if latest else None,
        rollback_note=_rollback_note(profile, latest.promotion_id if latest else None) if profile else None,
        change_count=len(changes),
        changes=changes,
        proposed_profile=proposed_profile,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=warnings,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_promotion_apply_plan_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_profile_promotion_apply_plan_markdown(result: ProfilePromotionApplyPlanResult) -> str:
    lines = [
        "# Profile Promotion Apply Plan",
        "",
        "> Proposal only. This file shows what a human-controlled profile status change would do; it does not mutate `state/project-profile.json` or certify agency compliance.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Can apply | {result.can_apply} |",
        f"| Profile | {_escape(result.profile_id or 'missing')} |",
        f"| Current profile status | {_escape(result.current_profile_status or 'missing')} |",
        f"| Proposed profile status | {_escape(result.proposed_profile_status or 'missing')} |",
        f"| Promotion record | {_escape(result.promotion_id or '-')} |",
        f"| Promotion decision | {_escape(result.promotion_decision or '-')} |",
        f"| Reviewer | {_escape(result.reviewer or '-')} |",
        f"| Reviewed at | {_escape(result.reviewed_at or '-')} |",
        f"| Profile-review hash | {_escape(result.profile_review_hash or '-')} |",
        f"| Change count | {result.change_count} |",
        "",
        "## Proposed Changes",
        "",
        "| Field | Before | After | Rationale |",
        "|---|---|---|---|",
    ]
    if not result.changes:
        lines.append("| - | - | - | No profile field change is proposed. |")
    for change in result.changes:
        lines.append(
            "| {field} | {before} | {after} | {rationale} |".format(
                field=_escape(change.field),
                before=_escape(_display(change.before)),
                after=_escape(_display(change.after)),
                rationale=_escape(change.rationale),
            )
        )
    lines.extend(
        [
            "",
            "## Rollback Note",
            "",
            _escape(result.rollback_note or "No rollback note is available because no current profile was loaded."),
            "",
            "## Proposed Profile",
            "",
            "```json",
            json.dumps(result.proposed_profile, indent=2, ensure_ascii=False),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def apply_profile_promotion_plan(
    root: str | Path,
    apply_plan_path: str | Path,
    apply_plan_hash: str,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    backup_dir: str | Path | None = None,
    applied_at: str | None = None,
) -> ProfilePromotionApplyResult:
    """Apply a current hash-matched profile promotion plan with a backup."""

    workspace = Path(root)
    plan_path = _resolve_workspace_path(workspace, apply_plan_path)
    actual_hash = _sha256_file(plan_path)
    expected_hash = _normalize_hash(apply_plan_hash)
    if actual_hash != expected_hash:
        raise ValueError("apply_plan_hash does not match the current profile promotion apply plan")

    plan = ProfilePromotionApplyPlanResult.model_validate_json(plan_path.read_text(encoding="utf-8-sig"))
    if not plan.can_apply or plan.status != "ready_to_apply":
        raise ValueError("profile promotion apply plan is not ready_to_apply")
    if not plan.profile_id:
        raise ValueError("profile promotion apply plan does not identify a profile_id")

    profile_path = workspace / "state" / "project-profile.json"
    profile = load_project_profile(profile_path)
    before = profile.model_dump()
    if profile.profile_id != plan.profile_id:
        raise ValueError("project profile_id does not match the apply plan")

    after = dict(before)
    applied_fields: list[str] = []
    allowed_fields = set(ProjectProfile.model_fields)
    for change in plan.changes:
        if change.field not in allowed_fields:
            raise ValueError(f"apply plan contains unsupported profile field: {change.field}")
        if change.field not in plan.proposed_profile:
            raise ValueError(f"apply plan proposed_profile is missing field: {change.field}")
        current_value = before.get(change.field)
        if current_value != change.before:
            raise ValueError(f"profile field `{change.field}` no longer matches the apply plan before value")
        proposed_value = plan.proposed_profile[change.field]
        if proposed_value != change.after:
            raise ValueError(f"apply plan change after value does not match proposed_profile for field: {change.field}")
        after[change.field] = proposed_value
        applied_fields.append(change.field)

    validated_after = ProjectProfile.model_validate(after).model_dump()
    timestamp = applied_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    target_backup_dir = _backup_dir(workspace, backup_dir)
    target_backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = target_backup_dir / f"project-profile-{_safe_timestamp(timestamp)}-{actual_hash[:8]}.json"
    backup_path.write_text(json.dumps(before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    profile_path.write_text(json.dumps(validated_after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = ProfilePromotionApplyResult(
        root=str(workspace),
        status="applied",
        applied=True,
        profile_id=plan.profile_id,
        profile_path=str(profile_path),
        backup_path=str(backup_path),
        apply_plan_path=str(plan_path),
        apply_plan_hash=f"sha256:{actual_hash}",
        promotion_id=plan.promotion_id,
        reviewer=plan.reviewer,
        reviewed_at=plan.reviewed_at,
        applied_at=timestamp,
        applied_fields=applied_fields,
        before_profile=before,
        after_profile=validated_after,
        rollback_note=_applied_rollback_note(backup_path),
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_promotion_apply_result_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def load_profile_promotion_apply_result(path: str | Path) -> ProfilePromotionApplyResult:
    return ProfilePromotionApplyResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_promotion_apply_result_markdown(result: ProfilePromotionApplyResult) -> str:
    lines = [
        "# Profile Promotion Apply Result",
        "",
        "> Guarded local mutation record only. This records a hash-matched profile promotion apply operation; it does not certify agency compliance.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Applied | {result.applied} |",
        f"| Profile | {_escape(result.profile_id or 'missing')} |",
        f"| Profile path | `{_escape(result.profile_path or '-')}` |",
        f"| Backup path | `{_escape(result.backup_path or '-')}` |",
        f"| Apply plan | `{_escape(result.apply_plan_path)}` |",
        f"| Apply plan hash | `{_escape(result.apply_plan_hash)}` |",
        f"| Promotion record | {_escape(result.promotion_id or '-')} |",
        f"| Reviewer | {_escape(result.reviewer or '-')} |",
        f"| Reviewed at | {_escape(result.reviewed_at or '-')} |",
        f"| Applied at | {_escape(result.applied_at)} |",
        f"| Applied fields | {_escape(', '.join(result.applied_fields) or '-')} |",
        "",
        "## Rollback",
        "",
        _escape(result.rollback_note or "Restore the profile from the backup path if this apply operation is revoked."),
        "",
        "## Before Profile",
        "",
        "```json",
        json.dumps(result.before_profile, indent=2, ensure_ascii=False),
        "```",
        "",
        "## After Profile",
        "",
        "```json",
        json.dumps(result.after_profile, indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    return "\n".join(lines)


def _blocked_status(summary_status: str, latest_decision: str | None) -> str:
    if summary_status == "not_recorded":
        return "missing_promotion_record"
    if summary_status == "stale_review_hash":
        return "stale_review_hash"
    if latest_decision in {"rejected", "revoked"}:
        return "promotion_rejected"
    if latest_decision == "needs_changes":
        return "promotion_needs_changes"
    return "blocked"


def _promoted_notes(existing: str | None, promotion_id: str, reviewer: str, reviewed_at: str, review_hash: str) -> str:
    line = (
        "Profile status promotion proposed from supplied human decision "
        f"{promotion_id} by {reviewer} at {reviewed_at}; profile_review_hash={review_hash}."
    )
    if not existing:
        return line
    if promotion_id in existing:
        return existing
    return f"{existing}\n\n{line}"


def _rollback_note(profile: ProjectProfile, promotion_id: str | None) -> str:
    promotion = promotion_id or "the promotion record"
    return (
        f"If applying {promotion} is later rejected, restore `status` to `{profile.status}` "
        "and restore `notes` from the before value in this apply plan or from version control."
    )


def _display(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _resolve_workspace_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        workspace_candidate = workspace / candidate
        if workspace_candidate.exists():
            return workspace_candidate
    if candidate.exists():
        return candidate
    raise ValueError(f"file not found: {path}")


def _backup_dir(workspace: Path, backup_dir: str | Path | None) -> Path:
    if backup_dir is None:
        return workspace / "state" / "profile-backups"
    candidate = Path(backup_dir)
    if candidate.is_absolute():
        return candidate
    return workspace / candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_hash(value: str) -> str:
    normalized = value.lower()
    if normalized.startswith("sha256:"):
        normalized = normalized.split(":", 1)[1]
    return normalized


def _safe_timestamp(value: str) -> str:
    return value.replace(":", "").replace("-", "").replace("+", "").replace("Z", "Z")


def _applied_rollback_note(backup_path: Path) -> str:
    return f"To roll back this local profile mutation, restore state/project-profile.json from `{backup_path}` or from version control."
