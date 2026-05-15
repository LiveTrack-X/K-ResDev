from __future__ import annotations

import zipfile
from pathlib import Path

from k_resdev_skill import extract_document_text, extract_evidence_items_from_document
from k_resdev_skill.models import ExtractedDocument, ExtractedSegment


def test_extract_docx_text_with_paragraph_provenance(tmp_path):
    path = tmp_path / "plan.docx"
    _write_minimal_docx(path, ["과제명: AI 진단", "KPI: Validation Dice 목표: 0.85"])

    document = extract_document_text(path)

    assert document.file_type == "docx"
    assert "Validation Dice" in document.text
    assert document.segments[1].line_range == "P2"


def test_extract_hwpx_text_from_section_xml(tmp_path):
    path = tmp_path / "plan.hwpx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "Contents/section0.xml",
            '<root xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
            "<hp:t>마일스톤: Prototype freeze 2026-06-30</hp:t>"
            "</root>",
        )

    document = extract_document_text(path)

    assert document.file_type == "hwpx"
    assert "Prototype freeze" in document.text
    assert document.segments[0].line_range == "Contents/section0.xml"


def test_extract_xlsx_text_with_sheet_and_row_provenance(tmp_path):
    path = tmp_path / "metrics.xlsx"
    _write_minimal_xlsx(path, [["case_id", "dice"], ["A", "0.81"]])

    document = extract_document_text(path)

    assert document.file_type == "xlsx"
    assert "dice=0.81" in document.text
    assert document.segments[0].sheet == "sheet1"
    assert document.segments[0].cell_range == "row:2"


def test_extract_hwp_requires_optional_rhwp_cli(tmp_path, monkeypatch):
    path = tmp_path / "plan.hwp"
    path.write_bytes(b"fake-hwp")
    monkeypatch.setenv("PATH", "")

    document = extract_document_text(path)

    assert document.file_type == "hwp"
    assert "rhwp_cli_not_found" in document.warnings


def test_extract_evidence_items_from_document_sets_provenance():
    document = ExtractedDocument(
        source_file="plan.txt",
        file_type="txt",
        text="KPI: Validation Dice 목표: 0.85",
        segments=[ExtractedSegment(text="KPI: Validation Dice 목표: 0.85", line_range="L1", quote="KPI: Validation Dice 목표: 0.85")],
    )

    items = extract_evidence_items_from_document(document, "sha256:abc", "ABCDEF12", project="demo")

    assert any(item.evidence_type == "kpi" for item in items)
    assert items[0].provenance.line_range == "L1"
    assert items[0].provenance.quote.startswith("KPI:")


def _write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


def _write_minimal_xlsx(path: Path, rows: list[list[str]]) -> None:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{_col_name(col_index)}{row_index}"
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        "</worksheet>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _col_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name
