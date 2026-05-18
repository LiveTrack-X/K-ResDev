import hashlib
import json
from pathlib import Path

from k_resdev_skill.cli import main
from k_resdev_skill.profile_promotion import create_profile_promotion_record, write_profile_promotion_record
from k_resdev_skill.profile_promotion_apply import apply_profile_promotion_plan, generate_profile_promotion_apply_plan
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_trace import generate_workspace_trace


def _make_verified_promotion(tmp_path):
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
    return record


def test_profile_promotion_apply_plan_is_non_destructive(tmp_path):
    record = _make_verified_promotion(tmp_path)
    profile_path = tmp_path / "state" / "project-profile.json"

    plan = generate_profile_promotion_apply_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-apply-plan.md",
        json_path=tmp_path / "state" / "profile-promotion-apply-plan.json",
    )
    profile_after = json.loads(profile_path.read_text(encoding="utf-8"))

    assert plan.status == "ready_to_apply"
    assert plan.can_apply is True
    assert plan.promotion_id == record.promotion_id
    assert plan.current_profile_status == "needs_review"
    assert plan.proposed_profile["status"] == "verified"
    assert {change.field for change in plan.changes} == {"status", "notes"}
    assert profile_after["status"] == "needs_review"
    assert "Proposal only" in (tmp_path / "reports" / "profile-promotion-apply-plan.md").read_text(encoding="utf-8")


def test_profile_promotion_apply_plan_blocks_without_current_verified_promotion(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    plan = generate_profile_promotion_apply_plan(tmp_path)

    assert plan.status == "missing_promotion_record"
    assert plan.can_apply is False
    assert plan.change_count == 0


def test_profile_promotion_apply_plan_blocks_stale_review_hash(tmp_path):
    _make_verified_promotion(tmp_path)
    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["verified_by"] = "project-owner-2"
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    generate_profile_review(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-review.md",
        json_path=tmp_path / "state" / "profile-review.json",
    )

    plan = generate_profile_promotion_apply_plan(tmp_path)

    assert plan.status == "stale_review_hash"
    assert plan.can_apply is False


def test_profile_promotion_apply_plan_flows_into_doctor_actions_and_trace(tmp_path):
    _make_verified_promotion(tmp_path)
    doctor_before = run_workspace_doctor(tmp_path)
    actions_before = generate_workspace_action_plan(tmp_path, doctor_result=doctor_before)

    generate_profile_promotion_apply_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-apply-plan.md",
        json_path=tmp_path / "state" / "profile-promotion-apply-plan.json",
    )
    doctor_after = run_workspace_doctor(tmp_path)
    trace = generate_workspace_trace(tmp_path)

    assert "profile_promotion_apply_plan_missing" in {finding.code for finding in doctor_before.findings}
    assert any(action.title == "Generate profile promotion apply plan" for action in actions_before.actions)
    assert "profile_promotion_apply_plan_missing" not in {finding.code for finding in doctor_after.findings}
    assert "profile_promotion_apply_plan" in {node.node_type for node in trace.nodes}


def test_profile_promotion_apply_plan_cli_and_schema_validation(tmp_path, capsys):
    _make_verified_promotion(tmp_path)
    output = tmp_path / "reports" / "profile-promotion-apply-plan.md"
    json_path = tmp_path / "state" / "profile-promotion-apply-plan.json"

    assert main(["profile-promotion-apply-plan", "--root", str(tmp_path), "--output", str(output), "--json", str(json_path)]) == 0
    assert main(["validate-json", "profile-promotion-apply-plan", str(json_path)]) == 0

    assert "profile-promotion-apply-plan.json" in capsys.readouterr().out


