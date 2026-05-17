from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .literature import generate_literature_matrix
from .models import BibliographyEntry, BibliographyImportResult, PaperRecord

SUPPORTED_FORMATS = {
    ".bib": "bibtex",
    ".ris": "ris",
    ".json": "csl-json",
}


def import_bibliography(
    bibliography_file: str | Path,
    state_dir: str | Path = "state",
    literature_matrix_path: str | Path | None = None,
    run_date: date | None = None,
) -> BibliographyImportResult:
    """Parse supplied bibliography metadata and write derived review indexes.

    Raw bibliography files are never modified. Missing or ambiguous citation
    metadata stays in `needs_review` form rather than being invented.
    """

    source = Path(bibliography_file)
    entries = parse_bibliography_file(source, run_date=run_date)
    source_hash = _sha256(source)
    source_format = _detect_format(source)
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)

    json_path = state / "bibliography-index.json"
    markdown_path = state / "bibliography-index.md"
    json_path.write_text(
        json.dumps(
            {
                "generated_by": "k-resdev-skill",
                "source_file": str(source),
                "source_hash": source_hash,
                "source_format": source_format,
                "entry_count": len(entries),
                "items": [entry.model_dump(mode="json") for entry in entries],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_bibliography_index(entries, source, source_format), encoding="utf-8")

    matrix_path: str | None = None
    if literature_matrix_path is not None:
        target = Path(literature_matrix_path)
        generate_literature_matrix(paper_records_from_bibliography(entries), target)
        matrix_path = str(target)

    return BibliographyImportResult(
        source_file=str(source),
        source_hash=source_hash,
        source_format=source_format,
        entry_count=len(entries),
        bibliography_index_markdown_path=str(markdown_path),
        bibliography_index_json_path=str(json_path),
        literature_matrix_path=matrix_path,
        warnings=_import_warnings(entries),
    )


def parse_bibliography_file(
    bibliography_file: str | Path,
    run_date: date | None = None,
) -> list[BibliographyEntry]:
    source = Path(bibliography_file)
    if not source.exists():
        raise FileNotFoundError(f"Bibliography file does not exist: {source}")
    if not source.is_file():
        raise ValueError(f"Bibliography path is not a file: {source}")

    source_format = _detect_format(source)
    source_hash = _sha256(source)
    today = run_date or date.today()
    if source_format == "csl-json":
        raw_items = _parse_csl_json(source)
    else:
        text = source.read_text(encoding="utf-8-sig")
        if source_format == "bibtex":
            raw_items = _parse_bibtex(text)
        elif source_format == "ris":
            raw_items = _parse_ris(text)
        else:
            raise ValueError(f"Unsupported bibliography format: {source.suffix}")

    return [
        _entry_from_raw(raw_item, source, source_format, source_hash, today, index)
        for index, raw_item in enumerate(raw_items, start=1)
    ]


def load_bibliography_index(path: str | Path) -> list[BibliographyEntry]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    items = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Bibliography index must be a list or an object with an items list.")
    return [BibliographyEntry.model_validate(item) for item in items]


def paper_records_from_bibliography(entries: Iterable[BibliographyEntry | dict]) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    for item in entries:
        entry = item if isinstance(item, BibliographyEntry) else BibliographyEntry.model_validate(item)
        records.append(
            PaperRecord(
                paper_id=entry.paper_id,
                title=entry.title,
                authors=entry.authors,
                year=entry.year,
                venue=entry.venue,
                doi=entry.doi,
                url=entry.url,
                key_claims=[],
                limitations=[],
                status=entry.status,
                notes="Imported from bibliography metadata only; claims, methods, datasets, and metrics need review.",
            )
        )
    return records


def render_bibliography_index(
    entries: Iterable[BibliographyEntry | dict],
    source_file: str | Path | None = None,
    source_format: str | None = None,
) -> str:
    records = [entry if isinstance(entry, BibliographyEntry) else BibliographyEntry.model_validate(entry) for entry in entries]
    lines = [
        "# Bibliography Index",
        "",
        "> Bibliography projection only. Do not treat imported citation metadata as verified until reviewed against the source publication.",
        "",
    ]
    if source_file is not None:
        lines.append(f"- Source file: `{source_file}`")
    if source_format is not None:
        lines.append(f"- Source format: `{source_format}`")
    lines.extend(
        [
            f"- Entry count: {len(records)}",
            "",
            "| Bibliography ID | Paper ID | Citation Key | Citation | DOI | URL | Status | Risk Flags |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for entry in records:
        lines.append(
            "| {bib_id} | {paper_id} | {key} | {citation} | {doi} | {url} | {status} | {risk} |".format(
                bib_id=_escape(entry.bibliography_id),
                paper_id=_escape(entry.paper_id),
                key=_escape(entry.citation_key or "-"),
                citation=_escape(_citation(entry)),
                doi=_escape(entry.doi or "-"),
                url=_escape(entry.url or "-"),
                status=_escape(entry.status),
                risk=_escape(", ".join(entry.risk_flags) or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _detect_format(source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix in SUPPORTED_FORMATS:
        return SUPPORTED_FORMATS[suffix]
    raise ValueError(f"Unsupported bibliography format: {source.suffix or source.name}")


def _parse_csl_json(source: Path) -> list[dict[str, Any]]:
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        payload = payload["items"]
    elif isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("CSL JSON bibliography must be an object, list, or object with items.")
    items = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        title = _first_text(item.get("title"))
        authors = _csl_authors(item.get("author"))
        items.append(
            {
                "entry_type": _first_text(item.get("type")) or "csl-item",
                "citation_key": _first_text(item.get("id")) or _first_text(item.get("citation-key")),
                "title": title,
                "authors": authors,
                "year": _csl_year(item.get("issued")) or _year_from_text(_first_text(item.get("issued")) or ""),
                "venue": _first_text(item.get("container-title")) or _first_text(item.get("publisher")),
                "doi": _clean_doi(_first_text(item.get("DOI")) or _first_text(item.get("doi"))),
                "url": _first_text(item.get("URL")) or _first_text(item.get("url")),
                "abstract": _first_text(item.get("abstract")),
                "keywords": _keywords(item.get("keyword") or item.get("keywords")),
            }
        )
    return items


def _parse_bibtex(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry_type, citation_key, body in _iter_bibtex_entries(text):
        fields = _parse_bibtex_fields(body)
        items.append(
            {
                "entry_type": entry_type.lower(),
                "citation_key": citation_key,
                "title": fields.get("title"),
                "authors": _split_bibtex_authors(fields.get("author")),
                "year": _year_from_text(fields.get("year") or fields.get("date") or ""),
                "venue": fields.get("journal") or fields.get("booktitle") or fields.get("conference") or fields.get("publisher"),
                "doi": _clean_doi(fields.get("doi")),
                "url": fields.get("url"),
                "abstract": fields.get("abstract"),
                "keywords": _keywords(fields.get("keywords") or fields.get("keyword")),
            }
        )
    return items


def _iter_bibtex_entries(text: str) -> Iterable[tuple[str, str | None, str]]:
    index = 0
    while True:
        marker = text.find("@", index)
        if marker == -1:
            break
        match = re.match(r"@([A-Za-z]+)\s*([{(])", text[marker:])
        if not match:
            index = marker + 1
            continue
        entry_type = match.group(1)
        opener = match.group(2)
        closer = "}" if opener == "{" else ")"
        body_start = marker + match.end()
        body_end = _find_matching(text, body_start - 1, opener, closer)
        if body_end == -1:
            break
        body = text[body_start:body_end].strip()
        citation_key, field_body = _split_bibtex_key(body)
        yield entry_type, citation_key, field_body
        index = body_end + 1


def _find_matching(text: str, opener_index: int, opener: str, closer: str) -> int:
    depth = 0
    in_quote = False
    escaped = False
    for index in range(opener_index, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return index
    return -1


def _split_bibtex_key(body: str) -> tuple[str | None, str]:
    parts = _split_top_level(body, ",", maxsplit=1)
    if len(parts) == 1:
        return None, body
    return parts[0].strip() or None, parts[1]


def _parse_bibtex_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in _split_top_level(body, ","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip().lower()
        if key:
            fields[key] = _clean_bibtex_value(value)
    return fields


def _split_top_level(text: str, delimiter: str, maxsplit: int | None = None) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    in_quote = False
    escaped = False
    splits = 0
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if not in_quote:
            if char in "{(":
                depth += 1
            elif char in "})" and depth > 0:
                depth -= 1
            elif char == delimiter and depth == 0:
                parts.append(text[start:index])
                start = index + 1
                splits += 1
                if maxsplit is not None and splits >= maxsplit:
                    break
    parts.append(text[start:])
    return parts


def _clean_bibtex_value(value: str) -> str:
    cleaned = value.strip().rstrip(",").strip()
    while len(cleaned) >= 2 and ((cleaned[0] == "{" and cleaned[-1] == "}") or (cleaned[0] == '"' and cleaned[-1] == '"')):
        cleaned = cleaned[1:-1].strip()
    cleaned = cleaned.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _split_bibtex_authors(value: str | None) -> list[str]:
    if not value:
        return []
    return [author.strip() for author in re.split(r"\s+and\s+", value) if author.strip()]


def _parse_ris(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, list[str]]] = []
    current: dict[str, list[str]] | None = None
    last_code: str | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        match = re.match(r"^([A-Z0-9]{2})\s*-\s*(.*)$", raw_line)
        if match:
            code, value = match.group(1), match.group(2).strip()
            if code == "TY":
                current = {"TY": [value]}
                records.append(current)
            elif current is not None:
                current.setdefault(code, []).append(value)
            if code == "ER":
                current = None
                last_code = None
                continue
            last_code = code
        elif current is not None and last_code:
            current.setdefault(last_code, []).append(raw_line.strip())

    items: list[dict[str, Any]] = []
    for record in records:
        title = _first_code(record, "TI", "T1", "BT", "CT")
        items.append(
            {
                "entry_type": _first_code(record, "TY") or "ris-item",
                "citation_key": _first_code(record, "ID"),
                "title": title,
                "authors": _all_codes(record, "AU", "A1", "A2", "A3"),
                "year": _year_from_text(_first_code(record, "PY", "Y1", "DA") or ""),
                "venue": _first_code(record, "JO", "JF", "T2", "PB"),
                "doi": _clean_doi(_first_code(record, "DO")),
                "url": _first_code(record, "UR"),
                "abstract": _first_code(record, "AB", "N2"),
                "keywords": _all_codes(record, "KW"),
            }
        )
    return items


def _entry_from_raw(
    raw: dict[str, Any],
    source: Path,
    source_format: str,
    source_hash: str,
    run_date: date,
    index: int,
) -> BibliographyEntry:
    title = _first_text(raw.get("title")) or "title_needs_review"
    authors = [_normalize_space(str(author)) for author in raw.get("authors", []) if _normalize_space(str(author))]
    citation_key = _first_text(raw.get("citation_key"))
    entry_type = _first_text(raw.get("entry_type")) or source_format
    year = _coerce_year(raw.get("year"))
    venue = _first_text(raw.get("venue"))
    doi = _clean_doi(_first_text(raw.get("doi")))
    url = _first_text(raw.get("url"))
    abstract = _first_text(raw.get("abstract"))
    keywords = _keywords(raw.get("keywords"))
    bib_id, paper_id = _stable_ids(raw, source_hash, run_date, index)
    risk_flags = ["imported_bibliography", "needs_human_review"]
    if title == "title_needs_review":
        risk_flags.append("missing_title")
    if not authors:
        risk_flags.append("missing_authors")
    if year is None:
        risk_flags.append("missing_year")
    if not venue:
        risk_flags.append("missing_venue")
    if not doi and not url:
        risk_flags.append("missing_identifier")

    return BibliographyEntry(
        bibliography_id=bib_id,
        paper_id=paper_id,
        citation_key=citation_key,
        entry_type=entry_type,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        url=url,
        abstract=abstract,
        keywords=keywords,
        source_file=str(source),
        source_format=source_format,
        source_hash=source_hash,
        status="needs_review",
        risk_flags=_unique(risk_flags),
        notes="Imported citation metadata. Verify against the source publication before relying on it.",
    )


def _stable_ids(raw: dict[str, Any], source_hash: str, run_date: date, index: int) -> tuple[str, str]:
    basis = (
        _first_text(raw.get("doi"))
        or _first_text(raw.get("citation_key"))
        or "|".join(
            [
                _first_text(raw.get("title")) or "",
                str(_coerce_year(raw.get("year")) or ""),
                ";".join(str(author) for author in raw.get("authors", [])),
            ]
        )
        or f"{source_hash}:{index}"
    )
    suffix = hashlib.sha1(f"{source_hash}:{index}:{basis}".encode("utf-8")).hexdigest()[:10].upper()
    return f"BIB-{run_date.year}-{suffix}", f"PAPER-{run_date.year}-{suffix}"


def _citation(entry: BibliographyEntry) -> str:
    author_text = ", ".join(entry.authors) if entry.authors else "authors_needs_review"
    year = str(entry.year) if entry.year is not None else "year_needs_review"
    venue = entry.venue or "venue_needs_review"
    return f"{author_text} ({year}). {entry.title}. {venue}."


def _import_warnings(entries: list[BibliographyEntry]) -> list[str]:
    warnings: list[str] = []
    if not entries:
        warnings.append("no_bibliography_entries_detected")
    for entry in entries:
        for flag in entry.risk_flags:
            if flag.startswith("missing_"):
                warnings.append(flag)
    return _unique(warnings)


def _csl_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for author in value:
        if isinstance(author, str):
            authors.append(_normalize_space(author))
        elif isinstance(author, dict):
            literal = _first_text(author.get("literal"))
            if literal:
                authors.append(literal)
                continue
            family = _first_text(author.get("family"))
            given = _first_text(author.get("given"))
            if family and given:
                authors.append(f"{family}, {given}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)
    return [author for author in authors if author]


def _csl_year(value: Any) -> int | None:
    if isinstance(value, dict):
        parts = value.get("date-parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
            return _coerce_year(parts[0][0])
        return _year_from_text(_first_text(value.get("raw")) or "")
    return None


def _first_code(record: dict[str, list[str]], *codes: str) -> str | None:
    for code in codes:
        values = record.get(code)
        if values:
            return _normalize_space(" ".join(values))
    return None


def _all_codes(record: dict[str, list[str]], *codes: str) -> list[str]:
    values: list[str] = []
    for code in codes:
        values.extend(record.get(code, []))
    return [_normalize_space(value) for value in values if _normalize_space(value)]


def _first_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        for item in value:
            result = _first_text(item)
            if result:
                return result
        return None
    result = _normalize_space(str(value))
    return result or None


def _keywords(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_normalize_space(str(item)) for item in value if _normalize_space(str(item))]
    return [part.strip() for part in re.split(r"\s*[;,]\s*", str(value)) if part.strip()]


def _year_from_text(text: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", text)
    return int(match.group(0)) if match else None


def _coerce_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if 1000 <= value <= 9999 else None
    return _year_from_text(str(value))


def _clean_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    return doi or None


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
