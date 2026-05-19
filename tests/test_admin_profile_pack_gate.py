import hashlib
import json
import shutil

from k_resdev_skill.admin_profile_pack_gate import generate_admin_profile_pack_promotion_gate
from k_resdev_skill.admin_profile_pack_reviews import create_admin_profile_pack_review_record, write_admin_profile_pack_review_record
from k_resdev_skill.cli import main
from k_resdev_skill.profile_promotion import create_profile_promotion_record, write_profile_promotion_record
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor


PROFILE_ID = "iris-innopolis-2026-017795"
PACK_PATH = "templates/agencies/iris-innopolis-2026-017795/admin-obligations.json"


def _make_passing_profile_promotion(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0056", "Admin Pack Gate Project", profile_id=PROFILE_ID)
    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["review_status"] = "verified"
    sources[0]["verified_by"] = "project-owner"
    sources[0]["risk_flags"] = []
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")

    review_path = tmp_path / "state" / "profile-review.json"
    review = generate_profile_review(tmp_path, output_path=tmp_path / "reports" / "profile-review.md", json_path=review_path)
    review_hash = _sha256_file(review_path)
    record = create_profile_promotion_record(
        tmp_path,
        decision="verified",
        reviewer="project-owner",
        profile_review_hash=review_hash,
        profile_review_path=review_path,
        reviewed_at="2026-05-19T09:00:00Z",
    )
    write_profile_promotion_record(record, tmp_path / "state" / "profile-promotions")
    assert review.can_promote is True
    return review_path, review_hash


def _record_admin_pack_review(tmp_path, decision="accepted", *, templates_root=None, profile_pack_path=None, pack_hash=None):
    record = create_admin_profile_pack_review_record(
        tmp_path,
        profile_id=PROFILE_ID,
        decision=decision,
        reviewer="Admin Reviewer",
        profile_pack_hash=pack_hash or _sha256_file(PACK_PATH),
        profile_pack_path=profile_pack_path,
        templates_root=templates_root,
        reviewed_at="2026-05-19T10:00:00Z",
    )
    write_admin_profile_pack_review_record(record, tmp_path / "state" / "admin-profile-pack-reviews")
    return record


def test_admin_profile_pack_gate_needs_review_without_promotion_or_admin_review(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0056", "Admin Pack Gate Project", profile_id=PROFILE_ID)

    result = generate_admin_profile_pack_promotion_gate(tmp_path, PROFILE_ID)

    assert result.status == "needs_review"
    assert result.can_use_reviewed_seed is False
    check_ids = {check.check_id for check in result.checks if check.status == "fail"}
    assert "profile_review_can_promote" in check_ids
    assert "profile_promotion_verified_current" in check_ids
    assert "admin_profile_pack_reviews_resolved" in check_ids


def test_admin_profile_pack_gate_allows_hash_bound_reviewed_seed_candidate(tmp_path):
    _make_passing_profile_promotion(tmp_path)
    _record_admin_pack_review(tmp_path, decision="accepted")

    result = generate_admin_profile_pack_promotion_gate(
        tmp_path,
        PROFILE_ID,
        output_path=tmp_path / "reports" / "admin-profile-pack-gate.md",
        json_path=tmp_path / "state" / "admin-profile-pack-gate.json",
    )
    doctor = run_workspace_doctor(tmp_path)

    assert result.status == "ready_with_notes"
    assert result.can_use_reviewed_seed is True
    assert result.admin_profile_pack_reviewed_target_count == result.admin_profile_pack_review_target_count
    assert "admin_profile_pack_gate_needs_review" not in {finding.code for finding in doctor.findings}
    assert (tmp_path / "reports" / "admin-profile-pack-gate.md").exists()
    assert (tmp_path / "state" / "admin-profile-pack-gate.json").exists()


def test_admin_profile_pack_gate_blocks_stale_admin_pack_review_hash(tmp_path):
    _make_passing_profile_promotion(tmp_path)
    templates_root = tmp_path / "templates"
    profile_dir = templates_root / PROFILE_ID
    profile_dir.mkdir(parents=True)
    pack_path = profile_dir / "admin-obligations.json"
    shutil.copyfile(PACK_PATH, pack_path)
    pack_hash = _sha256_file(pack_path)
    _record_admin_pack_review(tmp_path, decision="accepted", templates_root=templates_root, pack_hash=pack_hash)

    payload = json.loads(pack_path.read_text(encoding="utf-8"))
    payload["warnings"].append("changed_after_review")
    pack_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = generate_admin_profile_pack_promotion_gate(tmp_path, PROFILE_ID, templates_root=templates_root)

    assert result.status == "blocked"
    assert result.can_use_reviewed_seed is False
    assert result.high_count >= 1
    assert "admin_profile_pack_reviews_current" in {check.check_id for check in result.checks if check.status == "fail"}


def test_admin_profile_pack_gate_cli_and_schema_validation(tmp_path):
    _make_passing_profile_promotion(tmp_path)
    _record_admin_pack_review(tmp_path, decision="accepted_risk")

    assert (
        main(
            [
                "admin-profile-pack-gate",
                "--root",
                str(tmp_path),
                "--profile",
                PROFILE_ID,
                "--output",
                str(tmp_path / "reports" / "admin-profile-pack-gate.md"),
                "--json",
                str(tmp_path / "state" / "admin-profile-pack-gate.json"),
            ]
        )
        == 0
    )
    assert main(["validate-json", "admin-profile-pack-gate", str(tmp_path / "state" / "admin-profile-pack-gate.json")]) == 0


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
