from __future__ import annotations

import hashlib
import html
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from .io_utils import read_text_file
from .models import ProjectionExportResult

DRAFT_NOTICE = (
    "Draft projection only. Human approval is required before official submission, "
    "settlement, audit response, or scientific claim use."
)


def export_projection(
    markdown_path: str | Path,
    output_path: str | Path,
    output_format: str | None = None,
    title: str | None = None,
) -> ProjectionExportResult:
    """Export a Markdown projection to a review document without changing the source."""

    source = Path(markdown_path)
    target = Path(output_path)
    text = read_text_file(source)
    fmt = (output_format or target.suffix.lstrip(".") or "html").lower()
    if fmt == "hwpx":
        fmt = "hwpx-html"
    target.parent.mkdir(parents=True, exist_ok=True)
    document_title = title or _first_heading(text) or source.stem

    if fmt == "docx":
        write_projection_docx(text, target, document_title)
    elif fmt in {"html", "hwpx-html"}:
        write_projection_html(text, target, document_title)
    elif fmt == "txt":
        write_projection_text(text, target, document_title)
    else:
        raise ValueError(f"Unsupported export format: {output_format or fmt}")

    return ProjectionExportResult(
        export_id=_export_id(source, target, fmt),
        source_path=str(source),
        source_hash=_sha256(source),
        output_path=str(target),
        output_format=fmt,
        warnings=_export_warnings(fmt),
    )


def write_projection_html(markdown_text: str, output_path: str | Path, title: str | None = None) -> str:
    rendered_body = "\n".join(_markdown_to_html_blocks(markdown_text))
    document_title = title or _first_heading(markdown_text) or "K-ResDev Projection"
    rendered = "\n".join(
        [
            "<!doctype html>",
            '<html lang="ko">',
            "<head>",
            '  <meta charset="utf-8">',
            f"  <title>{html.escape(document_title)}</title>",
            "  <style>",
            "    body { font-family: Arial, 'Malgun Gothic', sans-serif; line-height: 1.55; }",
            "    table { border-collapse: collapse; width: 100%; margin: 1em 0; }",
            "    th, td { border: 1px solid #999; padding: 6px 8px; vertical-align: top; }",
            "    blockquote { border-left: 4px solid #777; margin-left: 0; padding-left: 12px; color: #333; }",
            "    .kresdev-notice { border: 1px solid #777; padding: 10px; margin-bottom: 16px; font-weight: bold; }",
            "  </style>",
            "</head>",
            "<body>",
            f'  <div class="kresdev-notice">{html.escape(DRAFT_NOTICE)}</div>',
            rendered_body,
            "</body>",
            "</html>",
            "",
        ]
    )
    Path(output_path).write_text(rendered, encoding="utf-8")
    return rendered


def write_projection_text(markdown_text: str, output_path: str | Path, title: str | None = None) -> str:
    document_title = title or _first_heading(markdown_text) or "K-ResDev Projection"
    rendered = f"{document_title}\n\n{DRAFT_NOTICE}\n\n{markdown_text.rstrip()}\n"
    Path(output_path).write_text(rendered, encoding="utf-8")
    return rendered


def write_projection_docx(markdown_text: str, output_path: str | Path, title: str | None = None) -> None:
    document_xml = _document_xml(markdown_text, title)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _rels_xml())
        archive.writestr("word/_rels/document.xml.rels", _document_rels_xml())
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", _styles_xml())


def _markdown_to_html_blocks(markdown_text: str) -> list[str]:
    blocks: list[str] = []
    table_buffer: list[str] = []
    list_open = False
    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if _is_table_line(line):
            table_buffer.append(line)
            continue
        if table_buffer:
            blocks.extend(_render_html_table(table_buffer))
            table_buffer = []
        if list_open and not line.startswith("- "):
            blocks.append("</ul>")
            list_open = False
        if not line.strip():
            continue
        if line.startswith("#"):
            level = min(len(line) - len(line.lstrip("#")), 6)
            text = line[level:].strip()
            blocks.append(f"<h{level}>{_inline_html(text)}</h{level}>")
        elif line.startswith(">"):
            blocks.append(f"<blockquote>{_inline_html(line.lstrip('>').strip())}</blockquote>")
        elif line.startswith("- "):
            if not list_open:
                blocks.append("<ul>")
                list_open = True
            blocks.append(f"  <li>{_inline_html(line[2:].strip())}</li>")
        else:
            blocks.append(f"<p>{_inline_html(line)}</p>")
    if table_buffer:
        blocks.extend(_render_html_table(table_buffer))
    if list_open:
        blocks.append("</ul>")
    return blocks


