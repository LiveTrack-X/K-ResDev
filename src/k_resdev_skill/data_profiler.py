from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .models import DataProfile, Missingness, NumericSummary

MISSING_VALUES = {"", "-", "na", "n/a", "none", "null", "nan"}
METRIC_HINTS = {
    "dice": ("dice", "dsc"),
    "iou": ("iou", "jaccard"),
    "auc": ("auc", "auroc"),
    "accuracy": ("accuracy", "acc"),
    "f1": ("f1", "f1_score"),
    "recall": ("recall", "sensitivity"),
    "precision": ("precision", "ppv"),
    "loss": ("loss", "error"),
    "latency": ("latency", "runtime", "inference_time"),
}


def profile_data_file(path: str | Path) -> DataProfile:
    """Profile CSV/XLSX tabular data without modifying the source file."""

    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        rows = _read_csv(source)
    elif suffix == ".xlsx":
        rows = _read_xlsx(source)
    else:
        raise ValueError(f"Unsupported data profile format: {suffix}")

    columns = list(rows[0].keys()) if rows else []
    row_count = len(rows)
    missingness: dict[str, Missingness] = {}
    numeric_summary: dict[str, NumericSummary] = {}

    for column in columns:
        values = [row.get(column) for row in rows]
        missing_count = sum(1 for value in values if _is_missing(value))
        missingness[column] = Missingness(
            missing_count=missing_count,
            missing_ratio=round(missing_count / row_count, 6) if row_count else 0.0,
        )

        numbers = [_to_float(value) for value in values if not _is_missing(value)]
        numbers = [number for number in numbers if number is not None]
        if numbers:
            numeric_summary[column] = NumericSummary(
                count=len(numbers),
                min=min(numbers),
                max=max(numbers),
                mean=round(sum(numbers) / len(numbers), 6),
            )

    return DataProfile(
        source_file=str(source),
        file_type=suffix.lstrip("."),
        row_count=row_count,
        column_count=len(columns),
        columns=columns,
        missingness=missingness,
        numeric_summary=numeric_summary,
        possible_metrics=_detect_metrics(columns),
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    return _rows_to_dicts(rows)


def _read_xlsx(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        sheet_names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        )
        if not sheet_names:
            return []
        shared_strings = _read_shared_strings(archive)
        xml_bytes = archive.read(sheet_names[0])

    root = ElementTree.fromstring(xml_bytes)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    table_rows: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        values: list[str] = []
        for cell in row.findall("x:c", namespace):
            ref = cell.attrib.get("r", "")
            index = _column_index(ref)
            while len(values) < index:
                values.append("")
            values.append(_cell_text(cell, shared_strings, namespace))
        table_rows.append(values)
    return _rows_to_dicts(table_rows)


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall(".//x:si", namespace):
        text = "".join(node.text or "" for node in item.findall(".//x:t", namespace))
        strings.append(text)
    return strings


def _cell_text(cell: ElementTree.Element, shared_strings: list[str], namespace: dict[str, str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//x:t", namespace))
    value = cell.find("x:v", namespace)
    raw = value.text if value is not None else ""
    if cell_type == "s" and raw:
        index = int(raw)
        return shared_strings[index] if 0 <= index < len(shared_strings) else ""
    return raw or ""


def _rows_to_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = _normalize_headers(rows[0])
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        if not any(str(value).strip() for value in row):
            continue
        padded = list(row) + [""] * max(0, len(headers) - len(row))
        records.append({header: str(padded[index]).strip() for index, header in enumerate(headers)})
    return records


def _normalize_headers(headers: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: dict[str, int] = {}
    for index, header in enumerate(headers, start=1):
        name = str(header).strip() or f"column_{index}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        normalized.append(name)
    return normalized


def _column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref.upper())
    if not match:
        return 1
    total = 0
    for char in match.group(1):
        total = total * 26 + (ord(char) - ord("A") + 1)
    return total


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_VALUES


def _to_float(value: object) -> float | None:
    text = str(value).strip().replace(",", "")
    if text.endswith("%"):
        text = text[:-1]
    try:
        return float(text)
    except ValueError:
        return None


def _detect_metrics(columns: list[str]) -> list[str]:
    found: list[str] = []
    lower_columns = [column.lower() for column in columns]
    for metric, hints in METRIC_HINTS.items():
        if any(any(hint in column for hint in hints) for column in lower_columns):
            found.append(metric)
    return found
