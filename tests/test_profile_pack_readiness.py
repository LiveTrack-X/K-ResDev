import json

from k_resdev_skill.cli import main
from k_resdev_skill.profile_pack_readiness import generate_profile_pack_readiness, load_profile_pack_readiness
from k_resdev_skill.profile_source_fix_plan import generate_profile_source_fix_plan
from k_resdev_skill.profile_source_fix_review import summarize_profile_source_fix_reviews
from k_resdev_skill.profile_source_queue import generate_profile_source_queue
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_profile_pack_readiness_summarizes_local_profile_pipeline(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project", profile_id="iris-innopolis-2026-017795")
    profile_before = (tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8")
    generate_profile_source_queue(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-queue.md",
        json_path=tmp_path / "state" / "profile-source-queue.json",
    )
    generate_profile_source_fix_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-fix-plan.md",
        json_path=tmp_path / "state" / "profile-source-fix-plan.json",
    )
    summarize_profile_source_fix_reviews(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-fix-summary.md",
        json_path=tmp_path / "state" / "profile-source-fix-summary.json",
    )

    result = generate_profile_pack_readiness(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-readiness.md",
        json_path=tmp_path / "state" / "profile-pack-readiness.json",
    )
    codes = {finding.code for finding in result.findings}

    assert result.profile_count >= 1
    assert result.finding_count >= 1
    assert result.status in {"blocked", "needs_review", "ready_with_notes"}
    assert any(profile.profile_id == "iris-innopolis-2026-017795" for profile in result.profiles)
    assert "profile_pack_source_queue_finding" in codes
    assert "profile_pack_fix_action_open" in codes
    assert (tmp_path / "reports" / "profile-pack-readiness.md").read_text(encoding="utf-8").startswith("# Profile Pack Readiness")
    assert load_profile_pack_readiness(tmp_path / "state" / "profile-pack-readiness.json").profile_count == result.profile_count
    assert (tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8") == profile_before


def test_profile_pack_readiness_cli_and_schema_validation(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "profile-pack-readiness.md"
    json_path = tmp_path / "state" / "profile-pack-readiness.json"

    assert main(["profile-pack-readiness", "--root", str(tmp_path), "--output", str(output), "--json", str(json_path)]) in {0, 1}
    payload = json.loads(capsys.readouterr().out)

    assert payload["profile_count"] >= 1
    assert output.exists()
    assert json_path.exists()
    assert main(["validate-json", "profile-pack-readiness", str(json_path)]) == 0


def test_profile_pack_readiness_flows_into_doctor_actions_summary_review_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    doctor_before = run_workspace_doctor(tmp_path)
    actions_before = generate_workspace_action_plan(tmp_path, doctor_result=doctor_before)
    before_codes = {finding.code for finding in doctor_before.findings}

    assert "profile_pack_readiness_missing" in before_codes
    assert any(action.title == "Review profile pack readiness" for action in actions_before.actions)

    generate_profile_pack_readiness(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-readiness.md",
        json_path=tmp_path / "state" / "profile-pack-readiness.json",
    )
    doctor_after = run_workspace_doctor(tmp_path)
    actions_after = generate_workspace_action_plan(tmp_path, doctor_result=doctor_after)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor_after, action_plan=actions_after)
    review_pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    after_codes = {finding.code for finding in doctor_after.findings}

    assert "profile_pack_readiness_missing" not in after_codes
    assert "profile_pack_readiness_findings" in after_codes or "profile_pack_readiness_high_findings" in after_codes
    assert summary.profile_pack_readiness_profile_count >= 1
    assert summary.profile_pack_readiness_finding_count >= 1
    assert review_pack.profile_pack_readiness_profile_count >= 1
    assert str(tmp_path / "reports" / "profile-pack-readiness.md") in review_pack.generated_paths
    assert "profile_pack_readiness" in {node.node_type for node in trace.nodes}
