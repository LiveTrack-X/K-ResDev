from __future__ import annotations

import json
import zipfile
from pathlib import Path

from .approval import load_approval_records
from .approval_coverage import generate_workspace_approval_coverage
from .budget import budget_evidence_gaps
from .evidence_index import load_evidence_index
from .models import (
    ProjectProfile,
    ProjectState,
    WorkspaceDoctorFinding,
    WorkspaceDoctorResult,
    WorkspaceInitResult,
)
from .profile_registry import default_agency_templates_root, load_project_profile
from .report_integrity import generate_workspace_report_integrity
from .schema_tools import validate_json_file
from .source_verification import verify_evidence_sources

DRAFT_NOTICE = "Draft projection only"
STANDARD_DIRS = (
    "inbox",
    "state",
    "evidence",
    "reports",
    "reports/analysis",
    "state/approvals",
)
OPERATIONAL_MARKDOWN_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "budget-checklist.md",
    "evidence-bundle-index.md",
    "next-actions.md",
    "readiness.md",
    "report-integrity.md",
    "source-verification.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
}


def initialize_workspace(
    root: str | Path,
    project_id: str,
    title: str,
    profile_id: str = "national-rnd-basic",
) -> WorkspaceInitResult:
    """Create a K-ResDev workspace skeleton without overwriting existing files."""

    workspace = Path(root)
    created: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []

    for relative in STANDARD_DIRS:
        target = workspace / relative
        if target.exists():
            skipped.append(str(target))
        else:
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))

    project_state = ProjectState(
        project_id=project_id,
        title=title,
        period="needs_review",
        status="planning",
    )
    _write_if_missing(
        workspace / "state" / "project-state.json",
        project_state.model_dump_json(indent=2) + "\n",
        created,
        skipped,
    )

    profile = _profile_for_id(profile_id, warnings)
    _write_if_missing(
        workspace / "state" / "project-profile.json",
        profile.model_dump_json(indent=2) + "\n",
        created,
        skipped,
    )

    _write_if_missing(
        workspace / "README.k-resdev.md",
        _starter_readme(project_id, title, profile.profile_id),
        created,
        skipped,
    )

    if profile.status == "needs_review":
        warnings.append("profile_needs_review")

    return WorkspaceInitResult(
        root=str(workspace),
        project_id=project_id,
        profile_id=profile.profile_id,
        created_paths=created,
        skipped_existing=skipped,
        warnings=_unique(warnings),
    )


