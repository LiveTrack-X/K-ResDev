from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from .models import (
    ProfilePackInvestigationPackageArtifact,
    ProfilePackInvestigationPackageExclusion,
    ProfilePackInvestigationPackageResult,
)
from .profile_pack_investigation import (
    generate_profile_pack_investigation_bundle,
    load_profile_pack_investigation_bundle,
    render_profile_pack_investigation_bundle_markdown,
)
from .schema_tools import validate_json_file


def generate_profile_pack_investigation_package(
    root: str | Path,
    profile_id: str | None = None,
    finding_code: str | None = None,
    bundle_path: str | Path | None = None,
    bundle_output_path: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    zip_path: str | Path | None = None,
) -> ProfilePackInvestigationPackageResult:
    """Package generated profile-pack investigation metadata without copying raw source bodies."""

    workspace = Path(root)
    reports = workspace / "reports"
    state = workspace / "state"
    warnings: list[str] = []

    bundle_json = _resolve_workspace_path(workspace, bundle_path or state / "profile-pack-investigation-bundle.json")
    bundle_md = _resolve_workspace_path(workspace, bundle_output_path or reports / "profile-pack-investigation-bundle.md")
    bundle = _load_or_generate_bundle(workspace, profile_id, finding_code, bundle_json, bundle_md, warnings)
    selected_items = _selected_items(bundle.items, profile_id, finding_code)
    selection_policy = _selection_policy(profile_id, finding_code)
    schema_result = _validate_bundle(bundle_json, warnings)
    artifacts = _collect_artifacts(workspace, bundle, bundle_json, bundle_md)
    exclusions = _collect_exclusions(workspace, bundle, artifacts)
    review_pack_manifest = workspace / "state" / "workspace-review-pack.json"
    result = ProfilePackInvestigationPackageResult(
        root=str(workspace),
        status=_status(bundle.status, selected_items, artifacts, schema_result),
        package_id=_package_id(workspace, profile_id, finding_code, bundle_json, selected_items),
        profile_id=profile_id,
        finding_code=finding_code,
        selection_policy=selection_policy,
        bundle_path=str(bundle_json),
        bundle_hash=_sha256_file(bundle_json) if bundle_json.exists() else None,
        bundle_status=bundle.status,
        bundle_item_count=bundle.bundle_item_count,
        selected_item_count=len(selected_items),
        schema_valid=bool(schema_result.get("valid")),
        schema_error_count=int(schema_result.get("error_count", 0)),
        review_pack_manifest_path=str(review_pack_manifest) if review_pack_manifest.exists() else None,
        review_pack_manifest_hash=_sha256_file(review_pack_manifest) if review_pack_manifest.exists() else None,
        artifact_count=len(artifacts),
        included_artifact_count=sum(1 for item in artifacts if item.included),
        missing_artifact_count=sum(1 for item in artifacts if not item.exists),
        excluded_artifact_count=len(exclusions),
        artifacts=artifacts,
        exclusions=exclusions,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=sorted(set(warnings)),
    )
    _write_outputs(result, output_path, json_path)
    if zip_path is not None:
        zip_target = _resolve_workspace_path(workspace, zip_path)
        _write_zip(workspace, result, zip_target)
        result.zip_path = str(zip_target)
        result.zip_hash = _sha256_file(zip_target)
        _write_outputs(result, output_path, json_path)
    return result


