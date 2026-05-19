from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import (
    ProfileIntegrityResult,
    ProfilePackReadinessDrilldownArtifact,
    ProfilePackReadinessDrilldownItem,
    ProfilePackReadinessDrilldownResult,
    ProfilePackReadinessFinding,
    ProfilePackReadinessResult,
    ProfilePromotionApplyPlanResult,
    ProfilePromotionSummaryResult,
)
from .profile_lifecycle import load_profile_lifecycle_ledger
from .profile_pack_readiness import generate_profile_pack_readiness, load_profile_pack_readiness
from .profile_promotion import summarize_profile_promotions
from .profile_promotion_apply import generate_profile_promotion_apply_plan, load_profile_promotion_apply_result
from .profile_promotion_revoke import load_profile_promotion_revoke_plan, load_profile_promotion_revoke_result
from .profile_review import load_profile_review
from .profile_source_fix_plan import load_profile_source_fix_plan
from .profile_source_fix_review import load_profile_source_fix_review_summary
from .profile_source_queue import load_profile_source_queue
from .profile_sources import generate_profile_integrity


def generate_profile_pack_readiness_drilldown(
    root: str | Path,
    readiness_path: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfilePackReadinessDrilldownResult:
    """Link profile-pack readiness findings to their local upstream artifacts."""

    workspace = Path(root)
    state = workspace / "state"
    readiness_file = _resolve_workspace_path(workspace, readiness_path or state / "profile-pack-readiness.json")
    warnings: list[str] = []

    readiness = _load_or_generate_readiness(workspace, readiness_file, warnings)
    artifacts = _load_artifacts(workspace, state, readiness_file, warnings)
    items: list[ProfilePackReadinessDrilldownItem] = []

    for index, finding in enumerate(readiness.findings):
        item = _drilldown_item(workspace, index, finding, artifacts)
        items.append(item)

    result = ProfilePackReadinessDrilldownResult(
        root=str(workspace),
        status=_status_from_items(items, readiness),
        readiness_path=str(readiness_file),
        readiness_hash=_sha256_file(readiness_file) if readiness_file.exists() else None,
        readiness_status=readiness.status,
        readiness_finding_count=readiness.finding_count,
        drilldown_count=len(items),
        matched_count=sum(1 for item in items if item.match_status == "matched"),
        unmatched_count=sum(1 for item in items if item.match_status == "unmatched"),
        missing_artifact_count=sum(1 for item in items if item.match_status == "missing_artifact"),
        high_count=sum(1 for item in items if item.severity == "high"),
        medium_count=sum(1 for item in items if item.severity == "medium"),
        low_count=sum(1 for item in items if item.severity == "low"),
        artifacts=[artifact.info for artifact in artifacts.values()],
        items=items,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=sorted(set(warnings)),
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_profile_pack_readiness_drilldown(path: str | Path) -> ProfilePackReadinessDrilldownResult:
    return ProfilePackReadinessDrilldownResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_pack_readiness_drilldown_markdown(result: ProfilePackReadinessDrilldownResult) -> str:
    lines = [
        "# Profile Pack Readiness Drilldown",
        "",
        "> Investigation projection only. This report links local readiness findings to local upstream artifacts and hashes; it does not fetch official sources, mutate profile/source records, promote profiles, or certify agency compliance.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Readiness path | `{_escape(result.readiness_path)}` |",
        f"| Readiness hash | {_escape(result.readiness_hash or '-')} |",
        f"| Readiness status | {_escape(result.readiness_status or '-')} |",
        f"| Readiness findings | {result.readiness_finding_count} |",
        f"| Drilldown items | {result.drilldown_count} |",
        f"| Matched | {result.matched_count} |",
        f"| Unmatched | {result.unmatched_count} |",
        f"| Missing artifacts | {result.missing_artifact_count} |",
        f"| High | {result.high_count} |",
        f"| Medium | {result.medium_count} |",
        f"| Low | {result.low_count} |",
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
            "## Drilldown",
            "",
            "| Severity | Finding | Profile | Match | Source Artifact | Source Ref | Source Code | Source Status | Artifact Hash | Source Path | Command |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if not result.items:
        lines.append("| ok | profile_pack_readiness_ready | - | matched | - | - | - | - | - | - | Continue human review before official use. |")
    for item in result.items:
        lines.append(
            "| {severity} | {finding} | {profile} | {match} | {artifact} | {ref} | {code} | {status} | {sha} | {path} | {command} |".format(
                severity=_escape(item.severity),
                finding=_escape(item.finding_code),
                profile=_escape(item.profile_id or "-"),
                match=_escape(item.match_status),
                artifact=_escape(item.source_artifact),
                ref=_escape(item.source_ref_id or "-"),
                code=_escape(item.source_code or "-"),
                status=_escape(item.source_status or "-"),
                sha=_escape(item.source_artifact_hash or "-"),
                path=_escape(item.source_path or item.finding_path or "-"),
                command=_escape(item.command or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Drilldown links local generated artifacts; it does not prove official source currency.",
            "- Missing or unmatched drilldown items mean investigation metadata is incomplete, not that a profile is compliant.",
            "- Keep accepted risks visible and require supplied human decisions before profile promotion.",
            "",
        ]
    )
    return "\n".join(lines)


class _LoadedArtifact:
    def __init__(self, info: ProfilePackReadinessDrilldownArtifact, payload: Any = None) -> None:
        self.info = info
        self.payload = payload


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


def _load_artifacts(workspace: Path, state: Path, readiness_file: Path, warnings: list[str]) -> dict[str, _LoadedArtifact]:
    specs = [
        ("profile_pack_readiness", readiness_file, ProfilePackReadinessResult, "findings"),
        ("profile_source_queue", state / "profile-source-queue.json", None, "items"),
        ("profile_source_fix_plan", state / "profile-source-fix-plan.json", None, "actions"),
        ("profile_source_fix_summary", state / "profile-source-fix-summary.json", None, "findings"),
        ("profile_integrity", state / "profile-integrity.json", ProfileIntegrityResult, "findings"),
        ("profile_review", state / "profile-review.json", None, "checklist"),
        ("profile_promotion_summary", state / "profile-promotion-summary.json", ProfilePromotionSummaryResult, "records"),
        ("profile_promotion_apply_plan", state / "profile-promotion-apply-plan.json", ProfilePromotionApplyPlanResult, "changes"),
        ("profile_promotion_apply_result", state / "profile-promotion-apply-result.json", None, "applied_fields"),
        ("profile_promotion_revoke_plan", state / "profile-promotion-revoke-plan.json", None, "changes"),
        ("profile_promotion_revoke_result", state / "profile-promotion-revoke-result.json", None, "revoked_fields"),
        ("profile_lifecycle_ledger", state / "profile-lifecycle-ledger.json", None, "findings"),
    ]
    loaded: dict[str, _LoadedArtifact] = {}
    for artifact_type, path, model, count_attr in specs:
        loaded[artifact_type] = _load_artifact(workspace, artifact_type, path, model, count_attr, warnings)
    return loaded


def _load_artifact(
    workspace: Path,
    artifact_type: str,
    path: Path,
    model,
    count_attr: str,
    warnings: list[str],
) -> _LoadedArtifact:
    if not path.exists():
        return _LoadedArtifact(
            ProfilePackReadinessDrilldownArtifact(
                artifact_type=artifact_type,
                path=str(path),
                exists=False,
                warning="missing",
            )
        )
    try:
        payload = _load_payload(workspace, artifact_type, path, model)
        status = str(getattr(payload, "status", "")) if getattr(payload, "status", None) is not None else None
        item_count = _item_count(payload, count_attr)
        return _LoadedArtifact(
            ProfilePackReadinessDrilldownArtifact(
                artifact_type=artifact_type,
                path=str(path),
                exists=True,
                sha256=_sha256_file(path),
                status=status,
                item_count=item_count,
            ),
            payload=payload,
        )
    except Exception as exc:
        warnings.append(f"{artifact_type}_unreadable:{exc}")
        return _LoadedArtifact(
            ProfilePackReadinessDrilldownArtifact(
                artifact_type=artifact_type,
                path=str(path),
                exists=True,
                sha256=_sha256_file(path),
                warning=f"unreadable:{exc}",
            )
        )


def _load_payload(workspace: Path, artifact_type: str, path: Path, model):
    if artifact_type == "profile_source_queue":
        return load_profile_source_queue(path)
    if artifact_type == "profile_source_fix_plan":
        return load_profile_source_fix_plan(path)
    if artifact_type == "profile_source_fix_summary":
        return load_profile_source_fix_review_summary(path)
    if artifact_type == "profile_review":
        return load_profile_review(path)
    if artifact_type == "profile_promotion_apply_result":
        return load_profile_promotion_apply_result(path)
    if artifact_type == "profile_promotion_revoke_plan":
        return load_profile_promotion_revoke_plan(path)
    if artifact_type == "profile_promotion_revoke_result":
        return load_profile_promotion_revoke_result(path)
    if artifact_type == "profile_lifecycle_ledger":
        return load_profile_lifecycle_ledger(path)
    if artifact_type == "profile_integrity":
        return model.model_validate_json(path.read_text(encoding="utf-8-sig"))
    if artifact_type == "profile_promotion_summary":
        return model.model_validate_json(path.read_text(encoding="utf-8-sig"))
    if artifact_type == "profile_promotion_apply_plan":
        return model.model_validate_json(path.read_text(encoding="utf-8-sig"))
    if artifact_type == "profile_pack_readiness":
        return load_profile_pack_readiness(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _drilldown_item(
    workspace: Path,
    index: int,
    finding: ProfilePackReadinessFinding,
    artifacts: dict[str, _LoadedArtifact],
) -> ProfilePackReadinessDrilldownItem:
    artifact_type = _artifact_for_finding(finding.code)
    artifact = artifacts[artifact_type]
    source = _match_source(finding, artifact_type, artifact.payload)
    match_status = "matched" if source else "missing_artifact" if not artifact.info.exists or artifact.info.warning else "unmatched"
    source = source or {}
    source_ref_id = source.get("ref_id")
    related_ids = source.get("related_ids", [])
    return ProfilePackReadinessDrilldownItem(
        drilldown_id=_drilldown_id(index, finding, artifact_type, source_ref_id),
        finding_code=finding.code,
        severity=finding.severity,
        profile_id=finding.profile_id,
        finding_message=finding.message,
        finding_path=finding.path,
        finding_suggested_action=finding.suggested_action,
        source_artifact=artifact_type,
        source_artifact_path=artifact.info.path if artifact.info.exists else artifact.info.path,
        source_artifact_hash=artifact.info.sha256,
        source_index=source.get("index"),
        source_ref_id=source_ref_id,
        source_code=source.get("code"),
        source_status=source.get("status"),
        source_message=source.get("message"),
        source_path=source.get("path"),
        related_ids=related_ids,
        command=_command_for_finding(workspace, finding.code),
        match_status=match_status,
    )


def _artifact_for_finding(code: str) -> str:
    if code == "profile_pack_source_queue_finding":
        return "profile_source_queue"
    if code in {"profile_pack_fix_action_open", "profile_pack_fix_plan_missing"}:
        return "profile_source_fix_plan"
    if code == "profile_pack_fix_review_finding":
        return "profile_source_fix_summary"
    if code == "profile_pack_integrity_finding":
        return "profile_integrity"
    if code == "profile_pack_profile_review_not_ready":
        return "profile_review"
    if code == "profile_pack_promotion_record_missing":
        return "profile_promotion_summary"
    if code == "profile_pack_promotion_apply_pending":
        return "profile_promotion_apply_plan"
    if code == "profile_pack_revoke_pending":
        return "profile_promotion_revoke_plan"
    if code == "profile_pack_lifecycle_finding":
        return "profile_lifecycle_ledger"
    return "profile_pack_readiness"


def _match_source(finding: ProfilePackReadinessFinding, artifact_type: str, payload) -> dict[str, Any] | None:
    if payload is None:
        return None
    if artifact_type == "profile_source_queue":
        for index, item in enumerate(getattr(payload, "items", [])):
            if _profile_matches(finding, item.profile_id) and _same_text(finding.message, item.message):
                return _source(index, item.queue_id, item.issue_code, item.source_status, item.message, item.source_file or item.source_record_path or item.profile_path)
        return _first_profile_match(finding, getattr(payload, "items", []), "queue_id", "issue_code", "source_status")
    if artifact_type == "profile_source_fix_plan":
        actions = getattr(payload, "actions", [])
        for index, action in enumerate(actions):
            if _profile_matches(finding, action.profile_id) and (_same_text(finding.message, action.rationale) or _same_path(finding.path, action.source_record_path or action.source_file)):
                return _source(index, action.action_id, action.issue_code, action.severity, action.rationale, action.source_record_path or action.source_file)
        if getattr(payload, "status", None) in {"missing_queue", "unreadable_queue"}:
            return _source(None, None, getattr(payload, "status", None), getattr(payload, "queue_status", None), "Fix plan is not available from a current queue.", getattr(payload, "queue_path", None))
        return _first_profile_match(finding, actions, "action_id", "issue_code", "severity")
    if artifact_type == "profile_source_fix_summary":
        findings = getattr(payload, "findings", [])
        for index, source_finding in enumerate(findings):
            if _same_text(finding.message, source_finding.message):
                related = [value for value in [source_finding.action_id, source_finding.review_id] if value]
                return _source(index, source_finding.action_id or source_finding.review_id, source_finding.code, source_finding.severity, source_finding.message, source_finding.path, related)
        return _first_message_match(finding, findings, "action_id", "code", "severity")
    if artifact_type == "profile_integrity":
        return _match_findings(finding, getattr(payload, "findings", []), "code", "severity")
    if artifact_type == "profile_review":
        failed = [item for item in getattr(payload, "checklist", []) if item.status != "passed"]
        if failed:
            related = [item.check_id for item in failed]
            first = failed[0]
            return _source(0, first.check_id, first.title, first.status, first.message, first.path, related)
        return _source(None, getattr(payload, "profile_id", None), "profile_review_status", getattr(payload, "status", None), "Profile review summary.", getattr(payload, "json_path", None))
    if artifact_type == "profile_promotion_summary":
        return _source(None, getattr(payload, "latest_promotion_id", None), "profile_promotion_status", getattr(payload, "status", None), "Profile promotion summary.", getattr(payload, "json_path", None))
    if artifact_type == "profile_promotion_apply_plan":
        return _source(None, getattr(payload, "promotion_id", None), "profile_promotion_apply_plan", getattr(payload, "status", None), "Profile promotion apply plan.", getattr(payload, "json_path", None), [change.field for change in getattr(payload, "changes", [])])
    if artifact_type == "profile_promotion_revoke_plan":
        return _source(None, getattr(payload, "promotion_id", None), "profile_promotion_revoke_plan", getattr(payload, "status", None), "Profile promotion revoke plan.", getattr(payload, "json_path", None), [change.field for change in getattr(payload, "changes", [])])
    if artifact_type == "profile_lifecycle_ledger":
        matched = _match_findings(finding, getattr(payload, "findings", []), "code", "severity")
        if matched:
            matched["related_ids"] = [entry.entry_id for entry in getattr(payload, "entries", [])]
            return matched
        return _source(None, getattr(payload, "profile_id", None), "profile_lifecycle_status", getattr(payload, "status", None), "Profile lifecycle ledger.", getattr(payload, "json_path", None), [entry.entry_id for entry in getattr(payload, "entries", [])])
    return None


def _match_findings(finding: ProfilePackReadinessFinding, source_findings: list[Any], code_attr: str, status_attr: str) -> dict[str, Any] | None:
    for index, source_finding in enumerate(source_findings):
        message = getattr(source_finding, "message", "")
        if _same_text(finding.message, message) or _same_path(finding.path, getattr(source_finding, "path", None)):
            return _source(index, getattr(source_finding, code_attr, None), getattr(source_finding, code_attr, None), getattr(source_finding, status_attr, None), message, getattr(source_finding, "path", None))
    return None


def _first_profile_match(finding: ProfilePackReadinessFinding, items: list[Any], ref_attr: str, code_attr: str, status_attr: str) -> dict[str, Any] | None:
    for index, item in enumerate(items):
        if _profile_matches(finding, getattr(item, "profile_id", None)):
            return _source(index, getattr(item, ref_attr, None), getattr(item, code_attr, None), getattr(item, status_attr, None), getattr(item, "message", None) or getattr(item, "rationale", None), getattr(item, "path", None) or getattr(item, "source_file", None) or getattr(item, "source_record_path", None))
    return None


def _first_message_match(finding: ProfilePackReadinessFinding, items: list[Any], ref_attr: str, code_attr: str, status_attr: str) -> dict[str, Any] | None:
    for index, item in enumerate(items):
        if _same_text(finding.message, getattr(item, "message", "")):
            return _source(index, getattr(item, ref_attr, None), getattr(item, code_attr, None), getattr(item, status_attr, None), getattr(item, "message", None), getattr(item, "path", None))
    return None


def _source(
    index: int | None,
    ref_id: str | None,
    code: str | None,
    status: str | None,
    message: str | None,
    path: str | None,
    related_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "index": index,
        "ref_id": ref_id,
        "code": code,
        "status": status,
        "message": message,
        "path": path,
        "related_ids": related_ids or [],
    }


def _command_for_finding(workspace: Path, code: str) -> str:
    command_by_artifact = {
        "profile_pack_source_queue_finding": "profile-source-queue",
        "profile_pack_fix_action_open": "profile-source-fix-plan",
        "profile_pack_fix_plan_missing": "profile-source-fix-plan",
        "profile_pack_fix_review_finding": "profile-source-fix-summary",
        "profile_pack_integrity_finding": "profile-integrity",
        "profile_pack_profile_review_not_ready": "profile-review",
        "profile_pack_promotion_record_missing": "profile-promotion-summary",
        "profile_pack_promotion_apply_pending": "profile-promotion-apply-plan",
        "profile_pack_revoke_pending": "profile-promotion-revoke-plan",
        "profile_pack_lifecycle_finding": "profile-lifecycle-ledger",
    }
    command = command_by_artifact.get(code, "profile-pack-readiness")
    filename = command + ".md"
    json_name = command + ".json"
    if command == "profile-source-fix-summary":
        json_name = "profile-source-fix-summary.json"
    return f'python -m k_resdev_skill {command} --root "{workspace}" --output "{workspace / "reports" / filename}" --json "{workspace / "state" / json_name}"'


def _status_from_items(items: list[ProfilePackReadinessDrilldownItem], readiness: ProfilePackReadinessResult) -> str:
    if readiness.status == "not_configured":
        return "not_configured"
    if any(item.severity == "high" for item in items):
        return "blocked"
    if any(item.match_status in {"missing_artifact", "unmatched"} for item in items):
        return "needs_review"
    if any(item.severity == "medium" for item in items):
        return "needs_review"
    if any(item.severity == "low" for item in items):
        return "ready_with_notes"
    return "ready"


def _item_count(payload, count_attr: str) -> int:
    value = getattr(payload, count_attr, None)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    if value is None:
        return 0
    try:
        return int(value)
    except Exception:
        return 0


def _write_outputs(
    result: ProfilePackReadinessDrilldownResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_pack_readiness_drilldown_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _resolve_workspace_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else workspace / candidate


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _drilldown_id(index: int, finding: ProfilePackReadinessFinding, artifact_type: str, ref_id: str | None) -> str:
    seed = "|".join([str(index), finding.code, finding.profile_id or "", finding.message, artifact_type, ref_id or ""])
    return "PPRD-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12].upper()


def _profile_matches(finding: ProfilePackReadinessFinding, profile_id: str | None) -> bool:
    return not finding.profile_id or not profile_id or finding.profile_id == profile_id


def _same_text(left: str | None, right: str | None) -> bool:
    return bool(left and right) and _normalize(left) == _normalize(right)


def _same_path(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return left.replace("\\", "/").rstrip("/") == right.replace("\\", "/").rstrip("/")


def _normalize(value: str) -> str:
    return " ".join(value.split())


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
