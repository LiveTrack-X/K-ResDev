import hashlib
import json
from pathlib import Path

import pytest

from k_resdev_skill.cli import main
from k_resdev_skill.profile_source_fix_plan import generate_profile_source_fix_plan
from k_resdev_skill.profile_source_fix_review import (
    create_profile_source_fix_review_record,
    summarize_profile_source_fix_reviews,
    write_profile_source_fix_review_record,
)
from k_resdev_skill.profile_source_queue import generate_profile_source_queue
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_profile_source_fix_review_record_requires_matching_plan_hash_and_action(tmp_path):
    plan, plan_path = _workspace_with_fix_plan(tmp_path)
    action = plan.actions[0]
    plan_hash = _sha256_file(plan_path)

    record = create_profile_source_fix_review_record(
        tmp_path,
        action.action_id,
        "resolved",
        "Reviewer",
        plan_hash,
        reviewed_at="2026-05-19T00:00:00Z",
        notes="Reviewed supplied remediation evidence.",
    )
    path = write_profile_source_fix_review_record(record, tmp_path / "state" / "profile-source-fix-reviews")

    assert path.exists()
    assert record.fix_plan_hash == plan_hash
    assert record.action_id == action.action_id
    assert record.decision == "resolved"
    assert summarize_profile_source_fix_reviews(tmp_path, reviews_dir="state/profile-source-fix-reviews").record_count == 1

    with pytest.raises(ValueError, match="fix_plan_hash"):
        create_profile_source_fix_review_record(tmp_path, action.action_id, "resolved", "Reviewer", "sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="action_id"):
        create_profile_source_fix_review_record(tmp_path, "PSF-DOES-NOT-EXIST", "resolved", "Reviewer", plan_hash)


def test_profile_source_fix_review_summary_reduces_unresolved_actions(tmp_path):
    plan, plan_path = _workspace_with_fix_plan(tmp_path)

    before = summarize_profile_source_fix_reviews(tmp_path)
    assert before.action_count == plan.action_count
    assert before.unresolved_count >= 1

    reviews_dir = tmp_path / "state" / "profile-source-fix-reviews"
    for index, action in enumerate(plan.actions):
        record = create_profile_source_fix_review_record(
            tmp_path,
            action.action_id,
            "resolved",
            "Reviewer",
            _sha256_file(plan_path),
            reviewed_at=f"2026-05-19T00:00:{index:02d}Z",
        )
        write_profile_source_fix_review_record(record, reviews_dir)

    after = summarize_profile_source_fix_reviews(tmp_path, output_path=tmp_path / "reports" / "profile-source-fix-summary.md", json_path=tmp_path / "state" / "profile-source-fix-summary.json")

    assert after.record_count == plan.action_count
    assert after.unresolved_count == 0
    assert after.high_unresolved_count == 0
    assert after.status == "ready"
    assert (tmp_path / "reports" / "profile-source-fix-summary.md").read_text(encoding="utf-8").startswith("# Profile Source Fix Review Summary")


def test_profile_source_fix_review_summary_flags_stale_hash(tmp_path):
    plan, plan_path = _workspace_with_fix_plan(tmp_path)
    record = create_profile_source_fix_review_record(
        tmp_path,
        plan.actions[0].action_id,
        "resolved",
        "Reviewer",
        _sha256_file(plan_path),
        reviewed_at="2026-05-19T00:00:00Z",
    )
    record_path = write_profile_source_fix_review_record(record, tmp_path / "state" / "profile-source-fix-reviews")
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["fix_plan_hash"] = "sha256:" + "0" * 64
    record_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = summarize_profile_source_fix_reviews(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert result.stale_record_count == 1
    assert "profile_source_fix_review_stale_plan_hash" in codes


def test_profile_source_fix_review_cli_and_schema_validation(tmp_path, capsys):
    plan, plan_path = _workspace_with_fix_plan(tmp_path)
    action_id = plan.actions[0].action_id
    output = tmp_path / "reports" / "profile-source-fix-summary.md"
    json_path = tmp_path / "state" / "profile-source-fix-summary.json"

    assert (
        main(
            [
                "profile-source-fix-record",
                "--root",
                str(tmp_path),
                "--action-id",
                action_id,
                "--decision",
                "resolved",
                "--reviewer",
                "Reviewer",
                "--fix-plan-hash",
                _sha256_file(plan_path),
            ]
        )
        == 0
    )
    record_payload = json.loads(capsys.readouterr().out)
    record_path = tmp_path / "state" / "profile-source-fix-reviews" / f"{record_payload['review_id']}.json"

    assert main(["profile-source-fix-summary", "--root", str(tmp_path), "--output", str(output), "--json", str(json_path)]) in {0, 1}
    assert main(["validate-json", "profile-source-fix-review", str(record_path)]) == 0
    assert main(["validate-json", "profile-source-fix-summary", str(json_path)]) == 0
    assert output.exists()


def test_profile_source_fix_reviews_flow_into_doctor_actions_summary_review_and_trace(tmp_path):
    plan, _plan_path = _workspace_with_fix_plan(tmp_path)

    doctor_before = run_workspace_doctor(tmp_path)
    actions_before = generate_workspace_action_plan(tmp_path, doctor_result=doctor_before)

    assert "profile_source_fix_summary_missing" in {finding.code for finding in doctor_before.findings}
    assert any(action.title == "Summarize profile source fix reviews" for action in actions_before.actions)

    summarize_profile_source_fix_reviews(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-fix-summary.md",
        json_path=tmp_path / "state" / "profile-source-fix-summary.json",
    )
    doctor_after = run_workspace_doctor(tmp_path)
    actions_after = generate_workspace_action_plan(tmp_path, doctor_result=doctor_after)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor_after, action_plan=actions_after)
    review_pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)

    assert "profile_source_fix_summary_missing" not in {finding.code for finding in doctor_after.findings}
    assert summary.profile_source_fix_review_unresolved_count >= 1
    assert summary.profile_source_fix_review_status in {"blocked", "needs_review"}
    assert str(tmp_path / "reports" / "profile-source-fix-summary.md") in review_pack.generated_paths
    assert review_pack.profile_source_fix_review_unresolved_count >= 1
    assert "profile_source_fix_review_summary" in {node.node_type for node in trace.nodes}
    assert plan.action_count >= 1


def _workspace_with_fix_plan(root: Path):
    initialize_workspace(root, "PRJ-2026-0001", "Demo Project")
    generate_profile_source_queue(
        root,
        output_path=root / "reports" / "profile-source-queue.md",
        json_path=root / "state" / "profile-source-queue.json",
    )
    plan_path = root / "state" / "profile-source-fix-plan.json"
    plan = generate_profile_source_fix_plan(
        root,
        output_path=root / "reports" / "profile-source-fix-plan.md",
        json_path=plan_path,
    )
    assert plan.action_count >= 1
    return plan, plan_path


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
