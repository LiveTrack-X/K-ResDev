from __future__ import annotations

from collections import Counter
from pathlib import Path

from .models import ApprovalRecord, EvidenceItem


def generate_evidence_bundle_index(
    evidence_items: list[EvidenceItem],
    approval_records: list[ApprovalRecord] | None = None,
    output_path: str | Path | None = None,
) -> str:
    """Render an audit-friendly evidence bundle index without copying raw files."""

    approvals = approval_records or []
    evidence_by_id = {item.evidence_id: item for item in evidence_items}
    approved_evidence = {
        evidence_id
        for record in approvals
        if record.decision == "approved"
        for evidence_id in record.evidence_ids
    }
    unresolved = [item for item in evidence_items if item.status != "accepted" or item.risk_flags]
    type_counts = Counter(str(item.evidence_type) for item in evidence_items)

    lines = [
        "# Evidence Bundle Index",
        "",
        "> Index projection only. This does not copy, alter, or certify raw evidence files.",
        "",
        "## Summary",
        "",
        f"- Evidence items: {len(evidence_items)}",
        f"- Accepted evidence: {sum(1 for item in evidence_items if item.status == 'accepted')}",
        f"- Unresolved or risk-flagged evidence: {len(unresolved)}",
        f"- Approval records supplied: {len(approvals)}",
        "",
        "| Evidence Type | Count |",
        "|---|---|",
    ]
    if not type_counts:
        lines.append("| needs_evidence | 0 |")
    for evidence_type, count in sorted(type_counts.items()):
        lines.append(f"| {_escape(evidence_type)} | {count} |")

    lines.extend(
        [
            "",
            "## Evidence Items",
            "",
            "| Evidence | Type | Status | Source | Provenance | Approval Hint | Claim | Risk Flags |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    if not evidence_items:
        lines.append("| needs_evidence | needs_review | missing | needs_review | needs_review | missing | No evidence supplied. | evidence_missing |")
    for item in sorted(evidence_items, key=lambda value: value.evidence_id):
        lines.append(
            "| {evidence} | {etype} | {status} | {source} | {provenance} | {approval} | {claim} | {risk} |".format(
                evidence=_escape(item.evidence_id),
                etype=_escape(str(item.evidence_type)),
                status=_escape(str(item.status)),
                source=_escape(item.source_file),
                provenance=_escape(_provenance_hint(item)),
                approval="approved" if item.evidence_id in approved_evidence else "needs_review",
                claim=_escape(item.claim),
                risk=_escape(", ".join(item.risk_flags) or "-"),
            )
        )

    lines.extend(["", "## Unresolved Review Items", ""])
    if not unresolved:
        lines.append("- None detected from indexed metadata.")
    for item in sorted(unresolved, key=lambda value: value.evidence_id):
        reason = []
        if item.status != "accepted":
            reason.append(f"status={item.status}")
        if item.risk_flags:
            reason.append("risk_flags=" + ",".join(item.risk_flags))
        lines.append(f"- `{item.evidence_id}`: {_escape('; '.join(reason))}")

    unknown_approved_ids = sorted(evidence_id for evidence_id in approved_evidence if evidence_id not in evidence_by_id)
    if unknown_approved_ids:
        lines.extend(["", "## Approval Records Referencing Missing Evidence", ""])
        for evidence_id in unknown_approved_ids:
            lines.append(f"- `{evidence_id}`")
    lines.append("")

    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def _provenance_hint(item: EvidenceItem) -> str:
    provenance = item.provenance
    parts: list[str] = []
    if provenance.page is not None:
        parts.append(f"page {provenance.page}")
    if provenance.sheet:
        parts.append(f"sheet {provenance.sheet}")
    if provenance.cell_range:
        parts.append(f"cell {provenance.cell_range}")
    if provenance.line_range:
        parts.append(f"line {provenance.line_range}")
    if provenance.quote:
        parts.append("quote")
    return ", ".join(parts) or "needs_review"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
