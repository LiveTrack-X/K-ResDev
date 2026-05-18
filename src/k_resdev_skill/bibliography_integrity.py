from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .bibliography import load_bibliography_index
from .bibliography_review import latest_bibliography_review, load_bibliography_review_records
from .models import (
    BibliographyEntry,
    BibliographyIntegrityFinding,
    BibliographyReviewDecision,
    BibliographyReviewRecord,
    WorkspaceBibliographyIntegrityResult,
)

BIBLIOGRAPHY_OPERATIONAL_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "bibliography-integrity.md",
    "bibliography-review-summary.md",
    "budget-ledger.md",
    "budget-checklist.md",
    "citation-support.md",
    "citation-support-summary.md",
    "evidence-bundle-index.md",
    "next-actions.md",
    "profile-integrity.md",
    "profile-source-summary.md",
    "readiness.md",
    "report-integrity.md",
    "source-verification.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
    "workspace-trace.md",
}


def generate_workspace_bibliography_integrity(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceBibliographyIntegrityResult:
    """Check local bibliography metadata and Markdown citation keys.

    This does not verify that a cited paper actually supports a scientific
    claim. It only checks local citation metadata presence, review state, and
    source hash drift.
    """

    workspace = Path(root)
    findings: list[BibliographyIntegrityFinding] = []
    warnings: list[str] = []
    report_citations = _citations_by_report(workspace)
    citation_count = sum(len(keys) for keys in report_citations.values())
    index_path = workspace / "state" / "bibliography-index.json"
    reviews, review_warnings = _load_review_records(workspace)
    warnings.extend(review_warnings)

    entries: list[BibliographyEntry] = []
    if not index_path.exists():
        if citation_count:
            findings.append(
                _finding(
                    "bibliography_index_missing_for_citations",
                    "high",
                    "Report citations were found but state/bibliography-index.json is missing.",
                    index_path,
                    suggested_action="Run bib-import or provide a reviewed bibliography index before external use.",
                )
            )
        else:
            warnings.append("bibliography_index_missing")
        return _result(workspace, entries, reviews, citation_count, findings, warnings, output_path, json_path)

    try:
        entries = load_bibliography_index(index_path)
    except Exception as exc:
        findings.append(
            _finding(
                "bibliography_index_unreadable",
                "high",
                f"Bibliography index could not be read: {exc}",
                index_path,
                suggested_action="Regenerate or repair state/bibliography-index.json.",
            )
        )
        return _result(workspace, entries, reviews, citation_count, findings, warnings, output_path, json_path)

    if not entries:
        findings.append(
            _finding(
                "empty_bibliography_index",
                "medium",
                "Bibliography index exists but contains no entries.",
                index_path,
                suggested_action="Import BibTeX/RIS/CSL JSON metadata or remove unused bibliography artifacts.",
            )
        )

    by_key: dict[str, list[BibliographyEntry]] = {}
    by_doi: dict[str, list[BibliographyEntry]] = {}
    for entry in entries:
        if entry.citation_key:
            by_key.setdefault(entry.citation_key, []).append(entry)
        if entry.doi:
            by_doi.setdefault(entry.doi.lower(), []).append(entry)
        findings.extend(_source_findings(workspace, entry))

    for key, duplicates in sorted(by_key.items()):
        if len(duplicates) > 1:
            findings.append(
                _finding(
                    "duplicate_citation_key",
                    "medium",
                    f"Citation key `{key}` appears in {len(duplicates)} bibliography entries.",
                    index_path,
                    citation_key=key,
                    bibliography_id=", ".join(entry.bibliography_id for entry in duplicates),
                    suggested_action="Deduplicate or rename citation keys before generating manuscripts.",
                )
            )

    for doi, duplicates in sorted(by_doi.items()):
        if len(duplicates) > 1:
            findings.append(
                _finding(
                    "duplicate_bibliography_doi",
                    "low",
                    f"DOI `{doi}` appears in {len(duplicates)} bibliography entries.",
                    index_path,
                    bibliography_id=", ".join(entry.bibliography_id for entry in duplicates),
                    suggested_action="Review duplicate DOI entries and merge if they refer to the same paper.",
                )
            )

    first_by_key = {key: values[0] for key, values in by_key.items()}
    for report_path, keys in report_citations.items():
        for key in sorted(keys):
            entry = first_by_key.get(key)
            if entry is None:
                findings.append(
                    _finding(
                        "missing_bibliography_citation",
                        "high",
                        f"Markdown citation `@{key}` has no matching bibliography entry.",
                        report_path,
                        citation_key=key,
                        suggested_action="Import or add the citation entry, or remove the unsupported citation.",
                    )
                )
                continue
            effective_status = _effective_review_status(entry, reviews)
            if effective_status == BibliographyReviewDecision.REJECTED.value or effective_status == BibliographyReviewDecision.SUPERSEDED.value:
                findings.append(
                    _finding(
                        "invalid_bibliography_review_citation",
                        "high",
                        f"Markdown citation `@{key}` points to bibliography entry `{entry.bibliography_id}` with latest review status `{effective_status}`.",
                        report_path,
                        citation_key=key,
                        bibliography_id=entry.bibliography_id,
                        suggested_action="Remove or replace citations whose bibliography metadata was rejected or superseded.",
                    )
                )
            elif effective_status != BibliographyReviewDecision.ACCEPTED.value:
                findings.append(
                    _finding(
                        "unreviewed_bibliography_citation",
                        "medium",
                        f"Markdown citation `@{key}` points to bibliography entry `{entry.bibliography_id}` with latest review status `{effective_status}`.",
                        report_path,
                        citation_key=key,
                        bibliography_id=entry.bibliography_id,
                        suggested_action="Human-review the bibliography entry before external manuscript/report use.",
                    )
                )

    return _result(workspace, entries, reviews, citation_count, findings, warnings, output_path, json_path)


def render_bibliography_integrity_markdown(result: WorkspaceBibliographyIntegrityResult) -> str:
    lines = [
        "# K-ResDev Bibliography Integrity",
        "",
        "> Bibliography integrity projection only. This checks local citation metadata and Markdown citation keys; it does not prove that a cited paper supports a claim.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Bibliography entries | {result.entry_count} |",
        f"| Bibliography reviews | {result.review_count} |",
        f"| Markdown citations | {result.citation_count} |",
        f"| Finding count | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Citation Key | Bibliography ID | Message | Path | Suggested Action |",
        "|---|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | ready | - | - | No bibliography integrity findings detected. | - | Continue human review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {key} | {bib_id} | {message} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                key=_escape(finding.citation_key or "-"),
                bib_id=_escape(finding.bibliography_id or "-"),
                message=_escape(finding.message),
                path=_escape(finding.path or "-"),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- `{_escape(warning)}`" for warning in result.warnings)
    lines.append("")
    return "\n".join(lines)


def _result(
    workspace: Path,
    entries: list[BibliographyEntry],
    reviews: list[BibliographyReviewRecord],
    citation_count: int,
    findings: list[BibliographyIntegrityFinding],
    warnings: list[str],
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> WorkspaceBibliographyIntegrityResult:
    high_count = sum(1 for finding in findings if finding.severity == "high")
    medium_count = sum(1 for finding in findings if finding.severity == "medium")
    low_count = sum(1 for finding in findings if finding.severity == "low")
    if high_count:
        status = "blocked"
    elif medium_count:
        status = "needs_review"
    elif low_count:
        status = "ready_with_notes"
    elif entries or citation_count:
        status = "ready"
    else:
        status = "not_configured"
    result = WorkspaceBibliographyIntegrityResult(
        root=str(workspace),
        status=status,
        entry_count=len(entries),
        review_count=len(reviews),
        citation_count=citation_count,
        finding_count=len(findings),
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_bibliography_integrity_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def _load_review_records(workspace: Path) -> tuple[list[BibliographyReviewRecord], list[str]]:
    reviews_dir = workspace / "state" / "bibliography-reviews"
    if not reviews_dir.exists():
        return [], []
    try:
        return load_bibliography_review_records(reviews_dir), []
    except Exception as exc:
        return [], [f"bibliography_reviews_unreadable:{exc}"]


def _effective_review_status(entry: BibliographyEntry, reviews: list[BibliographyReviewRecord]) -> str:
    latest = latest_bibliography_review(reviews, entry.bibliography_id)
    if latest is not None:
        return str(latest.decision)
    return str(entry.status or "needs_review")


def _source_findings(workspace: Path, entry: BibliographyEntry) -> list[BibliographyIntegrityFinding]:
    findings: list[BibliographyIntegrityFinding] = []
    if not entry.source_hash:
        findings.append(
            _finding(
                "bibliography_source_hash_unverified",
                "medium",
                f"Bibliography entry `{entry.bibliography_id}` is not bound to a source hash.",
                entry.source_file,
                citation_key=entry.citation_key,
                bibliography_id=entry.bibliography_id,
                suggested_action="Re-import from the raw bibliography file so source_hash is recorded.",
            )
        )
        return findings

    source_path = _resolve_path(workspace, entry.source_file)
    if source_path is None or not source_path.exists():
        findings.append(
            _finding(
                "bibliography_source_missing",
                "high",
                f"Bibliography source for `{entry.bibliography_id}` is missing.",
                entry.source_file,
                citation_key=entry.citation_key,
                bibliography_id=entry.bibliography_id,
                suggested_action="Restore the raw bibliography file or re-import from the current source.",
            )
        )
        return findings
    actual = _sha256(source_path)
    if actual != entry.source_hash:
        findings.append(
            _finding(
                "bibliography_source_hash_mismatch",
                "high",
                f"Bibliography source hash changed for `{entry.bibliography_id}`.",
                source_path,
                citation_key=entry.citation_key,
                bibliography_id=entry.bibliography_id,
                suggested_action="Review source changes and rerun bib-import if the new bibliography is intended.",
            )
        )
    return findings


def _citations_by_report(workspace: Path) -> dict[Path, set[str]]:
    reports = workspace / "reports"
    result: dict[Path, set[str]] = {}
    if not reports.exists():
        return result
    for path in sorted(reports.glob("*.md"), key=lambda item: item.as_posix()):
        if path.name in BIBLIOGRAPHY_OPERATIONAL_NAMES:
            continue
        keys = extract_markdown_citation_keys(path.read_text(encoding="utf-8", errors="replace"))
        if keys:
            result[path] = keys
    return result


def extract_markdown_citation_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for bracket in re.findall(r"\[([^\]]*@[^]]+)\]", text):
        keys.update(_clean_key(match) for match in re.findall(r"@([A-Za-z][A-Za-z0-9_.:-]*)", bracket))
    stripped = re.sub(r"\[[^\]]+\]", " ", text)
    keys.update(_clean_key(match) for match in re.findall(r"(?<![\w.%+-])@([A-Za-z][A-Za-z0-9_.:-]*)\b", stripped))
    return {key for key in keys if key}


def _clean_key(value: str) -> str:
    return value.strip().strip(".,;:")


def _resolve_path(workspace: Path, raw_path: str) -> Path | None:
    path = Path(raw_path)
    if path.exists():
        return path
    candidate = workspace / raw_path
    if candidate.exists():
        return candidate
    name_candidate = workspace / "references" / path.name
    if name_candidate.exists():
        return name_candidate
    return candidate


def _finding(
    code: str,
    severity: str,
    message: str,
    path: str | Path | None = None,
    citation_key: str | None = None,
    bibliography_id: str | None = None,
    suggested_action: str | None = None,
) -> BibliographyIntegrityFinding:
    return BibliographyIntegrityFinding(
        code=code,
        severity=severity,
        message=message,
        path=str(path) if path is not None else None,
        citation_key=citation_key,
        bibliography_id=bibliography_id,
        suggested_action=suggested_action,
    )


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
