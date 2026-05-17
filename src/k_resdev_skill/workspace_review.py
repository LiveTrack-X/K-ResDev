from __future__ import annotations

from pathlib import Path

from .models import WorkspaceReviewPackResult
from .workspace import run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan
from .workspace_summary import generate_workspace_summary


def generate_workspace_review_pack(
    root: str | Path,
    reports_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
    max_actions: int = 5,
) -> WorkspaceReviewPackResult:
    """Generate a bundled local review pack for readiness, actions, and status handoff."""

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
    index_md = reports / "workspace-review-pack.md"
    index_json = state / "workspace-review-pack.json"

    doctor = run_workspace_doctor(workspace, readiness_md, readiness_json)
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
        generated_paths=generated_paths,
        index_path=str(index_md),
        json_path=str(index_json),
    )
    index_md.write_text(render_workspace_review_pack_markdown(result), encoding="utf-8")
    index_json.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_workspace_review_pack_markdown(result: WorkspaceReviewPackResult) -> str:
    lines = [
        "# K-ResDev Workspace Review Pack",
        "",
        "> Review pack projection only. It bundles local readiness, next-action, and summary artifacts; it does not certify official agency compliance.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Evidence count | {result.evidence_count} |",
        f"| Approval count | {result.approval_count} |",
        f"| Finding count | {result.finding_count} |",
        f"| Action count | {result.action_count} |",
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
            "## Use",
            "",
            "- Start with `readiness.md` for blockers and warnings.",
            "- Use `next-actions.md` as a reviewable command plan.",
            "- Use `workspace-summary.md` as a one-page handoff/status snapshot.",
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
        "workspace-review-pack.md": "Review pack index",
        "workspace-review-pack.json": "Review pack JSON",
    }
    return labels.get(name, name)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