def load_profile_pack_investigation_package(path: str | Path) -> ProfilePackInvestigationPackageResult:
    return ProfilePackInvestigationPackageResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_pack_investigation_package_markdown(result: ProfilePackInvestigationPackageResult) -> str:
    lines = [
        "# Profile Pack Investigation Package",
        "",
        "> Transfer aid only. This manifest packages generated metadata for reviewer handoff; it does not copy raw official-source bodies, fetch official sources, mutate profile/source records, promote profiles, or certify agency compliance.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Package ID | `{_escape(result.package_id)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Profile filter | {_escape(result.profile_id or '-')} |",
        f"| Finding-code filter | {_escape(result.finding_code or '-')} |",
        f"| Selection policy | {_escape(result.selection_policy)} |",
        f"| Bundle path | `{_escape(result.bundle_path)}` |",
        f"| Bundle hash | {_escape(result.bundle_hash or '-')} |",
        f"| Bundle status | {_escape(result.bundle_status or '-')} |",
        f"| Bundle items | {result.bundle_item_count} |",
        f"| Selected items | {result.selected_item_count} |",
        f"| Schema valid | {result.schema_valid} |",
        f"| Schema errors | {result.schema_error_count} |",
        f"| Review-pack manifest | `{_escape(result.review_pack_manifest_path or '-')}` |",
        f"| Review-pack hash | {_escape(result.review_pack_manifest_hash or '-')} |",
        f"| Artifacts | {result.artifact_count} |",
        f"| Included artifacts | {result.included_artifact_count} |",
        f"| Missing artifacts | {result.missing_artifact_count} |",
        f"| Excluded raw/upstream paths | {result.excluded_artifact_count} |",
        f"| ZIP path | `{_escape(result.zip_path or '-')}` |",
        f"| ZIP hash | {_escape(result.zip_hash or '-')} |",
        "",
        "## Included Metadata Artifacts",
        "",
        "| Included | Role | Type | Exists | SHA-256 | Bytes | Path | Warning |",
        "|---:|---|---|---:|---|---:|---|---|",
    ]
    if not result.artifacts:
        lines.append("| no | - | - | no | - | - | - | No generated metadata artifacts were selected. |")
    for artifact in result.artifacts:
        lines.append(
            "| {included} | {role} | {kind} | {exists} | {sha} | {bytes} | `{path}` | {warning} |".format(
                included="yes" if artifact.included else "no",
                role=_escape(artifact.role),
                kind=_escape(artifact.artifact_type),
                exists="yes" if artifact.exists else "no",
                sha=_escape(artifact.sha256 or "-"),
                bytes=artifact.byte_count if artifact.byte_count is not None else "-",
                path=_escape(artifact.path),
                warning=_escape(artifact.warning or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Explicit Exclusions",
            "",
            "| Path | Reason | Related ID |",
            "|---|---|---|",
        ]
    )
    if not result.exclusions:
        lines.append("| - | No raw/upstream source paths were referenced by the selected bundle. | - |")
    for exclusion in result.exclusions:
        lines.append(
            "| `{path}` | {reason} | {related} |".format(
                path=_escape(exclusion.path),
                reason=_escape(exclusion.reason),
                related=_escape(exclusion.related_id or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- ZIP output, when requested, contains generated Markdown/JSON metadata artifacts only.",
            "- Raw official-source bodies, external source files, and workspace evidence inputs are deliberately excluded.",
            "- Schema validity checks the generated bundle structure only; it does not prove official rule currency.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_or_generate_bundle(
    workspace: Path,
    profile_id: str | None,
    finding_code: str | None,
    bundle_json: Path,
    bundle_md: Path,
    warnings: list[str],
):
    if bundle_json.exists():
        try:
            bundle = load_profile_pack_investigation_bundle(bundle_json)
            if not bundle_md.exists():
                bundle_md.parent.mkdir(parents=True, exist_ok=True)
                bundle_md.write_text(render_profile_pack_investigation_bundle_markdown(bundle), encoding="utf-8")
                warnings.append("profile_pack_investigation_bundle_markdown_regenerated")
            return bundle
        except Exception as exc:
            warnings.append(f"profile_pack_investigation_bundle_unreadable:{exc}")
    warnings.append("profile_pack_investigation_bundle_generated")
    return generate_profile_pack_investigation_bundle(
        workspace,
        profile_id=profile_id,
        finding_code=finding_code,
        output_path=bundle_md,
        json_path=bundle_json,
    )


def _selected_items(bundle_items, profile_id: str | None, finding_code: str | None):
    selected = []
    for item in bundle_items:
        if profile_id and item.profile_id != profile_id:
            continue
        if finding_code and item.finding_code != finding_code:
            continue
        if profile_id or finding_code:
            selected.append(item)
            continue
        if item.severity in {"high", "medium"} and (item.requires_human_review or item.requires_official_source_check):
            selected.append(item)
    return selected


def _selection_policy(profile_id: str | None, finding_code: str | None) -> str:
    parts = []
    if profile_id:
        parts.append(f"profile_id={profile_id}")
    if finding_code:
        parts.append(f"finding_code={finding_code}")
    if parts:
        return ";".join(parts)
    return "open_high_medium_blockers"


def _validate_bundle(bundle_json: Path, warnings: list[str]) -> dict[str, object]:
    if not bundle_json.exists():
        return {"valid": False, "error_count": 1}
    try:
        return validate_json_file(bundle_json, "profile-pack-investigation-bundle")
    except Exception as exc:
        warnings.append(f"profile_pack_investigation_bundle_schema_validation_failed:{exc}")
        return {"valid": False, "error_count": 1}


def _collect_artifacts(workspace: Path, bundle, bundle_json: Path, bundle_md: Path) -> list[ProfilePackInvestigationPackageArtifact]:
    artifacts: dict[tuple[str, str], ProfilePackInvestigationPackageArtifact] = {}
    _add_artifact(artifacts, workspace, "profile_pack_investigation_bundle", "bundle_json", bundle_json)
    _add_artifact(artifacts, workspace, "profile_pack_investigation_bundle_markdown", "bundle_markdown", bundle_md)
    _add_related_pair(artifacts, workspace, "profile_pack_readiness", "readiness", workspace / "state" / "profile-pack-readiness.json", workspace / "reports" / "profile-pack-readiness.md")
    _add_related_pair(artifacts, workspace, "profile_pack_readiness_drilldown", "drilldown", workspace / "state" / "profile-pack-readiness-drilldown.json", workspace / "reports" / "profile-pack-readiness-drilldown.md")
    review_pack_json = workspace / "state" / "workspace-review-pack.json"
    review_pack_md = workspace / "reports" / "workspace-review-pack.md"
    if review_pack_json.exists() or review_pack_md.exists():
        _add_related_pair(artifacts, workspace, "workspace_review_pack", "review_pack_reference", review_pack_json, review_pack_md)
    for artifact in bundle.artifacts:
        path = Path(artifact.path)
        _add_artifact(artifacts, workspace, artifact.artifact_type, "upstream_metadata", path)
    return sorted(artifacts.values(), key=lambda item: (item.role, item.artifact_type, item.path))


def _add_related_pair(
    artifacts: dict[tuple[str, str], ProfilePackInvestigationPackageArtifact],
    workspace: Path,
    artifact_type: str,
    role: str,
    json_path: Path,
    md_path: Path,
) -> None:
    _add_artifact(artifacts, workspace, artifact_type, f"{role}_json", json_path)
    _add_artifact(artifacts, workspace, artifact_type + "_markdown", f"{role}_markdown", md_path)


def _add_artifact(
    artifacts: dict[tuple[str, str], ProfilePackInvestigationPackageArtifact],
    workspace: Path,
    artifact_type: str,
    role: str,
    path: Path,
) -> None:
    resolved = _resolve_workspace_path(workspace, path)
    allowed = _is_allowed_metadata_artifact(workspace, resolved)
    exists = resolved.exists()
    warning = None
    if not allowed:
        warning = "excluded_non_metadata_path"
    elif not exists:
        warning = "missing"
    key = (artifact_type, str(resolved))
    artifacts[key] = ProfilePackInvestigationPackageArtifact(
        artifact_type=artifact_type,
        role=role,
        path=str(resolved),
        exists=exists,
        included=allowed and exists,
        sha256=_sha256_file(resolved) if exists else None,
        byte_count=resolved.stat().st_size if exists else None,
        warning=warning,
    )


def _collect_exclusions(workspace: Path, bundle, artifacts: list[ProfilePackInvestigationPackageArtifact]) -> list[ProfilePackInvestigationPackageExclusion]:
    included = {_normalize_path(item.path) for item in artifacts if item.included}
    exclusions: dict[tuple[str, str | None], ProfilePackInvestigationPackageExclusion] = {}
    for item in bundle.items:
        related = item.source_ref_id or item.drilldown_id or item.bundle_item_id
        for candidate in [item.source_path, item.source_artifact_path]:
            if not candidate:
                continue
            resolved = _resolve_workspace_path(workspace, candidate)
            normalized = _normalize_path(str(resolved))
            if normalized in included:
                continue
            reason = "raw_or_upstream_source_body_excluded"
            if _is_allowed_metadata_artifact(workspace, resolved):
                reason = "not_selected_generated_metadata_artifact"
            exclusions[(str(resolved), related)] = ProfilePackInvestigationPackageExclusion(
                path=str(resolved),
                reason=reason,
                related_id=related,
            )
    return sorted(exclusions.values(), key=lambda item: (item.path, item.related_id or ""))


def _status(bundle_status: str, selected_items, artifacts: list[ProfilePackInvestigationPackageArtifact], schema_result: dict[str, object]) -> str:
    if bundle_status == "not_configured":
        return "not_configured"
    if not schema_result.get("valid"):
        return "blocked"
    if any(item.warning == "missing" for item in artifacts if item.role in {"bundle_json", "bundle_markdown"}):
        return "blocked"
    if not selected_items:
        return "no_matches"
    if any(item.severity == "high" for item in selected_items):
        return "blocked"
    if any(item.requires_human_review or item.requires_official_source_check for item in selected_items):
        return "needs_review"
    if any(not artifact.exists for artifact in artifacts if artifact.included):
        return "needs_review"
    return "ready_with_notes"


def _write_outputs(
    result: ProfilePackInvestigationPackageResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_pack_investigation_package_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _write_zip(workspace: Path, result: ProfilePackInvestigationPackageResult, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for artifact in result.artifacts:
            if not artifact.included or not artifact.exists:
                continue
            path = Path(artifact.path)
            archive.write(path, _archive_name(workspace, path))


def _archive_name(workspace: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return path.name


def _is_allowed_metadata_artifact(workspace: Path, path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(workspace.resolve())
    except ValueError:
        return False
    if relative.parts and relative.parts[0] not in {"state", "reports"}:
        return False
    return path.suffix.lower() in {".json", ".md"}


def _resolve_workspace_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else workspace / candidate


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _package_id(
    workspace: Path,
    profile_id: str | None,
    finding_code: str | None,
    bundle_path: Path,
    selected_items,
) -> str:
    seed = "|".join(
        [
            str(workspace),
            profile_id or "",
            finding_code or "",
            str(bundle_path),
            ",".join(item.bundle_item_id for item in selected_items),
        ]
    )
    return "PPIP-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12].upper()


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").rstrip("/")


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