def run_workspace_doctor(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceDoctorResult:
    """Inspect workspace readiness using local metadata only."""

    workspace = Path(root)
    findings: list[WorkspaceDoctorFinding] = []
    evidence_count = _check_evidence(workspace, findings)
    approval_count = _check_approvals(workspace, findings)
    _check_approval_coverage(workspace, findings)
    _check_profile(workspace, findings)
    _check_reports(workspace, findings)
    _check_report_integrity(workspace, findings)
    _check_exports(workspace, findings)
    _check_analysis(workspace, findings)

    status = _status_from_findings(findings)
    result = WorkspaceDoctorResult(
        root=str(workspace),
        status=status,
        evidence_count=evidence_count,
        approval_count=approval_count,
        finding_count=len(findings),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
    )

    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_doctor_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_doctor_markdown(result: WorkspaceDoctorResult) -> str:
    lines = [
        "# K-ResDev Workspace Readiness",
        "",
        "> Readiness projection only. This does not certify official agency compliance.",
        "",
        f"- Root: `{result.root}`",
        f"- Status: `{result.status}`",
        f"- Evidence count: {result.evidence_count}",
        f"- Approval count: {result.approval_count}",
        f"- Finding count: {result.finding_count}",
        "",
        "| Severity | Code | Message | Path | Suggested Action |",
        "|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | ready | No readiness findings detected. | - | Continue evidence review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {message} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                message=_escape(finding.message),
                path=_escape(finding.path or "-"),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _check_evidence(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> int:
    index_path = workspace / "state" / "evidence-index.json"
    if not index_path.exists():
        findings.append(
            _finding(
                "missing_evidence_index",
                "high",
                "No evidence index found.",
                index_path,
                "Run intake or index evidence before reporting.",
            )
        )
        return 0

    try:
        validation = validate_json_file(index_path, "evidence")
        if not validation["valid"]:
            findings.append(
                _finding(
                    "invalid_evidence_index_schema",
                    "high",
                    f"Evidence index schema validation failed with {validation['error_count']} error(s).",
                    index_path,
                    "Run validate-json evidence and fix invalid metadata.",
                )
            )
        evidence = load_evidence_index(index_path)
    except Exception as exc:  # pragma: no cover - defensive path
        findings.append(_finding("unreadable_evidence_index", "high", str(exc), index_path, "Regenerate the evidence index."))
        return 0

    if not evidence:
        findings.append(_finding("empty_evidence_index", "high", "Evidence index contains no items.", index_path, "Add evidence via intake."))
    for item in evidence:
        if item.status == "needs_review":
            findings.append(
                _finding(
                    "evidence_needs_review",
                    "medium",
                    f"{item.evidence_id} is still needs_review.",
                    index_path,
                    "Review, accept, reject, or keep disclosed as draft.",
                )
            )
        if item.risk_flags:
            findings.append(
                _finding(
                    "evidence_risk_flags",
                    "medium",
                    f"{item.evidence_id} has risk flags: {', '.join(item.risk_flags)}.",
                    index_path,
                    "Resolve or disclose risk flags before official use.",
                )
            )
    for evidence_id, missing_fields in budget_evidence_gaps(evidence).items():
        findings.append(
            _finding(
                "budget_metadata_gap",
                "medium",
                f"{evidence_id} is missing budget fields: {', '.join(missing_fields)}.",
                index_path,
                "Complete generic budget metadata and verify official agency guidance.",
            )
        )
    _check_source_integrity(workspace, index_path, findings)
    return len(evidence)


def _check_source_integrity(workspace: Path, index_path: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = verify_evidence_sources(index_path, root=workspace)
    if result.warnings:
        findings.append(
            _finding(
                "source_verification_unreadable",
                "high",
                "Evidence source verification could not read the evidence index.",
                index_path,
                "Regenerate the evidence index before reporting.",
            )
        )
        return

    missing_hashed = [item for item in result.items if item.status == "missing" and item.expected_hashes]
    missing_unhashed = [item for item in result.items if item.status == "missing" and not item.expected_hashes]
    no_hash_existing = [item for item in result.items if item.status == "no_expected_hash"]

    if missing_hashed:
        findings.append(
            _finding(
                "source_file_missing",
                "high",
                f"{len(missing_hashed)} indexed hashed source file(s) are missing.",
                index_path,
                "Restore raw sources, rerun intake, or document source replacement before reporting.",
            )
        )
    if result.mismatch_count:
        findings.append(
            _finding(
                "source_hash_mismatch",
                "high",
                f"{result.mismatch_count} indexed source file(s) changed after evidence indexing.",
                index_path,
                "Restore the original raw file or rerun intake and review changed evidence.",
            )
        )
    if result.conflict_count:
        findings.append(
            _finding(
                "source_hash_conflict",
                "medium",
                f"{result.conflict_count} source file(s) have conflicting expected hashes across evidence items.",
                index_path,
                "Split or regenerate conflicting evidence records before relying on the index.",
            )
        )
    if no_hash_existing or missing_unhashed:
        unverified_count = len(no_hash_existing) + len(missing_unhashed)
        findings.append(
            _finding(
                "source_hash_unverified",
                "low",
                f"{unverified_count} source file(s) cannot be verified with a saved source hash.",
                index_path,
                "Prefer intake-generated evidence with source hashes for audit-sensitive use.",
            )
        )


def _check_approvals(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> int:
    approvals_dir = workspace / "state" / "approvals"
    if not approvals_dir.exists():
        findings.append(
            _finding(
                "approval_missing",
                "medium",
                "No approvals directory found.",
                approvals_dir,
                "Record supplied human review decisions before submission.",
            )
        )
        return 0
    try:
        approvals = load_approval_records(approvals_dir)
    except Exception as exc:
        findings.append(_finding("approval_unreadable", "medium", str(exc), approvals_dir, "Fix or remove invalid approval JSON."))
        return 0
    if not approvals:
        findings.append(
            _finding(
                "approval_missing",
                "medium",
                "No approval records found.",
                approvals_dir,
                "Record supplied human review decisions before submission.",
            )
        )
    return len(approvals)


def _check_approval_coverage(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_workspace_approval_coverage(workspace)
    if result.warnings and result.artifact_count:
        findings.append(
            _finding(
                "approval_coverage_unreadable",
                "medium",
                "Report approval coverage could not read approval records.",
                workspace / "state" / "approvals",
                "Fix approval records, then regenerate approval coverage.",
            )
        )
        return
    if result.missing_count:
        findings.append(
            _finding(
                "report_approval_missing",
                "medium",
                f"{result.missing_count} report artifact(s) have no supplied human approval record.",
                workspace / "reports",
                "Record supplied human decisions or keep artifacts clearly disclosed as draft.",
            )
        )
    if result.not_approved_count:
        findings.append(
            _finding(
                "report_approval_not_approved",
                "medium",
                f"{result.not_approved_count} report artifact(s) have latest decisions that are not approved.",
                workspace / "state" / "approvals",
                "Resolve requested changes before official use.",
            )
        )


def _check_profile(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    profile_path = workspace / "state" / "project-profile.json"
    if not profile_path.exists():
        findings.append(_finding("profile_missing", "medium", "No project profile found.", profile_path, "Run init-workspace or add a profile."))
        return
    try:
        profile = load_project_profile(profile_path)
    except Exception as exc:
        findings.append(_finding("profile_unreadable", "medium", str(exc), profile_path, "Fix project profile JSON."))
        return
    if profile.status == "needs_review":
        findings.append(
            _finding(
                "profile_needs_review",
                "medium",
                f"Profile {profile.profile_id} is marked needs_review.",
                profile_path,
                "Verify agency/program templates before official use.",
            )
        )


def _check_reports(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    reports_dir = workspace / "reports"
    reports = [path for path in reports_dir.glob("*.md") if path.name not in OPERATIONAL_MARKDOWN_NAMES] if reports_dir.exists() else []
    if not reports:
        findings.append(_finding("report_missing", "low", "No report Markdown drafts found.", reports_dir, "Generate a draft report when evidence is ready."))


def _check_report_integrity(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_workspace_report_integrity(workspace)
    if result.report_count == 0:
        return
    if any(warning.startswith("evidence_index_unreadable:") for warning in result.warnings):
        findings.append(
            _finding(
                "report_integrity_unchecked",
                "high",
                "Report integrity could not be checked because the evidence index is unavailable.",
                workspace / "state" / "evidence-index.json",
                "Regenerate the evidence index, then rerun report-integrity.",
            )
        )
        return
    if result.high_count:
        findings.append(
            _finding(
                "report_integrity_high_findings",
                "high",
                f"{result.high_count} high-severity report integrity finding(s) were detected.",
                workspace / "reports",
                "Run report-integrity and fix unsupported or mismatched claims before approval.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "report_integrity_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} report integrity review finding(s) or warnings were detected.",
                workspace / "reports",
                "Review report-integrity output before external use.",
            )
        )


def _check_exports(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    reports_dir = workspace / "reports"
    if not reports_dir.exists():
        findings.append(_finding("export_missing", "low", "No reports directory found for projection exports.", reports_dir, "Run init-workspace."))
        return
    export_files = [
        path
        for pattern in ("*.docx", "*.html", "*.txt")
        for path in reports_dir.glob(pattern)
    ]
    if not export_files:
        findings.append(
            _finding(
                "export_missing",
                "low",
                "No projection export files found.",
                reports_dir,
                "Run export-projection for review documents when drafts are ready.",
            )
        )
        return
    for path in export_files:
        if not _export_has_draft_notice(path):
            findings.append(
                _finding(
                    "export_notice_missing",
                    "medium",
                    f"Projection export {path.name} does not appear to contain the draft notice.",
                    path,
                    "Regenerate with export-projection.",
                )
            )


def _check_analysis(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    analysis_dir = workspace / "reports" / "analysis"
    manifests = list(analysis_dir.glob("*-analysis-run.json")) if analysis_dir.exists() else []
    if not manifests:
        findings.append(
            _finding(
                "analysis_manifest_missing",
                "low",
                "No analysis run manifest found.",
                analysis_dir,
                "Run run-analysis for datasets before using generated insights.",
            )
        )


def _export_has_draft_notice(path: Path) -> bool:
    try:
        if path.suffix.lower() == ".docx":
            with zipfile.ZipFile(path) as archive:
                return DRAFT_NOTICE in archive.read("word/document.xml").decode("utf-8", errors="replace")
        return DRAFT_NOTICE in path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False


def _write_if_missing(path: Path, text: str, created: list[str], skipped: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        skipped.append(str(path))
        return
    path.write_text(text, encoding="utf-8")
    created.append(str(path))


def _profile_for_id(profile_id: str, warnings: list[str]) -> ProjectProfile:
    profile_path = default_agency_templates_root() / profile_id / "project-profile.json"
    if profile_path.exists():
        return load_project_profile(profile_path)
    warnings.append(f"profile_not_found:{profile_id}")
    return ProjectProfile(
        profile_id=profile_id,
        status="needs_review",
        notes="Profile template was not found. Add a verified local profile before official use.",
    )


def _starter_readme(project_id: str, title: str, profile_id: str) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            "> K-ResDev workspace starter. Evidence is source of truth; reports and insights are draft projections until human-approved.",
            "",
            f"- Project ID: `{project_id}`",
            f"- Profile: `{profile_id}`",
            "- Put raw files in `inbox/`.",
            "- Run `k-resdev intake --inbox inbox --state-dir state --evidence-dir evidence` to build evidence metadata.",
            "- Run `k-resdev doctor --root . --output reports/readiness.md --json state/readiness.json` before reporting.",
            "- Run `k-resdev workspace-summary --root . --output reports/workspace-summary.md --json state/workspace-summary.json` for a one-page status handoff.",
            "- Run `k-resdev workspace-review-pack --root .` to refresh readiness, next actions, summary, source-verification, approval-coverage, and report-integrity artifacts together.",
            "- Run `k-resdev verify-review-pack state/workspace-review-pack.json` to check saved review-pack artifact hashes.",
            "- Run `k-resdev verify-evidence-sources state/evidence-index.json --root . --output reports/source-verification.md --json state/source-verification.json` to check indexed source hashes.",
            "- Run `k-resdev approval-coverage --root . --output reports/approval-coverage.md --json state/approval-coverage.json` to check report approval coverage.",
            "- Run `k-resdev report-integrity --root . --output reports/report-integrity.md --json state/report-integrity.json` to check report claims against evidence.",
            "",
        ]
    )


def _status_from_findings(findings: list[WorkspaceDoctorFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    return "ready"


def _finding(
    code: str,
    severity: str,
    message: str,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> WorkspaceDoctorFinding:
    return WorkspaceDoctorFinding(
        code=code,
        severity=severity,
        message=message,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


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
