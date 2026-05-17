from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import (
    ReviewPackArtifact,
    ReviewPackVerificationItem,
    WorkspaceReviewPackResult,
    WorkspaceReviewPackVerificationResult,
)
from .approval_coverage import generate_workspace_approval_coverage
from .bibliography_integrity import generate_workspace_bibliography_integrity
from .citation_support import generate_workspace_citation_support_integrity
from .report_integrity import generate_workspace_report_integrity
from .source_verification import verify_evidence_sources
from .workspace import run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan
from .workspace_summary import generate_workspace_summary


def generate_workspace_review_pack(
    root: str | Path,
    reports_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
    max_actions: int = 5,
) -> WorkspaceReviewPackResult:
    """Generate a bundled local review pack for readiness, actions, source, approval, report, bibliography, and citation-support checks."""

    workspace = Path(root)
    reports = Path(reports_dir) if reports_dir is not None else workspace / "reports"
    state = Path(state_dir) if state_dir is not None else workspace / "state"
    reports.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)

    readiness_md = reports / "readiness.md"
    readiness_json = state / "readiness.json"
    actions_md = reports / "next-actions.md"
    actions_json = state / "next-actions.json"
    summary_md = reports / "workspace-summary.md"
    summary_json = state / "workspace-summary.json"
    source_md = reports / "source-verification.md"
    source_json = state / "source-verification.json"
    approval_md = reports / "approval-coverage.md"
    approval_json = state / "approval-coverage.json"
    report_integrity_md = reports / "report-integrity.md"
    report_integrity_json = state / "report-integrity.json"
    bibliography_integrity_md = reports / "bibliography-integrity.md"
    bibliography_integrity_json = state / "bibliography-integrity.json"
    citation_support_md = reports / "citation-support.md"
    citation_support_json = state / "citation-support.json"
    index_md = reports / "workspace-review-pack.md"
    index_json = state / "workspace-review-pack.json"

    doctor = run_workspace_doctor(workspace, readiness_md, readiness_json)
    source_verification = verify_evidence_sources(state / "evidence-index.json", root=workspace, output_path=source_md, json_path=source_json)
    approval_coverage = generate_workspace_approval_coverage(workspace, output_path=approval_md, json_path=approval_json)
    report_integrity = generate_workspace_report_integrity(workspace, output_path=report_integrity_md, json_path=report_integrity_json)
    bibliography_integrity = generate_workspace_bibliography_integrity(workspace, output_path=bibliography_integrity_md, json_path=bibliography_integrity_json)
    citation_support = generate_workspace_citation_support_integrity(workspace, output_path=citation_support_md, json_path=citation_support_json)
    actions = generate_workspace_action_plan(workspace, doctor_result=doctor, output_path=actions_md, json_path=actions_json)
    summary = generate_workspace_summary(
        workspace,
        output_path=summary_md,
        json_path=summary_json,
        max_actions=max_actions,
        doctor_result=doctor,
        action_plan=actions,
    )
    generated_paths = [
        str(readiness_md),
        str(readiness_json),
        str(actions_md),
        str(actions_json),
        str(summary_md),
        str(summary_json),
        str(source_md),
        str(source_json),
        str(approval_md),
        str(approval_json),
        str(report_integrity_md),
        str(report_integrity_json),
        str(bibliography_integrity_md),
        str(bibliography_integrity_json),
        str(citation_support_md),
        str(citation_support_json),
        str(index_md),
        str(index_json),
    ]
    result = WorkspaceReviewPackResult(
        root=str(workspace),
        status=doctor.status,
        evidence_count=summary.evidence_count,
        approval_count=summary.approval_count,
        finding_count=doctor.finding_count,
        action_count=actions.action_count,
        source_verification_valid=source_verification.valid,
        source_missing_count=source_verification.missing_count,
        source_mismatch_count=source_verification.mismatch_count,
        approval_coverage_status=approval_coverage.status,
        approval_missing_count=approval_coverage.missing_count,
        approval_not_approved_count=approval_coverage.not_approved_count,
        approval_hash_mismatch_count=approval_coverage.hash_mismatch_count,
        approval_hash_unverified_count=approval_coverage.hash_unverified_count,
        report_integrity_status=report_integrity.status,
        report_integrity_finding_count=report_integrity.finding_count,
        report_integrity_high_count=report_integrity.high_count,
        bibliography_integrity_status=bibliography_integrity.status,
        bibliography_entry_count=bibliography_integrity.entry_count,
        bibliography_review_count=bibliography_integrity.review_count,
        bibliography_citation_count=bibliography_integrity.citation_count,
        bibliography_integrity_finding_count=bibliography_integrity.finding_count,
        bibliography_integrity_high_count=bibliography_integrity.high_count,
        citation_support_status=citation_support.status,
        citation_support_count=citation_support.support_count,
        citation_support_citation_count=citation_support.citation_count,
        citation_support_finding_count=citation_support.finding_count,
        citation_support_high_count=citation_support.high_count,
        generated_paths=generated_paths,
        index_path=str(index_md),
        json_path=str(index_json),
    )
    result = result.model_copy(update={"artifacts": _artifact_manifest(generated_paths, exclude={str(index_md), str(index_json)})})
    index_md.write_text(render_workspace_review_pack_markdown(result), encoding="utf-8")
    index_json.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def verify_workspace_review_pack(manifest_json: str | Path) -> WorkspaceReviewPackVerificationResult:
    """Verify review-pack generated artifacts against the saved manifest hashes."""

    manifest_path = Path(manifest_json)
    warnings: list[str] = []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        pack = WorkspaceReviewPackResult.model_validate(payload)
    except Exception as exc:
        return WorkspaceReviewPackVerificationResult(
            manifest_path=str(manifest_path),
            valid=False,
            warnings=[f"manifest_unreadable:{exc}"],
        )

    if not pack.artifacts:
        warnings.append("manifest_has_no_artifact_hashes")
    items = [_verify_artifact(artifact) for artifact in pack.artifacts]
    ok_count = sum(1 for item in items if item.status == "ok")
    missing_count = sum(1 for item in items if item.status == "missing")
    mismatch_count = sum(1 for item in items if item.status == "mismatch")
    unchecked_count = len(pack.generated_paths) - len(pack.artifacts)
    if str(manifest_path) in pack.generated_paths:
        unchecked_count = max(unchecked_count, 1)
        warnings.append("manifest_file_hash_not_self_checked")
    if unchecked_count:
        warnings.append("some_generated_paths_are_not_hash_checked")
    return WorkspaceReviewPackVerificationResult(
        manifest_path=str(manifest_path),
        valid=bool(items) and missing_count == 0 and mismatch_count == 0,
        checked_count=len(items),
        ok_count=ok_count,
        missing_count=missing_count,
        mismatch_count=mismatch_count,
        unchecked_count=unchecked_count,
        items=items,
        warnings=warnings,
    )