def test_profile_promotion_apply_is_hash_guarded_and_writes_backup(tmp_path):
    _make_verified_promotion(tmp_path)
    plan_path = tmp_path / "state" / "profile-promotion-apply-plan.json"
    generate_profile_promotion_apply_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-apply-plan.md",
        json_path=plan_path,
    )
    plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    result = apply_profile_promotion_plan(
        tmp_path,
        apply_plan_path=plan_path,
        apply_plan_hash=plan_hash,
        output_path=tmp_path / "reports" / "profile-promotion-apply-result.md",
        json_path=tmp_path / "state" / "profile-promotion-apply-result.json",
        applied_at="2026-05-19T10:00:00Z",
    )
    profile_after = json.loads((tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8"))
    backup = json.loads(Path(result.backup_path).read_text(encoding="utf-8"))

    assert result.status == "applied"
    assert result.applied is True
    assert result.applied_fields == ["status", "notes"]
    assert profile_after["status"] == "verified"
    assert backup["status"] == "needs_review"
    assert Path(result.backup_path).exists()
    assert "Guarded local mutation" in (tmp_path / "reports" / "profile-promotion-apply-result.md").read_text(encoding="utf-8")


def test_profile_promotion_apply_rejects_bad_hash_and_stale_profile(tmp_path):
    _make_verified_promotion(tmp_path)
    plan_path = tmp_path / "state" / "profile-promotion-apply-plan.json"
    generate_profile_promotion_apply_plan(tmp_path, json_path=plan_path)

    try:
        apply_profile_promotion_plan(tmp_path, apply_plan_path=plan_path, apply_plan_hash="bad")
        raise AssertionError("expected bad hash failure")
    except ValueError as exc:
        assert "apply_plan_hash" in str(exc)

    plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    profile_path = tmp_path / "state" / "project-profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["status"] = "draft"
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    try:
        apply_profile_promotion_plan(tmp_path, apply_plan_path=plan_path, apply_plan_hash=plan_hash)
        raise AssertionError("expected stale profile failure")
    except ValueError as exc:
        assert "before value" in str(exc)


def test_profile_promotion_apply_cli_and_schema_validation(tmp_path, capsys):
    _make_verified_promotion(tmp_path)
    plan_path = tmp_path / "state" / "profile-promotion-apply-plan.json"
    result_json = tmp_path / "state" / "profile-promotion-apply-result.json"
    generate_profile_promotion_apply_plan(tmp_path, json_path=plan_path)
    plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

    assert (
        main(
            [
                "profile-promotion-apply",
                "--root",
                str(tmp_path),
                "--apply-plan",
                str(plan_path),
                "--apply-plan-hash",
                plan_hash,
                "--applied-at",
                "2026-05-19T10:00:00Z",
                "--output",
                str(tmp_path / "reports" / "profile-promotion-apply-result.md"),
                "--json",
                str(result_json),
            ]
        )
        == 0
    )
    assert main(["validate-json", "profile-promotion-apply-result", str(result_json)]) == 0
    assert "profile-promotion-apply-result.json" in capsys.readouterr().out


def test_profile_promotion_apply_result_flows_into_doctor_actions_and_trace(tmp_path):
    _make_verified_promotion(tmp_path)
    plan_path = tmp_path / "state" / "profile-promotion-apply-plan.json"
    generate_profile_promotion_apply_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-apply-plan.md",
        json_path=plan_path,
    )
    doctor_before = run_workspace_doctor(tmp_path)
    actions_before = generate_workspace_action_plan(tmp_path, doctor_result=doctor_before)
    plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    apply_profile_promotion_plan(
        tmp_path,
        apply_plan_path=plan_path,
        apply_plan_hash=plan_hash,
        output_path=tmp_path / "reports" / "profile-promotion-apply-result.md",
        json_path=tmp_path / "state" / "profile-promotion-apply-result.json",
        applied_at="2026-05-19T10:00:00Z",
    )
    doctor_after = run_workspace_doctor(tmp_path)
    trace = generate_workspace_trace(tmp_path)

    assert "profile_promotion_apply_pending" in {finding.code for finding in doctor_before.findings}
    assert any(action.title == "Apply or review profile promotion plan" for action in actions_before.actions)
    assert "profile_promotion_apply_pending" not in {finding.code for finding in doctor_after.findings}
    assert "profile_promotion_apply_result" in {node.node_type for node in trace.nodes}
