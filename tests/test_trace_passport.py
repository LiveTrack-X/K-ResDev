import json

from k_resdev_skill.cli import main
from k_resdev_skill.trace_passport import (
    create_checkpoint,
    generate_checkpoint_resume_plan,
    generate_trace_passport,
    load_checkpoint_entries,
    render_trace_passport_markdown,
)
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_checkpoint_records_hash_metadata_without_copying_artifact_body(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report.md"
    report.write_text("Sensitive draft body should not be copied into checkpoint JSON.\n", encoding="utf-8")

    result = create_checkpoint(
        tmp_path,
        stage="monthly-report",
        summary="Monthly draft created.",
        artifact_paths=[report],
        status="accepted",
        resume_hint="Review monthly-report.md first.",
    )
    checkpoint_text = (tmp_path / "state" / "checkpoints" / f"{result.checkpoint_id}.json").read_text(encoding="utf-8")
    entries = load_checkpoint_entries(tmp_path / "state" / "checkpoints")

    assert result.artifact_count == 1
    assert entries[0].artifact_paths == ["reports/monthly-report.md"]
    assert entries[0].artifact_hashes["reports/monthly-report.md"].startswith("sha256:")
    assert "Sensitive draft body" not in checkpoint_text
    assert "reports/monthly-report.md" in checkpoint_text


def test_trace_passport_flags_stale_artifacts_and_ignores_superseded_as_latest(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report.md"
    report.write_text("draft v1\n", encoding="utf-8")
    old = create_checkpoint(tmp_path, "old-review", "Old checkpoint.", [report], status="superseded")
    current = create_checkpoint(tmp_path, "current-review", "Current checkpoint.", [report], status="accepted")

    report.write_text("draft v2\n", encoding="utf-8")
    passport = generate_trace_passport(tmp_path, tmp_path / "reports" / "trace-passport.md", tmp_path / "state" / "trace-passport.json")
    rendered = render_trace_passport_markdown(passport)
    codes = {finding.code for finding in passport.findings}

    assert passport.status == "stale"
    assert passport.latest_checkpoint_id == current.checkpoint_id
    assert passport.latest_checkpoint_id != old.checkpoint_id
    assert "checkpoint_artifact_stale" in codes
    assert "checkpoint_superseded" in codes
    assert "Trace passport projection only" in rendered
    assert json.loads((tmp_path / "state" / "trace-passport.json").read_text(encoding="utf-8"))["status"] == "stale"


def test_checkpoint_resume_plan_reports_stale_artifacts(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report.md"
    report.write_text("draft v1\n", encoding="utf-8")
    checkpoint = create_checkpoint(tmp_path, "monthly-report", "Monthly report checkpoint.", [report], status="accepted")
    report.write_text("draft v2\n", encoding="utf-8")

    plan = generate_checkpoint_resume_plan(
        tmp_path,
        checkpoint_id=checkpoint.checkpoint_id,
        output_path=tmp_path / "reports" / "checkpoint-resume-plan.md",
        json_path=tmp_path / "state" / "checkpoint-resume-plan.json",
    )

    assert plan.status == "stale"
    assert plan.stale_count == 1
    assert any(action.title == "Refresh stale checkpoint artifacts" for action in plan.actions)
    assert (tmp_path / "reports" / "checkpoint-resume-plan.md").exists()
    assert (tmp_path / "state" / "checkpoint-resume-plan.json").exists()


def test_checkpoint_resume_plan_keeps_unaccepted_checkpoint_in_review_state(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report.md"
    report.write_text("draft v1\n", encoding="utf-8")
    checkpoint = create_checkpoint(tmp_path, "monthly-report", "Monthly report checkpoint.", [report], status="needs_review")

    plan = generate_checkpoint_resume_plan(tmp_path, checkpoint_id=checkpoint.checkpoint_id)

    assert plan.status == "needs_review"
    assert any(action.title == "Review checkpoint status" for action in plan.actions)


def test_trace_passport_integrates_with_workspace_operations(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report.md"
    report.write_text("draft v1\n", encoding="utf-8")
    create_checkpoint(tmp_path, "monthly-report", "Monthly report checkpoint.", [report], status="needs_review")

    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor, action_plan=actions)
    pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    doctor_codes = {finding.code for finding in doctor.findings}
    node_types = {node.node_type for node in trace.nodes}

    assert "trace_passport_review_findings" in doctor_codes
    assert any(action.title == "Review trace passport checkpoints" for action in actions.actions)
    assert summary.checkpoint_count == 1
    assert summary.trace_passport_finding_count >= 1
    assert pack.checkpoint_count == 1
    assert pack.trace_passport_finding_count >= 1
    assert "checkpoint" in node_types
    assert (tmp_path / "reports" / "trace-passport.md").exists()
    assert (tmp_path / "state" / "trace-passport.json").exists()


def test_checkpoint_cli_round_trip_and_schema(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report.md"
    report.write_text("draft v1\n", encoding="utf-8")

    assert (
        main(
            [
                "checkpoint-create",
                "--root",
                str(tmp_path),
                "--stage",
                "monthly-report",
                "--summary",
                "Monthly report checkpoint.",
                "--artifact",
                str(report),
                "--status",
                "accepted",
                "--resume-hint",
                "Open the workspace summary first.",
            ]
        )
        == 0
    )
    create_payload = json.loads(capsys.readouterr().out)
    assert create_payload["checkpoint_id"].startswith("CHK-")

    assert (
        main(
            [
                "checkpoint-summary",
                "--root",
                str(tmp_path),
                "--output",
                str(tmp_path / "reports" / "trace-passport.md"),
                "--json",
                str(tmp_path / "state" / "trace-passport.json"),
            ]
        )
        == 0
    )
    summary_payload = json.loads(capsys.readouterr().out)
    assert summary_payload["checkpoint_count"] == 1

    assert (
        main(
            [
                "checkpoint-resume-plan",
                "--root",
                str(tmp_path),
                "--output",
                str(tmp_path / "reports" / "checkpoint-resume-plan.md"),
                "--json",
                str(tmp_path / "state" / "checkpoint-resume-plan.json"),
            ]
        )
        == 0
    )
    resume_payload = json.loads(capsys.readouterr().out)
    assert resume_payload["checkpoint_id"] == create_payload["checkpoint_id"]

    checkpoint_json = tmp_path / "state" / "checkpoints" / f"{create_payload['checkpoint_id']}.json"
    assert main(["validate-json", "checkpoint", str(checkpoint_json)]) == 0
    assert main(["validate-json", "trace-passport", str(tmp_path / "state" / "trace-passport.json")]) == 0
