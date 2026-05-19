import hashlib
import json

from k_resdev_skill.admin_operating import initialize_admin_obligations
from k_resdev_skill.admin_profile_pack_reviews import create_admin_profile_pack_review_record, write_admin_profile_pack_review_record
from k_resdev_skill.admin_reviewed_seed_drift import generate_admin_reviewed_seed_drift_dashboard
from k_resdev_skill.cli import main
from k_resdev_skill.profile_promotion import create_profile_promotion_record, write_profile_promotion_record
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_trace import generate_workspace_trace


PROFILE_ID = "iris-innopolis-2026-017795"
PACK_PATH = "templates/agencies/iris-innopolis-2026-017795/admin-obligations.json"


def test_reviewed_seed_drift_dashboard_not_configured_without_reviewed_seed(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0058", "Reviewed Seed Drift Project", profile_id=PROFILE_ID)

    result = generate_admin_reviewed_seed_drift_dashboard(tmp_path)

    assert result.status == "not_configured"
    assert result.drift_count == 0
    assert result.action_count == 0


def test_reviewed_seed_drift_dashboard_ready_when_hashes_match(tmp_path):
    _make_reviewed_seed_ready_workspace(tmp_path)
    initialize_admin_obligations(tmp_path, profile_id=PROFILE_ID, reviewed_seed=True)

    result = generate_admin_reviewed_seed_drift_dashboard(
        tmp_path,
        output_path=tmp_path / "reports" / "admin-reviewed-seed-drift.md",
        json_path=tmp_path / "state" / "admin-reviewed-seed-drift.json",
    )

    assert result.status == "ready"
    assert result.profile_id == PROFILE_ID
    assert result.drift_count == 0
    assert (tmp_path / "reports" / "admin-reviewed-seed-drift.md").exists()
    assert json.loads((tmp_path / "state" / "admin-reviewed-seed-drift.json").read_text(encoding="utf-8"))["status"] == "ready"


def test_reviewed_seed_drift_dashboard_routes_profile_review_hash_drift(tmp_path):
    _make_reviewed_seed_ready_workspace(tmp_path)
    initialize_admin_obligations(tmp_path, profile_id=PROFILE_ID, reviewed_seed=True)
    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["verified_by"] = "different-reviewer"
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    generate_profile_review(tmp_path, json_path=tmp_path / "state" / "profile-review.json")

    dashboard = generate_admin_reviewed_seed_drift_dashboard(tmp_path)
    doctor = run_workspace_doctor(tmp_path)
    action_plan = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    trace = generate_workspace_trace(tmp_path)

    assert dashboard.status == "blocked"
    assert dashboard.high_count == 1
    assert {item.finding_code for item in dashboard.items} == {"admin_reviewed_seed_profile_review_hash_mismatch"}
    assert dashboard.items[0].repair_command is not None
    assert "profile-review" in dashboard.items[0].repair_command
    assert "admin_reviewed_seed_drift_high_findings" in {finding.code for finding in doctor.findings}
    assert any("admin-reviewed-seed-drift" in (action.command or "") for action in action_plan.actions)
    assert any(node.node_type == "admin_reviewed_seed_drift" for node in trace.nodes)


def test_reviewed_seed_drift_cli_and_schema_validation(tmp_path):
    _make_reviewed_seed_ready_workspace(tmp_path)
    initialize_admin_obligations(tmp_path, profile_id=PROFILE_ID, reviewed_seed=True)

    assert (
        main(
            [
                "admin-reviewed-seed-drift",
                "--root",
                str(tmp_path),
                "--output",
                str(tmp_path / "reports" / "admin-reviewed-seed-drift.md"),
                "--json",
                str(tmp_path / "state" / "admin-reviewed-seed-drift.json"),
            ]
        )
        == 0
    )
    assert main(["validate-json", "admin-reviewed-seed-drift", str(tmp_path / "state" / "admin-reviewed-seed-drift.json")]) == 0
    assert main(["validate-json", "admin-reviewed-seed-drift-item", "templates/admin-reviewed-seed-drift-item.json"]) == 0


def _make_reviewed_seed_ready_workspace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0058", "Reviewed Seed Drift Project", profile_id=PROFILE_ID)
    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["review_status"] = "verified"
    sources[0]["verified_by"] = "project-owner"
    sources[0]["risk_flags"] = []
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")

    review_path = tmp_path / "state" / "profile-review.json"
    generate_profile_review(tmp_path, output_path=tmp_path / "reports" / "profile-review.md", json_path=review_path)
    promotion = create_profile_promotion_record(
        tmp_path,
        decision="verified",
        reviewer="project-owner",
        profile_review_hash=_sha256_file(review_path),
        profile_review_path=review_path,
        reviewed_at="2026-05-19T11:00:00Z",
    )
    write_profile_promotion_record(promotion, tmp_path / "state" / "profile-promotions")

    review = create_admin_profile_pack_review_record(
        tmp_path,
        profile_id=PROFILE_ID,
        decision="accepted",
        reviewer="Admin Reviewer",
        profile_pack_hash=_sha256_file(PACK_PATH),
        reviewed_at="2026-05-19T11:30:00Z",
    )
    write_admin_profile_pack_review_record(review, tmp_path / "state" / "admin-profile-pack-reviews")


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
