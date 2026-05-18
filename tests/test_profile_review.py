import json

from k_resdev_skill.cli import main
from k_resdev_skill.profile_review import generate_profile_review, load_profile_review
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan


def test_profile_review_keeps_source_backed_seed_in_needs_review(tmp_path):
    initialize_workspace(
        tmp_path,
        "PRJ-2026-0002",
        "IRIS Seed Project",
        profile_id="iris-innopolis-2026-017795",
    )

    result = generate_profile_review(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-review.md",
        json_path=tmp_path / "state" / "profile-review.json",
    )
    codes = {item.check_id for item in result.checklist if item.status == "fail"}

    assert result.status == "needs_review"
    assert result.can_promote is False
    assert result.source_count == 1
    assert "PRS-IRIS-017795-20260519:review_status_verified" in codes
    assert "PRS-IRIS-017795-20260519:risk_flags_resolved" in codes
    assert (tmp_path / "reports" / "profile-review.md").read_text(encoding="utf-8").startswith("# Profile Review")
    assert load_profile_review(tmp_path / "state" / "profile-review.json").status == "needs_review"


def test_profile_review_can_promote_after_supplied_human_source_review(tmp_path):
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

    result = generate_profile_review(tmp_path)

    assert result.status == "ready_for_human_promotion"
    assert result.can_promote is True
    assert result.failed_count == 0


def test_profile_review_blocks_hash_mismatch_and_routes_actions(tmp_path):
    initialize_workspace(
        tmp_path,
        "PRJ-2026-0002",
        "IRIS Seed Project",
        profile_id="iris-innopolis-2026-017795",
    )
    (tmp_path / "state" / "profile-sources" / "iris-announcement-017795-source-note.md").write_text("changed\n", encoding="utf-8")

    result = generate_profile_review(tmp_path)
    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)

    assert result.status == "blocked"
    assert any(item.check_id.endswith(":source_hash_matches") and item.status == "fail" for item in result.checklist)
    assert "profile_review_blocked" in {finding.code for finding in doctor.findings}
    assert any(action.title == "Review profile promotion readiness" for action in actions.actions)


def test_profile_review_cli_and_schema_validation(tmp_path, capsys):
    initialize_workspace(
        tmp_path,
        "PRJ-2026-0002",
        "IRIS Seed Project",
        profile_id="iris-innopolis-2026-017795",
    )
    review_md = tmp_path / "reports" / "profile-review.md"
    review_json = tmp_path / "state" / "profile-review.json"

    assert main(["profile-review", "--root", str(tmp_path), "--output", str(review_md), "--json", str(review_json)]) == 0
    assert main(["validate-json", "profile-review", str(review_json)]) == 0

    assert "profile-review.json" in capsys.readouterr().out
