import json

from k_resdev_skill.bibliography_review import (
    bibliography_review_status,
    create_bibliography_review_record,
    generate_bibliography_review_summary,
    load_bibliography_review_records,
    write_bibliography_review_record,
)
from k_resdev_skill.cli import main


def test_bibliography_review_record_round_trip_and_status(tmp_path):
    record = create_bibliography_review_record(
        bibliography_id="BIB-2026-ABCD1234",
        decision="accepted",
        reviewer="Dr. Kim",
        citation_key="kim2026",
        paper_id="PAPER-2026-ABCD1234",
        reviewed_at="2026-05-17T09:00:00Z",
    )
    path = write_bibliography_review_record(record, tmp_path / "bibliography-reviews")

    loaded = load_bibliography_review_records(path)
    status = bibliography_review_status(loaded, "BIB-2026-ABCD1234")
    summary = generate_bibliography_review_summary(loaded, tmp_path / "bibliography-review-summary.md")

    assert record.review_id.startswith("BIBREV-2026-")
    assert status["accepted"] is True
    assert status["decision"] == "accepted"
    assert "kim2026" in summary
    assert "Human bibliography metadata review log only" in (tmp_path / "bibliography-review-summary.md").read_text(encoding="utf-8")


def test_bibliography_review_cli_records_summary_and_status(tmp_path, capsys):
    reviews_dir = tmp_path / "bibliography-reviews"

    assert (
        main(
            [
                "bib-review-record",
                "--bibliography-id",
                "BIB-2026-ABCD1234",
                "--decision",
                "accepted",
                "--reviewer",
                "Reviewer",
                "--citation-key",
                "kim2026",
                "--paper-id",
                "PAPER-2026-ABCD1234",
                "--reviewed-at",
                "2026-05-17T09:00:00Z",
                "--reviews-dir",
                str(reviews_dir),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["review_id"].startswith("BIBREV-2026-")
    assert payload["decision"] == "accepted"
    assert len(list(reviews_dir.glob("*.json"))) == 1

    summary_path = tmp_path / "summary.md"
    assert main(["bib-review-summary", str(reviews_dir), "--output", str(summary_path)]) == 0
    assert "BIB-2026-ABCD1234" in summary_path.read_text(encoding="utf-8")
    capsys.readouterr()

    assert main(["bib-review-status", str(reviews_dir), "--bibliography-id", "BIB-2026-ABCD1234"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["accepted"] is True
    assert status["citation_key"] == "kim2026"


def test_missing_bibliography_review_status_is_explicit():
    status = bibliography_review_status([], "BIB-2026-MISSING")

    assert status["accepted"] is False
    assert status["decision"] == "missing"
