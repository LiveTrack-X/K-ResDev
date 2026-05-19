import json
import shutil

from k_resdev_skill.cli import main
from k_resdev_skill.profile_pack_package_receipt import (
    create_profile_pack_package_receipt_record,
    summarize_profile_pack_package_receipts,
    write_profile_pack_package_receipt_record,
)


def test_profile_pack_package_receipt_records_hash_bound_review(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    package = state / "profile-pack-investigation-package.json"
    shutil.copyfile("templates/profile-pack-investigation-package.json", package)
    package_hash = _sha256(package)

    before = summarize_profile_pack_package_receipts(tmp_path)
    assert before.status == "needs_review"
    assert before.unresolved_count == 1
    assert {finding.code for finding in before.findings} == {"profile_pack_package_receipt_missing"}

    record = create_profile_pack_package_receipt_record(
        tmp_path,
        decision="accepted_for_review",
        reviewer="Admin Reviewer",
        package_hash=package_hash,
        reviewed_at="2026-05-19T00:00:00Z",
    )
    write_profile_pack_package_receipt_record(record, tmp_path / "state" / "profile-pack-package-receipts")

    after = summarize_profile_pack_package_receipts(tmp_path)
    assert after.status == "ready"
    assert after.record_count == 1
    assert after.accepted_for_review_count == 1
    assert after.unresolved_count == 0


def test_profile_pack_package_receipt_detects_stale_hash(tmp_path):
    state = tmp_path / "state"
    receipts = state / "profile-pack-package-receipts"
    receipts.mkdir(parents=True)
    package = state / "profile-pack-investigation-package.json"
    shutil.copyfile("templates/profile-pack-investigation-package.json", package)
    package_hash = _sha256(package)

    record = create_profile_pack_package_receipt_record(
        tmp_path,
        decision="received",
        reviewer="Admin Reviewer",
        package_hash=package_hash,
        reviewed_at="2026-05-19T00:00:00Z",
    )
    write_profile_pack_package_receipt_record(record, receipts)

    payload = json.loads(package.read_text(encoding="utf-8"))
    payload["warnings"] = ["changed_after_receipt"]
    package.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = summarize_profile_pack_package_receipts(tmp_path)
    assert result.status == "blocked"
    assert result.stale_record_count == 1
    assert "profile_pack_package_receipt_stale_hash" in {finding.code for finding in result.findings}


def test_profile_pack_package_receipt_cli_smoke(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    package = state / "profile-pack-investigation-package.json"
    shutil.copyfile("templates/profile-pack-investigation-package.json", package)
    package_hash = _sha256(package)

    assert main(
        [
            "profile-pack-package-receipt-record",
            "--root",
            str(tmp_path),
            "--decision",
            "received",
            "--reviewer",
            "Admin Reviewer",
            "--package-hash",
            package_hash,
        ]
    ) == 0
    assert main(
        [
            "profile-pack-package-receipt-summary",
            "--root",
            str(tmp_path),
            "--output",
            str(tmp_path / "reports" / "profile-pack-package-receipt-summary.md"),
            "--json",
            str(tmp_path / "state" / "profile-pack-package-receipt-summary.json"),
        ]
    ) == 0
    assert main(["validate-json", "profile-pack-package-receipt-summary", str(tmp_path / "state" / "profile-pack-package-receipt-summary.json")]) == 0


def _sha256(path):
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
