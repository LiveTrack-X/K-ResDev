from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .bibliography import parse_bibliography_file
from .models import BibliographyEntry, ReferenceCorpusItem, ReferenceCorpusRejection, ReferenceCorpusResult

SUPPORTED_SUFFIXES = {".bib", ".json", ".md", ".pdf", ".ris", ".txt"}
COPYRIGHT_TEXT_LIMIT = 500
CITATION_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
YEAR_RE = re.compile(r"(19|20)\d{2}")


def build_reference_corpus(
    root: str | Path,
    references_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    rejection_json_path: str | Path | None = None,
    run_date: date | None = None,
) -> ReferenceCorpusResult:
    """Scan local reference files into a reviewable corpus index.

    The scanner imports local metadata and short user notes only. It never
    modifies reference files and does not treat imported records as verified
    bibliography entries or claim-support evidence.
    """

    workspace = Path(root)
    refs = Path(references_dir) if references_dir is not None else workspace / "references"
    today = run_date or date.today()
    warnings: list[str] = []
    items: list[ReferenceCorpusItem] = []
    rejections: list[ReferenceCorpusRejection] = []

    if not refs.exists():
        warnings.append("references_dir_missing")
        return _result(workspace, refs, [], [], warnings, output_path, json_path, rejection_json_path)
    if not refs.is_dir():
        rejection = _rejection("folder-scan", refs, "references_path_not_directory", "References path is not a directory.", severity="high")
        return _result(workspace, refs, [], [rejection], warnings, output_path, json_path, rejection_json_path)

    files = [path for path in sorted(refs.rglob("*"), key=lambda item: item.as_posix()) if path.is_file()]
    if not files:
        warnings.append("no_reference_files_detected")

    for path in files:
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            rejections.append(
                _rejection(
                    "folder-scan",
                    path,
                    "unsupported_file_type",
                    f"Unsupported reference file type `{suffix or path.name}`.",
                    severity="low",
                )
            )
            continue
        try:
            parsed_items, parsed_rejections = _parse_reference_file(path, workspace, today)
        except Exception as exc:
            parsed_items = []
            parsed_rejections = [
                _rejection(
                    _adapter_for_path(path),
                    path,
                    "reference_file_unreadable",
                    f"Reference file could not be read: {exc}",
                    severity="high",
                )
            ]
        items.extend(parsed_items)
        rejections.extend(parsed_rejections)

    items, duplicate_rejections = _dedupe_items(items)
    rejections.extend(duplicate_rejections)
    return _result(workspace, refs, items, rejections, warnings, output_path, json_path, rejection_json_path)


def load_reference_corpus(path: str | Path) -> list[ReferenceCorpusItem]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    items = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Reference corpus must be a list or an object with an items list.")
    return [ReferenceCorpusItem.model_validate(item) for item in items]


def load_reference_rejections(path: str | Path) -> list[ReferenceCorpusRejection]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    items = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Reference rejection log must be a list or an object with an items list.")
    return [ReferenceCorpusRejection.model_validate(item) for item in items]


