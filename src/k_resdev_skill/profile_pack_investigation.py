from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    ProfilePackInvestigationArtifact,
    ProfilePackInvestigationBundleResult,
    ProfilePackInvestigationItem,
    ProfilePackReadinessDrilldownItem,
    ProfilePackReadinessDrilldownResult,
    ProfilePackReadinessFinding,
    ProfilePackReadinessResult,
)
from .profile_pack_drilldown import generate_profile_pack_readiness_drilldown, load_profile_pack_readiness_drilldown
from .profile_pack_readiness import generate_profile_pack_readiness, load_profile_pack_readiness
from .profile_promotion import summarize_profile_promotions
from .profile_promotion_apply import generate_profile_promotion_apply_plan, load_profile_promotion_apply_result
from .profile_promotion_revoke import load_profile_promotion_revoke_plan, load_profile_promotion_revoke_result
from .profile_review import load_profile_review
from .profile_source_fix_review import load_profile_source_fix_review_summary


def generate_profile_pack_investigation_bundle(
    root: str | Path,
    profile_id: str | None = None,
    finding_code: str | None = None,
    readiness_path: str | Path | None = None,
    drilldown_path: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfilePackInvestigationBundleResult:
    """Create a compact local handoff bundle for profile-pack remediation review."""

    workspace = Path(root)
    state = workspace / "state"
    warnings: list[str] = []
    readiness_file = _resolve_workspace_path(workspace, readiness_path or state / "profile-pack-readiness.json")
    drilldown_file = _resolve_workspace_path(workspace, drilldown_path or state / "profile-pack-readiness-drilldown.json")

    readiness = _load_or_generate_readiness(workspace, readiness_file, warnings)
    drilldown = _load_or_generate_drilldown(workspace, readiness_file, drilldown_file, warnings)
    review_context = _load_review_context(workspace, warnings)

    items: list[ProfilePackInvestigationItem] = []
    readiness_by_key = _readiness_lookup(readiness.findings)
    for index, drilldown_item in enumerate(drilldown.items):
        if profile_id and drilldown_item.profile_id != profile_id:
            continue
        if finding_code and drilldown_item.finding_code != finding_code:
            continue
        readiness_item = _match_readiness_finding(drilldown_item, readiness_by_key)
        items.append(_bundle_item(index, drilldown_item, readiness_item, review_context))

    artifacts = _bundle_artifacts(readiness_file, drilldown_file, readiness, drilldown, items)
    result = ProfilePackInvestigationBundleResult(
        root=str(workspace),
        status=_status_from_items(items, readiness, drilldown, profile_id, finding_code),
        bundle_id=_bundle_id(workspace, profile_id, finding_code, readiness_file, drilldown_file, items),
        profile_id=profile_id,
        finding_code=finding_code,
        readiness_path=str(readiness_file),
        readiness_hash=_sha256_file(readiness_file) if readiness_file.exists() else None,
        readiness_status=readiness.status,
        drilldown_path=str(drilldown_file),
        drilldown_hash=_sha256_file(drilldown_file) if drilldown_file.exists() else None,
        drilldown_status=drilldown.status,
        readiness_finding_count=readiness.finding_count,
        drilldown_item_count=drilldown.drilldown_count,
        bundle_item_count=len(items),
        matched_count=sum(1 for item in items if item.drilldown_match_status == "matched"),
        missing_artifact_count=sum(1 for item in items if item.drilldown_match_status == "missing_artifact"),
        unmatched_count=sum(1 for item in items if item.drilldown_match_status == "unmatched"),
        high_count=sum(1 for item in items if item.severity == "high"),
        medium_count=sum(1 for item in items if item.severity == "medium"),
        low_count=sum(1 for item in items if item.severity == "low"),
        human_review_missing_count=sum(1 for item in items if item.requires_human_review),
        human_review_supplied_count=sum(1 for item in items if item.human_review_ref_id),
        official_source_check_count=sum(1 for item in items if item.requires_official_source_check),
        artifacts=artifacts,
        items=items,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=sorted(set(warnings)),
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_profile_pack_investigation_bundle(path: str | Path) -> ProfilePackInvestigationBundleResult:
    return ProfilePackInvestigationBundleResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_pack_investigation_bundle_markdown(result: ProfilePackInvestigationBundleResult) -> str:
    lines = [
        "# Profile Pack Investigation Bundle",
        "",
        "> Local investigation projection only. This bundle condenses profile-pack readiness and drilldown metadata for handoff; it does not copy raw official-source bodies, mutate profile/source records, promote profiles, or certify agency compliance.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Bundle ID | `{_escape(result.bundle_id)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Profile filter | {_escape(result.profile_id or '-')} |",
        f"| Finding-code filter | {_escape(result.finding_code or '-')} |",
        f"| Readiness path | `{_escape(result.readiness_path)}` |",
        f"| Readiness hash | {_escape(result.readiness_hash or '-')} |",
        f"| Readiness status | {_escape(result.readiness_status or '-')} |",
        f"| Drilldown path | `{_escape(result.drilldown_path)}` |",
        f"| Drilldown hash | {_escape(result.drilldown_hash or '-')} |",
        f"| Drilldown status | {_escape(result.drilldown_status or '-')} |",
        f"| Readiness findings | {result.readiness_finding_count} |",
        f"| Drilldown items | {result.drilldown_item_count} |",
        f"| Bundle items | {result.bundle_item_count} |",
        f"| Missing human review | {result.human_review_missing_count} |",
        f"| Supplied human review | {result.human_review_supplied_count} |",
        f"| Official-source checks | {result.official_source_check_count} |",
        "",
        "## Input Artifacts",
        "",
        "| Type | Exists | Status | Items | SHA-256 | Path | Warning |",
        "|---|---:|---|---:|---|---|---|",
    ]
    for artifact in result.artifacts:
        lines.append(
            "| {kind} | {exists} | {status} | {count} | {sha} | `{path}` | {warning} |".format(
                kind=_escape(artifact.artifact_type),
                exists="yes" if artifact.exists else "no",
                status=_escape(artifact.status or "-"),
                count=artifact.item_count,
                sha=_escape(artifact.sha256 or "-"),
                path=_escape(artifact.path),
                warning=_escape(artifact.warning or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Bundle Items",
            "",
            "| Severity | Finding | Profile | Drilldown | Source | Source Ref | Human Review | Official Check | Next Step |",
            "|---|---|---|---|---|---|---|---:|---|",
        ]
    )
    if not result.items:
        lines.append("| ok | no_matching_profile_pack_findings | - | - | - | - | - | 0 | Adjust `--profile-id` or `--finding-code`, or rerun profile-pack-readiness. |")
    for item in result.items:
        lines.append(
            "| {severity} | {finding} | {profile} | {drilldown} | {source} | {ref} | {review} | {official} | {next_step} |".format(
                severity=_escape(item.severity),
                finding=_escape(item.finding_code),
                profile=_escape(item.profile_id or "-"),
                drilldown=_escape(item.drilldown_match_status or "-"),
                source=_escape(item.source_artifact or "-"),
                ref=_escape(item.source_ref_id or "-"),
                review=_escape(item.human_review_status),
                official="yes" if item.requires_official_source_check else "no",
                next_step=_escape(item.next_step or item.command or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Bundle rows summarize local generated artifacts and supplied human-review metadata only.",
            "- Do not treat a bundle as evidence that official rules, forms, or agency interpretations are current.",
            "- Resolve missing human review and official-source checks before profile promotion.",
            "",
        ]
    )
    return "\n".join(lines)


@dataclass
class _HumanReview:
    status: str
    ref_id: str | None = None
    decision: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    requires_human_review: bool = True
    requires_official_source_check: bool = False


@dataclass
class _ReviewContext:
    fix_records_by_id: dict[str, Any]
    fix_records_by_action: dict[str, Any]
    promotion_summary: Any = None
    profile_review: Any = None
    apply_plan: Any = None
    apply_result: Any = None
    revoke_plan: Any = None
    revoke_result: Any = None


def _load_or_generate_readiness(
    workspace: Path,
    readiness_file: Path,
    warnings: list[str],
) -> ProfilePackReadinessResult:
    if readiness_file.exists():
        try:
            return load_profile_pack_readiness(readiness_file)
        except Exception as exc:
            warnings.append(f"profile_pack_readiness_unreadable:{exc}")
    warnings.append("profile_pack_readiness_generated_in_memory")
    return generate_profile_pack_readiness(workspace)


def _load_or_generate_drilldown(
    workspace: Path,
    readiness_file: Path,
    drilldown_file: Path,
    warnings: list[str],
) -> ProfilePackReadinessDrilldownResult:
    if drilldown_file.exists():
        try:
            return load_profile_pack_readiness_drilldown(drilldown_file)
        except Exception as exc:
            warnings.append(f"profile_pack_readiness_drilldown_unreadable:{exc}")
    warnings.append("profile_pack_readiness_drilldown_generated_in_memory")
    return generate_profile_pack_readiness_drilldown(workspace, readiness_path=readiness_file)


def _load_review_context(workspace: Path, warnings: list[str]) -> _ReviewContext:
    fix_records_by_id: dict[str, Any] = {}
    fix_records_by_action: dict[str, Any] = {}
    fix_summary_path = workspace / "state" / "profile-source-fix-summary.json"
    if fix_summary_path.exists():
        try:
            fix_summary = load_profile_source_fix_review_summary(fix_summary_path)
            for record in fix_summary.records:
                fix_records_by_id[record.review_id] = record
                fix_records_by_action[record.action_id] = record
        except Exception as exc:
            warnings.append(f"profile_source_fix_summary_unreadable:{exc}")

    context = _ReviewContext(
        fix_records_by_id=fix_records_by_id,
        fix_records_by_action=fix_records_by_action,
        promotion_summary=summarize_profile_promotions(workspace),
    )
    profile_review_path = workspace / "state" / "profile-review.json"
    if profile_review_path.exists():
        try:
            context.profile_review = load_profile_review(profile_review_path)
        except Exception as exc:
            warnings.append(f"profile_review_unreadable:{exc}")
    try:
        context.apply_plan = generate_profile_promotion_apply_plan(workspace)
    except Exception as exc:
        warnings.append(f"profile_promotion_apply_plan_unavailable:{exc}")
    apply_result_path = workspace / "state" / "profile-promotion-apply-result.json"
    if apply_result_path.exists():
        try:
            context.apply_result = load_profile_promotion_apply_result(apply_result_path)
        except Exception as exc:
            warnings.append(f"profile_promotion_apply_result_unreadable:{exc}")
    revoke_plan_path = workspace / "state" / "profile-promotion-revoke-plan.json"
    if revoke_plan_path.exists():
        try:
            context.revoke_plan = load_profile_promotion_revoke_plan(revoke_plan_path)
        except Exception as exc:
            warnings.append(f"profile_promotion_revoke_plan_unreadable:{exc}")
    revoke_result_path = workspace / "state" / "profile-promotion-revoke-result.json"
    if revoke_result_path.exists():
        try:
            context.revoke_result = load_profile_promotion_revoke_result(revoke_result_path)
        except Exception as exc:
            warnings.append(f"profile_promotion_revoke_result_unreadable:{exc}")
    return context


def _bundle_item(
    index: int,
    drilldown_item: ProfilePackReadinessDrilldownItem,
    readiness_item: ProfilePackReadinessFinding | None,
    review_context: _ReviewContext,
) -> ProfilePackInvestigationItem:
    human_review = _human_review_for_item(drilldown_item, review_context)
    return ProfilePackInvestigationItem(
        bundle_item_id=_bundle_item_id(index, drilldown_item),
        profile_id=drilldown_item.profile_id,
        finding_code=drilldown_item.finding_code,
        severity=drilldown_item.severity,
        readiness_message=readiness_item.message if readiness_item else drilldown_item.finding_message,
        readiness_path=readiness_item.path if readiness_item else drilldown_item.finding_path,
        readiness_suggested_action=readiness_item.suggested_action if readiness_item else drilldown_item.finding_suggested_action,
        drilldown_id=drilldown_item.drilldown_id,
        drilldown_match_status=drilldown_item.match_status,
        source_artifact=drilldown_item.source_artifact,
        source_artifact_path=drilldown_item.source_artifact_path,
        source_artifact_hash=drilldown_item.source_artifact_hash,
        source_ref_id=drilldown_item.source_ref_id,
        source_code=drilldown_item.source_code,
        source_status=drilldown_item.source_status,
        source_message=drilldown_item.source_message,
        source_path=drilldown_item.source_path,
        related_ids=drilldown_item.related_ids,
        command=drilldown_item.command,
        human_review_status=human_review.status,
        human_review_ref_id=human_review.ref_id,
        human_review_decision=human_review.decision,
        human_review_reviewer=human_review.reviewer,
        human_review_reviewed_at=human_review.reviewed_at,
        requires_human_review=human_review.requires_human_review,
        requires_official_source_check=human_review.requires_official_source_check,
        next_step=_next_step(drilldown_item, readiness_item, human_review),
    )


def _human_review_for_item(item: ProfilePackReadinessDrilldownItem, context: _ReviewContext) -> _HumanReview:
    if item.source_artifact == "profile_source_fix_summary":
        record = _match_fix_review_record(item, context)
        if record is not None:
            decision = _enum_value(record.decision)
            return _HumanReview(
                status=f"profile_source_fix_review:{decision}",
                ref_id=record.review_id,
                decision=decision,
                reviewer=record.reviewer,
                reviewed_at=record.reviewed_at,
                requires_human_review=decision in {"deferred", "rejected"},
                requires_official_source_check=decision != "resolved",
            )
        return _HumanReview(
            status="profile_source_fix_review:missing",
            requires_human_review=True,
            requires_official_source_check=True,
        )
    if item.source_artifact == "profile_promotion_summary":
        summary = context.promotion_summary
        if summary is not None and summary.latest_promotion_id:
            return _HumanReview(
                status=f"profile_promotion:{summary.latest_decision or summary.status}",
                ref_id=summary.latest_promotion_id,
                decision=summary.latest_decision,
                reviewer=summary.latest_reviewer,
                reviewed_at=summary.latest_reviewed_at,
                requires_human_review=summary.status != "verified_recorded",
                requires_official_source_check=summary.status != "verified_recorded",
            )
        return _HumanReview(status="profile_promotion:missing", requires_human_review=True, requires_official_source_check=True)
    if item.source_artifact == "profile_promotion_apply_plan" and context.apply_plan is not None:
        plan = context.apply_plan
        return _HumanReview(
            status=f"profile_promotion_apply_plan:{plan.status}",
            ref_id=plan.promotion_id,
            decision=plan.promotion_decision,
            reviewer=plan.reviewer,
            reviewed_at=plan.reviewed_at,
            requires_human_review=not plan.can_apply,
            requires_official_source_check=not plan.can_apply,
        )
    if item.source_artifact == "profile_promotion_apply_result" and context.apply_result is not None:
        result = context.apply_result
        return _HumanReview(
            status=f"profile_promotion_apply_result:{result.status}",
            ref_id=result.promotion_id,
            reviewer=result.reviewer,
            reviewed_at=result.reviewed_at or result.applied_at,
            requires_human_review=not result.applied,
            requires_official_source_check=not result.applied,
        )
    if item.source_artifact == "profile_promotion_revoke_plan" and context.revoke_plan is not None:
        plan = context.revoke_plan
        return _HumanReview(
            status=f"profile_promotion_revoke_plan:{plan.status}",
            ref_id=plan.promotion_id,
            reviewer=plan.reviewer,
            reviewed_at=plan.requested_at,
            requires_human_review=not plan.can_revoke,
            requires_official_source_check=not plan.can_revoke,
        )
    if item.source_artifact == "profile_promotion_revoke_result" and context.revoke_result is not None:
        result = context.revoke_result
        return _HumanReview(
            status=f"profile_promotion_revoke_result:{result.status}",
            ref_id=result.promotion_id,
            reviewer=result.reviewer,
            reviewed_at=result.revoked_at,
            requires_human_review=not result.revoked,
            requires_official_source_check=not result.revoked,
        )
    if item.source_artifact == "profile_review" and context.profile_review is not None:
        review = context.profile_review
        return _HumanReview(
            status=f"profile_review_projection:{review.status}",
            requires_human_review=not review.can_promote,
            requires_official_source_check=not review.can_promote,
        )
    if item.source_artifact in {"profile_source_queue", "profile_source_fix_plan", "profile_integrity"}:
        return _HumanReview(
            status="supplied_human_review:missing",
            requires_human_review=True,
            requires_official_source_check=_requires_official_source_check(item),
        )
    if item.match_status != "matched":
        return _HumanReview(
            status="drilldown_match:incomplete",
            requires_human_review=True,
            requires_official_source_check=True,
        )
    return _HumanReview(
        status="local_projection_only",
        requires_human_review=item.severity in {"high", "medium"},
        requires_official_source_check=_requires_official_source_check(item),
    )


def _match_fix_review_record(item: ProfilePackReadinessDrilldownItem, context: _ReviewContext):
    keys = [item.source_ref_id, *item.related_ids]
    for key in keys:
        if key in context.fix_records_by_id:
            return context.fix_records_by_id[key]
        if key in context.fix_records_by_action:
            return context.fix_records_by_action[key]
    return None


def _requires_official_source_check(item: ProfilePackReadinessDrilldownItem) -> bool:
    text = " ".join(
        value
        for value in [
            item.finding_code,
            item.finding_message,
            item.source_code or "",
            item.source_message or "",
            item.source_artifact or "",
        ]
        if value
    ).lower()
    return any(token in text for token in ["source", "official", "hash", "profile"])


def _next_step(
    item: ProfilePackReadinessDrilldownItem,
    readiness_item: ProfilePackReadinessFinding | None,
    human_review: _HumanReview,
) -> str | None:
    if human_review.status.endswith(":missing"):
        return "Record the supplied human review decision or keep the profile pack in needs_review."
    if human_review.requires_official_source_check:
        return "Check the current official source outside this tool, then update local source metadata through reviewable commands."
    return readiness_item.suggested_action if readiness_item and readiness_item.suggested_action else item.command


def _readiness_lookup(findings: list[ProfilePackReadinessFinding]) -> dict[tuple[str, str | None, str], ProfilePackReadinessFinding]:
    return {(_normalize(item.code), item.profile_id, _normalize(item.message)): item for item in findings}


def _match_readiness_finding(
    item: ProfilePackReadinessDrilldownItem,
    lookup: dict[tuple[str, str | None, str], ProfilePackReadinessFinding],
) -> ProfilePackReadinessFinding | None:
    key = (_normalize(item.finding_code), item.profile_id, _normalize(item.finding_message))
    if key in lookup:
        return lookup[key]
    fallback_key = (_normalize(item.finding_code), None, _normalize(item.finding_message))
    return lookup.get(fallback_key)


def _bundle_artifacts(
    readiness_file: Path,
    drilldown_file: Path,
    readiness: ProfilePackReadinessResult,
    drilldown: ProfilePackReadinessDrilldownResult,
    items: list[ProfilePackInvestigationItem],
) -> list[ProfilePackInvestigationArtifact]:
    artifacts: dict[tuple[str, str], ProfilePackInvestigationArtifact] = {}
    _add_artifact(artifacts, "profile_pack_readiness", readiness_file, readiness.status, readiness.finding_count)
    _add_artifact(artifacts, "profile_pack_readiness_drilldown", drilldown_file, drilldown.status, drilldown.drilldown_count)
    drilldown_artifacts = {artifact.artifact_type: artifact for artifact in drilldown.artifacts}
    for item in items:
        artifact = drilldown_artifacts.get(item.source_artifact or "")
        if artifact is not None:
            key = (artifact.artifact_type, artifact.path)
            artifacts[key] = ProfilePackInvestigationArtifact(
                artifact_type=artifact.artifact_type,
                path=artifact.path,
                exists=artifact.exists,
                sha256=artifact.sha256,
                status=artifact.status,
                item_count=artifact.item_count,
                warning=artifact.warning,
            )
        elif item.source_artifact_path:
            _add_artifact(artifacts, item.source_artifact or "source_artifact", Path(item.source_artifact_path), None, 0)
    return sorted(artifacts.values(), key=lambda artifact: (artifact.artifact_type, artifact.path))


def _add_artifact(
    artifacts: dict[tuple[str, str], ProfilePackInvestigationArtifact],
    artifact_type: str,
    path: Path,
    status: str | None,
    item_count: int,
) -> None:
    key = (artifact_type, str(path))
    artifacts[key] = ProfilePackInvestigationArtifact(
        artifact_type=artifact_type,
        path=str(path),
        exists=path.exists(),
        sha256=_sha256_file(path) if path.exists() else None,
        status=status,
        item_count=item_count,
        warning=None if path.exists() else "missing",
    )


def _status_from_items(
    items: list[ProfilePackInvestigationItem],
    readiness: ProfilePackReadinessResult,
    drilldown: ProfilePackReadinessDrilldownResult,
    profile_id: str | None,
    finding_code: str | None,
) -> str:
    if readiness.status == "not_configured" or drilldown.status == "not_configured":
        return "not_configured"
    if not items and (profile_id or finding_code):
        return "no_matches"
    if any(item.severity == "high" for item in items):
        return "blocked"
    if any(item.drilldown_match_status in {"missing_artifact", "unmatched"} for item in items):
        return "needs_review"
    if any(item.requires_human_review or item.requires_official_source_check for item in items):
        return "needs_review"
    if any(item.severity == "medium" for item in items):
        return "needs_review"
    if any(item.severity == "low" for item in items):
        return "ready_with_notes"
    return "ready"


def _write_outputs(
    result: ProfilePackInvestigationBundleResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_pack_investigation_bundle_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _resolve_workspace_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else workspace / candidate


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_id(
    workspace: Path,
    profile_id: str | None,
    finding_code: str | None,
    readiness_file: Path,
    drilldown_file: Path,
    items: list[ProfilePackInvestigationItem],
) -> str:
    seed = "|".join(
        [
            str(workspace),
            profile_id or "",
            finding_code or "",
            str(readiness_file),
            str(drilldown_file),
            ",".join(item.bundle_item_id for item in items),
        ]
    )
    return "PPIB-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12].upper()


def _bundle_item_id(index: int, item: ProfilePackReadinessDrilldownItem) -> str:
    seed = "|".join([str(index), item.drilldown_id, item.finding_code, item.profile_id or "", item.finding_message])
    return "PPI-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12].upper()


def _enum_value(value: object) -> str:
    return getattr(value, "value", str(value))


def _normalize(value: str | None) -> str:
    return " ".join((value or "").split())


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
