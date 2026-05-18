import json
from datetime import date

from k_resdev_skill.approval import create_approval_record, write_approval_record
from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem, KPI, Milestone, ProjectDeadline, ProjectGoalsFile, ProjectObjective, ProjectState
from k_resdev_skill.project_goals import generate_goals_review, initialize_project_goals, load_project_goals, render_goals_review_markdown
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_goals_init_seeds_deadlines_from_project_state_without_overwriting(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state = ProjectState(
        project_id="PRJ-2026-0001",
        title="Demo Project",
        period="2026",
        status="active",
        kpis=[KPI(kpi_id="KPI-01", name="Validation Dice", target=0.85)],
        milestones=[Milestone(milestone_id="MS-01", name="Interim report", due_date=date(2026, 6, 30), deliverable="interim_report")],
    )
    (state_dir / "project-state.json").write_text(state.model_dump_json(indent=2) + "\n", encoding="utf-8")

    goals = initialize_project_goals(tmp_path)
    skipped = initialize_project_goals(tmp_path)

    assert goals.project_id == "PRJ-2026-0001"
    assert goals.deadlines[0].deadline_id == "DL-MS-01"
    assert goals.deadlines[0].linked_milestones == ["MS-01"]
    assert "skipped_existing" in skipped.warnings
    assert load_project_goals(state_dir / "project-goals.json").title == "Demo Project"


def test_goals_review_flags_broken_links_unreviewed_evidence_and_overdue_deadline(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-LOW1234",
                source_file="inbox/metrics.csv",
                evidence_type="experiment_result",
                claim="Candidate result.",
                status="needs_review",
            )
        ],
        tmp_path / "state",
    )
    goals = ProjectGoalsFile(
        project_id="PRJ-2026-0001",
        title="Demo Project",
        status="accepted",
        objectives=[
            ProjectObjective(
                objective_id="OBJ-01",
                title="Validate KPI readiness",
                linked_kpis=["KPI-MISSING"],
                linked_evidence_ids=["EVI-2026-LOW1234"],
                review_status="accepted",
            )
        ],
        deadlines=[
            ProjectDeadline(
                deadline_id="DL-01",
                due_date=date(2026, 5, 18),
                title="Submit monthly report",
                deliverable_type="monthly_report",
                linked_objective_ids=["OBJ-01"],
                linked_report_paths=["reports/monthly-report.md"],
                status="planned",
                review_status="accepted",
            )
        ],
    )
    (tmp_path / "state" / "project-goals.json").write_text(goals.model_dump_json(indent=2) + "\n", encoding="utf-8")

    result = generate_goals_review(tmp_path, today="2026-05-19")
    rendered = render_goals_review_markdown(result)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert result.overdue_count == 1
    assert "deadline_overdue" in codes
    assert "deadline_linked_report_missing" in codes
    assert "objective_linked_kpi_missing" in codes
    assert "goals_linked_evidence_needs_review" in codes
    assert "Operating projection only" in rendered


def test_goals_review_accepts_hash_bound_approved_report_deadline(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report.md"
    report.write_text("# Monthly Report\n", encoding="utf-8")
    approval = create_approval_record(
        "report",
        "monthly-report",
        "approved",
        "Reviewer",
        target_path=str(report),
        reviewed_at="2026-05-18T09:00:00Z",
    )
    write_approval_record(approval, tmp_path / "state" / "approvals")
    goals = ProjectGoalsFile(
        project_id="PRJ-2026-0001",
        title="Demo Project",
        status="accepted",
        objectives=[
            ProjectObjective(
                objective_id="OBJ-01",
                title="Prepare report",
                linked_report_paths=["reports/monthly-report.md"],
                review_status="accepted",
            )
        ],
        deadlines=[
            ProjectDeadline(
                deadline_id="DL-01",
                due_date=date(2026, 6, 30),
                title="Monthly report review",
                deliverable_type="monthly_report",
                linked_objective_ids=["OBJ-01"],
                linked_report_paths=["reports/monthly-report.md"],
                status="planned",
                review_status="accepted",
            )
        ],
    )
    (tmp_path / "state" / "project-goals.json").write_text(goals.model_dump_json(indent=2) + "\n", encoding="utf-8")

    result = generate_goals_review(tmp_path, today=date(2026, 5, 19))

    assert result.status == "ready"
    assert result.finding_count == 0
    assert result.deadline_count == 1


def test_goals_review_cli_and_schema_round_trip(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "goals-review.md"
    json_output = tmp_path / "state" / "goals-review.json"

    assert main(["goals-review", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["root"] == str(tmp_path)
    assert output.exists()
    assert main(["deadline-check", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["validate-json", "project-goals", str(tmp_path / "state" / "project-goals.json")]) == 0
    assert main(["validate-json", "goals-review", str(json_output)]) == 0
    assert main(["validate-json", "project-objective", "templates/project-objective.json"]) == 0
    assert main(["validate-json", "project-deadline", "templates/project-deadline.json"]) == 0


def test_goals_review_integrates_with_workspace_operations_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    goals = ProjectGoalsFile(
        project_id="PRJ-2026-0001",
        title="Demo Project",
        status="accepted",
        deadlines=[
            ProjectDeadline(
                deadline_id="DL-01",
                due_date=date(2026, 5, 18),
                title="Overdue report",
                deliverable_type="monthly_report",
                linked_report_paths=["reports/missing-report.md"],
                status="planned",
                review_status="accepted",
            )
        ],
    )
    (tmp_path / "state" / "project-goals.json").write_text(goals.model_dump_json(indent=2) + "\n", encoding="utf-8")

    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor, action_plan=actions)
    pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    codes = {finding.code for finding in doctor.findings}
    titles = {action.title for action in actions.actions}
    node_types = {node.node_type for node in trace.nodes}

    assert "goals_review_high_findings" in codes
    assert "Review project goals and deadlines" in titles
    assert summary.goals_review_high_count >= 1
    assert pack.goals_review_high_count >= 1
    assert "project_deadline" in node_types
    assert (tmp_path / "reports" / "goals-review.md").exists()
    assert (tmp_path / "state" / "goals-review.json").exists()
