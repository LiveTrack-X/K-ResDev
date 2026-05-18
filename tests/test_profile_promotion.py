import hashlib
import json

import pytest

from k_resdev_skill.cli import main
from k_resdev_skill.profile_promotion import (
    create_profile_promotion_record,
    load_profile_promotion_records,
    summarize_profile_promotions,
    write_profile_promotion_record,
)
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_trace import generate_workspace_trace


def _make_passing_profile_review(tmp_path):
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
    review = generate_profile_review(tmp_path, output_path=tmp_path / "reports" / "profile-review.md", json_path=review_path)
    review_hash = hashlib.sha256(review_path.read_bytes()).hexdigest()
    assert review.can_promote is True
    return review_path, review_hash


def test_profile_promotion_record_binds_to_passing_review_hash(tmp_path):
    review_path, review_hash = _make_passing_profile_review(tmp_path)

    record = create_profile_promotion_record(
        tmp_path,
        decision="verified",
        reviewer="project-owner",
        profile_review_hash=review_hash,
        profile_review_path=review_path,
        reviewed_at="2026-05-19T09:00:00Z",
    )
    write_profile_promotion_record(record, tmp_path / "state" / "profile-promotions")
    summary = summarize_profile_promotions(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-summary.md",
        json_path=tmp_path / "state" / "profile-promotion-summary.json",
    )

    assert record.promotion_id.startswith("PPR-2026-")
    assert record.profile_review_hash == f"sha256:{review_hash}"
    assert summary.status == "verified_recorded"
    assert summary.hash_mismatch_count == 0
    assert load_profile_promotion_records(tmp_path / "state" / "profile-promotions")[0].decision == "verified"


def test_profile_promotion_record_rejects_hash_mismatch(tmp_path):
    review_path, _ = _make_passing_profile_review(tmp_path)

    with pytest.raises(ValueError, match="profile_review_hash"):
        create_profile_promotion_record(
            tmp_path,
            decision="verified",
            reviewer="project-owner",
            profile_review_hash="sha256:bad",
            profile_review_path=review_path,
        )


def test_profile_promotion_record_rejects_non_passing_review(tmp_path):
    initialize_workspace(
        tmp_path,
        "PRJ-2026-0002",
        "IRIS Seed Project",
        profile_id="iris-innopolis-2026-017795",
    )
    review_path = tmp_path / "state" / "profile-review.json"
    generate_profile_review(tmp_path, json_path=review_path)
    review_hash = hashlib.sha256(review_path.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="not ready"):
        create_profile_promotion_record(
            tmp_path,
            decision="verified",
            reviewer="project-owner",
            profile_review_hash=review_hash,
            profile_review_path=review_path,
        )


def test_profile_promotion_flows_into_doctor_actions_and_trace(tmp_path):
    review_path, review_hash = _make_passing_profile_review(tmp_path)
    doctor_before = run_workspace_doctor(tmp_path)
    actions_before = generate_workspace_action_plan(tmp_path, doctor_result=doctor_before)

    record = create_profile_promotion_record(
        tmp_path,
        decision="verified",
        reviewer="project-owner",
        profile_review_hash=review_hash,
        profile_review_path=review_path,
        reviewed_at="2026-05-19T09:00:00Z",
    )
    write_profile_promotion_record(record, tmp_path / "state" / "profile-promotions")
    doctor_after = run_workspace_doctor(tmp_path)
    trace = generate_workspace_trace(tmp_path)

    assert "profile_promotion_record_missing" in {finding.code for finding in doctor_before.findings}
    assert any(action.title == "Record profile promotion decision" for action in actions_before.actions)
    assert "profile_promotion_record_missing" not in {finding.code for finding in doctor_after.findings}
    assert "profile_promotion" in {node.node_type for node in trace.nodes}


def test_latest_matching_promotion_stays_current_when_older_record_is_stale(tmp_path):
    review_path, first_hash = _make_passing_profile_review(tmp_path)
    first = create_profile_promotion_record(
        tmp_path,
        decision="verified",
        reviewer="project-owner",
        profile_review_hash=first_hash,
        profile_review_path=review_path,
        reviewed_at="2026-05-19T09:00:00Z",
    )
    write_profile_promotion_record(first, tmp_path / "state" / "profile-promotions")

    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["verified_by"] = "project-owner-2"
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    generate_profile_review(tmp_path, output_path=tmp_path / "reports" / "profile-review.md", json_path=review_path)
    second_hash = hashlib.sha256(review_path.read_bytes()).hexdigest()
    second = create_profile_promotion_record(
        tmp_path,
        decision="verified",
        reviewer="project-owner",
        profile_review_hash=second_hash,
        profile_review_path=review_path,
        reviewed_at="2026-05-20T09:00:00Z",
    )
    write_profile_promotion_record(second, tmp_path / "state" / "profile-promotions")

    summary = summarize_profile_promotions(tmp_path)
    doctor = run_workspace_doctor(tmp_path)

    assert first_hash != second_hash
    assert summary.status == "verified_recorded"
    assert summary.hash_mismatch_count == 1
    assert "profile_promotion_review_hash_mismatch" not in {finding.code for finding in doctor.findings}


def test_profile_promotion_cli_and_schema_validation(tmp_path, capsys):
    review_path, review_hash = _make_passing_profile_review(tmp_path)

    assert (
        main(
            [
                "profile-promotion-record",
                "--root",
                str(tmp_path),
                "--decision",
                "verified",
                "--reviewer",
                "project-owner",
                "--profile-review",
                str(review_path),
                "--profile-review-hash",
                review_hash,
                "--reviewed-at",
                "2026-05-19T09:00:00Z",
            ]
        )
        == 0
    )
    assert main(["profile-promotion-summary", "--root", str(tmp_path), "--output", str(tmp_path / "reports" / "profile-promotion-summary.md"), "--json", str(tmp_path / "state" / "profile-promotion-summary.json")]) == 0
    assert main(["validate-json", "profile-promotion-record", str(next((tmp_path / "state" / "profile-promotions").glob("*.json")))]) == 0
    assert main(["validate-json", "profile-promotion-summary", str(tmp_path / "state" / "profile-promotion-summary.json")]) == 0

    assert "profile-promotion-summary.json" in capsys.readouterr().out