def _document_xml(markdown_text: str, title: str | None = None) -> str:
    paragraphs = [_paragraph_xml(DRAFT_NOTICE, style="Notice")]
    table_buffer: list[str] = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if _is_table_line(line):
            table_buffer.append(line)
            continue
        if table_buffer:
            paragraphs.append(_table_xml(table_buffer))
            table_buffer = []
        if not line.strip():
            continue
        if line.startswith("#"):
            level = min(len(line) - len(line.lstrip("#")), 3)
            paragraphs.append(_paragraph_xml(line[level:].strip(), style=f"Heading{level}"))
        elif line.startswith(">"):
            paragraphs.append(_paragraph_xml(line.lstrip(">").strip(), style="Quote"))
        elif line.startswith("- "):
            paragraphs.append(_paragraph_xml("• " + line[2:].strip()))
        else:
            paragraphs.append(_paragraph_xml(line))
    if table_buffer:
        paragraphs.append(_table_xml(table_buffer))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(paragraphs)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
        + "</w:body></w:document>"
    )


def _paragraph_xml(text: str, style: str | None = None) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}<w:r><w:t xml:space=\"preserve\">{xml_escape(_strip_inline_markdown(text))}</w:t></w:r></w:p>"


def _table_xml(lines: list[str]) -> str:
    rows = _parse_table_rows(lines)
    if not rows:
        return ""
    xml_rows = []
    for row in rows:
        cells = "".join(f"<w:tc><w:p><w:r><w:t>{xml_escape(_strip_inline_markdown(cell))}</w:t></w:r></w:p></w:tc>" for cell in row)
        xml_rows.append(f"<w:tr>{cells}</w:tr>")
    return "<w:tbl><w:tblPr><w:tblBorders><w:top w:val=\"single\"/><w:left w:val=\"single\"/><w:bottom w:val=\"single\"/><w:right w:val=\"single\"/><w:insideH w:val=\"single\"/><w:insideV w:val=\"single\"/></w:tblBorders></w:tblPr>" + "".join(xml_rows) + "</w:tbl>"


def _render_html_table(lines: list[str]) -> list[str]:
    rows = _parse_table_rows(lines)
    if not rows:
        return []
    output = ["<table>"]
    for index, row in enumerate(rows):
        tag = "th" if index == 0 else "td"
        output.append("  <tr>" + "".join(f"<{tag}>{_inline_html(cell)}</{tag}>" for cell in row) + "</tr>")
    output.append("</table>")
    return output


def _parse_table_rows(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _is_table_line(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().endswith("|") and line.count("|") >= 2


def _inline_html(text: str) -> str:
    escaped = html.escape(_strip_inline_markdown(text))
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def _strip_inline_markdown(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def _first_heading(markdown_text: str) -> str | None:
    for line in markdown_text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip() or None
    return None


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _export_id(source: Path, target: Path, fmt: str) -> str:
    digest = hashlib.sha256(f"{source}|{target}|{fmt}|{_sha256(source)}".encode("utf-8")).hexdigest()
    return f"EXP-{datetime.now(UTC).strftime('%Y')}-{digest[:8].upper()}"


def _export_warnings(fmt: str) -> list[str]:
    warnings = ["draft_projection", "human_approval_required"]
    if fmt == "hwpx-html":
        warnings.append("hwpx_compatible_html_intermediate_not_official_hwpx")
    return warnings


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        "</Types>"
    )


def _rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )


def _document_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="2"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Notice"><w:name w:val="Notice"/><w:basedOn w:val="Normal"/></w:style>'
        "</w:styles>"
    )
