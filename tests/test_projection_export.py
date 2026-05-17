import json
import zipfile

from k_resdev_skill.cli import main
from k_resdev_skill.projection_export import export_projection, write_projection_html, write_projection_text


def test_export_projection_docx_writes_review_notice(tmp_path):
    source = tmp_path / "report.md"
    target = tmp_path / "report.docx"
    source.write_text(
        "# Monthly Report\n\n> Draft only\n\n| Evidence | Claim |\n|---|---|\n| EVI-2026-0001 | Result improved. |\n",
        encoding="utf-8",
    )

    result = export_projection(source, target, "docx")

    assert result.output_format == "docx"
    assert result.status == "draft"
    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
        document = archive.read("word/document.xml").decode("utf-8")
    assert "[Content_Types].xml" in names
    assert "Draft projection only" in document
    assert "Monthly Report" in document
    assert "EVI-2026-0001" in document


def test_export_projection_hwpx_html_is_explicit_intermediate(tmp_path):
    source = tmp_path / "report.md"
    target = tmp_path / "report.hwpx.html"
    source.write_text("# 검토 보고서\n\n- 항목\n", encoding="utf-8")

    result = export_projection(source, target, "hwpx-html")
    html = target.read_text(encoding="utf-8")

    assert result.output_format == "hwpx-html"
    assert "hwpx_compatible_html_intermediate_not_official_hwpx" in result.warnings
    assert "<html lang=\"ko\">" in html
    assert "Draft projection only" in html
    assert "검토 보고서" in html


def test_text_and_html_helpers(tmp_path):
    html_path = tmp_path / "out.html"
    text_path = tmp_path / "out.txt"

    write_projection_html("# Title\n\n- item", html_path)
    write_projection_text("# Title\n\nbody", text_path)

    assert "<li>item</li>" in html_path.read_text(encoding="utf-8")
    assert "Draft projection only" in text_path.read_text(encoding="utf-8")


def test_export_projection_cli(tmp_path, capsys):
    source = tmp_path / "report.md"
    target = tmp_path / "report.html"
    source.write_text("# Report\n\nBody", encoding="utf-8")

    assert main(["export-projection", str(source), "--output", str(target), "--format", "html"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["output_path"].endswith("report.html")
    assert target.exists()
