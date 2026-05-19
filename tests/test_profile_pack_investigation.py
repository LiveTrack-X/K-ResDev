import hashlib
import json

from k_resdev_skill.cli import main
from k_resdev_skill.profile_lifecycle import generate_profile_lifecycle_ledger
from k_resdev_skill.profile_pack_drilldown import generate_profile_pack_readiness_drilldown
from k_resdev_skill.profile_pack_investigation import generate_profile_pack_investigation_bundle, load_profile_pack_investigation_bundle
from k_resdev_skill.profile_pack_readiness import generate_profile_pack_readiness
from k_resdev_skill.profile_promotion import summarize_profile_promotions
from k_resdev_skill.profile_promotion_apply import generate_profile_promotion_apply_plan
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.profile_source_fix_plan import generate_profile_source_fix_plan
from k_resdev_skill.profile_source_fix_review import (
    create_profile_source_fix_review_record,
    summarize_profile_source_fix_reviews,
    write_profile_source_fix_review_record,
)
from k_resdev_skill.profile_source_queue import generate_profile_source_queue
from k_resdev_skill.profile_sources import generate_profile_integrity
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_profile_pack_investigation_bundle_filters_and_preserves_profile(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    profile_before = (tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8")
    _write_profile_pack_inputs(tmp_path)

    result = generate_profile_pack_investigation_bundle(
        tmp_path,
        profile_id="national-rnd-basic",
        output_path=tmp_path / "reports" / "profile-pack-investigation-bundle.md",
        json_path=tmp_path / "state" / "profile-pack-investigation-bundle.json",
    )

    assert result.bundle_item_count >= 1
    assert result.profile_id == "national-rnd-basic"
    assert result.human_review_missing_count >= 1
    assert result.official_source_check_count >= 1
    assert all(item.profile_id == "national-rnd-basic" for item in result.items if item.profile_id)
    assert all("official" not in (item.source_message or "").lower() or item.requires_official_source_check for item in result.items)
    assert (tmp_path / "reports" / "profile-pack-investigation-bundle.md").read_text(encoding="utf-8").startswith("# Profile Pack Investigation Bundle")
    assert load_profile_pack_investigation_bundle(tmp_path / "state" / "profile-pack-investigation-bundle.json").bundle_id == result.bundle_id
    assert (tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8") == profile_before


def test_profile_pack_investigation_bundle_captures_supplied_fix_review(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    _write_profile_pack_inputs(tmp_path, with_fix_review=True)

    result = generate_profile_pack_investigation_bundle(
        tmp_path,
        finding_code="profile_pack_fix_review_finding",
    )

    assert result.bundle_item_count >= 1
    assert any(item.human_review_ref_id for item in result.items)
    assert any(item.human_review_status.startswith("profile_source_fix_review:") for item in result.items)


def test_profile_pack_investigation_cli_and_schema_validation(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    _write_profile_pack_inputs(tmp_path)
    output = tmp_path / "reports" / "profile-pack-investigation-bundle.md"
    json_path = tmp_path / "state" / "profile-pack-investigation-bundle.json"

    assert main(["profile-pack-investigation-bundle", "--root", str(tmp_path), "--profile-id", "national-rnd-basic", "--output", str(output), "--json", str(json_path)]) in {0, 1}
    payload = json.loads(capsys.readouterr().out)

    assert payload["bundle_item_count"] >= 1
    assert output.exists()
    assert json_path.exists()
    assert main(["validate-json", "profile-pack-investigation-bundle", str(json_path)]) == 0


def test_profile_pack_investigation_flows_into_doctor_actions_summary_review_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    _write_profile_pack_inputs(tmp_path, include_investigation=False)

    doctor_before = run_workspace_doctor(tmp_path)
    actions_before = generate_workspace_action_plan(tmp_path, doctor_result=doctor_before)
    before_codes = {finding.code for finding in doctor_before.findings}

    assert "profile_pack_investigation_bundle_missing" in before_codes
    assert any(action.title == "Prepare profile pack investigation bundle" for action in actions_before.actions)

    generate_profile_pack_investigation_bundle(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-investigation-bundle.md",
        json_path=tmp_path / "state" / "profile-pack-investigation-bundle.json",
    )
    doctor_after = run_workspace_doctor(tmp_path)
    actions_after = generate_workspace_action_plan(tmp_path, doctor_result=doctor_after)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor_after, action_plan=actions_after)
    review_pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    after_codes = {finding.code for finding in doctor_after.findings}

    assert "profile_pack_investigation_bundle_missing" not in after_codes
    assert summary.profile_pack_investigation_item_count >= 1
    assert review_pack.profile_pack_investigation_item_count >= 1
    assert str(tmp_path / "reports" / "profile-pack-investigation-bundle.md") in review_pack.generated_paths
    assert "profile_pack_investigation_bundle" in {node.node_type for node in trace.nodes}


def _write_profile_pack_inputs(tmp_path, include_investigation=True, with_fix_review=False):
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
    fix_plan = generate_profile_source_fix_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-fix-plan.md",
        json_path=tmp_path / "state" / "profile-source-fix-plan.json",
    )
    if with_fix_review and fix_plan.actions:
        record = create_profile_source_fix_review_record(
            tmp_path,
            action_id=fix_plan.actions[0].action_id,
            decision="accepted_risk",
            reviewer="Reviewer",
            fix_plan_hash=_sha256_file(tmp_path / "state" / "profile-source-fix-plan.json"),
        )
        write_profile_source_fix_review_record(record, tmp_path / "state" / "profile-source-fix-reviews")
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
    generate_profile_pack_readiness_drilldown(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-readiness-drilldown.md",
        json_path=tmp_path / "state" / "profile-pack-readiness-drilldown.json",
    )
    if include_investigation:
        generate_profile_pack_investigation_bundle(
            tmp_path,
            output_path=tmp_path / "reports" / "profile-pack-investigation-bundle.md",
            json_path=tmp_path / "state" / "profile-pack-investigation-bundle.json",
        )


def _sha256_file(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
