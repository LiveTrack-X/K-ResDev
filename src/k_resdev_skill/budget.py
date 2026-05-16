from __future__ import annotations

from pathlib import Path

from .models import EvidenceItem

GENERIC_BUDGET_FIELDS = (
    "amount",
    "category",
    "date",
    "vendor",
    "proof_type",
    "approval_id",
)


def generate_budget_evidence_checklist(
    evidence_items: list[EvidenceItem],
    output_path: str | Path | None = None,
) -> str:
    """Create a generic budget evidence checklist without encoding agency-specific rules."""

    budget_items = [item for item in evidence_items if item.evidence_type == "budget_evidence"]
    lines = [
        "# Budget Evidence Checklist",
        "",
        "> Generic checklist only. Verify the official agency/program guidance before reimbursement, settlement, or audit submission.",
        "",
        "| Evidence | Claim | Present Fields | Missing Fields | Provenance | Status | Risk Flags |",
        "|---|---|---|---|---|---|---|",
    ]
    if not budget_items:
        lines.append("| needs_evidence | No budget evidence indexed. | - | amount, category, date, vendor, proof_type, approval_id | needs_review | needs_review | budget_evidence_missing |")
    for item in budget_items:
        present, missing = _field_presence(item)
        lines.append(
            "| {evidence} | {claim} | {present} | {missing} | {provenance} | {status} | {risk} |".format(
                evidence=_escape(item.evidence_id),
                claim=_escape(item.claim),
                present=_escape(", ".join(present) or "-"),
                missing=_escape(", ".join(missing) or "-"),
                provenance=_escape(_provenance_hint(item)),
                status=_escape(str(item.status)),
                risk=_escape(", ".join(_budget_risk_flags(item, missing)) or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- This checklist checks metadata completeness, not official eligibility.",
            "- `approval_id` is a generic placeholder for approval/change/settlement references when applicable.",
            "- Keep raw receipts, invoices, purchase records, and approval documents unchanged.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def budget_evidence_gaps(evidence_items: list[EvidenceItem]) -> dict[str, list[str]]:
    """Return missing generic budget fields by evidence ID."""

    return {
        item.evidence_id: missing
        for item in evidence_items
        if item.evidence_type == "budget_evidence"
        for _, missing in [_field_presence(item)]
        if missing
    }


def _field_presence(item: EvidenceItem) -> tuple[list[str], list[str]]:
    value = item.value or {}
    present = [field for field in GENERIC_BUDGET_FIELDS if _has_value(value.get(field))]
    missing = [field for field in GENERIC_BUDGET_FIELDS if field not in present]
    return present, missing


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip() != "needs_review"
    return True


def _budget_risk_flags(item: EvidenceItem, missing: list[str]) -> list[str]:
    flags = list(item.risk_flags)
    if missing:
        flags.append("budget_metadata_incomplete")
    if not _provenance_hint(item):
        flags.append("provenance_missing")
    return _ordered_unique(flags)


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
    return ", ".join(parts)


def _ordered_unique(values: list[str]) -> list[str]:
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
