from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .bibliography import load_bibliography_index
from .bibliography_integrity import extract_markdown_citation_keys
from .models import (
    BibliographyEntry,
    CitationSupportDecision,
    CitationSupportFinding,
    CitationSupportRecord,
    WorkspaceCitationSupportResult,
)

CITATION_SUPPORT_OPERATIONAL_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "artifact-authority.md",
    "bibliography-integrity.md",
    "bibliography-review-summary.md",
    "budget-ledger.md",
    "budget-checklist.md",
    "checkpoint-resume-plan.md",
    "citation-support.md",
    "citation-support-summary.md",
    "evidence-bundle-index.md",
    "goals-review.md",
    "next-actions.md",
    "profile-integrity.md",
    "profile-source-summary.md",
    "readiness.md",
    "reference-corpus-summary.md",
    "research-claim-matrix.md",
    "research-claims.md",
    "report-integrity.md",
    "source-verification.md",
    "trace-passport.md",
    "workspace-discovery.md",
    "workspace-dashboard.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
    "workspace-trace.md",
}
CITATION_SUPPORT_OPERATIONAL_PREFIXES = ("weekly-review-",)


def create_citation_support_record(
    bibliography_id: str,
    claim: str,
    decision: str | CitationSupportDecision,
    reviewer: str,
    citation_key: str | None = None,
    paper_id: str | None = None,
    locator: str | None = None,
    quote: str | None = None,
    evidence_ids: list[str] | None = None,
    notes: str | None = None,
    risk_flags: list[str] | None = None,
    reviewed_at: str | None = None,
) -> CitationSupportRecord:
    """Create a supplied human paper-claim support decision."""

    reviewed = reviewed_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    decision_value = CitationSupportDecision(decision)
    support_id = _support_id(bibliography_id, claim, decision_value.value, reviewer, reviewed)
    return CitationSupportRecord(
        support_id=support_id,
        bibliography_id=bibliography_id,
        citation_key=citation_key,
        paper_id=paper_id,
        claim=claim,
        decision=decision_value,
        reviewer=reviewer,
        reviewed_at=reviewed,
        locator=locator,
        quote=quote,
        evidence_ids=evidence_ids or [],
        notes=notes,
        risk_flags=risk_flags or [],
    )


