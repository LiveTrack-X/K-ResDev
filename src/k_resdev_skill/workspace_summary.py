from __future__ import annotations

from pathlib import Path

from .approval import load_approval_records
from .evidence_index import load_evidence_index
from .models import (
    ApprovalRecord,
    EvidenceItem,
    ProjectProfile,
    WorkspaceActionPlan,
    WorkspaceDoctorResult,
    WorkspaceSummaryResult,
)
from .profile_registry import load_project_profile
from .profile_sources import generate_profile_integrity
from .budget_ledger import generate_workspace_budget_ledger
from .research_claims import generate_research_claim_matrix
from .trace_passport import generate_trace_passport
from .workspace import OPERATIONAL_MARKDOWN_NAMES, run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan
from .workspace_trace import generate_workspace_trace


def generate_workspace_summary(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    max_actions: int = 5,
    doctor_result: WorkspaceDoctorResult | None = None,
    action_plan: WorkspaceActionPlan | None = None,
) -> WorkspaceSummaryResult:
    """Generate a one-page operational summary from local K-ResDev metadata."""

    workspace = Path(root)
    action_limit = max(0, max_actions)
    doctor = doctor_result or run_workspace_doctor(workspace)
    actions = action_plan or generate_workspace_action_plan(workspace, doctor_result=doctor)
    evidence = _load_evidence(workspace)
    approvals = _load_approvals(workspace)
    profile = _load_profile(workspace)
    reports = _report_paths(workspace / "reports")
    exports = _sorted_paths(workspace / "reports", ["*.docx", "*.html", "*.txt"])
    manifests = _sorted_paths(workspace / "reports" / "analysis", ["*-analysis-run.json"])
    budget_ledger = generate_workspace_budget_ledger(workspace)
    research_claim_matrix = generate_research_claim_matrix(workspace)
    profile_integrity = generate_profile_integrity(workspace)
    trace = generate_workspace_trace(workspace)
    trace_passport = generate_trace_passport(workspace)

    summary = WorkspaceSummaryResult(
        root=str(workspace),
        status=doctor.status,
        profile_id=profile.profile_id if profile else None,
        profile_status=profile.status if profile else None,
        evidence_count=len(evidence),
        approval_count=len(approvals),
        finding_count=doctor.finding_count,
        action_count=actions.action_count,
        evidence_by_type=_count(_enum_value(item.evidence_type) for item in evidence),
        evidence_by_status=_count(_enum_value(item.status) for item in evidence),
        risk_flag_counts=_count(flag for item in evidence for flag in item.risk_flags),
        findings_by_severity=_count(finding.severity for finding in doctor.findings),
        actions_by_priority=_count(action.priority for action in actions.actions),
        report_paths=reports,
        export_paths=exports,
        analysis_manifest_paths=manifests,
        budget_ledger_status=budget_ledger.status,
        budget_ledger_count=budget_ledger.ledger_count,
        budget_ledger_finding_count=budget_ledger.finding_count,
        budget_total_by_currency=budget_ledger.total_by_currency,
        research_claim_matrix_status=research_claim_matrix.status,
        research_claim_count=research_claim_matrix.claim_count,
        research_claim_matrix_finding_count=research_claim_matrix.finding_count,
        profile_integrity_status=profile_integrity.status,
        profile_source_count=profile_integrity.source_count,
        profile_verified_source_count=profile_integrity.verified_source_count,
        profile_integrity_finding_count=profile_integrity.finding_count,
        trace_status=trace.status,
        trace_node_count=trace.node_count,
        trace_edge_count=trace.edge_count,
        trace_finding_count=trace.finding_count,
        trace_passport_status=trace_passport.status,
        checkpoint_count=trace_passport.checkpoint_count,
        latest_checkpoint_id=trace_passport.latest_checkpoint_id,
        trace_passport_finding_count=trace_passport.finding_count,
        top_actions=actions.actions[:action_limit],
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_workspace_summary_markdown(summary), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return summary


def render_workspace_summary_markdown(summary: WorkspaceSummaryResult) -> str:
    lines = [
        "# K-ResDev Workspace Summary",
        "",
        "> Operational projection only. This does not certify official agency compliance, submission readiness, or scientific validity.",
        "",
        "## Status",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(summary.root)}` |",
        f"| Readiness status | {_escape(summary.status)} |",
        f"| Profile | {_escape(summary.profile_id or 'missing')} |",
        f"| Profile status | {_escape(summary.profile_status or 'missing')} |",
        f"| Profile integrity | {_escape(summary.profile_integrity_status or '-')} |",
        f"| Profile sources | {summary.profile_source_count} |",
        f"| Verified profile sources | {summary.profile_verified_source_count} |",
        f"| Budget ledger | {_escape(summary.budget_ledger_status or '-')} |",
        f"| Budget ledger rows | {summary.budget_ledger_count} |",
        f"| Research claim matrix | {_escape(summary.research_claim_matrix_status or '-')} |",
        f"| Research claims | {summary.research_claim_count} |",
        f"| Evidence count | {summary.evidence_count} |",
        f"| Approval count | {summary.approval_count} |",
        f"| Finding count | {summary.finding_count} |",
        f"| Action count | {summary.action_count} |",
        f"| Trace status | {_escape(summary.trace_status or '-')} |",
        f"| Trace nodes | {summary.trace_node_count} |",
        f"| Trace findings | {summary.trace_finding_count} |",
        f"| Trace passport | {_escape(summary.trace_passport_status or '-')} |",
        f"| Checkpoints | {summary.checkpoint_count} |",
        f"| Latest checkpoint | {_escape(summary.latest_checkpoint_id or '-')} |",
        "",
        "## Evidence",
        "",
        "| Category | Counts |",
        "|---|---|",
        f"| By type | {_format_counts(summary.evidence_by_type)} |",
        f"| By status | {_format_counts(summary.evidence_by_status)} |",
        f"| Risk flags | {_format_counts(summary.risk_flag_counts)} |",
        "",
        "## Operations",
        "",
        "| Area | Counts | Paths |",
        "|---|---:|---|",
        f"| Doctor findings | {summary.finding_count} | {_format_counts(summary.findings_by_severity)} |",
        f"| Next actions | {summary.action_count} | {_format_counts(summary.actions_by_priority)} |",
        f"| Report Markdown | {len(summary.report_paths)} | {_format_paths(summary.report_paths)} |",
        f"| Projection exports | {len(summary.export_paths)} | {_format_paths(summary.export_paths)} |",
        f"| Analysis manifests | {len(summary.analysis_manifest_paths)} | {_format_paths(summary.analysis_manifest_paths)} |",
        f"| Budget ledger | {summary.budget_ledger_count} | status: {_escape(summary.budget_ledger_status or '-')}; findings: {summary.budget_ledger_finding_count}; totals: {_format_float_counts(summary.budget_total_by_currency)} |",
        f"| Research claim matrix | {summary.research_claim_count} | status: {_escape(summary.research_claim_matrix_status or '-')}; findings: {summary.research_claim_matrix_finding_count} |",
        f"| Profile integrity | {summary.profile_integrity_finding_count} | status: {_escape(summary.profile_integrity_status or '-')}; verified sources: {summary.profile_verified_source_count} |",
        f"| Workspace trace | {summary.trace_node_count} | status: {_escape(summary.trace_status or '-')}; findings: {summary.trace_finding_count} |",
        f"| Trace passport | {summary.checkpoint_count} | status: {_escape(summary.trace_passport_status or '-')}; latest: {_escape(summary.latest_checkpoint_id or '-')}; findings: {summary.trace_passport_finding_count} |",
        "",
        "## Top Actions",
        "",
        "| Priority | Action | Command |",
        "|---|---|---|",
    ]
    if not summary.top_actions:
        lines.append("| ok | No next action generated. | - |")
    for action in summary.top_actions:
        command = f"`{_escape(action.command)}`" if action.command else "-"
        lines.append(f"| {_escape(action.priority)} | {_escape(action.title)} | {command} |")
    lines.append("")
    return "\n".join(lines)


def _load_evidence(workspace: Path) -> list[EvidenceItem]:
    path = workspace / "state" / "evidence-index.json"
    if not path.exists():
        return []
    try:
        return load_evidence_index(path)
    except Exception:
        return []


def _load_approvals(workspace: Path) -> list[ApprovalRecord]:
    path = workspace / "state" / "approvals"
    if not path.exists():
        return []
    try:
        return load_approval_records(path)
    except Exception:
        return []


def _load_profile(workspace: Path) -> ProjectProfile | None:
    path = workspace / "state" / "project-profile.json"
    if not path.exists():
        return None
    try:
        return load_project_profile(path)
    except Exception:
        return None


def _sorted_paths(root: Path, patterns: list[str]) -> list[str]:
    if not root.exists():
        return []
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(root.glob(pattern))
    return [str(path) for path in sorted(paths, key=lambda item: item.as_posix())]


def _report_paths(root: Path) -> list[str]:
    if not root.exists():
        return []
    paths = [path for path in root.glob("*.md") if path.name not in OPERATIONAL_MARKDOWN_NAMES]
    return [str(path) for path in sorted(paths, key=lambda item: item.as_posix())]


def _count(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"{key}: {value}" for key, value in counts.items())


def _format_float_counts(counts: dict[str, float]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"{key}: {_format_amount(value)}" for key, value in counts.items())


def _format_amount(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _format_paths(paths: list[str]) -> str:
    if not paths:
        return "-"
    return "<br>".join(f"`{_escape(path)}`" for path in paths[:5])


def _enum_value(value: object) -> str:
    return getattr(value, "value", str(value))


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
