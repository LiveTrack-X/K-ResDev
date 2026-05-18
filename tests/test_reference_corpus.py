import json

from k_resdev_skill.cli import main
from k_resdev_skill.reference_corpus import build_reference_corpus, load_reference_corpus, load_reference_rejections
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_reference_corpus_scans_markdown_and_pdf_without_copying_raw_body(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    note = tmp_path / "references" / "kim2026.md"
    note.write_text(
        """---
title: Small Lesion Segmentation
authors: Kim, A.; Lee, B.
year: 2026
venue: Example Journal
doi: 10.1000/example
citation_key: kim2026
note: Short user note.
---

# Raw note body should not be copied into corpus JSON

Sensitive detailed reading notes stay in the source file.
""",
        encoding="utf-8",
    )
    pdf = tmp_path / "references" / "file-only-paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\nRaw PDF bytes should not be copied.\n")
    unsupported = tmp_path / "references" / "archive.zip"
    unsupported.write_bytes(b"zip")

    result = build_reference_corpus(
        tmp_path,
        output_path=tmp_path / "reports" / "reference-corpus-summary.md",
        json_path=tmp_path / "state" / "literature-corpus.json",
        rejection_json_path=tmp_path / "state" / "reference-rejection-log.json",
    )
    corpus_text = (tmp_path / "state" / "literature-corpus.json").read_text(encoding="utf-8")
    rejection_log = load_reference_rejections(tmp_path / "state" / "reference-rejection-log.json")

    assert result.item_count == 2
    assert {item.source_format for item in result.items} == {"md", "pdf"}
    assert any(item.citation_key == "kim2026" for item in result.items)
    assert any("file_only_reference" in item.risk_flags for item in result.items)
    assert "Sensitive detailed reading notes" not in corpus_text
    assert {item.reason for item in rejection_log} == {"unsupported_file_type"}
    assert (tmp_path / "reports" / "reference-corpus-summary.md").exists()


def test_reference_corpus_zotero_json_dedupes_and_omits_copyright_risk_text(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    long_abstract = "UNSAFE_ABSTRACT_TEXT_" + ("x" * 700)
    zotero = [
        {
            "key": "ABC123",
            "itemType": "journalArticle",
            "title": "Model Audit",
            "creators": [{"firstName": "A", "lastName": "Kim"}],
            "date": "2026",
            "publicationTitle": "Example Journal",
            "DOI": "10.1000/dup",
            "url": "https://example.org/a",
            "abstractNote": long_abstract,
            "tags": [{"tag": "segmentation"}],
        },
        {
            "key": "DEF456",
            "itemType": "journalArticle",
            "title": "Model Audit Duplicate",
            "creators": [{"firstName": "A", "lastName": "Kim"}],
            "date": "2026",
            "publicationTitle": "Example Journal",
            "DOI": "10.1000/dup",
        },
    ]
    source = tmp_path / "references" / "zotero.json"
    source.write_text(json.dumps(zotero), encoding="utf-8")

    result = build_reference_corpus(tmp_path, json_path=tmp_path / "state" / "literature-corpus.json", rejection_json_path=tmp_path / "state" / "reference-rejection-log.json")
    corpus_text = (tmp_path / "state" / "literature-corpus.json").read_text(encoding="utf-8")
    reasons = {rejection.reason for rejection in result.rejections}

    assert result.item_count == 1
    assert "duplicate_reference" in reasons
    assert "copyright_risk_text_omitted" in reasons
    assert "UNSAFE_ABSTRACT_TEXT" not in corpus_text


def test_reference_corpus_cli_and_schema_round_trip(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    note = tmp_path / "references" / "paper.md"
    note.write_text("---\ntitle: Paper\ncitation_key: paper2026\nyear: 2026\n---\n", encoding="utf-8")

    assert (
        main(
            [
                "reference-corpus",
                "--root",
                str(tmp_path),
                "--output",
                str(tmp_path / "reports" / "reference-corpus-summary.md"),
                "--json",
                str(tmp_path / "state" / "literature-corpus.json"),
                "--rejections",
                str(tmp_path / "state" / "reference-rejection-log.json"),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["item_count"] == 1
    assert load_reference_corpus(tmp_path / "state" / "literature-corpus.json")[0].citation_key == "paper2026"
    assert main(["validate-json", "reference-corpus", str(tmp_path / "state" / "literature-corpus.json")]) == 0
    assert main(["validate-json", "reference-rejection", str(tmp_path / "state" / "reference-rejection-log.json")]) == 0


def test_reference_corpus_integrates_with_workspace_operations(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    (tmp_path / "references" / "paper.md").write_text("---\ntitle: Paper\ncitation_key: paper2026\nyear: 2026\n---\n", encoding="utf-8")
    (tmp_path / "references" / "unsupported.bin").write_bytes(b"bin")

    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor, action_plan=actions)
    pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    doctor_codes = {finding.code for finding in doctor.findings}
    action_titles = {action.title for action in actions.actions}
    node_types = {node.node_type for node in trace.nodes}

    assert "reference_corpus_review_findings" in doctor_codes
    assert "Review reference corpus import" in action_titles
    assert summary.reference_corpus_count == 1
    assert summary.reference_rejection_count == 1
    assert pack.reference_corpus_count == 1
    assert pack.reference_rejection_count == 1
    assert "reference" in node_types
    assert (tmp_path / "reports" / "reference-corpus-summary.md").exists()
    assert (tmp_path / "state" / "literature-corpus.json").exists()