def write_citation_support_record(
    record: CitationSupportRecord,
    support_dir: str | Path = "state/citation-support",
) -> Path:
    target_dir = Path(support_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{record.support_id}.json"
    target.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


def load_citation_support_records(path: str | Path) -> list[CitationSupportRecord]:
    source = Path(path)
    if source.is_dir():
        records: list[CitationSupportRecord] = []
        for record_path in sorted(source.glob("*.json")):
            records.extend(load_citation_support_records(record_path))
        return records
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [CitationSupportRecord.model_validate(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [CitationSupportRecord.model_validate(item) for item in payload["items"]]
    return [CitationSupportRecord.model_validate(payload)]


def latest_citation_support(
    records: list[CitationSupportRecord],
    bibliography_id: str,
    claim: str | None = None,
) -> CitationSupportRecord | None:
    """Return the latest supplied support decision for a bibliography entry and optional claim."""

    matches = [record for record in records if record.bibliography_id == bibliography_id]
    if claim is not None:
        matches = [record for record in matches if _normalize_claim(record.claim) == _normalize_claim(claim)]
    return max(matches, key=lambda record: record.reviewed_at, default=None)


def citation_support_status(
    records: list[CitationSupportRecord],
    bibliography_id: str,
    claim: str | None = None,
) -> dict[str, object]:
    """Summarize the latest supplied paper-claim support decision."""

    latest = latest_citation_support(records, bibliography_id, claim)
    if latest is None:
        return {
            "bibliography_id": bibliography_id,
            "claim": claim,
            "supported": False,
            "decision": "missing",
            "message": "No citation support record found.",
            "support_id": None,
        }
    supported = latest.decision in {CitationSupportDecision.SUPPORTS.value, CitationSupportDecision.PARTIALLY_SUPPORTS.value}
    return {
        "bibliography_id": latest.bibliography_id,
        "claim": latest.claim,
        "supported": supported,
        "decision": latest.decision,
        "message": "Human paper-claim support recorded." if supported else "Latest human review does not support this claim.",
        "support_id": latest.support_id,
        "reviewer": latest.reviewer,
        "reviewed_at": latest.reviewed_at,
        "citation_key": latest.citation_key,
        "paper_id": latest.paper_id,
        "locator": latest.locator,
    }


def generate_citation_support_summary(
    records: list[CitationSupportRecord],
    output_path: str | Path | None = None,
) -> str:
    lines = [
        "# Citation Support Summary",
        "",
        "> Human paper-claim support log only. This records supplied review decisions; it does not independently prove scientific truth.",
        "",
        "| Support | Bibliography ID | Citation Key | Decision | Claim | Locator | Evidence | Reviewer | Reviewed At | Risk Flags |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    if not records:
        lines.append("| needs_review | needs_review | - | missing | needs_claim | - | needs_evidence | needs_review | needs_review | citation_support_missing |")
    for record in sorted(records, key=lambda item: (item.bibliography_id, item.citation_key or "", item.reviewed_at)):
        lines.append(
            "| {support} | {bib_id} | {key} | {decision} | {claim} | {locator} | {evidence} | {reviewer} | {reviewed} | {risk} |".format(
                support=_escape(record.support_id),
                bib_id=_escape(record.bibliography_id),
                key=_escape(record.citation_key or "-"),
                decision=_escape(str(record.decision)),
                claim=_escape(record.claim),
                locator=_escape(record.locator or "-"),
                evidence=_escape(", ".join(record.evidence_ids) or "-"),
                reviewer=_escape(record.reviewer),
                reviewed=_escape(record.reviewed_at),
                risk=_escape(", ".join(record.risk_flags) or "-"),
            )
        )
    lines.append("")
    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def generate_workspace_citation_support_integrity(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceCitationSupportResult:
    """Check whether cited papers have supplied claim-support review records."""

    workspace = Path(root)
    warnings: list[str] = []
    findings: list[CitationSupportFinding] = []
    citations_by_report = _citations_by_report(workspace)
    citation_count = sum(len(keys) for keys in citations_by_report.values())
    support_records, support_warnings = _load_support_records(workspace)
    warnings.extend(support_warnings)
    entries = _load_bibliography_entries(workspace, warnings)
    entries_by_key = {entry.citation_key: entry for entry in entries if entry.citation_key}

    if not support_records and not citation_count:
        warnings.append("citation_support_not_configured")
        return _result(workspace, support_records, citation_count, findings, warnings, output_path, json_path)

    support_by_key: dict[str, list[CitationSupportRecord]] = {}
    support_by_bib: dict[str, list[CitationSupportRecord]] = {}
    for record in support_records:
        if record.citation_key:
            support_by_key.setdefault(record.citation_key, []).append(record)
            if entries and record.citation_key not in entries_by_key:
                findings.append(
                    _finding(
                        "citation_support_bibliography_missing",
                        "medium",
                        f"Citation support `{record.support_id}` references unknown citation key `@{record.citation_key}`.",
                        workspace / "state" / "bibliography-index.json",
                        citation_key=record.citation_key,
                        bibliography_id=record.bibliography_id,
                        support_id=record.support_id,
                        suggested_action="Import or repair bibliography metadata so support records resolve to reviewed papers.",
                    )
                )
        support_by_bib.setdefault(record.bibliography_id, []).append(record)

    for report_path, citation_keys in citations_by_report.items():
        for key in sorted(citation_keys):
            entry = entries_by_key.get(key)
            supports = list(support_by_key.get(key, []))
            if entry is not None:
                supports.extend(support_by_bib.get(entry.bibliography_id, []))
            supports = _dedupe_supports(supports)
            if not supports:
                findings.append(
                    _finding(
                        "citation_support_missing",
                        "medium",
                        f"Markdown citation `@{key}` has no supplied paper-claim support record.",
                        report_path,
                        citation_key=key,
                        bibliography_id=entry.bibliography_id if entry else None,
                        suggested_action="Record citation-support evidence for the specific claim before external manuscript/report use.",
                    )
                )
                continue

            decisions = {str(record.decision) for record in supports}
            strongest = _strongest_support(supports)
            if decisions <= {CitationSupportDecision.DOES_NOT_SUPPORT.value, CitationSupportDecision.SUPERSEDED.value}:
                findings.append(
                    _finding(
                        "citation_support_invalid",
                        "high",
                        f"Markdown citation `@{key}` only has negative or superseded paper-claim support decisions.",
                        report_path,
                        citation_key=key,
                        bibliography_id=entry.bibliography_id if entry else strongest.bibliography_id,
                        support_id=strongest.support_id,
                        suggested_action="Remove or replace the citation, or add reviewed support for the claim.",
                    )
                )
            elif not any(decision in decisions for decision in (CitationSupportDecision.SUPPORTS.value, CitationSupportDecision.PARTIALLY_SUPPORTS.value)):
                findings.append(
                    _finding(
                        "citation_support_unreviewed",
                        "medium",
                        f"Markdown citation `@{key}` has support records, but none marked supports or partially_supports.",
                        report_path,
                        citation_key=key,
                        bibliography_id=entry.bibliography_id if entry else strongest.bibliography_id,
                        support_id=strongest.support_id,
                        suggested_action="Human-review the citation support decision before external use.",
                    )
                )
            elif CitationSupportDecision.PARTIALLY_SUPPORTS.value in decisions and CitationSupportDecision.SUPPORTS.value not in decisions:
                findings.append(
                    _finding(
                        "citation_support_partial",
                        "low",
                        f"Markdown citation `@{key}` is marked as partially supporting the supplied claim.",
                        report_path,
                        citation_key=key,
                        bibliography_id=entry.bibliography_id if entry else strongest.bibliography_id,
                        support_id=strongest.support_id,
                        suggested_action="Check that the report/manuscript wording reflects partial support.",
                    )
                )

            for record in supports:
                if str(record.decision) in {CitationSupportDecision.SUPPORTS.value, CitationSupportDecision.PARTIALLY_SUPPORTS.value}:
                    if not record.quote and not record.locator and not record.evidence_ids:
                        findings.append(
                            _finding(
                                "citation_support_provenance_gap",
                                "low",
                                f"Citation support `{record.support_id}` lacks quote, locator, or evidence IDs.",
                                report_path,
                                citation_key=key,
                                bibliography_id=record.bibliography_id,
                                support_id=record.support_id,
                                suggested_action="Add quote, page/section locator, or supporting evidence IDs for auditability.",
                            )
                        )

    return _result(workspace, support_records, citation_count, findings, warnings, output_path, json_path)


def render_citation_support_integrity_markdown(result: WorkspaceCitationSupportResult) -> str:
    lines = [
        "# K-ResDev Citation Support",
        "",
        "> Citation-support projection only. This checks supplied paper-claim support records for cited papers; it does not independently prove scientific truth.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Support records | {result.support_count} |",
        f"| Markdown citations | {result.citation_count} |",
        f"| Finding count | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Citation Key | Bibliography ID | Support ID | Message | Path | Suggested Action |",
        "|---|---|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | ready | - | - | - | No citation-support findings detected. | - | Continue human review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {key} | {bib_id} | {support_id} | {message} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                key=_escape(finding.citation_key or "-"),
                bib_id=_escape(finding.bibliography_id or "-"),
                support_id=_escape(finding.support_id or "-"),
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
    support_records: list[CitationSupportRecord],
    citation_count: int,
    findings: list[CitationSupportFinding],
    warnings: list[str],
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> WorkspaceCitationSupportResult:
    high_count = sum(1 for finding in findings if finding.severity == "high")
    medium_count = sum(1 for finding in findings if finding.severity == "medium")
    low_count = sum(1 for finding in findings if finding.severity == "low")
    if high_count:
        status = "blocked"
    elif medium_count:
        status = "needs_review"
    elif low_count:
        status = "ready_with_notes"
    elif support_records or citation_count:
        status = "ready"
    else:
        status = "not_configured"
    result = WorkspaceCitationSupportResult(
        root=str(workspace),
        status=status,
        support_count=len(support_records),
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
        target.write_text(render_citation_support_integrity_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def _citations_by_report(workspace: Path) -> dict[Path, set[str]]:
    reports = workspace / "reports"
    result: dict[Path, set[str]] = {}
    if not reports.exists():
        return result
    for path in sorted(reports.glob("*.md"), key=lambda item: item.as_posix()):
        if _is_operational_markdown(path):
            continue
        keys = extract_markdown_citation_keys(path.read_text(encoding="utf-8", errors="replace"))
        if keys:
            result[path] = keys
    return result


def _is_operational_markdown(path: str | Path) -> bool:
    name = Path(path).name
    return name in CITATION_SUPPORT_OPERATIONAL_NAMES or any(name.startswith(prefix) for prefix in CITATION_SUPPORT_OPERATIONAL_PREFIXES)


def _load_support_records(workspace: Path) -> tuple[list[CitationSupportRecord], list[str]]:
    support_dir = workspace / "state" / "citation-support"
    if not support_dir.exists():
        return [], []
    try:
        return load_citation_support_records(support_dir), []
    except Exception as exc:
        return [], [f"citation_support_unreadable:{exc}"]


def _load_bibliography_entries(workspace: Path, warnings: list[str]) -> list[BibliographyEntry]:
    index_path = workspace / "state" / "bibliography-index.json"
    if not index_path.exists():
        if (workspace / "state" / "citation-support").exists():
            warnings.append("bibliography_index_missing_for_support_resolution")
        return []
    try:
        return load_bibliography_index(index_path)
    except Exception as exc:
        warnings.append(f"bibliography_index_unreadable_for_support_resolution:{exc}")
        return []


def _dedupe_supports(records: list[CitationSupportRecord]) -> list[CitationSupportRecord]:
    seen: set[str] = set()
    result: list[CitationSupportRecord] = []
    for record in records:
        if record.support_id in seen:
            continue
        seen.add(record.support_id)
        result.append(record)
    return result


def _strongest_support(records: list[CitationSupportRecord]) -> CitationSupportRecord:
    return max(records, key=lambda item: item.reviewed_at)


def _finding(
    code: str,
    severity: str,
    message: str,
    path: str | Path | None = None,
    citation_key: str | None = None,
    bibliography_id: str | None = None,
    support_id: str | None = None,
    suggested_action: str | None = None,
) -> CitationSupportFinding:
    return CitationSupportFinding(
        code=code,
        severity=severity,
        message=message,
        path=str(path) if path is not None else None,
        citation_key=citation_key,
        bibliography_id=bibliography_id,
        support_id=support_id,
        suggested_action=suggested_action,
    )


def _support_id(bibliography_id: str, claim: str, decision: str, reviewer: str, reviewed_at: str) -> str:
    digest = hashlib.sha256(f"{bibliography_id}|{claim}|{decision}|{reviewer}|{reviewed_at}".encode("utf-8")).hexdigest()
    year = reviewed_at[:4] if reviewed_at[:4].isdigit() else datetime.now(UTC).strftime("%Y")
    return f"CITSUP-{year}-{digest[:8].upper()}"


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


def _normalize_claim(value: str) -> str:
    return " ".join(value.split()).casefold()
