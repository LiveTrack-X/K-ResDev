import json
from datetime import date

from k_resdev_skill.cli import main
from k_resdev_skill.models import ProjectDeadline, ProjectGoalsFile
from k_resdev_skill.schema_tools import validate_json_file
from k_resdev_skill.weekly_review import (
    generate_weekly_review,
    generate_workspace_dashboard,
    load_latest_weekly_review,
    load_saved_workspace_dashboard,
    render_weekly_review_markdown,
    render_workspace_dashboard_markdown,
)
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_weekly_review_writes_dated_operating_artifacts(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "weekly-review-2026-05-19.md"
    json_output = tmp_path / "state" / "weekly-review-2026-05-19.json"

    result = generate_weekly_review(tmp_path, review_date="2026-05-19", output_path=output, json_path=json_output, max_actions=2)
    rendered = render_weekly_review_markdown(result)

    assert result.status == "blocked"
    assert result.item_count > 0
    assert result.high_finding_count >= 1
    assert len([item for item in result.items if item.category == "next_action"]) <= 2
    assert output.exists()
    assert json_output.exists()
    assert "Weekly Review" in rendered
    assert validate_json_file(json_output, "weekly-review")["valid"] is True
    assert load_latest_weekly_review(tmp_path).review_date == date(2026, 5, 19)


def test_weekly_review_surfaces_overdue_deadlines(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    goals = ProjectGoalsFile(
        project_id="PRJ-2026-0001",
        title="Demo Project",
        status="needs_review",
        deadlines=[
            ProjectDeadline(
                deadline_id="DL-2026-0001",
                due_date=date(2026, 5, 1),
                title="Interim report",
                deliverable_type="report",
                linked_report_paths=["reports/monthly-report.md"],
            )
        ],
    )
    (tmp_path / "state" / "project-goals.json").write_text(goals.model_dump_json(indent=2) + "\n", encoding="utf-8")

    result = generate_weekly_review(tmp_path, review_date=date(2026, 5, 19))

    assert result.overdue_count >= 1
    assert any(item.category == "deadline" and item.severity == "high" for item in result.items)


def test_workspace_dashboard_writes_cards_and_schema(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "workspace-dashboard.md"
    json_output = tmp_path / "state" / "workspace-dashboard.json"

    result = generate_workspace_dashboard(tmp_path, output_path=output, json_path=json_output)
    rendered = render_workspace_dashboard_markdown(result)

    assert result.card_count >= 6
    assert any(card.card_id == "readiness" for card in result.cards)
    assert result.status == "blocked"
    assert output.exists()
    assert json_output.exists()
    assert "Workspace Dashboard" in rendered
    assert validate_json_file(json_output, "workspace-dashboard")["valid"] is True
    assert load_saved_workspace_dashboard(tmp_path).card_count == result.card_count


def test_weekly_review_and_dashboard_cli_write_default_paths(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    assert main(["weekly-review", "--root", str(tmp_path), "--date", "2026-05-19", "--max-actions", "2"]) == 0
    weekly_payload = json.loads(capsys.readouterr().out)
    assert weekly_payload["review_date"] == "2026-05-19"
    assert (tmp_path / "reports" / "weekly-review-2026-05-19.md").exists()
    assert (tmp_path / "state" / "weekly-review-2026-05-19.json").exists()

    assert main(["workspace-dashboard", "--root", str(tmp_path)]) == 0
    dashboard_payload = json.loads(capsys.readouterr().out)
    assert dashboard_payload["root"] == str(tmp_path)
    assert (tmp_path / "reports" / "workspace-dashboard.md").exists()
    assert (tmp_path / "state" / "workspace-dashboard.json").exists()


def test_weekly_dashboard_integrate_with_doctor_summary_review_pack_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    generate_weekly_review(tmp_path, review_date="2026-05-19", output_path=tmp_path / "reports" / "weekly-review-2026-05-19.md", json_path=tmp_path / "state" / "weekly-review-2026-05-19.json")
    generate_workspace_dashboard(tmp_path, output_path=tmp_path / "reports" / "workspace-dashboard.md", json_path=tmp_path / "state" / "workspace-dashboard.json")

    doctor = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in doctor.findings}
    summary = generate_workspace_summary(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    pack = generate_workspace_review_pack(tmp_path, max_actions=2)

    assert "weekly_review_missing" not in codes
    assert "workspace_dashboard_missing" not in codes
    assert summary.weekly_review_status is not None
    assert summary.dashboard_status is not None
    assert {"weekly_review", "workspace_dashboard"}.issubset({node.node_type for node in trace.nodes})
    assert pack.weekly_review_status is not None
    assert pack.dashboard_status is not None
    assert any(path.endswith("workspace-dashboard.md") for path in pack.generated_paths)
