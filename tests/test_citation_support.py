import json

from k_resdev_skill.bibliography import import_bibliography, load_bibliography_index
from k_resdev_skill.citation_support import (
    citation_support_status,
    create_citation_support_record,
    generate_citation_support_summary,
    generate_workspace_citation_support_integrity,
    load_citation_support_records,
    write_citation_support_record,
)
from k_resdev_skill.cli import main
from k_resdev_skill.workspace import initialize_workspace


def test_citation_support_record_round_trip_summary_and_status(tmp_path):
    record = create_citation_support_record(
        bibliography_id="BIB-2026-ABCD1234",
        claim="Model A underperforms on small-lesion cases.",
        decision="supports",
        reviewer="Reviewer",
        citation_key="kim2026",
        locator="p. 4",
        quote="Small-lesion subgroup performance is lower.",
        evidence_ids=["EVI-2026-0001"],
        reviewed_at="2026-05-17T09:00:00Z",
    )

    path = write_citation_support_record(record, tmp_path / "state" / "citation-support")
    records = load_citation_support_records(path)
    rendered = generate_citation_support_summary(records, tmp_path / "reports" / "citation-support-summary.md")
    status = citation_support_status(records, "BIB-2026-ABCD1234", "Model A underperforms on small-lesion cases.")

    assert records[0].support_id.startswith("CITSUP-2026-")
    assert "Human paper-claim support log only" in rendered
    assert status["supported"] is True
    assert status["decision"] == "supports"
    assert (tmp_path / "reports" / "citation-support-summary.md").exists()


def test_citation_support_integrity_flags_missing_support_for_citation(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    entry = _write_sample_bibliography(tmp_path)
    (tmp_path / "reports" / "manuscript.md").write_text("See [@kim2026].\n", encoding="utf-8")

    result = generate_workspace_citation_support_integrity(
        tmp_path,
        output_path=tmp_path / "reports" / "citation-support.md",
        json_path=tmp_path / "state" / "citation-support.json",
    )

    assert result.status == "needs_review"
    assert result.citation_count == 1
    assert result.findings[0].code == "citation_support_missing"
    assert result.findings[0].bibliography_id == entry.bibliography_id
    assert json.loads((tmp_path / "state" / "citation-support.json").read_text(encoding="utf-8"))["status"] == "needs_review"


def test_citation_support_integrity_accepts_reviewed_support_with_provenance(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    entry = _write_sample_bibliography(tmp_path)
    (tmp_path / "reports" / "manuscript.md").write_text("See [@kim2026].\n", encoding="utf-8")
    record = create_citation_support_record(
        bibliography_id=entry.bibliography_id,
        claim="Model A underperforms on small-lesion cases.",
        decision="supports",
        reviewer="Reviewer",
        citation_key="kim2026",
        paper_id=entry.paper_id,
        locator="Results, p. 4",
        quote="Small-lesion subgroup performance is lower.",
        evidence_ids=["EVI-2026-0001"],
        reviewed_at="2026-05-17T09:00:00Z",
    )
    write_citation_support_record(record, tmp_path / "state" / "citation-support")

    result = generate_workspace_citation_support_integrity(tmp_path)

    assert result.status == "ready"
    assert result.support_count == 1
    assert result.finding_count == 0


def test_citation_support_integrity_blocks_negative_support_decision(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    entry = _write_sample_bibliography(tmp_path)
    (tmp_path / "reports" / "manuscript.md").write_text("See [@kim2026].\n", encoding="utf-8")
    record = create_citation_support_record(
        bibliography_id=entry.bibliography_id,
        claim="Model A underperforms on small-lesion cases.",
        decision="does_not_support",
        reviewer="Reviewer",
        citation_key="kim2026",
        reviewed_at="2026-05-17T09:00:00Z",
    )
    write_citation_support_record(record, tmp_path / "state" / "citation-support")

    result = generate_workspace_citation_support_integrity(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "citation_support_invalid" in codes
    assert result.high_count == 1


def test_citation_support_cli_round_trip(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    entry = _write_sample_bibliography(tmp_path)
    (tmp_path / "reports" / "manuscript.md").write_text("See [@kim2026].\n", encoding="utf-8")

    assert (
        main(
            [
                "citation-support-integrity",
                "--root",
                str(tmp_path),
                "--output",
                str(tmp_path / "reports" / "citation-support.md"),
                "--json",
                str(tmp_path / "state" / "citation-support.json"),
            ]
        )
        == 0
    )
    before_payload = json.loads(capsys.readouterr().out)
    assert before_payload["status"] == "needs_review"

    assert (
        main(
            [
                "citation-support-record",
                "--bibliography-id",
                entry.bibliography_id,
                "--citation-key",
                "kim2026",
                "--paper-id",
                entry.paper_id,
                "--claim",
                "Model A underperforms on small-lesion cases.",
                "--decision",
                "supports",
                "--reviewer",
                "Reviewer",
                "--locator",
                "Results, p. 4",
                "--quote",
                "Small-lesion subgroup performance is lower.",
                "--evidence-id",
                "EVI-2026-0001",
                "--reviewed-at",
                "2026-05-17T09:00:00Z",
                "--support-dir",
                str(tmp_path / "state" / "citation-support"),
            ]
        )
        == 0
    )
    record_payload = json.loads(capsys.readouterr().out)
    assert record_payload["support_id"].startswith("CITSUP-2026-")

    assert main(["citation-support-summary", str(tmp_path / "state" / "citation-support"), "--output", str(tmp_path / "reports" / "citation-support-summary.md")]) == 0
    assert "Citation Support Summary" in capsys.readouterr().out

    assert (
        main(
            [
                "citation-support-status",
                str(tmp_path / "state" / "citation-support"),
                "--bibliography-id",
                entry.bibliography_id,
                "--claim",
                "Model A underperforms on small-lesion cases.",
            ]
        )
        == 0
    )
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["supported"] is True

    assert main(["citation-support-integrity", "--root", str(tmp_path)]) == 0
    after_payload = json.loads(capsys.readouterr().out)
    assert after_payload["status"] == "ready"
    assert after_payload["finding_count"] == 0


def _write_sample_bibliography(tmp_path):
    bib = tmp_path / "references" / "library.bib"
    bib.write_text(
        """@article{kim2026,
  title = {Small Lesion Evidence},
  author = {Kim, Mina},
  year = {2026},
  journal = {Journal of Research Operations}
}
""",
        encoding="utf-8",
    )
    import_bibliography(bib, tmp_path / "state")
    return load_bibliography_index(tmp_path / "state" / "bibliography-index.json")[0]
