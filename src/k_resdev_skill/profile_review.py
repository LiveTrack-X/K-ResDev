from __future__ import annotations

import hashlib
from pathlib import Path

from .models import ProfileReviewChecklistItem, ProfileReviewResult, ProfileSource, ProjectProfile
from .profile_registry import load_project_profile
from .profile_sources import default_profile_sources_path, load_profile_sources


def generate_profile_review(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfileReviewResult:
    """Generate a promotion-readiness review for the local project profile."""

    workspace = Path(root)
    profile_path = workspace / "state" / "project-profile.json"
    source_path = default_profile_sources_path(workspace)
    warnings: list[str] = []
    checklist: list[ProfileReviewChecklistItem] = []
    profile: ProjectProfile | None = None
    sources: list[ProfileSource] = []

    if not profile_path.exists():
        checklist.append(
            _item(
                "profile_present",
                "Profile file exists",
                False,
                "high",
                "No project profile file was found.",
                path=str(profile_path),
                suggested_action="Run init-workspace or add state/project-profile.json before profile review.",
            )
        )
    else:
        try:
            profile = load_project_profile(profile_path)
            checklist.append(
                _item(
                    "profile_present",
                    "Profile file exists",
                    True,
                    "high",
                    f"Profile `{profile.profile_id}` was loaded.",
                    path=str(profile_path),
                )
            )
        except Exception as exc:
            checklist.append(
                _item(
                    "profile_present",
                    "Profile file exists",
                    False,
                    "high",
                    f"Project profile could not be read: {exc}",
                    path=str(profile_path),
                    suggested_action="Fix state/project-profile.json before profile review.",
                )
            )

    if profile is not None:
        if profile.status == "deprecated":
            checklist.append(
                _item(
                    "profile_not_deprecated",
                    "Profile is not deprecated",
                    False,
                    "high",
                    f"Profile `{profile.profile_id}` is deprecated.",
                    path=str(profile_path),
                    suggested_action="Choose a current profile seed before promotion review.",
                )
            )
        else:
            checklist.append(
                _item(
                    "profile_not_deprecated",
                    "Profile is not deprecated",
                    True,
                    "high",
                    f"Profile status is `{profile.status}`.",
                    path=str(profile_path),
                )
            )

    if not source_path.exists():
        checklist.append(
            _item(
                "profile_sources_present",
                "Profile source records exist",
                False,
                "medium",
                "No profile source index was found.",
                path=str(source_path),
                suggested_action="Record hash-backed official source metadata before profile promotion.",
            )
        )
    else:
        try:
            all_sources = load_profile_sources(source_path)
            sources = [source for source in all_sources if profile is None or source.profile_id == profile.profile_id]
        except Exception as exc:
            warnings.append(f"profile_sources_unreadable:{exc}")
            checklist.append(
                _item(
                    "profile_sources_present",
                    "Profile source records exist",
                    False,
                    "high",
                    f"Profile source index could not be read: {exc}",
                    path=str(source_path),
                    suggested_action="Fix state/profile-sources.json before profile promotion.",
                )
            )

    checklist.append(
        _item(
            "profile_sources_non_empty",
            "At least one profile source applies",
            bool(sources),
            "medium",
            f"{len(sources)} source record(s) apply to the profile.",
            path=str(source_path),
            suggested_action="Add at least one official source record for this profile." if not sources else None,
        )
    )

    for source in sources:
        checklist.extend(_source_checks(workspace, source))

    failed = [item for item in checklist if item.status == "fail"]
    warnings_items = [item for item in checklist if item.status == "warn"]
    passed = [item for item in checklist if item.status == "pass"]
    can_promote = bool(sources) and not failed and all(source.review_status == "verified" for source in sources)
    status = _status(can_promote, failed)
    result = ProfileReviewResult(
        root=str(workspace),
        profile_id=profile.profile_id if profile else None,
        profile_status=profile.status if profile else None,
        status=status,
        can_promote=can_promote,
        checklist_count=len(checklist),
        passed_count=len(passed),
        failed_count=len(failed),
        warning_count=len(warnings_items),
        source_count=len(sources),
        verified_source_count=sum(1 for source in sources if source.review_status == "verified"),
        checklist=checklist,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=warnings,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_review_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_profile_review_markdown(result: ProfileReviewResult) -> str:
    lines = [
        "# Profile Review",
        "",
        "> Profile review projection only. This checks local source records and human-review metadata; it does not certify official agency compliance, legal currency, or submission readiness.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Profile | {_escape(result.profile_id or 'missing')} |",
        f"| Profile status | {_escape(result.profile_status or 'missing')} |",
        f"| Review status | {_escape(result.status)} |",
        f"| Can promote | {result.can_promote} |",
        f"| Sources | {result.source_count} |",
        f"| Verified sources | {result.verified_source_count} |",
        f"| Checklist | {result.checklist_count} |",
        f"| Failed | {result.failed_count} |",
        f"| Warnings | {result.warning_count} |",
        "",
        "## Checklist",
        "",
        "| Status | Severity | Check | Source | Path | Message | Suggested Action |",
        "|---|---|---|---|---|---|---|",
    ]
    if not result.checklist:
        lines.append("| fail | high | profile_review_empty | - | - | No profile review checks were generated. | Re-run profile-review. |")
    for item in result.checklist:
        lines.append(
            "| {status} | {severity} | {check} | {source} | {path} | {message} | {action} |".format(
                status=_escape(item.status),
                severity=_escape(item.severity),
                check=_escape(item.title),
                source=_escape(item.source_id or "-"),
                path=_escape(item.path or "-"),
                message=_escape(item.message),
                action=_escape(item.suggested_action or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Promotion Boundary",
            "",
            "- `can_promote=true` means local metadata is ready for a human-controlled profile status change.",
            "- This command never changes `state/project-profile.json` and never creates an official approval.",
            "- Keep source-backed profiles in `needs_review` until a project owner records explicit verification.",
            "",
        ]
    )
    return "\n".join(lines)


def load_profile_review(path: str | Path) -> ProfileReviewResult:
    return ProfileReviewResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def _source_checks(workspace: Path, source: ProfileSource) -> list[ProfileReviewChecklistItem]:
    items = [
        _item(
            f"{source.source_id}:review_status_verified",
            "Source is human-verified",
            source.review_status == "verified",
            "medium",
            f"Source `{source.source_id}` review_status is `{source.review_status}`.",
            source_id=source.source_id,
            path=source.source_file,
            suggested_action="Record supplied human verification before profile promotion." if source.review_status != "verified" else None,
        ),
        _item(
            f"{source.source_id}:verified_by_present",
            "Reviewer identity is recorded",
            bool(source.verified_by),
            "medium",
            f"Source `{source.source_id}` reviewer is `{source.verified_by or 'missing'}`.",
            source_id=source.source_id,
            path=source.source_file,
            suggested_action="Set verified_by on the profile source record after human review." if not source.verified_by else None,
        ),
        _item(
            f"{source.source_id}:retrieved_at_present",
            "Retrieved date is recorded",
            bool(source.retrieved_at),
            "medium",
            f"Source `{source.source_id}` retrieved_at is `{source.retrieved_at or 'missing'}`.",
            source_id=source.source_id,
            path=source.source_file,
            suggested_action="Record the retrieval date for the official source." if not source.retrieved_at else None,
        ),
        _item(
            f"{source.source_id}:applicability_notes_present",
            "Applicability notes are recorded",
            bool(source.validity_notes),
            "medium",
            f"Source `{source.source_id}` validity notes are {'present' if source.validity_notes else 'missing'}.",
            source_id=source.source_id,
            path=source.source_file,
            suggested_action="Explain the profile scope and applicability before promotion." if not source.validity_notes else None,
        ),
        _item(
            f"{source.source_id}:risk_flags_resolved",
            "Risk flags are resolved",
            not source.risk_flags,
            "medium",
            f"Source `{source.source_id}` has {len(source.risk_flags)} unresolved risk flag(s).",
            source_id=source.source_id,
            path=source.source_file,
            suggested_action="Clear or supersede risk flags after human review before promotion." if source.risk_flags else None,
        ),
    ]
    items.extend(_source_file_checks(workspace, source))
    return items


def _source_file_checks(workspace: Path, source: ProfileSource) -> list[ProfileReviewChecklistItem]:
    if not source.source_file:
        return [
            _item(
                f"{source.source_id}:source_file_present",
                "Hash-backed source file exists",
                False,
                "high",
                f"Source `{source.source_id}` has no local source file.",
                source_id=source.source_id,
                suggested_action="Store a local source snapshot or review note before promotion.",
            )
        ]
    path = _resolve_file(source.source_file, workspace)
    if path is None:
        return [
            _item(
                f"{source.source_id}:source_file_present",
                "Hash-backed source file exists",
                False,
                "high",
                f"Source file `{source.source_file}` is missing.",
                source_id=source.source_id,
                path=source.source_file,
                suggested_action="Restore the source file or update the source record.",
            )
        ]
    expected_hash = _normalize_hash(source.source_hash)
    hash_ok = expected_hash is not None and _sha256_file(path) == expected_hash
    return [
        _item(
            f"{source.source_id}:source_file_present",
            "Hash-backed source file exists",
            True,
            "high",
            f"Source file `{source.source_file}` exists.",
            source_id=source.source_id,
            path=source.source_file,
        ),
        _item(
            f"{source.source_id}:source_hash_matches",
            "Source hash matches",
            hash_ok,
            "high",
            f"Source `{source.source_id}` hash {'matches' if hash_ok else 'is missing or changed'}.",
            source_id=source.source_id,
            path=source.source_file,
            suggested_action="Re-review the source and record a fresh hash before promotion." if not hash_ok else None,
        ),
    ]


def _item(
    check_id: str,
    title: str,
    passed: bool,
    severity: str,
    message: str,
    *,
    source_id: str | None = None,
    path: str | None = None,
    suggested_action: str | None = None,
) -> ProfileReviewChecklistItem:
    return ProfileReviewChecklistItem(
        check_id=check_id,
        title=title,
        status="pass" if passed else "fail",
        severity=severity,
        message=message,
        source_id=source_id,
        path=path,
        suggested_action=suggested_action,
    )


def _status(can_promote: bool, failed: list[ProfileReviewChecklistItem]) -> str:
    if can_promote:
        return "ready_for_human_promotion"
    if any(item.severity == "high" for item in failed):
        return "blocked"
    return "needs_review"


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
    return digest.hexdigest()


def _normalize_hash(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.lower()
    if normalized.startswith("sha256:"):
        normalized = normalized.split(":", 1)[1]
    return normalized


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
