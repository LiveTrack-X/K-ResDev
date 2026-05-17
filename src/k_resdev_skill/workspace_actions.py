from __future__ import annotations

import hashlib
from pathlib import Path

from .models import WorkspaceActionItem, WorkspaceActionPlan, WorkspaceDoctorFinding, WorkspaceDoctorResult
from .workspace import STANDARD_DIRS, run_workspace_doctor


def generate_workspace_action_plan(
    root: str | Path,
    doctor_result: WorkspaceDoctorResult | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceActionPlan:
    """Convert doctor findings into a deterministic next-action plan."""

    workspace = Path(root)
    result = doctor_result or run_workspace_doctor(workspace)
    actions = _actions_for_findings(workspace, result.findings)
    plan = WorkspaceActionPlan(
        root=str(workspace),
        status="ready" if not actions else "actions_needed",
        action_count=len(actions),
        actions=actions,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_action_plan_markdown(plan), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(plan.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return plan


def render_action_plan_markdown(plan: WorkspaceActionPlan) -> str:
    lines = [
        "# K-ResDev Next Actions",
        "",
        "> Action plan projection only. Review commands before running and keep official submissions human-approved.",
        "",
        f"- Root: `{plan.root}`",
        f"- Status: `{plan.status}`",
        f"- Action count: {plan.action_count}",
        "",
        "| Priority | Action | Rationale | Command | Related Findings |",
        "|---|---|---|---|---|",
    ]
    if not plan.actions:
        lines.append("| ok | No action needed | Doctor did not report readiness findings. | - | - |")
    for action in plan.actions:
        command = f"`{_escape(action.command)}`" if action.command else "-"
        lines.append(
            "| {priority} | {title} | {rationale} | {command} | {findings} |".format(
                priority=_escape(action.priority),
                title=_escape(action.title),
                rationale=_escape(action.rationale),
                command=command,
                findings=_escape(", ".join(action.related_findings) or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _actions_for_findings(root: Path, findings: list[WorkspaceDoctorFinding]) -> list[WorkspaceActionItem]:
    by_code: dict[str, list[WorkspaceDoctorFinding]] = {}
    for finding in findings:
        by_code.setdefault(finding.code, []).append(finding)

    candidates = [
        _action_for_workspace_skeleton(root, by_code),
        _action_for_missing_evidence(root, by_code),
        _action_for_invalid_evidence(root, by_code),
        _action_for_source_integrity(root, by_code),
        _action_for_review_evidence(root, by_code),
        _action_for_budget_gaps(root, by_code),
        _action_for_profile(root, by_code),
        _action_for_approval_coverage(root, by_code),
        _action_for_report_integrity(root, by_code),
        _action_for_bibliography_integrity(root, by_code),
        _action_for_citation_support_integrity(root, by_code),
        _action_for_reports(root, by_code),
        _action_for_analysis(root, by_code),
        _action_for_exports(root, by_code),
        _action_for_approvals(root, by_code),
    ]
    actions = [(index, action) for index, action in enumerate(candidates) if action is not None]
    return [action for _, action in sorted(actions, key=lambda item: (_priority_rank(item[1].priority), item[0]))]


def _action_for_workspace_skeleton(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("approval_missing", "profile_missing", "export_missing", "analysis_manifest_missing")):
        return None
    missing_dirs = [relative for relative in STANDARD_DIRS if not (root / relative).exists()]
    if not missing_dirs:
        return None
    return _action(
        root,
        "high",
        "Initialize the workspace skeleton",
        "Standard K-ResDev folders are missing; initialize them before intake or report generation.",
        f'python -m k_resdev_skill init-workspace --root "{root}" --project-id "<project-id>" --title "<project-title>"',
        by_code,
        ["missing_evidence_index", "approval_missing", "profile_missing", "export_missing", "analysis_manifest_missing"],
    )


def _action_for_missing_evidence(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("missing_evidence_index", "empty_evidence_index", "unreadable_evidence_index")):
        return None
    return _action(
        root,
        "high",
        "Build or regenerate the evidence index",
        "Evidence metadata is required before reports, bundles, and claim checks are meaningful.",
        f'python -m k_resdev_skill intake --inbox "{root / "inbox"}" --state-dir "{root / "state"}" --evidence-dir "{root / "evidence"}"',
        by_code,
        ["missing_evidence_index", "empty_evidence_index", "unreadable_evidence_index"],
    )


def _action_for_invalid_evidence(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if "invalid_evidence_index_schema" not in by_code:
        return None
    return _action(
        root,
        "high",
        "Validate and repair evidence metadata",
        "The evidence index exists but does not match the expected schema.",
        f'python -m k_resdev_skill validate-json evidence "{root / "state" / "evidence-index.json"}"',
        by_code,
        ["invalid_evidence_index_schema"],
    )


def _action_for_source_integrity(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "source_verification_unreadable",
        "source_file_missing",
        "source_hash_mismatch",
        "source_hash_conflict",
        "source_hash_unverified",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if any(code in by_code for code in ("source_verification_unreadable", "source_file_missing", "source_hash_mismatch")) else "medium"
    if priority == "medium" and "source_hash_conflict" not in by_code:
        priority = "low"
    return _action(
        root,
        priority,
        "Verify indexed source files",
        "Evidence source files should be present and hash-consistent before audit-sensitive reports or bundles are used.",
        f'python -m k_resdev_skill verify-evidence-sources "{root / "state" / "evidence-index.json"}" --root "{root}" --output "{root / "reports" / "source-verification.md"}" --json "{root / "state" / "source-verification.json"}"',
        by_code,
        codes,
    )


def _action_for_review_evidence(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("evidence_needs_review", "evidence_risk_flags")):
        return None
    return _action(
        root,
        "medium",
        "Review unresolved evidence and risk flags",
        "Evidence marked needs_review or risk-flagged should be accepted, rejected, or disclosed as draft before official use.",
        f'python -m k_resdev_skill bundle-index "{root / "state" / "evidence-index.json"}" --approval-records "{root / "state" / "approvals"}" --output "{root / "reports" / "evidence-bundle-index.md"}"',
        by_code,
        ["evidence_needs_review", "evidence_risk_flags"],
    )


def _action_for_budget_gaps(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if "budget_metadata_gap" not in by_code:
        return None
    return _action(
        root,
        "medium",
        "Complete generic budget evidence metadata",
        "Budget evidence is missing generic metadata fields such as date, vendor, proof type, or approval reference.",
        f'python -m k_resdev_skill budget-check "{root / "state" / "evidence-index.json"}" --output "{root / "reports" / "budget-checklist.md"}"',
        by_code,
        ["budget_metadata_gap"],
    )


def _action_for_profile(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("profile_missing", "profile_unreadable", "profile_needs_review")):
        return None
    return _action(
        root,
        "medium",
        "Verify the project profile",
        "Agency profiles remain local needs-review skeletons until a human verifies the official program form.",
        f'python -m k_resdev_skill validate-profile "{root / "state" / "project-profile.json"}"',
        by_code,
        ["profile_missing", "profile_unreadable", "profile_needs_review"],
    )


def _action_for_approval_coverage(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "approval_coverage_unreadable",
        "report_approval_missing",
        "report_approval_not_approved",
        "approval_target_hash_mismatch",
        "approval_target_hash_unverified",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "approval_target_hash_mismatch" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review report approval coverage",
        "Report artifacts should be linked to supplied human approval records before official use.",
        f'python -m k_resdev_skill approval-coverage --root "{root}" --output "{root / "reports" / "approval-coverage.md"}" --json "{root / "state" / "approval-coverage.json"}"',
        by_code,
        codes,
    )


def _action_for_report_integrity(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["report_integrity_unchecked", "report_integrity_high_findings", "report_integrity_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if any(code in by_code for code in ("report_integrity_unchecked", "report_integrity_high_findings")) else "medium"
    return _action(
        root,
        priority,
        "Review report claim integrity",
        "Report drafts should not contain unsupported numbers, missing evidence IDs, or evidence-mismatched claims.",
        f'python -m k_resdev_skill report-integrity --root "{root}" --output "{root / "reports" / "report-integrity.md"}" --json "{root / "state" / "report-integrity.json"}"',
        by_code,
        codes,
    )


def _action_for_bibliography_integrity(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["bibliography_integrity_high_findings", "bibliography_integrity_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "bibliography_integrity_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review bibliography integrity",
        "Bibliography metadata and Markdown citation keys should be present, reviewed, and source-hash-consistent before external manuscript or report use.",
        f'python -m k_resdev_skill bib-integrity --root "{root}" --output "{root / "reports" / "bibliography-integrity.md"}" --json "{root / "state" / "bibliography-integrity.json"}"',
        by_code,
        codes,
    )


def _action_for_citation_support_integrity(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["citation_support_high_findings", "citation_support_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "citation_support_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review citation support",
        "Cited papers should have supplied human paper-claim support records before external manuscript or report use.",
        f'python -m k_resdev_skill citation-support-integrity --root "{root}" --output "{root / "reports" / "citation-support.md"}" --json "{root / "state" / "citation-support.json"}"',
        by_code,
        codes,
    )


def _action_for_reports(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if "report_missing" not in by_code:
        return None
    return _action(
        root,
        "low",
        "Generate a draft report when evidence is ready",
        "No report draft was found; draft reports should be projections from evidence metadata.",
        f'python -m k_resdev_skill draft-report "{root / "state" / "evidence-index.json"}" --project-state "{root / "state" / "project-state.json"}" --reports-dir "{root / "reports"}"',
        by_code,
        ["report_missing"],
    )


def _action_for_analysis(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if "analysis_manifest_missing" not in by_code:
        return None
    return _action(
        root,
        "low",
        "Run reproducible analysis for tabular datasets",
        "No analysis manifest was found; dataset insights should have profile, script, and manifest traces.",
        f'python -m k_resdev_skill run-analysis "{root / "inbox" / "metrics.csv"}" --output-dir "{root / "reports" / "analysis"}"',
        by_code,
        ["analysis_manifest_missing"],
    )


def _action_for_exports(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("export_missing", "export_notice_missing")):
        return None
    return _action(
        root,
        "low",
        "Create review exports from Markdown drafts",
        "Projection exports should include the draft/human-approval notice before external review.",
        f'python -m k_resdev_skill export-projection "{root / "reports" / "monthly-report.md"}" --output "{root / "reports" / "monthly-report.docx"}" --format docx',
        by_code,
        ["export_missing", "export_notice_missing"],
    )


def _action_for_approvals(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("approval_missing", "approval_unreadable", "report_approval_missing", "report_approval_not_approved")):
        return None
    return _action(
        root,
        "medium",
        "Record supplied human review decisions",
        "K-ResDev does not infer approval; human decisions must be recorded explicitly.",
        f'python -m k_resdev_skill approval-record --target-type report --target-id monthly-report --decision needs_changes --reviewer "<reviewer>" --approvals-dir "{root / "state" / "approvals"}"',
        by_code,
        ["approval_missing", "approval_unreadable", "report_approval_missing", "report_approval_not_approved"],
    )


def _action(
    root: Path,
    priority: str,
    title: str,
    rationale: str,
    command: str,
    by_code: dict[str, list[WorkspaceDoctorFinding]],
    codes: list[str],
) -> WorkspaceActionItem:
    related = [code for code in codes if code in by_code]
    digest = hashlib.sha256(f"{root}|{title}|{','.join(related)}".encode("utf-8")).hexdigest()[:8].upper()
    return WorkspaceActionItem(
        action_id=f"ACT-{digest}",
        priority=priority,
        title=title,
        rationale=rationale,
        command=command,
        related_findings=related,
    )


def _priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 3)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
