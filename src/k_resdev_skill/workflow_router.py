from __future__ import annotations

from datetime import date
from pathlib import Path

from .approval_coverage import generate_workspace_approval_coverage
from .artifact_authority import generate_artifact_authority
from .bibliography_integrity import generate_workspace_bibliography_integrity
from .budget_ledger import generate_workspace_budget_ledger
from .citation_support import generate_workspace_citation_support_integrity
from .models import WorkflowStep, WorkspaceWorkflowPlan
from .project_goals import generate_goals_review
from .reference_corpus import build_reference_corpus
from .research_claims import generate_research_claim_matrix
from .report_integrity import generate_workspace_report_integrity
from .source_verification import verify_evidence_sources
from .trace_passport import generate_trace_passport
from .weekly_review import generate_weekly_review, generate_workspace_dashboard
from .workspace import run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan
from .workspace_discovery import discover_workspace
from .workspace_summary import generate_workspace_summary
from .workspace_trace import generate_workspace_trace

WORKFLOW_NAMES = ("admin-review", "research-review", "integrity-review", "weekly")


def generate_workflow_plan(
    root: str | Path,
    workflow: str,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    *,
    execute: bool = False,
    review_date: str | date | None = None,
    max_actions: int = 5,
) -> WorkspaceWorkflowPlan:
    """Build and optionally run a thin local workflow over existing K-ResDev commands."""

    workspace = Path(root)
    workflow_name = _normalize_workflow(workflow)
    reports = workspace / "reports"
    state = workspace / "state"
    current_date = _coerce_date(review_date) or date.today()
    steps = _workflow_steps(workspace, workflow_name, current_date, max_actions)
    warnings: list[str] = []
    if execute:
        reports.mkdir(parents=True, exist_ok=True)
        state.mkdir(parents=True, exist_ok=True)
        executed_steps: list[WorkflowStep] = []
        for step in steps:
            executed_steps.append(_execute_step(workspace, step, current_date, max_actions))
        steps = executed_steps
        warnings.extend(warning for step in steps for warning in step.warnings)

    generated = _generated_paths(steps)
    status = _status(steps, execute)
    result = WorkspaceWorkflowPlan(
        root=str(workspace),
        workflow=workflow_name,
        status=status,
        execute=execute,
        step_count=len(steps),
        steps=steps,
        generated_paths=generated,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_workflow_plan_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_workflow_plan_markdown(plan: WorkspaceWorkflowPlan) -> str:
    lines = [
        "# K-ResDev Workflow Plan",
        "",
        "> Workflow router output only. It lists and optionally runs local deterministic commands; it does not approve reports, certify compliance, or run connector/network actions by default.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(plan.root)}` |",
        f"| Workflow | {_escape(plan.workflow)} |",
        f"| Status | {_escape(plan.status)} |",
        f"| Execute | {plan.execute} |",
        f"| Steps | {plan.step_count} |",
        f"| Generated paths | {len(plan.generated_paths)} |",
        f"| Warnings | {_format_list(plan.warnings)} |",
        "",
        "## Steps",
        "",
        "| Status | Step | Command | Outputs | Safety Notes | Warnings |",
        "|---|---|---|---|---|---|",
    ]
    for step in plan.steps:
        lines.append(
            "| {status} | {title} | `{command}` | {outputs} | {notes} | {warnings} |".format(
                status=_escape(step.status),
                title=_escape(step.title),
                command=_escape(step.command),
                outputs=_format_paths(step.output_paths),
                notes=_format_list(step.safety_notes),
                warnings=_format_list(step.warnings),
            )
        )
    if not plan.steps:
        lines.append("| empty | No workflow steps were generated. | - | - | - | - |")
    lines.extend(
        [
            "",
            "## Use",
            "",
            "- Review the commands and output paths before using `--run`.",
            "- Generated workflow Markdown and JSON are operating summaries, not report drafts.",
            "- Use the underlying commands directly when a step needs custom arguments.",
            "",
        ]
    )
    return "\n".join(lines)


def load_workflow_plan(path: str | Path) -> WorkspaceWorkflowPlan:
    return WorkspaceWorkflowPlan.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def _workflow_steps(workspace: Path, workflow: str, review_date: date, max_actions: int) -> list[WorkflowStep]:
    reports = workspace / "reports"
    state = workspace / "state"
    common_notes = ["local_only", "human_review_required", "no_connector_actions"]
    definitions: dict[str, list[tuple[str, str, list[Path]]]] = {
        "admin-review": [
            ("discover_workspace", "Discover workspace layout", [reports / "workspace-discovery.md", state / "workspace-discovery.json"]),
            ("doctor", "Run readiness doctor", [reports / "readiness.md", state / "readiness.json"]),
            ("goals_review", "Review goals and deadlines", [reports / "goals-review.md", state / "goals-review.json"]),
            ("budget_ledger", "Review budget ledger integrity", [reports / "budget-ledger.md", state / "budget-ledger-integrity.json"]),
            ("approval_coverage", "Check approval coverage", [reports / "approval-coverage.md", state / "approval-coverage.json"]),
            ("report_integrity", "Check report integrity", [reports / "report-integrity.md", state / "report-integrity.json"]),
            ("artifact_authority", "Review artifact authority", [reports / "artifact-authority.md", state / "artifact-authority.json"]),
            ("next_actions", "Generate next actions", [reports / "next-actions.md", state / "next-actions.json"]),
            ("workspace_summary", "Generate workspace summary", [reports / "workspace-summary.md", state / "workspace-summary.json"]),
        ],
        "research-review": [
            ("reference_corpus", "Build reference corpus", [reports / "reference-corpus-summary.md", state / "literature-corpus.json", state / "reference-rejection-log.json"]),
            ("bibliography_integrity", "Check bibliography integrity", [reports / "bibliography-integrity.md", state / "bibliography-integrity.json"]),
            ("citation_support", "Check citation support", [reports / "citation-support.md", state / "citation-support.json"]),
            ("research_claim_matrix", "Review research claim matrix", [reports / "research-claim-matrix.md", state / "research-claim-matrix.json"]),
            ("workspace_trace", "Generate workspace trace", [reports / "workspace-trace.md", state / "workspace-trace.json"]),
            ("next_actions", "Generate next actions", [reports / "next-actions.md", state / "next-actions.json"]),
            ("workspace_summary", "Generate workspace summary", [reports / "workspace-summary.md", state / "workspace-summary.json"]),
        ],
        "integrity-review": [
            ("verify_sources", "Verify evidence sources", [reports / "source-verification.md", state / "source-verification.json"]),
            ("artifact_authority", "Review artifact authority", [reports / "artifact-authority.md", state / "artifact-authority.json"]),
            ("approval_coverage", "Check approval coverage", [reports / "approval-coverage.md", state / "approval-coverage.json"]),
            ("report_integrity", "Check report integrity", [reports / "report-integrity.md", state / "report-integrity.json"]),
            ("bibliography_integrity", "Check bibliography integrity", [reports / "bibliography-integrity.md", state / "bibliography-integrity.json"]),
            ("citation_support", "Check citation support", [reports / "citation-support.md", state / "citation-support.json"]),
            ("research_claim_matrix", "Review research claim matrix", [reports / "research-claim-matrix.md", state / "research-claim-matrix.json"]),
            ("workspace_trace", "Generate workspace trace", [reports / "workspace-trace.md", state / "workspace-trace.json"]),
            ("trace_passport", "Summarize trace passport", [reports / "trace-passport.md", state / "trace-passport.json"]),
            ("doctor", "Run readiness doctor", [reports / "readiness.md", state / "readiness.json"]),
            ("next_actions", "Generate next actions", [reports / "next-actions.md", state / "next-actions.json"]),
        ],
        "weekly": [
            ("weekly_review", "Generate weekly review", [reports / f"weekly-review-{review_date.isoformat()}.md", state / f"weekly-review-{review_date.isoformat()}.json"]),
            ("workspace_dashboard", "Generate workspace dashboard", [reports / "workspace-dashboard.md", state / "workspace-dashboard.json"]),
            ("doctor", "Run readiness doctor", [reports / "readiness.md", state / "readiness.json"]),
            ("next_actions", "Generate next actions", [reports / "next-actions.md", state / "next-actions.json"]),
            ("workspace_summary", "Generate workspace summary", [reports / "workspace-summary.md", state / "workspace-summary.json"]),
        ],
    }
    steps: list[WorkflowStep] = []
    for index, (operation_id, title, outputs) in enumerate(definitions[workflow], start=1):
        steps.append(
            WorkflowStep(
                step_id=f"WF-{workflow.upper()}-{index:02d}",
                title=title,
                operation_id=operation_id,
                command=_command(workspace, operation_id, outputs, review_date, max_actions),
                output_paths=[str(path) for path in outputs],
                safety_notes=list(common_notes),
            )
        )
    return steps


def _execute_step(workspace: Path, step: WorkflowStep, review_date: date, max_actions: int) -> WorkflowStep:
    try:
        outputs = [Path(path) for path in step.output_paths]
        op = step.operation_id
        if op == "discover_workspace":
            discover_workspace(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "doctor":
            run_workspace_doctor(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "goals_review":
            generate_goals_review(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "budget_ledger":
            generate_workspace_budget_ledger(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "approval_coverage":
            generate_workspace_approval_coverage(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "report_integrity":
            generate_workspace_report_integrity(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "artifact_authority":
            generate_artifact_authority(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "next_actions":
            generate_workspace_action_plan(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "workspace_summary":
            generate_workspace_summary(workspace, output_path=outputs[0], json_path=outputs[1], max_actions=max_actions)
        elif op == "reference_corpus":
            build_reference_corpus(workspace, output_path=outputs[0], json_path=outputs[1], rejection_json_path=outputs[2])
        elif op == "bibliography_integrity":
            generate_workspace_bibliography_integrity(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "citation_support":
            generate_workspace_citation_support_integrity(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "research_claim_matrix":
            generate_research_claim_matrix(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "workspace_trace":
            generate_workspace_trace(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "trace_passport":
            generate_trace_passport(workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "verify_sources":
            verify_evidence_sources(workspace / "state" / "evidence-index.json", root=workspace, output_path=outputs[0], json_path=outputs[1])
        elif op == "weekly_review":
            generate_weekly_review(workspace, review_date=review_date, output_path=outputs[0], json_path=outputs[1], max_actions=max_actions)
        elif op == "workspace_dashboard":
            generate_workspace_dashboard(workspace, output_path=outputs[0], json_path=outputs[1])
        else:  # pragma: no cover - defensive guard for future workflow additions
            return step.model_copy(update={"status": "failed", "warnings": [f"unknown_operation:{op}"]})
    except Exception as exc:  # pragma: no cover - defensive guard around filesystem/runtime failures
        return step.model_copy(update={"status": "failed", "warnings": [f"{step.operation_id}_failed:{exc}"]})
    return step.model_copy(update={"status": "executed"})


def _command(workspace: Path, operation_id: str, outputs: list[Path], review_date: date, max_actions: int) -> str:
    root_arg = f'--root "{workspace}"'
    if operation_id == "discover_workspace":
        return f'python -m k_resdev_skill discover-workspace {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "doctor":
        return f'python -m k_resdev_skill doctor {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "goals_review":
        return f'python -m k_resdev_skill goals-review {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "budget_ledger":
        return f'python -m k_resdev_skill budget-ledger-integrity {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "approval_coverage":
        return f'python -m k_resdev_skill approval-coverage {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "report_integrity":
        return f'python -m k_resdev_skill report-integrity {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "artifact_authority":
        return f'python -m k_resdev_skill artifact-authority {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "next_actions":
        return f'python -m k_resdev_skill next-actions {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "workspace_summary":
        return f'python -m k_resdev_skill workspace-summary {root_arg} --output "{outputs[0]}" --json "{outputs[1]}" --max-actions {max_actions}'
    if operation_id == "reference_corpus":
        return f'python -m k_resdev_skill reference-corpus {root_arg} --output "{outputs[0]}" --json "{outputs[1]}" --rejections "{outputs[2]}"'
    if operation_id == "bibliography_integrity":
        return f'python -m k_resdev_skill bib-integrity {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "citation_support":
        return f'python -m k_resdev_skill citation-support-integrity {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "research_claim_matrix":
        return f'python -m k_resdev_skill research-claim-matrix {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "workspace_trace":
        return f'python -m k_resdev_skill workspace-trace {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "trace_passport":
        return f'python -m k_resdev_skill checkpoint-summary {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "verify_sources":
        return f'python -m k_resdev_skill verify-evidence-sources "{workspace / "state" / "evidence-index.json"}" {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    if operation_id == "weekly_review":
        return f'python -m k_resdev_skill weekly-review {root_arg} --date {review_date.isoformat()} --output "{outputs[0]}" --json "{outputs[1]}" --max-actions {max_actions}'
    if operation_id == "workspace_dashboard":
        return f'python -m k_resdev_skill workspace-dashboard {root_arg} --output "{outputs[0]}" --json "{outputs[1]}"'
    return f'python -m k_resdev_skill {operation_id} {root_arg}'


def _generated_paths(steps: list[WorkflowStep]) -> list[str]:
    paths: list[str] = []
    for step in steps:
        if step.status != "executed":
            continue
        for raw_path in step.output_paths:
            if Path(raw_path).exists():
                paths.append(raw_path)
    return sorted(dict.fromkeys(paths))


def _normalize_workflow(workflow: str) -> str:
    value = workflow.strip().lower()
    if value not in WORKFLOW_NAMES:
        raise ValueError(f"unknown workflow: {workflow}")
    return value


def _coerce_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _status(steps: list[WorkflowStep], execute: bool) -> str:
    if not execute:
        return "planned"
    if any(step.status == "failed" for step in steps):
        return "failed"
    if any(step.warnings for step in steps):
        return "executed_with_warnings"
    return "executed"


def _format_paths(paths: list[str]) -> str:
    if not paths:
        return "-"
    return "<br>".join(f"`{_escape(path)}`" for path in paths)


def _format_list(values: list[str]) -> str:
    if not values:
        return "-"
    return "<br>".join(_escape(value) for value in values)


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
