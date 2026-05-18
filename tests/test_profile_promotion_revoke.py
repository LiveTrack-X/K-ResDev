import hashlib
import json
from pathlib import Path

from k_resdev_skill.cli import main
from k_resdev_skill.profile_promotion import create_profile_promotion_record, write_profile_promotion_record
from k_resdev_skill.profile_promotion_apply import apply_profile_promotion_plan, generate_profile_promotion_apply_plan
from k_resdev_skill.profile_promotion_revoke import generate_profile_promotion_revoke_plan
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_trace import generate_workspace_trace


def _make_applied_profile_promotion(tmp_path):
    initialize_workspace(
        tmp_path,
        "PRJ-2026-0002",
        "IRIS Seed Project",
        profile_id="iris-innopolis-2026-017795",
    )
    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["review_status"] = "verified"
    sources[0]["verified_by"] = "project-owner"
    sources[0]["risk_flags"] = []
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    review_path = tmp_path / "state" / "profile-review.json"
    generate_profile_review(tmp_path, output_path=tmp_path / "reports" / "profile-review.md", json_path=review_path)
    review_hash = hashlib.sha256(review_path.read_bytes()).hexdigest()
    record = create_profile_promotion_record(
        tmp_path,
        decision="verified",
        reviewer="project-owner",
        profile_review_hash=review_hash,
        profile_review_path=review_path,
        reviewed_at="2026-05-19T09:00:00Z",
    )
    write_profile_promotion_record(record, tmp_path / "state" / "profile-promotions")
    plan_path = tmp_path / "state" / "profile-promotion-apply-plan.json"
    generate_profile_promotion_apply_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-apply-plan.md",
        json_path=plan_path,
    )
    plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    return apply_profile_promotion_plan(
        tmp_path,
        apply_plan_path=plan_path,
        apply_plan_hash=plan_hash,
        output_path=tmp_path / "reports" / "profile-promotion-apply-result.md",
        json_path=tmp_path / "state" / "profile-promotion-apply-result.json",
        applied_at="2026-05-19T10:00:00Z",
    )


def test_profile_promotion_revoke_plan_ready_without_mutation(tmp_path):
    apply_result = _make_applied_profile_promotion(tmp_path)
    profile_path = tmp_path / "state" / "project-profile.json"

    plan = generate_profile_promotion_revoke_plan(
        tmp_path,
        reviewer="project-owner",
        reason="Supplied revocation review.",
        requested_at="2026-05-19T11:00:00Z",
        output_path=tmp_path / "reports" / "profile-promotion-revoke-plan.md",
        json_path=tmp_path / "state" / "profile-promotion-revoke-plan.json",
    )
    profile_after = json.loads(profile_path.read_text(encoding="utf-8"))

    assert plan.status == "ready_to_revoke"
    assert plan.can_revoke is True
    assert plan.current_matches_applied_profile is True
    assert plan.backup_available is True
    assert plan.apply_result_hash.startswith("sha256:")
    assert plan.backup_hash.startswith("sha256:")
    assert plan.current_profile_status == "verified"
    assert plan.restore_profile_status == "needs_review"
    assert plan.promotion_id == apply_result.promotion_id
    assert {change.field for change in plan.changes} == {"status", "notes"}
    assert plan.restored_profile["status"] == "needs_review"
    assert profile_after["status"] == "verified"
    assert "Proposal only" in (tmp_path / "reports" / "profile-promotion-revoke-plan.md").read_text(encoding="utf-8")


def test_profile_promotion_revoke_plan_blocks_missing_backup(tmp_path):
    apply_result = _make_applied_profile_promotion(tmp_path)
    Path(apply_result.backup_path).unlink()

    plan = generate_profile_promotion_revoke_plan(tmp_path, reviewer="project-owner", reason="Backup missing check.")

    assert plan.status == "missing_backup"
    assert plan.can_revoke is False
    assert plan.backup_available is False


def test_profile_promotion_revoke_plan_blocks_profile_drift(tmp_path):
    _make_applied_profile_promotion(tmp_path)
    profile_path = tmp_path / "state" / "project-profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["notes"] = "manual drift"
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    plan = generate_profile_promotion_revoke_plan(tmp_path, reviewer="project-owner", reason="Drift check.")

    assert plan.status == "current_profile_drift"
    assert plan.can_revoke is False
    assert plan.current_matches_applied_profile is False


def test_profile_promotion_revoke_cli_and_schema_validation(tmp_path, capsys):
    _make_applied_profile_promotion(tmp_path)
    output = tmp_path / "reports" / "profile-promotion-revoke-plan.md"
    json_path = tmp_path / "state" / "profile-promotion-revoke-plan.json"

    assert (
        main(
            [
                "profile-promotion-revoke-plan",
                "--root",
                str(tmp_path),
                "--reviewer",
                "project-owner",
                "--reason",
                "Supplied revocation review.",
                "--requested-at",
                "2026-05-19T11:00:00Z",
                "--output",
                str(output),
                "--json",
                str(json_path),
            ]
        )
        == 0
    )
    assert main(["validate-json", "profile-promotion-revoke-plan", str(json_path)]) == 0
    assert "profile-promotion-revoke-plan.json" in capsys.readouterr().out


def test_profile_promotion_revoke_plan_flows_into_trace_doctor_and_actions(tmp_path):
    apply_result = _make_applied_profile_promotion(tmp_path)
    ready_plan = generate_profile_promotion_revoke_plan(
        tmp_path,
        reviewer="project-owner",
        reason="Trace check.",
        output_path=tmp_path / "reports" / "profile-promotion-revoke-plan.md",
        json_path=tmp_path / "state" / "profile-promotion-revoke-plan.json",
    )
    trace = generate_workspace_trace(tmp_path)

    assert ready_plan.status == "ready_to_revoke"
    assert "profile_promotion_revoke_plan" in {node.node_type for node in trace.nodes}

    Path(apply_result.backup_path).unlink()
    generate_profile_promotion_revoke_plan(
        tmp_path,
        reviewer="project-owner",
        reason="Missing backup check.",
        json_path=tmp_path / "state" / "profile-promotion-revoke-plan.json",
    )
    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)

    assert "profile_promotion_revoke_missing_backup" in {finding.code for finding in doctor.findings}
    assert any(action.title == "Review profile promotion revocation plan" for action in actions.actions)
