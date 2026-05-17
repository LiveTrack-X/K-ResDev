import json
from datetime import date

from k_resdev_skill.bibliography import (
    import_bibliography,
    load_bibliography_index,
    paper_records_from_bibliography,
    parse_bibliography_file,
    render_bibliography_index,
)


def test_parse_bibtex_without_inventing_missing_metadata(tmp_path):
    bib = tmp_path / "library.bib"
    bib.write_text(
        """@article{kim2026,
  title = {Evidence-First R&D Reporting},
  author = {Kim, Mina and Lee, Joon},
  year = {2026},
  journal = {Journal of Research Operations},
  doi = {https://doi.org/10.1234/example}
}

@inproceedings{missing2025,
  author = {Park, Hana},
  year = {2025}
}
""",
        encoding="utf-8",
    )

    entries = parse_bibliography_file(bib, run_date=date(2026, 5, 17))

    assert len(entries) == 2
    assert entries[0].citation_key == "kim2026"
    assert entries[0].doi == "10.1234/example"
    assert entries[0].authors == ["Kim, Mina", "Lee, Joon"]
    assert entries[0].status == "needs_review"
    assert entries[1].title == "title_needs_review"
    assert "missing_title" in entries[1].risk_flags
    assert "missing_identifier" in entries[1].risk_flags


def test_parse_ris_and_csl_json(tmp_path):
    ris = tmp_path / "library.ris"
    ris.write_text(
        """TY  - JOUR
TI  - Reproducible Evidence Operations
AU  - Choi, Ara
PY  - 2024
JO  - R&D Methods
DO  - 10.5555/ris
KW  - reproducibility
ER  -
""",
        encoding="utf-8",
    )
    csl = tmp_path / "library.json"
    csl.write_text(
        json.dumps(
            [
                {
                    "id": "csl-1",
                    "type": "article-journal",
                    "title": "KPI Evidence Graphs",
                    "author": [{"family": "Jung", "given": "Sol"}],
                    "issued": {"date-parts": [[2023, 1, 1]]},
                    "container-title": "Evidence Systems",
                    "URL": "https://example.test/paper",
                }
            ]
        ),
        encoding="utf-8",
    )

    ris_entries = parse_bibliography_file(ris, run_date=date(2026, 5, 17))
    csl_entries = parse_bibliography_file(csl, run_date=date(2026, 5, 17))

    assert ris_entries[0].title == "Reproducible Evidence Operations"
    assert ris_entries[0].keywords == ["reproducibility"]
    assert csl_entries[0].citation_key == "csl-1"
    assert csl_entries[0].authors == ["Jung, Sol"]
    assert csl_entries[0].year == 2023


def test_import_bibliography_writes_index_and_literature_matrix(tmp_path):
    bib = tmp_path / "library.bib"
    bib.write_text(
        """@article{kim2026,
  title = {Evidence-First R&D Reporting},
  author = {Kim, Mina and Lee, Joon},
  year = {2026},
  journal = {Journal of Research Operations}
}
""",
        encoding="utf-8",
    )
    state = tmp_path / "state"
    matrix = tmp_path / "reports" / "literature-review-matrix.md"

    result = import_bibliography(bib, state, matrix, run_date=date(2026, 5, 17))

    assert result.entry_count == 1
    assert result.source_format == "bibtex"
    assert (state / "bibliography-index.json").exists()
    assert (state / "bibliography-index.md").exists()
    assert matrix.exists()
    payload = json.loads((state / "bibliography-index.json").read_text(encoding="utf-8"))
    assert payload["items"][0]["paper_id"].startswith("PAPER-2026-")
    assert "Kim, Mina, Lee, Joon (2026)." in matrix.read_text(encoding="utf-8")


def test_bibliography_index_round_trip_to_paper_records(tmp_path):
    bib = tmp_path / "library.bib"
    bib.write_text(
        """@article{kim2026,
  title = {Evidence-First R&D Reporting},
  author = {Kim, Mina},
  year = {2026}
}
""",
        encoding="utf-8",
    )
    result = import_bibliography(bib, tmp_path / "state", run_date=date(2026, 5, 17))

    entries = load_bibliography_index(result.bibliography_index_json_path)
    records = paper_records_from_bibliography(entries)
    rendered = render_bibliography_index(entries)

    assert records[0].paper_id == entries[0].paper_id
    assert records[0].key_claims == []
    assert "claims, methods, datasets, and metrics need review" in (records[0].notes or "")
    assert "Bibliography projection only" in rendered
