import hashlib
import json

import pytest

from k_resdev_skill.admin_operating import initialize_admin_obligations, review_admin_obligations
from k_resdev_skill.admin_profile_pack_reviews import create_admin_profile_pack_review_record, write_admin_profile_pack_review_record
from k_resdev_skill.cli import main
from k_resdev_skill.profile_promotion import create_profile_promotion_record, write_profile_promotion_record
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.workspace import initialize_workspace


PROFILE_ID = "iris-innopolis-2026-017795"
PACK_PATH = "templates/agencies/iris-innopolis-2026-017795/admin-obligations.json"


def _make_reviewed_seed_ready_workspace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0057", "Reviewed Seed Project", profile_id=PROFILE_ID)
    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["review_status"] = "verified"
    sources[0]["verified_by"] = "project-owner"
    sources[0]["risk_flags"] = []
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")

    review_path = tmp_path / "state" / "profile-review.json"
    generate_profile_review(tmp_path, output_path=tmp_path / "reports" / "profile-review.md", json_path=review_path)
    review_hash = _sha256_file(review_path)
    promotion = create_profile_promotion_record(
        tmp_path,
        decision="verified",
        reviewer="project-owner",
        profile_review_hash=review_hash,
        profile_review_path=review_path,
        reviewed_at="2026-05-19T09:00:00Z",
    )
    write_profile_promotion_record(promotion, tmp_path / "state" / "profile-promotions")

    review = create_admin_profile_pack_review_record(
        tmp_path,
        profile_id=PROFILE_ID,
        decision="accepted",
        reviewer="Admin Reviewer",
        profile_pack_hash=_sha256_file(PACK_PATH),
        reviewed_at="2026-05-19T10:00:00Z",
    )
    write_admin_profile_pack_review_record(review, tmp_path / "state" / "admin-profile-pack-reviews")
    return promotion, review


def test_reviewed_seed_requires_passing_gate(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0057", "Reviewed Seed Project", profile_id=PROFILE_ID)

    with pytest.raises(ValueError, match="not reviewed-seed eligible"):
        initialize_admin_obligations(tmp_path, profile_id=PROFILE_ID, reviewed_seed=True)

    assert not (tmp_path / "state" / "admin-obligations.json").exists()


def test_reviewed_seed_writes_hash_bound_metadata_and_accepted_risk_rows(tmp_path):
    promotion, review = _make_reviewed_seed_ready_workspace(tmp_path)

    result = initialize_admin_obligations(
        tmp_path,
        profile_id=PROFILE_ID,
        reviewed_seed=True,
        output_path=tmp_path / "reports" / "admin-obligations.md",
        json_path=tmp_path / "state" / "admin-obligations-review.json",
    )
    payload = json.loads((tmp_path / "state" / "admin-obligations.json").read_text(encoding="utf-8"))

    assert payload["seed_mode"] == "reviewed_seed"
    assert payload["status"] == "reviewed_seed_candidate"
    assert payload["reviewed_seed_gate_status"] == "ready_with_notes"
    assert payload["reviewed_seed_profile_promotion_id"] == promotion.promotion_id
    assert payload["reviewed_seed_review_ids"] == [review.review_id]
    assert payload["source_pack_hash"] == _sha256_file(PACK_PATH)
    assert all(item["status"] == "accepted_risk" for item in payload["obligations"])
    assert all("official_source_needs_review" not in item["risk_flags"] for item in payload["obligations"])
    assert all("reviewed_seed_candidate" in item["risk_flags"] for item in payload["obligations"])
    assert result.seed_mode == "reviewed_seed"
    assert result.reviewed_seed_profile_promotion_id == promotion.promotion_id
    assert result.reviewed_seed_review_ids == [review.review_id]
    assert "admin_obligation_needs_review" not in {finding.code for finding in result.findings}
    assert (tmp_path / "state" / "admin-profile-pack-gate.json").exists()


def test_reviewed_seed_does_not_overwrite_existing_admin_obligations(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0057", "Reviewed Seed Project", profile_id=PROFILE_ID)
    initialize_admin_obligations(tmp_path, profile_id=PROFILE_ID)
    original = (tmp_path / "state" / "admin-obligations.json").read_text(encoding="utf-8")

    result = initialize_admin_obligations(tmp_path, profile_id=PROFILE_ID, reviewed_seed=True)

    assert (tmp_path / "state" / "admin-obligations.json").read_text(encoding="utf-8") == original
    assert result.seed_mode is None
    assert {item.status for item in result.obligations} == {"needs_review"}


def test_reviewed_seed_detects_profile_review_hash_drift(tmp_path):
    _make_reviewed_seed_ready_workspace(tmp_path)
    initialize_admin_obligations(tmp_path, profile_id=PROFILE_ID, reviewed_seed=True)
    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["verified_by"] = "different-reviewer"
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    generate_profile_review(tmp_path, json_path=tmp_path / "state" / "profile-review.json")

    result = review_admin_obligations(tmp_path)

    assert "admin_reviewed_seed_profile_review_hash_mismatch" in {finding.code for finding in result.findings}
    assert result.high_count >= 1


def test_reviewed_seed_cli_and_schema_validation(tmp_path):
    _make_reviewed_seed_ready_workspace(tmp_path)

    assert (
        main(
            [
                "admin-obligations-init",
                "--root",
                str(tmp_path),
                "--profile",
                PROFILE_ID,
                "--reviewed-seed",
                "--output",
                str(tmp_path / "reports" / "admin-obligations.md"),
                "--json",
                str(tmp_path / "state" / "admin-obligations-review.json"),
            ]
        )
        == 0
    )
    assert main(["validate-json", "admin-obligations", str(tmp_path / "state" / "admin-obligations-review.json")]) == 0


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
