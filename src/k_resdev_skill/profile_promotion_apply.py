from __future__ import annotations

import json
from pathlib import Path

from .models import ProfilePromotionApplyChange, ProfilePromotionApplyPlanResult, ProjectProfile
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
