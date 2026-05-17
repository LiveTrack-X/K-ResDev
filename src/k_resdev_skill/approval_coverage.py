from __future__ import annotations

from pathlib import Path

from .approval import load_approval_records
from .models import ApprovalDecision, ApprovalRecord, WorkspaceApprovalCoverageItem, WorkspaceApprovalCoverageResult

OPERATIONAL_MARKDOWN_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "budget-checklist.md",
    "evidence-bundle-index.md",
    "next-actions.md",
    "readiness.md",
    "source-verification.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
}


def generate_workspace_approval_coverage(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceApprovalCoverageResult:
    """Check whether report artifacts have supplied human approval records."""

    workspace = Path(root)
    warnings: list[str] = []
    try:
        approvals = load_approval_records(workspace / "state" / "approvals")
    except Exception as exc:
        approvals = []
        warnings.append(f"approvals_unreadable:{exc}")

    artifacts = _report_artifacts(workspace)
    items = [_coverage_item(workspace, path, artifact_type, approvals) for path, artifact_type in artifacts]
    approved_count = sum(1 for item in items if item.approved)
    missing_count = sum(1 for item in items if item.decision == "missing")
    not_approved_count = sum(1 for item in items if item.decision != "missing" and not item.approved)
    if not items:
        status = "no_artifacts"
    elif missing_count or not_approved_count or warnings:
        status = "needs_review"
    else:
        status = "ready"

    result = WorkspaceApprovalCoverageResult(
        root=str(workspace),
        status=status,
        artifact_count=len(items),
        approved_count=approved_count,
        missing_count=missing_count,
        not_approved_count=not_approved_count,
        items=items,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=warnings,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_approval_coverage_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_approval_coverage_markdown(result: WorkspaceApprovalCoverageResult) -> str:
    lines = [
        "# Workspace Approval Coverage",
        "",
        "> Human decision coverage only. This checks whether local report artifacts are linked to supplied approval records; it does not approve or certify any artifact.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Artifact count | {result.artifact_count} |",
        f"| Approved | {result.approved_count} |",
        f"| Missing approval | {result.missing_count} |",
        f"| Not approved | {result.not_approved_count} |",
        f"| Warnings | {_escape(', '.join(result.warnings) or '-')} |",
        "",
        "## Artifacts",
        "",
        "| Artifact | Path | Target ID | Approved | Decision | Approval ID | Reviewer | Reviewed At | Warnings |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    if not result.items:
        lines.append("| no_artifacts | - | - | False | missing | - | - | - | no_report_artifacts |")
    for item in result.items:
        lines.append(
            "| {artifact} | {path} | {target} | {approved} | {decision} | {approval} | {reviewer} | {reviewed} | {warnings} |".format(
                artifact=_escape(item.artifact_type),
                path=_escape(item.path),
                target=_escape(item.target_id),
                approved=item.approved,
                decision=_escape(item.decision),
                approval=_escape(item.approval_id or "-"),
                reviewer=_escape(item.reviewer or "-"),
                reviewed=_escape(item.reviewed_at or "-"),
                warnings=_escape(", ".join(item.warnings) or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _report_artifacts(workspace: Path) -> list[tuple[Path, str]]:
    reports_dir = workspace / "reports"
    if not reports_dir.exists():
        return []
    artifacts: list[tuple[Path, str]] = []
    artifacts.extend((path, "report_draft") for path in sorted(reports_dir.glob("*.md")) if path.name not in OPERATIONAL_MARKDOWN_NAMES)
    for pattern in ("*.docx", "*.html", "*.txt"):
        artifacts.extend((path, "projection_export") for path in sorted(reports_dir.glob(pattern)))
    return artifacts


def _coverage_item(
    workspace: Path,
    path: Path,
    artifact_type: str,
    approvals: list[ApprovalRecord],
) -> WorkspaceApprovalCoverageItem:
    candidates = _target_id_candidates(workspace, path)
    approval = _latest_matching_approval(workspace, path, candidates, approvals)
    if approval is None:
        return WorkspaceApprovalCoverageItem(
            path=str(path),
            artifact_type=artifact_type,
            target_id=candidates[0],
            target_id_candidates=candidates,
            warnings=["approval_missing"],
        )
    approved = approval.decision == ApprovalDecision.APPROVED.value
    warnings = [] if approved else ["latest_decision_not_approved"]
    return WorkspaceApprovalCoverageItem(
        path=str(path),
        artifact_type=artifact_type,
        target_id=approval.target_id,
        target_id_candidates=candidates,
        approved=approved,
        decision=str(approval.decision),
        approval_id=approval.approval_id,
        reviewer=approval.reviewer,
        reviewed_at=approval.reviewed_at,
        warnings=warnings,
    )


def _latest_matching_approval(
    workspace: Path,
    path: Path,
    target_id_candidates: list[str],
    approvals: list[ApprovalRecord],
) -> ApprovalRecord | None:
    path_candidates = _target_path_candidates(workspace, path)
    matches = [
        record
        for record in approvals
        if str(record.target_type) == "report"
        and (record.target_id in target_id_candidates or _normalize_target_path(record.target_path) in path_candidates)
    ]
    return max(matches, key=lambda record: record.reviewed_at, default=None)


def _target_id_candidates(workspace: Path, path: Path) -> list[str]:
    relative = _relative_path(workspace, path)
    candidates = [
        path.stem,
        relative.as_posix(),
        str(relative),
        path.name,
    ]
    if path.stem.startswith("monthly-report-"):
        candidates.append(f"monthly-{path.stem.removeprefix('monthly-report-')}")
    return _unique(candidates)


def _target_path_candidates(workspace: Path, path: Path) -> set[str]:
    relative = _relative_path(workspace, path)
    candidates = {
        _normalize_target_path(str(path)),
        _normalize_target_path(str(path.resolve())),
        _normalize_target_path(relative.as_posix()),
        _normalize_target_path(str(relative)),
    }
    return {value for value in candidates if value}


def _relative_path(workspace: Path, path: Path) -> Path:
    try:
        return path.relative_to(workspace)
    except ValueError:
        return Path(path.name)


def _normalize_target_path(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("\\", "/").strip()


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
