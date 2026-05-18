from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .models import ProfilePromotionRevocationChange, ProfilePromotionRevocationPlanResult, ProjectProfile
from .profile_promotion_apply import load_profile_promotion_apply_result
from .profile_registry import load_project_profile


def generate_profile_promotion_revoke_plan(
    root: str | Path,
    reviewer: str,
    reason: str,
    apply_result_path: str | Path | None = None,
    requested_at: str | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfilePromotionRevocationPlanResult:
    """Generate a non-destructive revocation plan for a guarded profile promotion apply result."""

    workspace = Path(root)
    reviewer_text = _require_text(reviewer, "reviewer")
    reason_text = _require_text(reason, "reason")
    timestamp = requested_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    profile_path = workspace / "state" / "project-profile.json"
    result_path = _resolve_workspace_path(workspace, apply_result_path or workspace / "state" / "profile-promotion-apply-result.json")
    warnings: list[str] = []

    apply_result = None
    apply_result_hash: str | None = None
    status = "blocked"
    if not result_path.exists():
        status = "missing_apply_result"
        warnings.append("apply_result_missing")
    else:
        try:
            apply_result = load_profile_promotion_apply_result(result_path)
            apply_result_hash = _sha256_file(result_path)
        except Exception as exc:
            status = "apply_result_unreadable"
            warnings.append(f"apply_result_unreadable:{exc}")

    current_profile: ProjectProfile | None = None
    current_profile_payload: dict[str, object] = {}
    if profile_path.exists():
        try:
            current_profile = load_project_profile(profile_path)
            current_profile_payload = current_profile.model_dump()
        except Exception as exc:
            warnings.append(f"profile_unreadable:{exc}")
            if apply_result is not None:
                status = "profile_unreadable"
    else:
        warnings.append("profile_missing")
        if apply_result is not None:
            status = "missing_profile"

    backup_path: Path | None = None
    backup_hash: str | None = None
    backup_payload: dict[str, object] = {}
    backup_available = False
    if apply_result is not None:
        backup_path = _resolve_workspace_path(workspace, apply_result.backup_path) if apply_result.backup_path else None
        if not apply_result.applied or apply_result.status != "applied":
            status = "apply_result_not_applied"
            warnings.append(f"apply_result_not_applied:{apply_result.status}")
        elif backup_path is None:
            status = "missing_backup"
            warnings.append("backup_path_missing")
        elif not backup_path.exists():
            status = "missing_backup"
            warnings.append("backup_missing")
        else:
            try:
                backup_profile = ProjectProfile.model_validate_json(backup_path.read_text(encoding="utf-8-sig"))
                backup_payload = backup_profile.model_dump()
                backup_hash = _sha256_file(backup_path)
                backup_available = True
            except Exception as exc:
                status = "backup_unreadable"
                warnings.append(f"backup_unreadable:{exc}")

    current_matches_applied_profile = False
    changes: list[ProfilePromotionRevocationChange] = []
    can_revoke = False
    restored_profile = backup_payload

    if apply_result is not None and current_profile is not None and backup_available:
        try:
            after_profile = ProjectProfile.model_validate(apply_result.after_profile).model_dump() if apply_result.after_profile else {}
            before_profile = ProjectProfile.model_validate(apply_result.before_profile).model_dump() if apply_result.before_profile else {}
        except Exception as exc:
            after_profile = {}
            before_profile = {}
            status = "apply_result_profile_invalid"
            warnings.append(f"apply_result_profile_invalid:{exc}")
        if before_profile and backup_payload != before_profile:
            status = "backup_mismatch"
            warnings.append("backup_differs_from_apply_result_before_profile")
        elif status == "apply_result_profile_invalid":
            pass
        elif current_profile_payload == backup_payload:
            status = "already_restored"
            warnings.append("current_profile_already_matches_backup")
        elif current_profile_payload != after_profile:
            status = "current_profile_drift"
            warnings.append("current_profile_differs_from_apply_result_after_profile")
        else:
            status = "ready_to_revoke"
            can_revoke = True
            current_matches_applied_profile = True
            changes = _revocation_changes(current_profile_payload, backup_payload, apply_result.promotion_id)

    result = ProfilePromotionRevocationPlanResult(
        root=str(workspace),
        status=status,
        can_revoke=can_revoke,
        profile_id=(current_profile.profile_id if current_profile else apply_result.profile_id if apply_result else None),
        profile_path=str(profile_path),
        apply_result_path=str(result_path),
        apply_result_hash=apply_result_hash,
        promotion_id=apply_result.promotion_id if apply_result else None,
        reviewer=reviewer_text,
        reason=reason_text,
        requested_at=timestamp,
        current_profile_status=current_profile.status if current_profile else None,
        restore_profile_status=str(backup_payload.get("status")) if backup_payload else None,
        backup_path=str(backup_path) if backup_path else None,
        backup_hash=backup_hash,
        backup_available=backup_available,
        current_matches_applied_profile=current_matches_applied_profile,
        change_count=len(changes),
        changes=changes,
        restored_profile=restored_profile,
        rollback_note=_rollback_note(backup_path, result_path),
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=warnings,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_promotion_revoke_plan_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def load_profile_promotion_revoke_plan(path: str | Path) -> ProfilePromotionRevocationPlanResult:
    return ProfilePromotionRevocationPlanResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_promotion_revoke_plan_markdown(result: ProfilePromotionRevocationPlanResult) -> str:
    lines = [
        "# Profile Promotion Revocation Plan",
        "",
        "> Proposal only. This file evaluates whether a previously applied profile promotion can be revoked cleanly; it does not mutate `state/project-profile.json`, revoke a human decision, or certify agency compliance.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Can revoke | {result.can_revoke} |",
        f"| Profile | {_escape(result.profile_id or 'missing')} |",
        f"| Current profile status | {_escape(result.current_profile_status or 'missing')} |",
        f"| Restore profile status | {_escape(result.restore_profile_status or 'missing')} |",
        f"| Promotion record | {_escape(result.promotion_id or '-')} |",
        f"| Reviewer | {_escape(result.reviewer)} |",
        f"| Reason | {_escape(result.reason)} |",
        f"| Requested at | {_escape(result.requested_at)} |",
        f"| Apply result | `{_escape(result.apply_result_path or '-')}` |",
        f"| Apply result hash | {_escape(result.apply_result_hash or '-')} |",
        f"| Backup path | `{_escape(result.backup_path or '-')}` |",
        f"| Backup hash | {_escape(result.backup_hash or '-')} |",
        f"| Backup available | {result.backup_available} |",
        f"| Current matches applied profile | {result.current_matches_applied_profile} |",
        f"| Change count | {result.change_count} |",
        "",
        "## Proposed Restore Changes",
        "",
        "| Field | Current | Restore To | Rationale |",
        "|---|---|---|---|",
    ]
    if not result.changes:
        lines.append("| - | - | - | No restore field change is proposed. |")
    for change in result.changes:
        lines.append(
            "| {field} | {current} | {restore_to} | {rationale} |".format(
                field=_escape(change.field),
                current=_escape(_display(change.current)),
                restore_to=_escape(_display(change.restore_to)),
                rationale=_escape(change.rationale),
            )
        )
    lines.extend(
        [
            "",
            "## Rollback Note",
            "",
            _escape(result.rollback_note or "No rollback note is available."),
            "",
            "## Restored Profile Candidate",
            "",
            "```json",
            json.dumps(result.restored_profile, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Warnings",
            "",
        ]
    )
    if not result.warnings:
        lines.append("- none")
    for warning in result.warnings:
        lines.append(f"- {_escape(warning)}")
    lines.append("")
    return "\n".join(lines)


def _revocation_changes(current: dict[str, object], backup: dict[str, object], promotion_id: str | None) -> list[ProfilePromotionRevocationChange]:
    changes: list[ProfilePromotionRevocationChange] = []
    promotion = promotion_id or "the applied profile promotion"
    for field in ProjectProfile.model_fields:
        current_value = current.get(field)
        restore_value = backup.get(field)
        if current_value == restore_value:
            continue
        changes.append(
            ProfilePromotionRevocationChange(
                field=field,
                current=current_value,
                restore_to=restore_value,
                rationale=f"Restore `{field}` to the pre-apply value captured before {promotion}.",
            )
        )
    return changes


def _rollback_note(backup_path: Path | None, apply_result_path: Path) -> str:
    backup = f"`{backup_path}`" if backup_path else "the missing profile backup"
    return (
        "This revocation plan is non-mutating. A later guarded revoke command should hash-check this plan, "
        f"restore `state/project-profile.json` from {backup}, and preserve `{apply_result_path}` as audit history."
    )


def _display(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _resolve_workspace_path(workspace: Path, path: str | Path | None) -> Path:
    if path is None:
        return workspace / "state" / "profile-promotion-apply-result.json"
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


def _require_text(value: str, name: str) -> str:
    text = value.strip() if value else ""
    if not text:
        raise ValueError(f"{name} must not be blank")
    return text
