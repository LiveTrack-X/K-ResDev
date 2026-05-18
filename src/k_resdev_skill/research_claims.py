from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from .bibliography import load_bibliography_index
from .citation_support import load_citation_support_records
from .evidence_index import load_evidence_index
from .models import (
    BibliographyEntry,
    CitationSupportDecision,
    CitationSupportRecord,
    EvidenceItem,
    ResearchClaim,
    ResearchClaimImportResult,
    ResearchClaimMatrixFinding,
    WorkspaceResearchClaimMatrixResult,
)

SUPPORTED_CLAIM_SUFFIXES = {".csv": "csv", ".json": "json"}
UNRESOLVED_STATUSES = {"hypothesis", "candidate", "needs_review"}
INVALID_STATUSES = {"rejected", "superseded"}


def import_research_claims(
    claim_file: str | Path,
    state_dir: str | Path = "state",
    markdown_path: str | Path | None = None,
) -> ResearchClaimImportResult:
    """Import supplied research claims into state without editing the source file."""

    source = Path(claim_file)
    claims = parse_research_claim_file(source)
    source_hash = _sha256_file(source)
    source_format = _detect_format(source)
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)
    json_path = state / "research-claims.json"
    md_path = Path(markdown_path) if markdown_path is not None else state / "research-claims.md"

    write_research_claims(claims, json_path, source_file=str(source), source_hash=source_hash, source_format=source_format)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_research_claims_markdown(claims, source_file=source, source_format=source_format), encoding="utf-8")

    return ResearchClaimImportResult(
        source_file=str(source),
        source_hash=source_hash,
        source_format=source_format,
        claim_count=len(claims),
        claims_json_path=str(json_path),
        claims_markdown_path=str(md_path),
        warnings=_import_warnings(claims),
    )


def parse_research_claim_file(claim_file: str | Path) -> list[ResearchClaim]:
    source = Path(claim_file)
    if not source.exists():
        raise FileNotFoundError(f"Research claim file does not exist: {source}")
    if not source.is_file():
        raise ValueError(f"Research claim path is not a file: {source}")
    source_format = _detect_format(source)
    if source_format == "csv":
        rows = list(csv.DictReader(source.read_text(encoding="utf-8-sig").splitlines()))
    else:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            rows = payload["items"]
        elif isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = [payload]
        else:
            raise ValueError("Research claim JSON must be an object, list, or object with an items list.")
    return [_claim_from_row(row, source, index) for index, row in enumerate(rows, start=1) if isinstance(row, dict)]


def load_research_claims(path: str | Path) -> list[ResearchClaim]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("Research claims must be a JSON list or an object with an items list.")
    return [ResearchClaim.model_validate(item) for item in items]


