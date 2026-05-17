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
from .workspace import run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan


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
    reports = _sorted_paths(workspace / "reports", ["*.md"])
    exports = _sorted_paths(workspace / "reports", ["*.docx", "*.html", "*.txt"])
    manifests = _sorted_paths(workspace / "reports" / "analysis", ["*-analysis-run.json"])

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
        f"| Evidence count | {summary.evidence_count} |",
        f"| Approval count | {summary.approval_count} |",
        f"| Finding count | {summary.finding_count} |",
        f"| Action count | {summary.action_count} |",
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


def _format_paths(paths: list[str]) -> str:
    if not paths:
        return "-"
    return "<br>".join(f"`{_escape(path)}`" for path in paths[:5])


def _enum_value(value: object) -> str:
    return getattr(value, "value", str(value))


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