def render_workspace_review_pack_markdown(result: WorkspaceReviewPackResult) -> str:
    lines = [
        "# K-ResDev Workspace Review Pack",
        "",
        "> Review pack projection only. It bundles local readiness, next-action, summary, source-verification, approval-coverage, report-integrity, bibliography-integrity, and citation-support artifacts; it does not certify official agency compliance.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Evidence count | {result.evidence_count} |",
        f"| Approval count | {result.approval_count} |",
        f"| Finding count | {result.finding_count} |",
        f"| Action count | {result.action_count} |",
        f"| Source verification valid | {result.source_verification_valid} |",
        f"| Source missing count | {result.source_missing_count} |",
        f"| Source mismatch count | {result.source_mismatch_count} |",
        f"| Approval coverage status | {_escape(result.approval_coverage_status or '-')} |",
        f"| Approval missing count | {result.approval_missing_count} |",
        f"| Approval not approved count | {result.approval_not_approved_count} |",
        f"| Approval hash mismatch count | {result.approval_hash_mismatch_count} |",
        f"| Approval hash unverified count | {result.approval_hash_unverified_count} |",
        f"| Report integrity status | {_escape(result.report_integrity_status or '-')} |",
        f"| Report integrity finding count | {result.report_integrity_finding_count} |",
        f"| Report integrity high count | {result.report_integrity_high_count} |",
        f"| Bibliography integrity status | {_escape(result.bibliography_integrity_status or '-')} |",
        f"| Bibliography entry count | {result.bibliography_entry_count} |",
        f"| Bibliography review count | {result.bibliography_review_count} |",
        f"| Bibliography citation count | {result.bibliography_citation_count} |",
        f"| Bibliography integrity finding count | {result.bibliography_integrity_finding_count} |",
        f"| Bibliography integrity high count | {result.bibliography_integrity_high_count} |",
        f"| Citation support status | {_escape(result.citation_support_status or '-')} |",
        f"| Citation support records | {result.citation_support_count} |",
        f"| Citation support citation count | {result.citation_support_citation_count} |",
        f"| Citation support finding count | {result.citation_support_finding_count} |",
        f"| Citation support high count | {result.citation_support_high_count} |",
        "",
        "## Generated Artifacts",
        "",
        "| Artifact | Path |",
        "|---|---|",
    ]
    for path in result.generated_paths:
        lines.append(f"| {_artifact_label(path)} | `{_escape(path)}` |")
    lines.append("")
    lines.extend(
        [
            "## Manifest",
            "",
            f"- Hashed artifacts: {len(result.artifacts)}",
            f"- Manifest JSON: `{_escape(result.json_path)}`",
            "- The manifest JSON is not self-hashed; use `verify-review-pack` to check the other generated artifacts.",
            "",
            "## Use",
            "",
            "- Start with `readiness.md` for blockers and warnings.",
            "- Use `next-actions.md` as a reviewable command plan.",
            "- Use `workspace-summary.md` as a one-page handoff/status snapshot.",
            "- Use `source-verification.md` to check local source presence and hash drift.",
            "- Use `approval-coverage.md` to check report artifacts against supplied human decisions.",
            "- Use `report-integrity.md` to check draft report claims against indexed evidence.",
            "- Use `bibliography-integrity.md` to check local citation keys and bibliography source hashes.",
            "- Use `citation-support.md` to check cited papers against supplied paper-claim support records.",
            "- Run `verify-review-pack state/workspace-review-pack.json` before relying on a saved pack.",
            "- Keep official reports and scientific claims human-approved.",
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_label(path: str) -> str:
    name = Path(path).name
    labels = {
        "readiness.md": "Readiness report",
        "readiness.json": "Readiness JSON",
        "next-actions.md": "Next actions",
        "next-actions.json": "Next actions JSON",
        "workspace-summary.md": "Workspace summary",
        "workspace-summary.json": "Workspace summary JSON",
        "source-verification.md": "Evidence source verification",
        "source-verification.json": "Evidence source verification JSON",
        "approval-coverage.md": "Approval coverage",
        "approval-coverage.json": "Approval coverage JSON",
        "report-integrity.md": "Report integrity",
        "report-integrity.json": "Report integrity JSON",
        "bibliography-integrity.md": "Bibliography integrity",
        "bibliography-integrity.json": "Bibliography integrity JSON",
        "citation-support.md": "Citation support",
        "citation-support.json": "Citation support JSON",
        "workspace-review-pack.md": "Review pack index",
        "workspace-review-pack.json": "Review pack JSON",
    }
    return labels.get(name, name)


def _artifact_manifest(paths: list[str], exclude: set[str]) -> list[ReviewPackArtifact]:
    artifacts: list[ReviewPackArtifact] = []
    for path in paths:
        if path in exclude:
            continue
        target = Path(path)
        if not target.exists():
            continue
        artifacts.append(
            ReviewPackArtifact(
                path=str(target),
                artifact_type=_artifact_label(str(target)),
                sha256=_sha256_file(target),
                byte_count=target.stat().st_size,
            )
        )
    return artifacts


def _verify_artifact(artifact: ReviewPackArtifact) -> ReviewPackVerificationItem:
    path = Path(artifact.path)
    if not path.exists():
        return ReviewPackVerificationItem(
            path=artifact.path,
            artifact_type=artifact.artifact_type,
            expected_sha256=artifact.sha256,
            status="missing",
        )
    actual = _sha256_file(path)
    status = "ok" if actual == artifact.sha256 else "mismatch"
    return ReviewPackVerificationItem(
        path=artifact.path,
        artifact_type=artifact.artifact_type,
        expected_sha256=artifact.sha256,
        actual_sha256=actual,
        byte_count=path.stat().st_size,
        status=status,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
