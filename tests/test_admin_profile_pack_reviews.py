import json
import shutil

from k_resdev_skill.admin_profile_pack_reviews import (
    create_admin_profile_pack_review_record,
    summarize_admin_profile_pack_reviews,
    write_admin_profile_pack_review_record,
)
from k_resdev_skill.cli import main


def test_admin_profile_pack_review_records_hash_bound_pack_review(tmp_path):
    profile_id = "iris-innopolis-2026-017795"
    pack_path = "templates/agencies/iris-innopolis-2026-017795/admin-obligations.json"
    pack_hash = _sha256(pack_path)

    before = summarize_admin_profile_pack_reviews(tmp_path, profile_id=profile_id)
    assert before.status == "needs_review"
    assert before.target_count == 4
    assert before.missing_target_review_count == 4
    assert "admin_profile_pack_review_missing" in {finding.code for finding in before.findings}

    record = create_admin_profile_pack_review_record(
        tmp_path,
        profile_id=profile_id,
        decision="accepted_risk",
        reviewer="Admin Reviewer",
        profile_pack_hash=pack_hash,
        reviewed_at="2026-05-19T00:00:00Z",
    )
    write_admin_profile_pack_review_record(record, tmp_path / "state" / "admin-profile-pack-reviews")

    after = summarize_admin_profile_pack_reviews(tmp_path, profile_id=profile_id)
    assert after.status == "ready_with_notes"
    assert after.record_count == 1
    assert after.accepted_risk_count == 1
    assert after.reviewed_target_count == 4
    assert after.missing_target_review_count == 0
    assert after.unresolved_count == 0
    assert {finding.code for finding in after.findings} == {"admin_profile_pack_review_accepted_risk"}


def test_admin_profile_pack_review_detects_stale_hash(tmp_path):
    profile_id = "national-rnd-basic"
    pack_path = tmp_path / "admin-obligations.json"
    shutil.copyfile("templates/agencies/national-rnd-basic/admin-obligations.json", pack_path)
    pack_hash = _sha256(pack_path)

    record = create_admin_profile_pack_review_record(
        tmp_path,
        profile_id=profile_id,
        decision="accepted",
        reviewer="Admin Reviewer",
        profile_pack_hash=pack_hash,
        profile_pack_path=pack_path,
        reviewed_at="2026-05-19T00:00:00Z",
    )
    write_admin_profile_pack_review_record(record, tmp_path / "state" / "admin-profile-pack-reviews")

    payload = json.loads(pack_path.read_text(encoding="utf-8"))
    payload["warnings"].append("changed_after_review")
    pack_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = summarize_admin_profile_pack_reviews(tmp_path, profile_id=profile_id, profile_pack_path=pack_path)
    assert result.status == "blocked"
    assert result.stale_record_count == 1
    assert "admin_profile_pack_review_stale_hash" in {finding.code for finding in result.findings}


def test_admin_profile_pack_review_row_level_cli_smoke(tmp_path):
    profile_id = "iris-innopolis-2026-017795"
    pack_path = "templates/agencies/iris-innopolis-2026-017795/admin-obligations.json"
    pack_hash = _sha256(pack_path)

    assert main(
        [
            "admin-profile-pack-review-record",
            "--root",
            str(tmp_path),
            "--profile",
            profile_id,
            "--decision",
            "accepted",
            "--reviewer",
            "Admin Reviewer",
            "--profile-pack-hash",
            pack_hash,
            "--target-type",
            "obligation",
            "--target-id",
            "ADM-IRIS-017795-APPLICATION-001",
        ]
    ) == 0
    assert main(
        [
            "admin-profile-pack-review-summary",
            "--root",
            str(tmp_path),
            "--profile",
            profile_id,
            "--output",
            str(tmp_path / "reports" / "admin-profile-pack-review-summary.md"),
            "--json",
            str(tmp_path / "state" / "admin-profile-pack-review-summary.json"),
        ]
    ) == 0
    assert main(["validate-json", "admin-profile-pack-review-summary", str(tmp_path / "state" / "admin-profile-pack-review-summary.json")]) == 0


def _sha256(path):
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
