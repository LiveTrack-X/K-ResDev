import json

from k_resdev_skill.cli import main
from k_resdev_skill.models import WorkspaceDoctorFinding, WorkspaceDoctorResult
from k_resdev_skill.workspace import initialize_workspace
from k_resdev_skill.workspace_actions import generate_workspace_action_plan, render_action_plan_markdown


def test_workspace_action_plan_maps_empty_workspace_findings_to_commands(tmp_path):
    markdown_path = tmp_path / "reports" / "next-actions.md"
    json_path = tmp_path / "state" / "next-actions.json"

    plan = generate_workspace_action_plan(tmp_path, output_path=markdown_path, json_path=json_path)
    titles = {action.title for action in plan.actions}
    priorities = [action.priority for action in plan.actions]

    assert plan.status == "actions_needed"
    assert plan.actions[0].title == "Initialize the workspace skeleton"
    assert "Build or regenerate the evidence index" in titles
    assert "Verify the project profile" in titles
    assert "Record supplied human review decisions" in titles
    assert priorities[0] == "high"
    assert markdown_path.read_text(encoding="utf-8").startswith("# K-ResDev Next Actions")
    assert json.loads(json_path.read_text(encoding="utf-8"))["action_count"] == plan.action_count


def test_workspace_action_plan_can_render_ready_state_without_actions(tmp_path):
    doctor_result = WorkspaceDoctorResult(root=str(tmp_path), status="ready")

    plan = generate_workspace_action_plan(tmp_path, doctor_result=doctor_result)
    rendered = render_action_plan_markdown(plan)

    assert plan.status == "ready"
    assert plan.action_count == 0
    assert "No action needed" in rendered


def test_workspace_action_plan_maps_source_integrity_findings(tmp_path):
    doctor_result = WorkspaceDoctorResult(
        root=str(tmp_path),
        status="blocked",
        findings=[
            WorkspaceDoctorFinding(
                code="source_hash_mismatch",
                severity="high",
                message="source changed",
                path=str(tmp_path / "state" / "evidence-index.json"),
            )
        ],
    )

    plan = generate_workspace_action_plan(tmp_path, doctor_result=doctor_result)
    action = next(item for item in plan.actions if item.title == "Verify indexed source files")

    assert action.priority == "high"
    assert "source_hash_mismatch" in action.related_findings
    assert "verify-evidence-sources" in (action.command or "")


def test_next_actions_cli_writes_outputs(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "next-actions.md"
    json_output = tmp_path / "state" / "next-actions.json"

    assert main(["next-actions", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["root"] == str(tmp_path)
    assert payload["action_count"] > 0
    assert output.exists()
    assert json_output.exists()
