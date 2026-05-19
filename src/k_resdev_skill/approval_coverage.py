from __future__ import annotations

import hashlib
from pathlib import Path

from .approval import load_approval_records
from .models import ApprovalDecision, ApprovalRecord, WorkspaceApprovalCoverageItem, WorkspaceApprovalCoverageResult

OPERATIONAL_MARKDOWN_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "artifact-authority.md",
    "bibliography-integrity.md",
    "bibliography-review-summary.md",
    "budget-ledger.md",
    "budget-checklist.md",
    "checkpoint-resume-plan.md",
    "citation-support.md",
    "citation-support-summary.md",
    "evidence-bundle-index.md",
    "goals-review.md",
    "profile-integrity.md",
    "profile-promotion-apply-plan.md",
    "profile-promotion-apply-result.md",
    "profile-lifecycle-ledger.md",
    "profile-promotion-revoke-plan.md",
    "profile-promotion-revoke-result.md",
    "profile-promotion-summary.md",
    "profile-review.md",
    "profile-source-fix-plan.md",
    "profile-source-fix-summary.md",
    "profile-pack-investigation-bundle.md",
    "profile-pack-investigation-package.md",
    "profile-pack-readiness-drilldown.md",
    "profile-pack-readiness.md",
    "profile-source-queue.md",
    "profile-source-summary.md",
    "reference-corpus-summary.md",
    "research-claim-matrix.md",
    "research-claims.md",
    "report-integrity.md",
    "next-actions.md",
    "readiness.md",
    "source-verification.md",
    "trace-passport.md",
    "workspace-discovery.md",
    "workspace-dashboard.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
    "workspace-trace.md",
}
OPERATIONAL_MARKDOWN_PREFIXES = ("weekly-review-", "workflow-")


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
    hash_mismatch_count = sum(1 for item in items if item.hash_status == "mismatch")
    hash_unverified_count = sum(1 for item in items if item.hash_status in {"not_recorded", "missing_target"})
    if not items:
        status = "no_artifacts"
    elif hash_mismatch_count:
        status = "blocked"
    elif missing_count or not_approved_count or hash_unverified_count or warnings:
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
        hash_mismatch_count=hash_mismatch_count,
        hash_unverified_count=hash_unverified_count,
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
        f"| Hash mismatch | {result.hash_mismatch_count} |",
        f"| Hash unverified | {result.hash_unverified_count} |",
        f"| Warnings | {_escape(', '.join(result.warnings) or '-')} |",
        "",
        "## Artifacts",
        "",
        "| Artifact | Path | Target ID | Approved | Decision | Hash Status | Approval ID | Reviewer | Reviewed At | Warnings |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    if not result.items:
        lines.append("| no_artifacts | - | - | False | missing | not_checked | - | - | - | no_report_artifacts |")
    for item in result.items:
        lines.append(
            "| {artifact} | {path} | {target} | {approved} | {decision} | {hash_status} | {approval} | {reviewer} | {reviewed} | {warnings} |".format(
                artifact=_escape(item.artifact_type),
                path=_escape(item.path),
                target=_escape(item.target_id),
                approved=item.approved,
                decision=_escape(item.decision),
                hash_status=_escape(item.hash_status),
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
    artifacts.extend((path, "report_draft") for path in sorted(reports_dir.glob("*.md")) if not _is_operational_markdown(path))
    for pattern in ("*.docx", "*.html", "*.txt"):
        artifacts.extend((path, "projection_export") for path in sorted(reports_dir.glob(pattern)))
    return artifacts


def _is_operational_markdown(path: str | Path) -> bool:
    name = Path(path).name
    return name in OPERATIONAL_MARKDOWN_NAMES or any(name.startswith(prefix) for prefix in OPERATIONAL_MARKDOWN_PREFIXES)


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
    actual_hash = _sha256_file(path) if path.exists() and path.is_file() else None
    actual_size = path.stat().st_size if path.exists() and path.is_file() else None
    hash_status = _hash_status(approval, actual_hash)
    if approved and hash_status == "mismatch":
        warnings.append("approval_target_hash_mismatch")
    elif approved and hash_status in {"not_recorded", "missing_target"}:
        warnings.append("approval_target_hash_unverified")
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
        expected_target_hash=approval.target_hash,
        actual_target_hash=actual_hash,
        expected_size_bytes=approval.target_size_bytes,
        actual_size_bytes=actual_size,
        hash_status=hash_status,
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


def _hash_status(record: ApprovalRecord, actual_hash: str | None) -> str:
    if str(record.decision) != ApprovalDecision.APPROVED.value:
        return "not_checked"
    if actual_hash is None:
        return "missing_target"
    if not record.target_hash:
        return "not_recorded"
    return "ok" if actual_hash == record.target_hash else "mismatch"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


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
