import json

from k_resdev_skill.cli import main
from k_resdev_skill.profile_lifecycle import generate_profile_lifecycle_ledger
from k_resdev_skill.profile_pack_drilldown import generate_profile_pack_readiness_drilldown, load_profile_pack_readiness_drilldown
from k_resdev_skill.profile_pack_readiness import generate_profile_pack_readiness
from k_resdev_skill.profile_promotion import summarize_profile_promotions
from k_resdev_skill.profile_promotion_apply import generate_profile_promotion_apply_plan
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.profile_source_fix_plan import generate_profile_source_fix_plan
from k_resdev_skill.profile_source_fix_review import summarize_profile_source_fix_reviews
from k_resdev_skill.profile_source_queue import generate_profile_source_queue
from k_resdev_skill.profile_sources import generate_profile_integrity
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_profile_pack_drilldown_links_readiness_findings_to_upstream_artifacts(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    profile_before = (tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8")
    _write_profile_pack_inputs(tmp_path)

    result = generate_profile_pack_readiness_drilldown(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-readiness-drilldown.md",
        json_path=tmp_path / "state" / "profile-pack-readiness-drilldown.json",
    )
    source_artifacts = {item.source_artifact for item in result.items}

    assert result.drilldown_count >= 1
    assert result.matched_count == result.drilldown_count
    assert result.missing_artifact_count == 0
    assert result.unmatched_count == 0
    assert "profile_source_queue" in source_artifacts
    assert "profile_source_fix_plan" in source_artifacts
    assert "profile_source_fix_summary" in source_artifacts
    assert all(item.source_artifact_hash for item in result.items)
    assert (tmp_path / "reports" / "profile-pack-readiness-drilldown.md").read_text(encoding="utf-8").startswith("# Profile Pack Readiness Drilldown")
    assert load_profile_pack_readiness_drilldown(tmp_path / "state" / "profile-pack-readiness-drilldown.json").drilldown_count == result.drilldown_count
    assert (tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8") == profile_before


def test_profile_pack_drilldown_cli_and_schema_validation(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    _write_profile_pack_inputs(tmp_path)
    output = tmp_path / "reports" / "profile-pack-readiness-drilldown.md"
    json_path = tmp_path / "state" / "profile-pack-readiness-drilldown.json"

    assert main(["profile-pack-readiness-drilldown", "--root", str(tmp_path), "--output", str(output), "--json", str(json_path)]) in {0, 1}
    payload = json.loads(capsys.readouterr().out)

    assert payload["drilldown_count"] >= 1
    assert output.exists()
    assert json_path.exists()
    assert main(["validate-json", "profile-pack-readiness-drilldown", str(json_path)]) == 0


def test_profile_pack_drilldown_flows_into_doctor_actions_summary_review_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    _write_profile_pack_inputs(tmp_path, include_drilldown=False)

    doctor_before = run_workspace_doctor(tmp_path)
    actions_before = generate_workspace_action_plan(tmp_path, doctor_result=doctor_before)
    before_codes = {finding.code for finding in doctor_before.findings}

    assert "profile_pack_readiness_drilldown_missing" in before_codes
    assert any(action.title == "Review profile pack readiness drilldown" for action in actions_before.actions)

    generate_profile_pack_readiness_drilldown(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-readiness-drilldown.md",
        json_path=tmp_path / "state" / "profile-pack-readiness-drilldown.json",
    )
    doctor_after = run_workspace_doctor(tmp_path)
    actions_after = generate_workspace_action_plan(tmp_path, doctor_result=doctor_after)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor_after, action_plan=actions_after)
    review_pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    after_codes = {finding.code for finding in doctor_after.findings}

    assert "profile_pack_readiness_drilldown_missing" not in after_codes
    assert summary.profile_pack_drilldown_item_count >= 1
    assert review_pack.profile_pack_drilldown_item_count >= 1
    assert str(tmp_path / "reports" / "profile-pack-readiness-drilldown.md") in review_pack.generated_paths
    assert "profile_pack_readiness_drilldown" in {node.node_type for node in trace.nodes}


def _write_profile_pack_inputs(tmp_path, include_drilldown=True):
    generate_profile_integrity(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-integrity.md",
        json_path=tmp_path / "state" / "profile-integrity.json",
    )
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
    generate_profile_review(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-review.md",
        json_path=tmp_path / "state" / "profile-review.json",
    )
    summarize_profile_promotions(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-summary.md",
        json_path=tmp_path / "state" / "profile-promotion-summary.json",
    )
    generate_profile_promotion_apply_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-apply-plan.md",
        json_path=tmp_path / "state" / "profile-promotion-apply-plan.json",
    )
    generate_profile_lifecycle_ledger(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-lifecycle-ledger.md",
        json_path=tmp_path / "state" / "profile-lifecycle-ledger.json",
    )
    generate_profile_pack_readiness(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-readiness.md",
        json_path=tmp_path / "state" / "profile-pack-readiness.json",
    )
    if include_drilldown:
        generate_profile_pack_readiness_drilldown(
            tmp_path,
            output_path=tmp_path / "reports" / "profile-pack-readiness-drilldown.md",
            json_path=tmp_path / "state" / "profile-pack-readiness-drilldown.json",
        )
