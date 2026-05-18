import hashlib
import json
from pathlib import Path

from k_resdev_skill.cli import main
from k_resdev_skill.profile_lifecycle import generate_profile_lifecycle_ledger, load_profile_lifecycle_ledger
from k_resdev_skill.profile_promotion import create_profile_promotion_record, write_profile_promotion_record
from k_resdev_skill.profile_promotion_apply import apply_profile_promotion_plan, generate_profile_promotion_apply_plan
from k_resdev_skill.profile_promotion_revoke import generate_profile_promotion_revoke_plan, revoke_profile_promotion_plan
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
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


def test_profile_lifecycle_ledger_tracks_apply_and_revoke(tmp_path):
    _make_applied_profile_promotion(tmp_path)
    plan_path = tmp_path / "state" / "profile-promotion-revoke-plan.json"
    generate_profile_promotion_revoke_plan(
        tmp_path,
        reviewer="project-owner",
        reason="Supplied revocation review.",
        requested_at="2026-05-19T11:00:00Z",
        output_path=tmp_path / "reports" / "profile-promotion-revoke-plan.md",
        json_path=plan_path,
    )
    revoke_profile_promotion_plan(
        tmp_path,
        revoke_plan_path=plan_path,
        revoke_plan_hash=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        output_path=tmp_path / "reports" / "profile-promotion-revoke-result.md",
        json_path=tmp_path / "state" / "profile-promotion-revoke-result.json",
        revoked_at="2026-05-19T12:00:00Z",
    )

    ledger = generate_profile_lifecycle_ledger(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-lifecycle-ledger.md",
        json_path=tmp_path / "state" / "profile-lifecycle-ledger.json",
    )

    assert ledger.status == "ready"
    assert ledger.finding_count == 0
    assert {
        "current_profile",
        "profile_review",
        "profile_promotion",
        "profile_promotion_apply_plan",
        "profile_promotion_apply_result",
        "profile_promotion_revoke_plan",
        "profile_promotion_revoke_result",
    }.issubset({entry.entry_type for entry in ledger.entries})
    assert "Operating projection only" in (tmp_path / "reports" / "profile-lifecycle-ledger.md").read_text(encoding="utf-8")
    assert load_profile_lifecycle_ledger(tmp_path / "state" / "profile-lifecycle-ledger.json").entry_count == ledger.entry_count


def test_profile_lifecycle_ledger_flags_pending_revoke(tmp_path):
    _make_applied_profile_promotion(tmp_path)
    generate_profile_promotion_revoke_plan(
        tmp_path,
        reviewer="project-owner",
        reason="Pending revoke check.",
        json_path=tmp_path / "state" / "profile-promotion-revoke-plan.json",
    )

    ledger = generate_profile_lifecycle_ledger(tmp_path)

    assert ledger.status == "needs_review"
    assert "profile_lifecycle_revoke_pending" in {finding.code for finding in ledger.findings}


def test_profile_lifecycle_ledger_flags_missing_backup_and_unexplained_drift(tmp_path):
    apply_result = _make_applied_profile_promotion(tmp_path)
    Path(apply_result.backup_path).unlink()
    profile_path = tmp_path / "state" / "project-profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["notes"] = "manual lifecycle drift"
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    ledger = generate_profile_lifecycle_ledger(tmp_path)

    codes = {finding.code for finding in ledger.findings}
    assert ledger.status == "blocked"
    assert "profile_lifecycle_apply_backup_missing" in codes
    assert "profile_lifecycle_apply_result_drift" in codes


def test_profile_lifecycle_cli_and_schema_validation(tmp_path, capsys):
    _make_applied_profile_promotion(tmp_path)
    output = tmp_path / "reports" / "profile-lifecycle-ledger.md"
    json_path = tmp_path / "state" / "profile-lifecycle-ledger.json"

    assert main(["profile-lifecycle-ledger", "--root", str(tmp_path), "--output", str(output), "--json", str(json_path)]) == 0
    assert main(["validate-json", "profile-lifecycle-ledger", str(json_path)]) == 0
    assert "profile-lifecycle-ledger.json" in capsys.readouterr().out


def test_profile_lifecycle_flows_into_doctor_actions_summary_review_and_trace(tmp_path):
    _make_applied_profile_promotion(tmp_path)
    generate_profile_promotion_revoke_plan(
        tmp_path,
        reviewer="project-owner",
        reason="Pending revoke check.",
        json_path=tmp_path / "state" / "profile-promotion-revoke-plan.json",
    )
    generate_profile_lifecycle_ledger(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-lifecycle-ledger.md",
        json_path=tmp_path / "state" / "profile-lifecycle-ledger.json",
    )

    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor, action_plan=actions)
    review_pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)

    assert "profile_lifecycle_review_findings" in {finding.code for finding in doctor.findings}
    assert any(action.title == "Review profile lifecycle ledger" for action in actions.actions)
    assert summary.profile_lifecycle_status == "needs_review"
    assert summary.profile_lifecycle_finding_count >= 1
    assert str(tmp_path / "reports" / "profile-lifecycle-ledger.md") in review_pack.generated_paths
    assert review_pack.profile_lifecycle_status == "needs_review"
    assert "profile_lifecycle_ledger" in {node.node_type for node in trace.nodes}
