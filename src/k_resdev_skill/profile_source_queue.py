from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import ProfileSource, ProfileSourceQueueItem, ProfileSourceQueueResult, ProjectProfile
from .profile_registry import default_agency_templates_root, load_project_profile
from .profile_sources import default_profile_sources_path, load_profile_sources

PROFILE_SOURCE_STATUSES = {"needs_review", "verified", "rejected", "superseded"}


def generate_profile_source_queue(
    root: str | Path,
    templates_root: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfileSourceQueueResult:
    """Scan profile source packs and produce a local review queue without certifying agency rules."""

    workspace = Path(root)
    template_root = Path(templates_root) if templates_root is not None else default_agency_templates_root()
    items: list[ProfileSourceQueueItem] = []
    warnings: list[str] = []
    template_profiles: dict[str, ProjectProfile] = {}
    workspace_profiles: dict[str, ProjectProfile] = {}
    source_count = 0

    for profile, profile_path, source_path in _iter_template_profiles(template_root, warnings):
        template_profiles[profile.profile_id] = profile
        sources = _load_sources(source_path, warnings, "template")
        source_count += len(sources)
        items.extend(
            _profile_items(
                scope="template",
                profile=profile,
                profile_path=profile_path,
                source_path=source_path,
                sources=sources,
                source_file_root=source_path.parent,
            )
        )

    workspace_profile, workspace_profile_path = _load_workspace_profile(workspace, warnings)
    workspace_source_path = default_profile_sources_path(workspace)
    workspace_sources = _load_sources(workspace_source_path, warnings, "workspace") if workspace_source_path.exists() else []
    if workspace_profile is not None:
        workspace_profiles[workspace_profile.profile_id] = workspace_profile
    for source in workspace_sources:
        workspace_profiles.setdefault(source.profile_id, ProjectProfile(profile_id=source.profile_id))
    source_count += len(workspace_sources)

    for profile_id, profile in sorted(workspace_profiles.items()):
        source_path = workspace_source_path
        selected = [source for source in workspace_sources if source.profile_id == profile_id]
        items.extend(
            _profile_items(
                scope="workspace",
                profile=profile,
                profile_path=workspace_profile_path if workspace_profile and workspace_profile.profile_id == profile_id else None,
                source_path=source_path,
                sources=selected,
                source_file_root=workspace,
            )
        )

    if not template_profiles and workspace_profile is None and not workspace_sources:
        result = ProfileSourceQueueResult(
            root=str(workspace),
            status="not_configured",
            templates_root=str(template_root),
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
            warnings=warnings,
        )
        _write_outputs(result, output_path, json_path)
        return result

    items = _dedupe_items(items)
    profiles = set(template_profiles) | set(workspace_profiles)
    result = ProfileSourceQueueResult(
        root=str(workspace),
        status=_status_from_items(items),
        templates_root=str(template_root),
        profile_count=len(profiles),
        template_profile_count=len(template_profiles),
        workspace_profile_count=len(workspace_profiles),
        source_count=source_count,
        queue_item_count=len(items),
        high_count=sum(1 for item in items if item.severity == "high"),
        medium_count=sum(1 for item in items if item.severity == "medium"),
        low_count=sum(1 for item in items if item.severity == "low"),
        items=items,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=sorted(set(warnings)),
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_profile_source_queue(path: str | Path) -> ProfileSourceQueueResult:
    return ProfileSourceQueueResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_source_queue_markdown(result: ProfileSourceQueueResult) -> str:
    lines = [
        "# Profile Source Queue",
        "",
        "> Review queue projection only. This scans local profile source metadata for missing or stale review inputs; it does not certify official agency compliance, legal currency, or submission readiness.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Templates root | `{_escape(result.templates_root or '-')}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Profiles | {result.profile_count} |",
        f"| Template profiles | {result.template_profile_count} |",
        f"| Workspace profiles | {result.workspace_profile_count} |",
        f"| Source records | {result.source_count} |",
        f"| Queue items | {result.queue_item_count} |",
        f"| High items | {result.high_count} |",
        f"| Medium items | {result.medium_count} |",
        f"| Low items | {result.low_count} |",
        "",
        "## Queue",
        "",
        "| Severity | Scope | Profile | Source | Issue | Message | Path | Suggested Action | Risk Flags |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    if not result.items:
        lines.append("| ok | - | - | - | profile_source_queue_ready | No profile source queue items detected. | - | Keep official source metadata current. | - |")
    for item in result.items:
        lines.append(
            "| {severity} | {scope} | {profile} | {source} | {issue} | {message} | {path} | {action} | {risks} |".format(
                severity=_escape(item.severity),
                scope=_escape(item.scope),
                profile=_escape(item.profile_id),
                source=_escape(item.source_id or "-"),
                issue=_escape(item.issue_code),
                message=_escape(item.message),
                path=_escape(item.source_file or item.source_record_path or item.profile_path or "-"),
                action=_escape(item.suggested_action or "-"),
                risks=_escape(", ".join(item.risk_flags) or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Queue items indicate local metadata gaps only.",
            "- A profile remains `needs_review` until official source records and supplied human decisions support promotion.",
            "- Do not use this output as proof that agency rules, forms, or dates are current.",
            "",
        ]
    )
    return "\n".join(lines)


def _iter_template_profiles(
    templates_root: Path,
    warnings: list[str],
) -> list[tuple[ProjectProfile, Path, Path]]:
    if not templates_root.exists():
        warnings.append(f"templates_root_missing:{templates_root}")
        return []
    profiles: list[tuple[ProjectProfile, Path, Path]] = []
    for profile_path in sorted(templates_root.glob("*/project-profile.json")):
        try:
            profile = load_project_profile(profile_path)
        except Exception as exc:
            warnings.append(f"template_profile_unreadable:{profile_path}:{exc}")
            continue
        profiles.append((profile, profile_path, profile_path.parent / "profile-sources.json"))
    return profiles


def _load_workspace_profile(workspace: Path, warnings: list[str]) -> tuple[ProjectProfile | None, Path | None]:
    path = workspace / "state" / "project-profile.json"
    if not path.exists():
        return None, None
    try:
        return load_project_profile(path), path
    except Exception as exc:
        warnings.append(f"workspace_profile_unreadable:{exc}")
        return None, path


def _load_sources(path: Path, warnings: list[str], scope: str) -> list[ProfileSource]:
    if not path.exists():
        return []
    try:
        return load_profile_sources(path)
    except Exception as exc:
        warnings.append(f"{scope}_profile_sources_unreadable:{path}:{exc}")
        return []


def _profile_items(
    scope: str,
    profile: ProjectProfile,
    profile_path: Path | None,
    source_path: Path,
    sources: list[ProfileSource],
    source_file_root: Path,
) -> list[ProfileSourceQueueItem]:
    items: list[ProfileSourceQueueItem] = []
    if not sources:
        items.append(
            _item(
                scope=scope,
                profile=profile,
                profile_path=profile_path,
                source_path=source_path,
                source=None,
                issue_code="profile_source_records_missing",
                severity="medium",
                message=f"No profile source records were found for `{profile.profile_id}`.",
                suggested_action="Record source URL/file metadata before treating this profile pack as verified.",
            )
        )
    verified_count = sum(1 for source in sources if source.review_status == "verified")
    if profile.status == "verified" and verified_count == 0:
        items.append(
            _item(
                scope=scope,
                profile=profile,
                profile_path=profile_path,
                source_path=source_path,
                source=None,
                issue_code="profile_verified_without_verified_source",
                severity="high",
                message=f"Profile `{profile.profile_id}` is verified but no verified source record is present.",
                suggested_action="Add a verified source record or set the profile back to needs_review.",
            )
        )
    for source in sources:
        items.extend(_source_items(scope, profile, profile_path, source_path, source, source_file_root))
    return items


def _source_items(
    scope: str,
    profile: ProjectProfile,
    profile_path: Path | None,
    source_path: Path,
    source: ProfileSource,
    source_file_root: Path,
) -> list[ProfileSourceQueueItem]:
    items: list[ProfileSourceQueueItem] = []
    if source.review_status not in PROFILE_SOURCE_STATUSES:
        items.append(
            _item(
                scope,
                profile,
                profile_path,
                source_path,
                source,
                "profile_source_unknown_status",
                "medium",
                f"Profile source `{source.source_id}` has unknown review_status `{source.review_status}`.",
                "Use needs_review, verified, rejected, or superseded.",
            )
        )
    if source.review_status != "verified":
        severity = "high" if source.review_status in {"rejected", "superseded"} else "medium"
        items.append(
            _item(
                scope,
                profile,
                profile_path,
                source_path,
                source,
                "profile_source_not_verified",
                severity,
                f"Profile source `{source.source_id}` is `{source.review_status}`.",
                "Keep profile packs in needs_review or record supplied human verification.",
            )
        )
    if not source.source_url and not source.source_file:
        items.append(
            _item(
                scope,
                profile,
                profile_path,
                source_path,
                source,
                "profile_source_locator_missing",
                "medium",
                f"Profile source `{source.source_id}` has no source URL or source file.",
                "Record source_url or source_file before relying on this profile source.",
            )
        )
    if not source.retrieved_at:
        items.append(
            _item(
                scope,
                profile,
                profile_path,
                source_path,
                source,
                "profile_source_retrieved_at_missing",
                "medium",
                f"Profile source `{source.source_id}` has no retrieved_at date.",
                "Record when the source was retrieved or reviewed.",
            )
        )
    if not source.source_hash:
        severity = "medium" if source.review_status == "verified" else "low"
        items.append(
            _item(
                scope,
                profile,
                profile_path,
                source_path,
                source,
                "profile_source_hash_missing",
                severity,
                f"Profile source `{source.source_id}` has no source hash.",
                "Keep a hash-backed local source note or official source copy when possible.",
            )
        )
    if source.review_status == "verified" and not source.verified_by:
        items.append(
            _item(
                scope,
                profile,
                profile_path,
                source_path,
                source,
                "profile_source_verified_by_missing",
                "medium",
                f"Profile source `{source.source_id}` is verified but has no verified_by reviewer.",
                "Record the supplied human reviewer before promotion.",
            )
        )
    if source.risk_flags:
        items.append(
            _item(
                scope,
                profile,
                profile_path,
                source_path,
                source,
                "profile_source_unresolved_risk_flags",
                "medium",
                f"Profile source `{source.source_id}` still has risk flags.",
                "Resolve or explicitly accept risk flags before profile promotion.",
            )
        )
    if source.source_file:
        resolved = _resolve_file(source.source_file, source_file_root)
        if resolved is None:
            items.append(
                _item(
                    scope,
                    profile,
                    profile_path,
                    source_path,
                    source,
                    "profile_source_file_missing",
                    "high",
                    f"Profile source file `{source.source_file}` is missing.",
                    "Restore the local source file or update the profile source record.",
                )
            )
        elif source.source_hash and _normalize_hash(_sha256_file(resolved)) != _normalize_hash(source.source_hash):
            items.append(
                _item(
                    scope,
                    profile,
                    profile_path,
                    source_path,
                    source,
                    "profile_source_hash_mismatch",
                    "high",
                    f"Profile source file `{source.source_file}` changed after source metadata was recorded.",
                    "Re-review the source and record a new hash-backed profile source record.",
                )
            )
    return items


def _item(
    scope: str,
    profile: ProjectProfile,
    profile_path: Path | None,
    source_path: Path,
    source: ProfileSource | None,
    issue_code: str,
    severity: str,
    message: str,
    suggested_action: str,
) -> ProfileSourceQueueItem:
    source_id = source.source_id if source else None
    return ProfileSourceQueueItem(
        queue_id=_queue_id(scope, profile.profile_id, source_id, issue_code),
        scope=scope,
        profile_id=profile.profile_id,
        profile_status=profile.status,
        profile_path=str(profile_path) if profile_path else None,
        source_id=source_id,
        source_title=source.title if source else None,
        source_status=source.review_status if source else None,
        source_url=source.source_url if source else None,
        source_file=source.source_file if source else None,
        source_record_path=str(source_path),
        issue_code=issue_code,
        severity=severity,
        message=message,
        suggested_action=suggested_action,
        risk_flags=source.risk_flags if source else [],
    )


def _write_outputs(
    result: ProfileSourceQueueResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_source_queue_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _dedupe_items(items: list[ProfileSourceQueueItem]) -> list[ProfileSourceQueueItem]:
    deduped: dict[tuple[str, str, str | None, str], ProfileSourceQueueItem] = {}
    for item in items:
        deduped[(item.scope, item.profile_id, item.source_id, item.issue_code)] = item
    return sorted(deduped.values(), key=lambda item: (_severity_rank(item.severity), item.scope, item.profile_id, item.source_id or "", item.issue_code))


def _status_from_items(items: list[ProfileSourceQueueItem]) -> str:
    if any(item.severity == "high" for item in items):
        return "blocked"
    if any(item.severity == "medium" for item in items):
        return "needs_review"
    if items:
        return "ready_with_notes"
    return "ready"


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _queue_id(scope: str, profile_id: str, source_id: str | None, issue_code: str) -> str:
    digest = hashlib.sha256(f"{scope}|{profile_id}|{source_id or ''}|{issue_code}".encode("utf-8")).hexdigest()
    return f"PSQ-{digest[:12].upper()}"


def _resolve_file(path: str, root: Path) -> Path | None:
    target = Path(path)
    candidates = [target]
    if not target.is_absolute():
        candidates.append(root / target)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _normalize_hash(value: str) -> str:
    text = value.strip().lower()
    return text.split(":", 1)[1] if text.startswith("sha256:") else text


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