def write_research_claims(
    claims: list[ResearchClaim],
    json_path: str | Path,
    source_file: str | None = None,
    source_hash: str | None = None,
    source_format: str | None = None,
) -> Path:
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = sorted(claims, key=lambda claim: claim.claim_id)
    payload = {
        "generated_by": "k-resdev-skill",
        "source_file": source_file,
        "source_hash": source_hash,
        "source_format": source_format,
        "claim_count": len(records),
        "items": [claim.model_dump(mode="json") for claim in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def generate_research_claim_matrix(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceResearchClaimMatrixResult:
    """Check research claims against evidence, bibliography, and supplied citation-support records."""

    workspace = Path(root)
    warnings: list[str] = []
    findings: list[ResearchClaimMatrixFinding] = []
    claim_path = workspace / "state" / "research-claims.json"

    if not claim_path.exists():
        warnings.append("research_claims_not_configured")
        return _result(workspace, [], findings, warnings, output_path, json_path)

    try:
        claims = load_research_claims(claim_path)
    except Exception as exc:
        findings.append(
            _finding(
                "research_claims_unreadable",
                "high",
                f"Research claims could not be read: {exc}",
                path=claim_path,
                suggested_action="Fix state/research-claims.json or re-import supplied research claims.",
            )
        )
        return _result(workspace, [], findings, warnings, output_path, json_path)

    evidence_by_id = _load_evidence(workspace, warnings, findings)
    needs_bibliography = any(claim.citation_keys or claim.bibliography_ids for claim in claims)
    needs_support = any(claim.citation_keys or claim.bibliography_ids or claim.support_ids for claim in claims)
    bibliography_by_id, bibliography_by_key = _load_bibliography(workspace, warnings) if needs_bibliography else ({}, {})
    support_records = _load_support_records(workspace, warnings) if needs_support else []
    support_by_id = {record.support_id: record for record in support_records}

    for claim in claims:
        findings.extend(_claim_findings(claim, claim_path, evidence_by_id, bibliography_by_id, bibliography_by_key, support_records, support_by_id))

    return _result(workspace, claims, findings, warnings, output_path, json_path)


def render_research_claims_markdown(
    claims: list[ResearchClaim],
    source_file: str | Path | None = None,
    source_format: str | None = None,
) -> str:
    lines = [
        "# Research Claims",
        "",
        "> Claim ledger projection only. Claims remain hypotheses, candidates, or needs-review items unless supplied human review accepts them.",
        "",
    ]
    if source_file is not None:
        lines.append(f"- Source file: `{source_file}`")
    if source_format is not None:
        lines.append(f"- Source format: `{source_format}`")
    lines.extend(
        [
            f"- Claim count: {len(claims)}",
            "",
            "| Claim ID | Type | Status | Confidence | Evidence | Citations | Bibliography | Support | Risk Flags | Next Checks | Claim |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if not claims:
        lines.append("| needs_claim | research | needs_review | unknown | - | - | - | - | claim_missing | Add supplied claims. | needs_review |")
    for claim in sorted(claims, key=lambda item: item.claim_id):
        lines.append(
            "| {claim_id} | {kind} | {status} | {confidence} | {evidence} | {citations} | {bibliography} | {support} | {risk} | {checks} | {claim} |".format(
                claim_id=_escape(claim.claim_id),
                kind=_escape(claim.claim_type),
                status=_escape(str(claim.status)),
                confidence=_escape(str(claim.confidence)),
                evidence=_escape(", ".join(claim.evidence_ids) or "-"),
                citations=_escape(", ".join(f"@{key}" for key in claim.citation_keys) or "-"),
                bibliography=_escape(", ".join(claim.bibliography_ids) or "-"),
                support=_escape(", ".join(claim.support_ids) or "-"),
                risk=_escape(", ".join(claim.risk_flags) or "-"),
                checks=_escape("; ".join(claim.next_checks) or "-"),
                claim=_escape(claim.claim),
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_research_claim_matrix_markdown(result: WorkspaceResearchClaimMatrixResult) -> str:
    lines = [
        "# K-ResDev Research Claim Matrix",
        "",
        "> Research-claim projection only. This checks supplied claim records against local evidence, bibliography, and citation-support metadata; it does not establish scientific truth.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Research claims | {result.claim_count} |",
        f"| Finding count | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        f"| Warnings | {_escape(', '.join(result.warnings) or '-')} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Claim ID | Evidence | Citation | Bibliography | Support | Message | Path | Suggested Action |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | research_claim_matrix_ready | - | - | - | - | - | No research-claim matrix findings detected. | - | Continue human review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {claim_id} | {evidence} | {citation} | {bibliography} | {support} | {message} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                claim_id=_escape(finding.claim_id or "-"),
                evidence=_escape(finding.evidence_id or "-"),
                citation=_escape(f"@{finding.citation_key}" if finding.citation_key else "-"),
                bibliography=_escape(finding.bibliography_id or "-"),
                support=_escape(finding.support_id or "-"),
                message=_escape(finding.message),
                path=_escape(finding.path or "-"),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Claims",
            "",
            "| Claim ID | Type | Status | Confidence | Evidence | Citations | Bibliography | Support | Risk Flags | Next Checks | Claim |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    if not result.claims:
        lines.append("| needs_claim | research | needs_review | unknown | - | - | - | - | claim_missing | Add supplied claims. | needs_review |")
    for claim in result.claims:
        lines.append(
            "| {claim_id} | {kind} | {status} | {confidence} | {evidence} | {citations} | {bibliography} | {support} | {risk} | {checks} | {claim} |".format(
                claim_id=_escape(claim.claim_id),
                kind=_escape(claim.claim_type),
                status=_escape(str(claim.status)),
                confidence=_escape(str(claim.confidence)),
                evidence=_escape(", ".join(claim.evidence_ids) or "-"),
                citations=_escape(", ".join(f"@{key}" for key in claim.citation_keys) or "-"),
                bibliography=_escape(", ".join(claim.bibliography_ids) or "-"),
                support=_escape(", ".join(claim.support_ids) or "-"),
                risk=_escape(", ".join(claim.risk_flags) or "-"),
                checks=_escape("; ".join(claim.next_checks) or "-"),
                claim=_escape(claim.claim),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _claim_findings(
    claim: ResearchClaim,
    claim_path: Path,
    evidence_by_id: dict[str, EvidenceItem],
    bibliography_by_id: dict[str, BibliographyEntry],
    bibliography_by_key: dict[str, BibliographyEntry],
    support_records: list[CitationSupportRecord],
    support_by_id: dict[str, CitationSupportRecord],
) -> list[ResearchClaimMatrixFinding]:
    findings: list[ResearchClaimMatrixFinding] = []
    status = str(claim.status)
    if status in INVALID_STATUSES:
        findings.append(
            _finding(
                "research_claim_invalid_status",
                "high",
                f"Research claim `{claim.claim_id}` is `{status}`.",
                claim_id=claim.claim_id,
                path=claim_path,
                suggested_action="Do not use rejected or superseded claims in downstream reports or manuscripts.",
            )
        )
    elif status in UNRESOLVED_STATUSES:
        findings.append(
            _finding(
                "research_claim_unresolved",
                "medium",
                f"Research claim `{claim.claim_id}` is `{status}`.",
                claim_id=claim.claim_id,
                path=claim_path,
                suggested_action="Keep the claim as a hypothesis/candidate or record supplied human acceptance before external use.",
            )
        )

    if claim.risk_flags:
        findings.append(
            _finding(
                "research_claim_risk_flags",
                "low",
                f"Research claim `{claim.claim_id}` has risk flags: {', '.join(claim.risk_flags)}.",
                claim_id=claim.claim_id,
                path=claim_path,
                suggested_action="Resolve or disclose risk flags before using this claim externally.",
            )
        )

    if not claim.evidence_ids:
        findings.append(
            _finding(
                "research_claim_missing_evidence",
                "medium",
                f"Research claim `{claim.claim_id}` has no evidence IDs.",
                claim_id=claim.claim_id,
                path=claim_path,
                suggested_action="Link local evidence IDs or keep the claim explicitly marked as a hypothesis.",
            )
        )
    for evidence_id in claim.evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            findings.append(
                _finding(
                    "research_claim_unknown_evidence",
                    "high",
                    f"Research claim `{claim.claim_id}` references unknown evidence `{evidence_id}`.",
                    claim_id=claim.claim_id,
                    evidence_id=evidence_id,
                    path=claim_path,
                    suggested_action="Add the evidence record or remove the stale evidence ID.",
                )
            )
        elif str(evidence.status) in {"draft", "needs_review"}:
            findings.append(
                _finding(
                    "research_claim_unreviewed_evidence",
                    "medium",
                    f"Research claim `{claim.claim_id}` uses `{evidence_id}` with status `{evidence.status}`.",
                    claim_id=claim.claim_id,
                    evidence_id=evidence_id,
                    path=claim_path,
                    suggested_action="Review linked evidence before treating the claim as accepted.",
                )
            )
        elif str(evidence.status) in {"rejected", "superseded"}:
            findings.append(
                _finding(
                    "research_claim_invalid_evidence",
                    "high",
                    f"Research claim `{claim.claim_id}` uses `{evidence_id}` with status `{evidence.status}`.",
                    claim_id=claim.claim_id,
                    evidence_id=evidence_id,
                    path=claim_path,
                    suggested_action="Replace or remove invalid evidence links.",
                )
            )

    bibliography_ids = set(claim.bibliography_ids)
    for key in claim.citation_keys:
        entry = bibliography_by_key.get(key)
        if entry is None:
            findings.append(
                _finding(
                    "research_claim_unknown_citation_key",
                    "high",
                    f"Research claim `{claim.claim_id}` cites unknown citation key `@{key}`.",
                    claim_id=claim.claim_id,
                    citation_key=key,
                    path=claim_path,
                    suggested_action="Import or repair bibliography metadata for this citation key.",
                )
            )
        else:
            bibliography_ids.add(entry.bibliography_id)
    for bibliography_id in claim.bibliography_ids:
        if bibliography_id not in bibliography_by_id:
            findings.append(
                _finding(
                    "research_claim_unknown_bibliography",
                    "high",
                    f"Research claim `{claim.claim_id}` references unknown bibliography `{bibliography_id}`.",
                    claim_id=claim.claim_id,
                    bibliography_id=bibliography_id,
                    path=claim_path,
                    suggested_action="Import or repair bibliography metadata for this reference.",
                )
            )

    if not claim.citation_keys and not claim.bibliography_ids:
        severity = "medium" if claim.claim_type in {"paper", "paper_claim", "manuscript", "literature"} else "low"
        findings.append(
            _finding(
                "research_claim_missing_citation_reference",
                severity,
                f"Research claim `{claim.claim_id}` has no citation keys or bibliography IDs.",
                claim_id=claim.claim_id,
                path=claim_path,
                suggested_action="Link citation keys/bibliography IDs when the claim is intended for manuscript or literature-backed use.",
            )
        )

    matched_supports = _support_records_for_claim(claim, support_records, support_by_id, bibliography_by_key)
    if (claim.citation_keys or bibliography_ids or claim.support_ids) and not matched_supports:
        findings.append(
            _finding(
                "research_claim_support_missing",
                "medium",
                f"Research claim `{claim.claim_id}` has citation/bibliography references but no matching citation-support record.",
                claim_id=claim.claim_id,
                path=claim_path,
                suggested_action="Record supplied paper-claim support decisions before external manuscript/report use.",
            )
        )
    for support_id in claim.support_ids:
        if support_id not in support_by_id:
            findings.append(
                _finding(
                    "research_claim_unknown_support",
                    "high",
                    f"Research claim `{claim.claim_id}` references unknown citation support `{support_id}`.",
                    claim_id=claim.claim_id,
                    support_id=support_id,
                    path=claim_path,
                    suggested_action="Add the support record or remove the stale support ID.",
                )
            )
    for support in matched_supports:
        decision = str(support.decision)
        if decision in {CitationSupportDecision.DOES_NOT_SUPPORT.value, CitationSupportDecision.SUPERSEDED.value}:
            findings.append(
                _finding(
                    "research_claim_negative_support",
                    "high",
                    f"Research claim `{claim.claim_id}` is linked to support `{support.support_id}` with decision `{decision}`.",
                    claim_id=claim.claim_id,
                    citation_key=support.citation_key,
                    bibliography_id=support.bibliography_id,
                    support_id=support.support_id,
                    path=claim_path,
                    suggested_action="Revise or remove the claim, or replace the citation/support record.",
                )
            )
        elif decision == CitationSupportDecision.NEEDS_REVIEW.value:
            findings.append(
                _finding(
                    "research_claim_support_needs_review",
                    "medium",
                    f"Research claim `{claim.claim_id}` is linked to support `{support.support_id}` that still needs review.",
                    claim_id=claim.claim_id,
                    citation_key=support.citation_key,
                    bibliography_id=support.bibliography_id,
                    support_id=support.support_id,
                    path=claim_path,
                    suggested_action="Resolve the citation-support decision before external manuscript/report use.",
                )
            )
        elif decision == CitationSupportDecision.PARTIALLY_SUPPORTS.value:
            findings.append(
                _finding(
                    "research_claim_partial_support",
                    "low",
                    f"Research claim `{claim.claim_id}` is only partially supported by `{support.support_id}`.",
                    claim_id=claim.claim_id,
                    citation_key=support.citation_key,
                    bibliography_id=support.bibliography_id,
                    support_id=support.support_id,
                    path=claim_path,
                    suggested_action="Make the claim wording reflect partial support.",
                )
            )
        if support.evidence_ids and not set(support.evidence_ids).issubset(set(claim.evidence_ids)):
            findings.append(
                _finding(
                    "research_claim_support_evidence_gap",
                    "low",
                    f"Support `{support.support_id}` cites evidence not listed on research claim `{claim.claim_id}`.",
                    claim_id=claim.claim_id,
                    bibliography_id=support.bibliography_id,
                    support_id=support.support_id,
                    path=claim_path,
                    suggested_action="Synchronize claim evidence IDs with the support record or document the difference.",
                )
            )
    return findings


def _support_records_for_claim(
    claim: ResearchClaim,
    support_records: list[CitationSupportRecord],
    support_by_id: dict[str, CitationSupportRecord],
    bibliography_by_key: dict[str, BibliographyEntry],
) -> list[CitationSupportRecord]:
    matches: list[CitationSupportRecord] = []
    normalized_claim = _normalize_claim(claim.claim)
    bibliography_ids = set(claim.bibliography_ids)
    for key in claim.citation_keys:
        entry = bibliography_by_key.get(key)
        if entry is not None:
            bibliography_ids.add(entry.bibliography_id)
    for support_id in claim.support_ids:
        record = support_by_id.get(support_id)
        if record is not None:
            matches.append(record)
    for record in support_records:
        if record.support_id in {item.support_id for item in matches}:
            continue
        same_claim = _normalize_claim(record.claim) == normalized_claim
        same_key = record.citation_key is not None and record.citation_key in claim.citation_keys
        same_bib = record.bibliography_id in bibliography_ids
        if same_claim and (same_key or same_bib):
            matches.append(record)
    return sorted(matches, key=lambda item: (item.bibliography_id, item.support_id))


def _result(
    workspace: Path,
    claims: list[ResearchClaim],
    findings: list[ResearchClaimMatrixFinding],
    warnings: list[str],
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> WorkspaceResearchClaimMatrixResult:
    findings = _dedupe_findings(findings)
    result = WorkspaceResearchClaimMatrixResult(
        root=str(workspace),
        status=_status_from_findings(findings, claims),
        claim_count=len(claims),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        claims=sorted(claims, key=lambda claim: claim.claim_id),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_research_claim_matrix_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def _load_evidence(
    workspace: Path,
    warnings: list[str],
    findings: list[ResearchClaimMatrixFinding],
) -> dict[str, EvidenceItem]:
    path = workspace / "state" / "evidence-index.json"
    if not path.exists():
        warnings.append("evidence_index_missing_for_research_claims")
        return {}
    try:
        return {item.evidence_id: item for item in load_evidence_index(path)}
    except Exception as exc:
        warnings.append(f"evidence_index_unreadable_for_research_claims:{exc}")
        findings.append(
            _finding(
                "research_claim_evidence_index_unreadable",
                "high",
                f"Evidence index could not be read: {exc}",
                path=path,
                suggested_action="Regenerate the evidence index before relying on research claims.",
            )
        )
        return {}


def _load_bibliography(
    workspace: Path,
    warnings: list[str],
) -> tuple[dict[str, BibliographyEntry], dict[str, BibliographyEntry]]:
    path = workspace / "state" / "bibliography-index.json"
    if not path.exists():
        warnings.append("bibliography_index_missing_for_research_claims")
        return {}, {}
    try:
        entries = load_bibliography_index(path)
    except Exception as exc:
        warnings.append(f"bibliography_index_unreadable_for_research_claims:{exc}")
        return {}, {}
    by_id = {entry.bibliography_id: entry for entry in entries}
    by_key = {entry.citation_key: entry for entry in entries if entry.citation_key}
    return by_id, by_key


def _load_support_records(workspace: Path, warnings: list[str]) -> list[CitationSupportRecord]:
    support_dir = workspace / "state" / "citation-support"
    if not support_dir.exists():
        warnings.append("citation_support_missing_for_research_claims")
        return []
    try:
        return load_citation_support_records(support_dir)
    except Exception as exc:
        warnings.append(f"citation_support_unreadable_for_research_claims:{exc}")
        return []


def _claim_from_row(row: dict[str, Any], source: Path, index: int) -> ResearchClaim:
    normalized = {_normalize_key(key): value for key, value in row.items()}
    claim_text = _text(_get(normalized, "claim", "statement", "claim_text", "research_claim")) or "needs_review"
    claim = ResearchClaim(
        claim_id=_text(_get(normalized, "claim_id", "id")) or _stable_claim_id(claim_text, source, index),
        claim=claim_text,
        claim_type=_text(_get(normalized, "claim_type", "type", "kind")) or "research",
        evidence_ids=_split_list(_get(normalized, "evidence_ids", "evidence_id", "evidence")),
        citation_keys=[item.removeprefix("@") for item in _split_list(_get(normalized, "citation_keys", "citation_key", "citations"))],
        bibliography_ids=_split_list(_get(normalized, "bibliography_ids", "bibliography_id", "bibliography")),
        support_ids=_split_list(_get(normalized, "support_ids", "support_id", "citation_support_ids", "citation_support_id")),
        insight_ids=_split_list(_get(normalized, "insight_ids", "insight_id", "insights")),
        status=_text(_get(normalized, "status", "review_status")) or "needs_review",
        confidence=_text(_get(normalized, "confidence")) or "unknown",
        risk_flags=_split_list(_get(normalized, "risk_flags", "risk_flag")),
        next_checks=_split_list(_get(normalized, "next_checks", "next_check", "checks")),
        notes=_text(_get(normalized, "notes", "note")),
    )
    return claim.model_copy(update={"risk_flags": _unique(claim.risk_flags + _row_risk_flags(claim))})


def _finding(
    code: str,
    severity: str,
    message: str,
    claim_id: str | None = None,
    evidence_id: str | None = None,
    citation_key: str | None = None,
    bibliography_id: str | None = None,
    support_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> ResearchClaimMatrixFinding:
    return ResearchClaimMatrixFinding(
        code=code,
        severity=severity,
        message=message,
        claim_id=claim_id,
        evidence_id=evidence_id,
        citation_key=citation_key,
        bibliography_id=bibliography_id,
        support_id=support_id,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _status_from_findings(findings: list[ResearchClaimMatrixFinding], claims: list[ResearchClaim]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    if claims:
        return "ready"
    return "not_configured"


def _dedupe_findings(findings: list[ResearchClaimMatrixFinding]) -> list[ResearchClaimMatrixFinding]:
    seen: set[tuple[str, str, str | None, str | None, str | None]] = set()
    result: list[ResearchClaimMatrixFinding] = []
    for finding in findings:
        key = (finding.code, finding.message, finding.claim_id, finding.path, finding.support_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.code, item.message))


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_CLAIM_SUFFIXES:
        raise ValueError(f"Unsupported research claim format: {path.suffix or path.name}")
    return SUPPORTED_CLAIM_SUFFIXES[suffix]


def _stable_claim_id(claim: str, source: Path, index: int) -> str:
    digest = hashlib.sha1(f"{source}|{index}|{claim}".encode("utf-8")).hexdigest()[:10].upper()
    return f"RCL-{digest}"


def _row_risk_flags(claim: ResearchClaim) -> list[str]:
    flags: list[str] = []
    if str(claim.status) in UNRESOLVED_STATUSES:
        flags.append("claim_not_accepted")
    if not claim.evidence_ids:
        flags.append("evidence_missing")
    if not claim.citation_keys and not claim.bibliography_ids:
        flags.append("citation_reference_missing")
    return flags


def _import_warnings(claims: list[ResearchClaim]) -> list[str]:
    warnings: list[str] = []
    if not claims:
        warnings.append("no_research_claims_detected")
    for claim in claims:
        warnings.extend(claim.risk_flags)
    return _unique(warnings)


def _get(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _normalize_key(value: object) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_claim(value: str) -> str:
    return " ".join(value.split()).casefold()


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace(";", ",").split(",") if part.strip()]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
