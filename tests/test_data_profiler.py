from __future__ import annotations

import zipfile
from pathlib import Path

from k_resdev_skill import profile_data_file


def test_csv_data_profiler_detects_metrics_and_missingness(tmp_path):
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text(
        "case_id,dice,accuracy,note\n"
        "A,0.81,0.90,ok\n"
        "B,,0.87,needs review\n"
        "C,0.86,0.91,\n",
        encoding="utf-8",
    )

    profile = profile_data_file(csv_path)

    assert profile.row_count == 3
    assert profile.column_count == 4
    assert profile.missingness["dice"].missing_count == 1
    assert profile.numeric_summary["accuracy"].mean == 0.893333
    assert "dice" in profile.possible_metrics
    assert "accuracy" in profile.possible_metrics


def test_xlsx_data_profiler_uses_first_worksheet(tmp_path):
    xlsx_path = tmp_path / "metrics.xlsx"
    _write_minimal_xlsx(
        xlsx_path,
        [
            ["case_id", "auc", "loss"],
            ["A", "0.91", "0.12"],
            ["B", "0.88", ""],
        ],
    )

    profile = profile_data_file(xlsx_path)

    assert profile.row_count == 2
    assert profile.missingness["loss"].missing_count == 1
    assert profile.numeric_summary["auc"].max == 0.91
    assert "auc" in profile.possible_metrics
    assert "loss" in profile.possible_metrics


def _write_minimal_xlsx(path: Path, rows: list[list[str]]) -> None:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{_col_name(col_index)}{row_index}"
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'
                if value
                else f'<c r="{ref}"><v></v></c>'
            )
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
