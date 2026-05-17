import json
from datetime import date

from k_resdev_skill.bibliography import import_bibliography
from k_resdev_skill.bibliography_integrity import (
    extract_markdown_citation_keys,
    generate_workspace_bibliography_integrity,
    render_bibliography_integrity_markdown,
)
from k_resdev_skill.cli import main
from k_resdev_skill.workspace import initialize_workspace


def test_extract_markdown_citation_keys_supports_bracket_and_standalone_forms():
    keys = extract_markdown_citation_keys("Prior work [@kim2026; @lee-2025] and @park:2024 apply. Contact a@b.test.")

    assert keys == {"kim2026", "lee-2025", "park:2024"}


def test_bibliography_integrity_detects_missing_and_unreviewed_citations(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    bib = tmp_path / "references" / "library.bib"
    bib.write_text(
        """@article{kim2026,
  title = {Evidence-First R&D Reporting},
  author = {Kim, Mina},
  year = {2026}
}
""",
        encoding="utf-8",
    )
    import_bibliography(bib, tmp_path / "state", run_date=date(2026, 5, 17))
    (tmp_path / "reports" / "manuscript.md").write_text("See [@kim2026; @missing2024].\n", encoding="utf-8")

    result = generate_workspace_bibliography_integrity(tmp_path)
    rendered = render_bibliography_integrity_markdown(result)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert result.entry_count == 1
    assert result.citation_count == 2
    assert "missing_bibliography_citation" in codes
    assert "unreviewed_bibliography_citation" in codes
    assert "Bibliography integrity projection only" in rendered


def test_bibliography_integrity_detects_source_hash_mismatch(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    bib = tmp_path / "references" / "library.bib"
    bib.write_text(
        """@article{kim2026,
  title = {Evidence-First R&D Reporting},
  author = {Kim, Mina},
  year = {2026}
}
""",
        encoding="utf-8",
    )
    import_bibliography(bib, tmp_path / "state", run_date=date(2026, 5, 17))
    bib.write_text(
        """@article{kim2026,
  title = {Changed Citation Metadata},
  author = {Kim, Mina},
  year = {2026}
}
""",
        encoding="utf-8",
    )

    result = generate_workspace_bibliography_integrity(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "bibliography_source_hash_mismatch" in codes


def test_bibliography_integrity_detects_duplicate_citation_key(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    bib = tmp_path / "references" / "library.bib"
    bib.write_text(
        """@article{kim2026,
  title = {Evidence-First R&D Reporting},
  author = {Kim, Mina},
  year = {2026}
}
@article{kim2026,
  title = {Duplicate Citation Key},
  author = {Lee, Joon},
  year = {2025}
}
""",
        encoding="utf-8",
    )
    import_bibliography(bib, tmp_path / "state", run_date=date(2026, 5, 17))

    result = generate_workspace_bibliography_integrity(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "needs_review"
    assert "duplicate_citation_key" in codes


def test_bib_integrity_cli_writes_outputs(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    (tmp_path / "reports" / "manuscript.md").write_text("See [@missing2024].\n", encoding="utf-8")
    output = tmp_path / "reports" / "bibliography-integrity.md"
    json_output = tmp_path / "state" / "bibliography-integrity.json"

    assert main(["bib-integrity", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "blocked"
    assert payload["high_count"] == 1
    assert output.exists()
    assert json_output.exists()