def render_reference_corpus_summary(result: ReferenceCorpusResult) -> str:
    lines = [
        "# K-ResDev Reference Corpus Summary",
        "",
        "> Reference corpus projection only. This imports local metadata and short user notes for review; it does not verify paper relevance, citation correctness, or claim support.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| References dir | `{_escape(result.references_dir)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Corpus items | {result.item_count} |",
        f"| Rejection log entries | {result.rejection_count} |",
        f"| High rejections | {result.high_count} |",
        f"| Medium rejections | {result.medium_count} |",
        f"| Low rejections | {result.low_count} |",
        f"| Warnings | {_escape(', '.join(result.warnings) or '-')} |",
        "",
        "## Corpus Items",
        "",
        "| Reference ID | Adapter | Citation Key | Title | Year | DOI | Status | Risk Flags | Source |",
        "|---|---|---|---|---:|---|---|---|---|",
    ]
    if not result.items:
        lines.append("| - | - | - | No reference corpus items detected. | - | - | - | - | - |")
    for item in result.items:
        lines.append(
            "| {ref} | {adapter} | {key} | {title} | {year} | {doi} | {status} | {flags} | {source} |".format(
                ref=_escape(item.reference_id),
                adapter=_escape(item.adapter),
                key=_escape(item.citation_key or "-"),
                title=_escape(item.title or "title_needs_review"),
                year=item.year if item.year is not None else "-",
                doi=_escape(item.doi or "-"),
                status=_escape(item.status),
                flags=_escape(", ".join(item.risk_flags) or "-"),
                source=_escape(item.source_file),
            )
        )
    lines.extend(
        [
            "",
            "## Rejection Log",
            "",
            "| Severity | Reason | Citation Key | Reference | Message | Source |",
            "|---|---|---|---|---|---|",
        ]
    )
    if not result.rejections:
        lines.append("| ok | reference_corpus_ready | - | - | No rejection log entries detected. | - |")
    for rejection in result.rejections:
        lines.append(
            "| {severity} | {reason} | {key} | {ref} | {message} | {source} |".format(
                severity=_escape(rejection.severity),
                reason=_escape(rejection.reason),
                key=_escape(rejection.citation_key or "-"),
                ref=_escape(rejection.reference_id or "-"),
                message=_escape(rejection.message),
                source=_escape(rejection.source_file),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _parse_reference_file(path: Path, workspace: Path, run_date: date) -> tuple[list[ReferenceCorpusItem], list[ReferenceCorpusRejection]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return [_pdf_item(path, workspace, run_date)], []
    if suffix in {".md", ".txt"}:
        return _markdown_note_items(path, workspace, run_date)
    if suffix == ".json":
        return _json_items(path, workspace, run_date)
    if suffix in {".bib", ".ris"}:
        entries = parse_bibliography_file(path, run_date=run_date)
        return [_item_from_bibliography(entry, workspace, run_date) for entry in entries], []
    return [], [
        _rejection(
            "folder-scan",
            path,
            "unsupported_file_type",
            f"Unsupported reference file type `{suffix or path.name}`.",
            severity="low",
        )
    ]


def _json_items(path: Path, workspace: Path, run_date: date) -> tuple[list[ReferenceCorpusItem], list[ReferenceCorpusRejection]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    raw_items = _json_item_list(payload)
    if not raw_items:
        return [], [_rejection("zotero-json", path, "empty_reference_json", "JSON reference export contains no records.", severity="medium")]
    if any(_looks_like_zotero(item) for item in raw_items):
        return _zotero_items(path, workspace, raw_items, run_date)
    try:
        entries = parse_bibliography_file(path, run_date=run_date)
    except Exception as exc:
        return [], [
            _rejection(
                "zotero-json",
                path,
                "unsupported_json_reference_format",
                f"JSON file did not look like Zotero export or CSL JSON: {exc}",
                severity="medium",
            )
        ]
    return [_item_from_bibliography(entry, workspace, run_date) for entry in entries], []


def _zotero_items(path: Path, workspace: Path, raw_items: list[dict[str, Any]], run_date: date) -> tuple[list[ReferenceCorpusItem], list[ReferenceCorpusRejection]]:
    items: list[ReferenceCorpusItem] = []
    rejections: list[ReferenceCorpusRejection] = []
    source_hash = _sha256(path)
    for index, raw in enumerate(raw_items, start=1):
        data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
        citation_key = _first_text(data.get("citationKey")) or _first_text(data.get("citation-key")) or _first_text(data.get("key"))
        title = _first_text(data.get("title"))
        year = _year_from_text(_first_text(data.get("date")) or _first_text(data.get("year")) or "")
        if year is None and data.get("issued") is not None:
            year = _year_from_text(json.dumps(data.get("issued"), ensure_ascii=False))
        authors = _zotero_authors(data.get("creators"))
        venue = (
            _first_text(data.get("publicationTitle"))
            or _first_text(data.get("bookTitle"))
            or _first_text(data.get("conferenceName"))
            or _first_text(data.get("publisher"))
        )
        doi = _clean_doi(_first_text(data.get("DOI")) or _first_text(data.get("doi")))
        url = _first_text(data.get("url")) or _first_text(data.get("URL"))
        keywords = _zotero_keywords(data.get("tags"))
        user_notes, note_rejections = _zotero_notes(path, data, citation_key, source_hash)
        rejections.extend(note_rejections)
        item = _make_item(
            adapter="zotero-json",
            source=path,
            workspace=workspace,
            source_hash=source_hash,
            source_format="zotero-json",
            run_date=run_date,
            index=index,
            citation_key=citation_key,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            keywords=keywords,
            user_notes=user_notes,
            metadata={"item_type": _first_text(data.get("itemType")) or _first_text(data.get("type"))},
            risk_flags=["imported_zotero_metadata", "needs_human_review"],
        )
        if _invalid_citation_key(item.citation_key):
            rejections.append(
                _rejection(
                    "zotero-json",
                    path,
                    "invalid_citation_key",
                    f"Citation key `{item.citation_key}` is not supported by K-ResDev Markdown citation checks.",
                    severity="medium",
                    citation_key=item.citation_key,
                    reference_id=item.reference_id,
                    source_hash=source_hash,
                )
            )
            continue
        items.append(item)
    return items, rejections


def _markdown_note_items(path: Path, workspace: Path, run_date: date) -> tuple[list[ReferenceCorpusItem], list[ReferenceCorpusRejection]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    frontmatter, body = _frontmatter(text)
    source_hash = _sha256(path)
    citation_key = _first_text(_field(frontmatter, "citation_key", "citation-key", "citekey", "key"))
    title = _first_text(_field(frontmatter, "title")) or _first_heading(body) or path.stem
    authors = _list_field(_field(frontmatter, "authors", "author"))
    year = _year_from_text(_first_text(_field(frontmatter, "year", "date")) or "")
    venue = _first_text(_field(frontmatter, "venue", "journal", "booktitle", "publication"))
    doi = _clean_doi(_first_text(_field(frontmatter, "doi", "DOI")))
    url = _first_text(_field(frontmatter, "url", "URL"))
    keywords = _list_field(_field(frontmatter, "keywords", "tags"))
    note = _first_text(_field(frontmatter, "user_note", "user-notes", "note", "notes"))
    rejections: list[ReferenceCorpusRejection] = []
    if note and len(note) > COPYRIGHT_TEXT_LIMIT:
        rejections.append(
            _rejection(
                "markdown-note",
                path,
                "copyright_risk_text_omitted",
                "Markdown note metadata is longer than the safe import limit and was omitted.",
                severity="low",
                citation_key=citation_key,
                source_hash=source_hash,
            )
        )
        note = None
    risk_flags = ["imported_markdown_note", "needs_human_review"]
    if not frontmatter:
        risk_flags.append("missing_frontmatter")
    if title == path.stem and not _first_text(_field(frontmatter, "title")) and not _first_heading(body):
        risk_flags.append("filename_title_needs_review")
    item = _make_item(
        adapter="markdown-note",
        source=path,
        workspace=workspace,
        source_hash=source_hash,
        source_format=path.suffix.lower().lstrip(".") or "markdown",
        run_date=run_date,
        index=1,
        citation_key=citation_key,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        url=url,
        keywords=keywords,
        user_notes=note,
        metadata={"frontmatter_keys": sorted(frontmatter)},
        risk_flags=risk_flags,
    )
    if _invalid_citation_key(item.citation_key):
        rejections.append(
            _rejection(
                "markdown-note",
                path,
                "invalid_citation_key",
                f"Citation key `{item.citation_key}` is not supported by K-ResDev Markdown citation checks.",
                severity="medium",
                citation_key=item.citation_key,
                reference_id=item.reference_id,
                source_hash=source_hash,
            )
        )
        return [], rejections
    return [item], rejections


def _pdf_item(path: Path, workspace: Path, run_date: date) -> ReferenceCorpusItem:
    source_hash = _sha256(path)
    return _make_item(
        adapter="folder-scan",
        source=path,
        workspace=workspace,
        source_hash=source_hash,
        source_format="pdf",
        run_date=run_date,
        index=1,
        title=path.stem,
        metadata={"file_only": True},
        risk_flags=[
            "file_only_reference",
            "filename_title_needs_review",
            "missing_authors",
            "missing_year",
            "missing_identifier",
            "needs_human_review",
        ],
    )


def _item_from_bibliography(entry: BibliographyEntry, workspace: Path, run_date: date) -> ReferenceCorpusItem:
    return _make_item(
        adapter="bibliography-file",
        source=Path(entry.source_file),
        workspace=workspace,
        source_hash=entry.source_hash,
        source_format=entry.source_format,
        run_date=run_date,
        index=1,
        citation_key=entry.citation_key,
        title=entry.title,
        authors=entry.authors,
        year=entry.year,
        venue=entry.venue,
        doi=entry.doi,
        url=entry.url,
        keywords=entry.keywords,
        metadata={"bibliography_id": entry.bibliography_id, "paper_id": entry.paper_id},
        risk_flags=["imported_bibliography_metadata", "needs_human_review"] + entry.risk_flags,
    )


def _make_item(
    adapter: str,
    source: Path,
    workspace: Path,
    source_hash: str | None,
    source_format: str,
    run_date: date,
    index: int,
    citation_key: str | None = None,
    title: str | None = None,
    authors: list[str] | None = None,
    year: int | None = None,
    venue: str | None = None,
    doi: str | None = None,
    url: str | None = None,
    keywords: list[str] | None = None,
    user_notes: str | None = None,
    metadata: dict[str, Any] | None = None,
    risk_flags: list[str] | None = None,
) -> ReferenceCorpusItem:
    authors = authors or []
    keywords = keywords or []
    risk = list(risk_flags or [])
    if not title:
        risk.append("missing_title")
    if not authors:
        risk.append("missing_authors")
    if year is None:
        risk.append("missing_year")
    if not doi and not url and not citation_key:
        risk.append("missing_identifier")
    reference_id = _reference_id(source_hash or str(source), citation_key, doi, title, year, run_date, index)
    return ReferenceCorpusItem(
        reference_id=reference_id,
        adapter=adapter,
        source_file=_display_path(workspace, source),
        source_hash=source_hash,
        source_format=source_format,
        citation_key=citation_key,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        url=url,
        keywords=keywords,
        user_notes=user_notes,
        status="needs_review",
        risk_flags=_unique(risk),
        metadata=metadata or {},
    )


def _dedupe_items(items: list[ReferenceCorpusItem]) -> tuple[list[ReferenceCorpusItem], list[ReferenceCorpusRejection]]:
    seen: dict[str, ReferenceCorpusItem] = {}
    result: list[ReferenceCorpusItem] = []
    rejections: list[ReferenceCorpusRejection] = []
    for item in sorted(items, key=lambda value: (value.source_file, value.reference_id)):
        key = _dedupe_key(item)
        if key in seen:
            first = seen[key]
            rejections.append(
                ReferenceCorpusRejection(
                    rejection_id=_rejection_id(item.source_file, "duplicate_reference", item.reference_id),
                    adapter=item.adapter,
                    source_file=item.source_file,
                    source_hash=item.source_hash,
                    reason="duplicate_reference",
                    message=f"Reference duplicates `{first.reference_id}` by DOI, citation key, or title/year key.",
                    severity="medium",
                    citation_key=item.citation_key,
                    reference_id=item.reference_id,
                    metadata={"first_reference_id": first.reference_id, "dedupe_key": key},
                )
            )
            continue
        seen[key] = item
        result.append(item)
    return result, rejections


def _dedupe_key(item: ReferenceCorpusItem) -> str:
    if item.doi:
        return f"doi:{item.doi.lower()}"
    if item.citation_key:
        return f"key:{item.citation_key.lower()}"
    title = re.sub(r"\W+", "", (item.title or "").lower())
    return f"title:{title}:{item.year or ''}:{';'.join(author.lower() for author in item.authors)}"


def _result(
    workspace: Path,
    references_dir: Path,
    items: list[ReferenceCorpusItem],
    rejections: list[ReferenceCorpusRejection],
    warnings: list[str],
    output_path: str | Path | None,
    json_path: str | Path | None,
    rejection_json_path: str | Path | None,
) -> ReferenceCorpusResult:
    rejections = sorted(_unique_rejections(rejections), key=lambda item: (_severity_rank(item.severity), item.reason, item.source_file, item.rejection_id))
    items = sorted(items, key=lambda item: (item.adapter, item.source_file, item.reference_id))
    high_count = sum(1 for item in rejections if item.severity == "high")
    medium_count = sum(1 for item in rejections if item.severity == "medium")
    low_count = sum(1 for item in rejections if item.severity == "low")
    if high_count:
        status = "blocked"
    elif medium_count:
        status = "needs_review"
    elif low_count:
        status = "ready_with_notes"
    elif items:
        status = "ready"
    else:
        status = "not_configured"
    result = ReferenceCorpusResult(
        root=str(workspace),
        references_dir=str(references_dir),
        status=status,
        item_count=len(items),
        rejection_count=len(rejections),
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        items=items,
        rejections=rejections,
        summary_markdown_path=str(output_path) if output_path else None,
        corpus_json_path=str(json_path) if json_path else None,
        rejection_log_json_path=str(rejection_json_path) if rejection_json_path else None,
        warnings=_unique(warnings),
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_reference_corpus_summary(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    if rejection_json_path is not None:
        target = Path(rejection_json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "generated_by": "k-resdev-skill",
                    "root": str(workspace),
                    "references_dir": str(references_dir),
                    "rejection_count": len(rejections),
                    "items": [item.model_dump(mode="json") for item in rejections],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return result


def _json_item_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        payload = payload["items"]
    elif isinstance(payload, dict) and isinstance(payload.get("references"), list):
        payload = payload["references"]
    elif isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    result: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            result.append(item)
    return result


def _looks_like_zotero(item: dict[str, Any]) -> bool:
    data = item.get("data") if isinstance(item.get("data"), dict) else item
    return any(key in data for key in ("itemType", "creators", "publicationTitle", "abstractNote", "DOI", "key"))


def _zotero_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for creator in value:
        if isinstance(creator, str):
            authors.append(_normalize_space(creator))
        elif isinstance(creator, dict):
            name = _first_text(creator.get("name"))
            if name:
                authors.append(name)
                continue
            last = _first_text(creator.get("lastName"))
            first = _first_text(creator.get("firstName"))
            if last and first:
                authors.append(f"{last}, {first}")
            elif last:
                authors.append(last)
            elif first:
                authors.append(first)
    return [author for author in authors if author]


def _zotero_keywords(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    keywords: list[str] = []
    for tag in value:
        if isinstance(tag, str):
            keywords.append(_normalize_space(tag))
        elif isinstance(tag, dict):
            text = _first_text(tag.get("tag"))
            if text:
                keywords.append(text)
    return _unique([item for item in keywords if item])


def _zotero_notes(path: Path, data: dict[str, Any], citation_key: str | None, source_hash: str) -> tuple[str | None, list[ReferenceCorpusRejection]]:
    notes: list[str] = []
    rejections: list[ReferenceCorpusRejection] = []
    abstract = _first_text(data.get("abstractNote"))
    if abstract:
        rejections.append(
            _rejection(
                "zotero-json",
                path,
                "copyright_risk_text_omitted",
                "Zotero abstractNote was detected and omitted from the corpus index.",
                severity="low",
                citation_key=citation_key,
                source_hash=source_hash,
                metadata={"field": "abstractNote", "char_count": len(abstract)},
            )
        )
    raw_notes = data.get("notes")
    if isinstance(raw_notes, list):
        for note in raw_notes:
            note_text = _first_text(note.get("note")) if isinstance(note, dict) else _first_text(note)
            if note_text:
                notes.append(_strip_html(note_text))
    single_note = _first_text(data.get("note"))
    if single_note:
        notes.append(_strip_html(single_note))
    combined = "\n".join(_unique(notes)).strip()
    if not combined:
        return None, rejections
    if len(combined) > COPYRIGHT_TEXT_LIMIT:
        rejections.append(
            _rejection(
                "zotero-json",
                path,
                "copyright_risk_text_omitted",
                "Zotero note text is longer than the safe import limit and was omitted.",
                severity="low",
                citation_key=citation_key,
                source_hash=source_hash,
                metadata={"field": "notes", "char_count": len(combined)},
            )
        )
        return None, rejections
    return combined, rejections


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized
    end = normalized.find("\n---", 4)
    if end == -1:
        return {}, normalized
    raw = normalized[4:end]
    body = normalized[end + len("\n---") :]
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip("\"'")
        if key:
            fields[key] = value
    return fields, body


def _field(fields: dict[str, str], *names: str) -> str | None:
    for name in names:
        value = fields.get(name.lower())
        if value:
            return value
    return None


def _list_field(value: str | None) -> list[str]:
    if not value:
        return []
    cleaned = value.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return [_normalize_space(part.strip().strip("\"'")) for part in re.split(r"\s*(?:;|,|\|)\s*", cleaned) if _normalize_space(part.strip().strip("\"'"))]


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
    return None


def _adapter_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "zotero-json"
    if suffix in {".md", ".txt"}:
        return "markdown-note"
    if suffix == ".pdf":
        return "folder-scan"
    if suffix in {".bib", ".ris"}:
        return "bibliography-file"
    return "folder-scan"


def _rejection(
    adapter: str,
    source: Path,
    reason: str,
    message: str,
    severity: str = "medium",
    citation_key: str | None = None,
    reference_id: str | None = None,
    source_hash: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ReferenceCorpusRejection:
    return ReferenceCorpusRejection(
        rejection_id=_rejection_id(str(source), reason, citation_key or reference_id or message),
        adapter=adapter,
        source_file=str(source),
        source_hash=source_hash if source_hash is not None else (_sha256(source) if source.exists() and source.is_file() else None),
        reason=reason,
        message=message,
        severity=severity,
        citation_key=citation_key,
        reference_id=reference_id,
        path=str(source),
        metadata=metadata or {},
    )


def _invalid_citation_key(value: str | None) -> bool:
    return bool(value) and CITATION_KEY_RE.match(value) is None


def _reference_id(source_hash: str, citation_key: str | None, doi: str | None, title: str | None, year: int | None, run_date: date, index: int) -> str:
    basis = doi or citation_key or "|".join([title or "", str(year or ""), str(index)])
    digest = hashlib.sha1(f"{source_hash}:{basis}:{index}".encode("utf-8")).hexdigest()[:10].upper()
    return f"REF-{run_date.year}-{digest}"


def _rejection_id(source_file: str, reason: str, detail: str | None) -> str:
    digest = hashlib.sha1(f"{source_file}:{reason}:{detail or ''}".encode("utf-8")).hexdigest()[:10].upper()
    return f"RRJ-{digest}"


def _year_from_text(text: str) -> int | None:
    match = YEAR_RE.search(str(text))
    return int(match.group(0)) if match else None


def _clean_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    return doi or None


def _first_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        for item in value:
            text = _first_text(item)
            if text:
                return text
        return None
    result = _normalize_space(str(value))
    return result or None


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _strip_html(value: str) -> str:
    return _normalize_space(re.sub(r"<[^>]+>", " ", value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _display_path(workspace: Path, path: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return str(path)


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _unique_rejections(values: Iterable[ReferenceCorpusRejection]) -> list[ReferenceCorpusRejection]:
    seen: set[tuple[str, str, str, str | None]] = set()
    result: list[ReferenceCorpusRejection] = []
    for value in values:
        key = (value.source_file, value.reason, value.message, value.citation_key)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
