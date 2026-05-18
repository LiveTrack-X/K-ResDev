import json

from k_resdev_skill.cli import main
from k_resdev_skill.schema_tools import validate_json_file
from k_resdev_skill.workflow_router import generate_workflow_plan, render_workflow_plan_markdown
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_workflow_plan_writes_reviewable_commands_without_running(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "workflow-admin-review.md"
    json_output = tmp_path / "state" / "workflow-admin-review.json"

    plan = generate_workflow_plan(tmp_path, "admin-review", output_path=output, json_path=json_output)
    rendered = render_workflow_plan_markdown(plan)

    assert plan.status == "planned"
    assert plan.execute is False
    assert plan.step_count >= 5
    assert plan.generated_paths == []
    assert any("doctor" in step.command for step in plan.steps)
    assert all("gmail" not in step.command.lower() for step in plan.steps)
    assert all("slack" not in step.command.lower() for step in plan.steps)
    assert output.exists()
    assert json_output.exists()
    assert "Workflow router output only" in rendered
    assert validate_json_file(json_output, "workflow-plan")["valid"] is True


def test_workflow_weekly_run_executes_local_artifacts(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    assert main(["workflow", "weekly", "--root", str(tmp_path), "--date", "2026-05-19", "--run", "--max-actions", "2"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workflow"] == "weekly"
    assert payload["status"] == "executed"
    assert payload["execute"] is True
    assert (tmp_path / "reports" / "workflow-weekly.md").exists()
    assert (tmp_path / "state" / "workflow-weekly.json").exists()
    assert (tmp_path / "reports" / "weekly-review-2026-05-19.md").exists()
    assert (tmp_path / "reports" / "workspace-dashboard.md").exists()
    assert validate_json_file(tmp_path / "state" / "workflow-weekly.json", "workflow-plan")["valid"] is True


def test_workflow_research_and_integrity_plans_have_expected_steps(tmp_path):
    research = generate_workflow_plan(tmp_path, "research-review")
    integrity = generate_workflow_plan(tmp_path, "integrity-review")

    assert {step.operation_id for step in research.steps} >= {"reference_corpus", "research_claim_matrix", "workspace_trace"}
    assert {step.operation_id for step in integrity.steps} >= {"verify_sources", "artifact_authority", "trace_passport"}


def test_workflow_markdown_is_operational_not_report_draft(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    generate_workflow_plan(tmp_path, "weekly", output_path=tmp_path / "reports" / "workflow-weekly.md", json_path=tmp_path / "state" / "workflow-weekly.json")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert "report_missing" in codes


def test_workflow_plan_is_visible_in_workspace_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    generate_workflow_plan(
        tmp_path,
        "weekly",
        output_path=tmp_path / "reports" / "workflow-weekly.md",
        json_path=tmp_path / "state" / "workflow-weekly.json",
        execute=True,
        review_date="2026-05-19",
    )

    trace = generate_workspace_trace(tmp_path)

    assert "workflow_plan" in {node.node_type for node in trace.nodes}
