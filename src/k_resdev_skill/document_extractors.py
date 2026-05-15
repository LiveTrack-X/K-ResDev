from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .data_profiler import _read_xlsx
from .io_utils import read_text_file
from .models import ExtractedDocument, ExtractedSegment

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".jsonl", ".log", ".tsv"}


def extract_document_text(path: str | Path, limit: int | None = None) -> ExtractedDocument:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return _extract_plain_text(source, limit)
    if suffix == ".docx":
        return _extract_docx(source, limit)
    if suffix == ".hwpx":
        return _extract_hwpx(source, limit)
    if suffix == ".xlsx":
        return _extract_xlsx(source, limit)
    if suffix == ".pdf":
        return _extract_pdf(source, limit)
    if suffix == ".hwp":
        return _extract_hwp(source, limit)
    return ExtractedDocument(
        source_file=str(source),
        file_type=suffix.lstrip(".") or "unknown",
        text="",
        warnings=[f"unsupported_text_extraction_format:{suffix}"],
    )


def _extract_plain_text(path: Path, limit: int | None) -> ExtractedDocument:
    text = read_text_file(path, limit)
    segments = [
        ExtractedSegment(text=line, line_range=f"L{index}", quote=line[:500])
        for index, line in enumerate(text.splitlines(), start=1)
        if line.strip()
    ]
    return ExtractedDocument(
        source_file=str(path),
        file_type=path.suffix.lower().lstrip("."),
        text=_limit_text(text, limit),
        segments=segments,
    )


def _extract_pdf(path: Path, limit: int | None) -> ExtractedDocument:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ExtractedDocument(source_file=str(path), file_type="pdf", text="", warnings=["pypdf_not_installed"])

    reader = PdfReader(str(path))
    segments: list[ExtractedSegment] = []
    for page_index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            segments.append(ExtractedSegment(text=page_text, page=page_index, quote=page_text.strip()[:500]))
    text = "\n".join(segment.text for segment in segments)
    return ExtractedDocument(source_file=str(path), file_type="pdf", text=_limit_text(text, limit), segments=segments)


def _extract_hwp(path: Path, limit: int | None) -> ExtractedDocument:
    rhwp = shutil.which("rhwp")
    if not rhwp:
        return ExtractedDocument(
            source_file=str(path),
            file_type="hwp",
            text="",
            warnings=["rhwp_cli_not_found"],
        )
    try:
        result = subprocess.run(
            [rhwp, "dump", str(path)],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ExtractedDocument(source_file=str(path), file_type="hwp", text="", warnings=[f"rhwp_dump_failed:{exc}"])
    if result.returncode != 0:
        warning = (result.stderr or "rhwp_dump_failed").strip().splitlines()[0]
        return ExtractedDocument(source_file=str(path), file_type="hwp", text="", warnings=[f"rhwp_dump_failed:{warning}"])
    text = _limit_text(result.stdout, limit)
    segments = [
        ExtractedSegment(text=line, line_range=f"rhwp-dump:L{index}", quote=line[:500])
        for index, line in enumerate(text.splitlines(), start=1)
        if line.strip()
    ]
    return ExtractedDocument(source_file=str(path), file_type="hwp", text=text, segments=segments)


def _extract_docx(path: Path, limit: int | None) -> ExtractedDocument:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        if "word/document.xml" not in archive.namelist():
            return ExtractedDocument(source_file=str(path), file_type="docx", text="", warnings=["missing_word_document_xml"])
        root = ElementTree.fromstring(archive.read("word/document.xml"))

    segments: list[ExtractedSegment] = []
    for index, paragraph in enumerate(root.findall(".//w:p", namespace), start=1):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if text:
            segments.append(ExtractedSegment(text=text, line_range=f"P{index}", quote=text[:500]))
    if not segments:
        warnings.append("no_docx_text_found")
    text = "\n".join(segment.text for segment in segments)
    return ExtractedDocument(source_file=str(path), file_type="docx", text=_limit_text(text, limit), segments=segments, warnings=warnings)


def _extract_hwpx(path: Path, limit: int | None) -> ExtractedDocument:
    warnings: list[str] = []
    segments: list[ExtractedSegment] = []
    with zipfile.ZipFile(path) as archive:
        xml_names = sorted(name for name in archive.namelist() if name.lower().endswith(".xml"))
        section_names = [name for name in xml_names if "section" in name.lower()]
        for xml_name in section_names or xml_names:
            try:
                root = ElementTree.fromstring(archive.read(xml_name))
            except ElementTree.ParseError:
                warnings.append(f"xml_parse_failed:{xml_name}")
                continue
            texts = []
            for node in root.iter():
                if _local_name(node.tag) in {"t", "text"} and node.text:
                    texts.append(node.text)
            joined = " ".join(text.strip() for text in texts if text.strip())
            if joined:
                segments.append(ExtractedSegment(text=joined, line_range=xml_name, quote=joined[:500]))
    if not segments:
        warnings.append("no_hwpx_text_found")
    text = "\n".join(segment.text for segment in segments)
    return ExtractedDocument(source_file=str(path), file_type="hwpx", text=_limit_text(text, limit), segments=segments, warnings=warnings)


def _extract_xlsx(path: Path, limit: int | None) -> ExtractedDocument:
    try:
        rows = _read_xlsx(path)
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        return ExtractedDocument(source_file=str(path), file_type="xlsx", text="", warnings=[f"xlsx_extract_failed:{exc}"])
    if not rows:
        return ExtractedDocument(source_file=str(path), file_type="xlsx", text="", warnings=["no_xlsx_rows_found"])
    columns = list(rows[0].keys())
    segments = []
    for index, row in enumerate(rows, start=2):
        text = ", ".join(f"{column}={row.get(column, '')}" for column in columns)
        segments.append(ExtractedSegment(text=text, sheet="sheet1", cell_range=f"row:{index}", quote=text[:500]))
    text = "\n".join(segment.text for segment in segments)
    return ExtractedDocument(source_file=str(path), file_type="xlsx", text=_limit_text(text, limit), segments=segments)


def _limit_text(text: str, limit: int | None) -> str:
    return text[:limit] if limit is not None else text


def _local_name(tag: str) -> str:
    return re.sub(r"^\{.*\}", "", tag)
