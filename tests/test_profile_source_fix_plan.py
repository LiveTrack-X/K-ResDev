import json

from k_resdev_skill.cli import main
from k_resdev_skill.profile_source_fix_plan import generate_profile_source_fix_plan, load_profile_source_fix_plan
from k_resdev_skill.profile_source_queue import generate_profile_source_queue
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_profile_source_fix_plan_reports_missing_queue(tmp_path):
    result = generate_profile_source_fix_plan(tmp_path)

    assert result.status == "missing_queue"
    assert result.action_count == 1
    assert result.actions[0].command
    assert result.actions[0].requires_human_review is False


def test_profile_source_fix_plan_translates_queue_items_to_manual_commands(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    generate_profile_source_queue(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-queue.md",
        json_path=tmp_path / "state" / "profile-source-queue.json",
    )

    result = generate_profile_source_fix_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-fix-plan.md",
        json_path=tmp_path / "state" / "profile-source-fix-plan.json",
    )

    assert result.status in {"needs_review", "blocked"}
    assert result.queue_hash and result.queue_hash.startswith("sha256:")
    assert result.action_count >= 1
    assert result.manual_count >= 1
    assert result.official_source_check_count >= 1
    assert all("verified" not in (action.command or "").split("--review-status", 1)[-1].split()[:1] for action in result.actions)
    assert "Proposal only" in (tmp_path / "reports" / "profile-source-fix-plan.md").read_text(encoding="utf-8")


def test_profile_source_fix_plan_cli_and_schema_validation(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project", profile_id="iris-innopolis-2026-017795")
    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["risk_flags"] = []
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    generate_profile_source_queue(tmp_path, json_path=tmp_path / "state" / "profile-source-queue.json")
    output = tmp_path / "reports" / "profile-source-fix-plan.md"
    json_path = tmp_path / "state" / "profile-source-fix-plan.json"

    assert main(["profile-source-fix-plan", "--root", str(tmp_path), "--output", str(output), "--json", str(json_path)]) == 0
    assert main(["validate-json", "profile-source-fix-plan", str(json_path)]) == 0
    assert "profile-source-fix-plan.json" in capsys.readouterr().out
    assert load_profile_source_fix_plan(json_path).action_count >= 1


def test_profile_source_fix_plan_flows_into_doctor_actions_summary_review_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    generate_profile_source_queue(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-queue.md",
        json_path=tmp_path / "state" / "profile-source-queue.json",
    )

    doctor_before = run_workspace_doctor(tmp_path)
    actions_before = generate_workspace_action_plan(tmp_path, doctor_result=doctor_before)

    assert "profile_source_fix_plan_missing" in {finding.code for finding in doctor_before.findings}
    assert any(action.title == "Plan profile source queue fixes" for action in actions_before.actions)

    generate_profile_source_fix_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-fix-plan.md",
        json_path=tmp_path / "state" / "profile-source-fix-plan.json",
    )
    doctor_after = run_workspace_doctor(tmp_path)
    actions_after = generate_workspace_action_plan(tmp_path, doctor_result=doctor_after)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor_after, action_plan=actions_after)
    review_pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)

    assert "profile_source_fix_plan_missing" not in {finding.code for finding in doctor_after.findings}
    assert summary.profile_source_fix_plan_action_count >= 1
    assert str(tmp_path / "reports" / "profile-source-fix-plan.md") in review_pack.generated_paths
    assert review_pack.profile_source_fix_plan_action_count >= 1
    assert "profile_source_fix_plan" in {node.node_type for node in trace.nodes}
