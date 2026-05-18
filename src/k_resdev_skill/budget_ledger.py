from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from .evidence_index import load_evidence_index
from .models import BudgetLedgerFinding, BudgetLedgerImportResult, BudgetLedgerItem, EvidenceItem, WorkspaceBudgetLedgerResult

SUPPORTED_LEDGER_SUFFIXES = {".csv": "csv", ".json": "json"}
REVIEW_STATUSES = {"needs_review", "accepted", "rejected", "superseded"}


def import_budget_ledger(
    ledger_file: str | Path,
    state_dir: str | Path = "state",
    markdown_path: str | Path | None = None,
) -> BudgetLedgerImportResult:
    """Import a supplied local budget ledger without editing the raw file."""

    source = Path(ledger_file)
    items = parse_budget_ledger_file(source)
    source_hash = _sha256_file(source)
    source_format = _detect_format(source)
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)
    json_path = state / "budget-ledger.json"
    md_path = Path(markdown_path) if markdown_path is not None else state / "budget-ledger.md"

    normalized_items = []
    for item in items:
        update: dict[str, object] = {}
        if not item.source_file:
            update["source_file"] = str(source)
        if not item.source_hash:
            update["source_hash"] = source_hash
        normalized_items.append(item.model_copy(update=update))

    write_budget_ledger(normalized_items, json_path, source_file=str(source), source_hash=source_hash, source_format=source_format)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_budget_ledger_markdown(normalized_items, source_file=source, source_format=source_format), encoding="utf-8")

    return BudgetLedgerImportResult(
        source_file=str(source),
        source_hash=source_hash,
        source_format=source_format,
        item_count=len(normalized_items),
        ledger_json_path=str(json_path),
        ledger_markdown_path=str(md_path),
        warnings=_import_warnings(normalized_items),
    )


def parse_budget_ledger_file(ledger_file: str | Path) -> list[BudgetLedgerItem]:
    source = Path(ledger_file)
    if not source.exists():
        raise FileNotFoundError(f"Budget ledger file does not exist: {source}")
    if not source.is_file():
        raise ValueError(f"Budget ledger path is not a file: {source}")
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
            raise ValueError("Budget ledger JSON must be an object, list, or object with an items list.")
    return [_ledger_item_from_row(row, source, index) for index, row in enumerate(rows, start=1) if isinstance(row, dict)]


def load_budget_ledger(path: str | Path) -> list[BudgetLedgerItem]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("Budget ledger must be a JSON list or an object with an items list.")
    return [BudgetLedgerItem.model_validate(item) for item in items]


def write_budget_ledger(
    items: list[BudgetLedgerItem],
    json_path: str | Path,
    source_file: str | None = None,
    source_hash: str | None = None,
    source_format: str | None = None,
) -> Path:
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = sorted(items, key=lambda item: item.ledger_id)
    payload = {
        "generated_by": "k-resdev-skill",
        "source_file": source_file,
        "source_hash": source_hash,
        "source_format": source_format,
        "item_count": len(records),
        "items": [item.model_dump(mode="json") for item in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def generate_workspace_budget_ledger(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceBudgetLedgerResult:
    """Check budget ledger completeness and evidence links without inferring eligibility."""

    workspace = Path(root)
    ledger_path = workspace / "state" / "budget-ledger.json"
    evidence_path = workspace / "state" / "evidence-index.json"
    warnings: list[str] = []
    findings: list[BudgetLedgerFinding] = []
    items: list[BudgetLedgerItem] = []
    evidence_by_id: dict[str, EvidenceItem] = {}

    if evidence_path.exists():
        try:
            evidence_by_id = {item.evidence_id: item for item in load_evidence_index(evidence_path)}
        except Exception as exc:
            warnings.append(f"evidence_index_unreadable:{exc}")
            findings.append(
                _finding(
                    "budget_ledger_evidence_index_unreadable",
                    "high",
                    f"Evidence index could not be read: {exc}",
                    path=evidence_path,
                    suggested_action="Regenerate the evidence index before relying on budget ledger links.",
                )
            )

    if not ledger_path.exists():
        budget_evidence = [item for item in evidence_by_id.values() if str(item.evidence_type) == "budget_evidence"]
        if budget_evidence:
            findings.append(
                _finding(
                    "budget_ledger_missing",
                    "medium",
                    "Budget evidence exists but no budget ledger was found.",
                    path=ledger_path,
                    suggested_action="Import or create state/budget-ledger.json for reviewable amount/proof tracking.",
                )
            )
            return _result(workspace, "needs_review", [], findings, output_path, json_path, warnings)
        return _result(workspace, "not_configured", [], [], output_path, json_path, warnings)

    try:
        items = load_budget_ledger(ledger_path)
    except Exception as exc:
        findings.append(
            _finding(
                "budget_ledger_unreadable",
                "high",
                f"Budget ledger could not be read: {exc}",
                path=ledger_path,
                suggested_action="Fix state/budget-ledger.json or re-import the ledger.",
            )
        )
        return _result(workspace, "blocked", [], findings, output_path, json_path, warnings)

    if not items:
        findings.append(
            _finding(
                "budget_ledger_empty",
                "low",
                "Budget ledger is present but contains no items.",
                path=ledger_path,
                suggested_action="Add ledger rows when budget evidence becomes available.",
            )
        )

    linked_budget_evidence: set[str] = set()
    for item in items:
        findings.extend(_item_findings(item, evidence_by_id, ledger_path))
        for evidence_id in item.evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is not None and str(evidence.evidence_type) == "budget_evidence":
                linked_budget_evidence.add(evidence_id)

    for finding in _duplicate_findings(items, ledger_path):
        findings.append(finding)

    for evidence in evidence_by_id.values():
        if str(evidence.evidence_type) == "budget_evidence" and evidence.evidence_id not in linked_budget_evidence:
            findings.append(
                _finding(
                    "budget_evidence_not_in_ledger",
                    "medium",
                    f"Budget evidence `{evidence.evidence_id}` is not linked from any ledger item.",
                    path=ledger_path,
                    suggested_action="Link the budget evidence ID from a ledger item or explain why it is out of scope.",
                )
            )

    return _result(workspace, _status_from_findings(findings), items, findings, output_path, json_path, warnings)


def render_budget_ledger_markdown(
    items: list[BudgetLedgerItem],
    source_file: str | Path | None = None,
    source_format: str | None = None,
) -> str:
    lines = [
        "# Budget Evidence Ledger",
        "",
        "> Generic budget ledger projection only. It summarizes supplied local budget metadata; it does not infer official eligibility, reimbursement validity, or agency compliance.",
        "",
    ]
    if source_file is not None:
        lines.append(f"- Source file: `{source_file}`")
    if source_format is not None:
        lines.append(f"- Source format: `{source_format}`")
    lines.extend(
        [
            f"- Item count: {len(items)}",
            "",
            "| Ledger ID | Date | Vendor | Amount | Currency | Category | Proof Type | Approval Reference | Evidence IDs | Status | Risk Flags |",
            "|---|---|---|---:|---|---|---|---|---|---|---|",
        ]
    )
    if not items:
        lines.append("| needs_ledger | - | - | - | - | - | - | - | - | needs_review | budget_ledger_empty |")
    for item in sorted(items, key=lambda value: value.ledger_id):
        lines.append(
            "| {ledger_id} | {date} | {vendor} | {amount} | {currency} | {category} | {proof} | {approval} | {evidence} | {status} | {risk} |".format(
                ledger_id=_escape(item.ledger_id),
                date=_escape(item.date or "-"),
                vendor=_escape(item.vendor or "-"),
                amount=_format_amount(item.amount),
                currency=_escape(item.currency or "-"),
                category=_escape(item.category or "-"),
                proof=_escape(item.proof_type or "-"),
                approval=_escape(item.approval_reference or "-"),
                evidence=_escape(", ".join(item.evidence_ids) or "-"),
                status=_escape(item.review_status),
                risk=_escape(", ".join(item.risk_flags) or "-"),
            )
        )
    lines.extend(["", "## Rollups", ""])
    for currency, amount in _total_by_currency(items).items():
        lines.append(f"- {currency}: {_format_amount(amount)}")
    if not items:
        lines.append("- -")
    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- Missing proof or approval references are review findings, not official eligibility decisions.",
            "- Category labels are project/profile labels until verified against official guidance.",
            "- Keep raw receipts, invoices, card statements, approvals, and settlement files unchanged.",
            "",
        ]
    )
    return "\n".join(lines)


def render_budget_ledger_integrity_markdown(result: WorkspaceBudgetLedgerResult) -> str:
    lines = [
        "# Budget Ledger Integrity",
        "",
        "> Budget integrity projection only. This checks supplied local ledger metadata and evidence links; it does not certify official cost eligibility or agency compliance.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Ledger count | {result.ledger_count} |",
        f"| Linked evidence count | {result.linked_evidence_count} |",
        f"| Findings | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        f"| Total by currency | {_escape(_format_counts(result.total_by_currency))} |",
        f"| Amount by category | {_escape(_format_counts(result.amount_by_category))} |",
        f"| Warnings | {_escape(', '.join(result.warnings) or '-')} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Message | Ledger ID | Path | Suggested Action |",
        "|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | budget_ledger_ready | No budget ledger findings detected. | - | - | Continue human review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {message} | {ledger_id} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                message=_escape(finding.message),
                ledger_id=_escape(finding.ledger_id or "-"),
                path=_escape(finding.path or "-"),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(["", "## Ledger", ""])
    lines.append(render_budget_ledger_markdown(result.items).split("## Rollups", 1)[0].strip())
    lines.append("")
    return "\n".join(lines)


def _ledger_item_from_row(row: dict[str, Any], source: Path, index: int) -> BudgetLedgerItem:
    normalized = {_normalize_key(key): value for key, value in row.items()}
    evidence_ids = _split_list(_get(normalized, "evidence_ids", "evidence_id", "evidence"))
    item = BudgetLedgerItem(
        ledger_id=_text(_get(normalized, "ledger_id", "id")) or _stable_ledger_id(normalized, source, index),
        date=_text(_get(normalized, "date", "transaction_date", "payment_date")),
        vendor=_text(_get(normalized, "vendor", "merchant", "supplier")),
        amount=_amount(_get(normalized, "amount", "cost", "expense")),
        currency=_text(_get(normalized, "currency")) or "KRW",
        category=_text(_get(normalized, "category", "budget_category", "cost_category")),
        proof_type=_text(_get(normalized, "proof_type", "proof", "receipt_type")),
        approval_reference=_text(_get(normalized, "approval_reference", "approval_id", "approval", "approval_ref")),
        evidence_ids=evidence_ids,
        invoice_id=_text(_get(normalized, "invoice_id", "invoice", "receipt_id")),
        source_file=_text(_get(normalized, "source_file")),
        source_hash=_text(_get(normalized, "source_hash")),
        review_status=_text(_get(normalized, "review_status", "status")) or "needs_review",
        notes=_text(_get(normalized, "notes", "note")),
        risk_flags=_split_list(_get(normalized, "risk_flags", "risk_flag")),
    )
    return item.model_copy(update={"risk_flags": _unique(item.risk_flags + _row_risk_flags(item))})


def _item_findings(
    item: BudgetLedgerItem,
    evidence_by_id: dict[str, EvidenceItem],
    ledger_path: Path,
) -> list[BudgetLedgerFinding]:
    findings: list[BudgetLedgerFinding] = []
    required_fields = {
        "date": item.date,
        "vendor": item.vendor,
        "amount": item.amount,
        "category": item.category,
        "proof_type": item.proof_type,
        "approval_reference": item.approval_reference,
    }
    for field, value in required_fields.items():
        if not _has_value(value):
            severity = "medium" if field in {"proof_type", "approval_reference"} else "low"
            findings.append(
                _finding(
                    f"budget_ledger_missing_{field}",
                    severity,
                    f"Budget ledger item `{item.ledger_id}` is missing {field}.",
                    ledger_id=item.ledger_id,
                    path=ledger_path,
                    suggested_action=f"Add {field} metadata or keep the item clearly marked needs_review.",
                )
            )
    if item.review_status not in REVIEW_STATUSES:
        findings.append(
            _finding(
                "budget_ledger_unknown_review_status",
                "medium",
                f"Budget ledger item `{item.ledger_id}` has unknown review_status `{item.review_status}`.",
                ledger_id=item.ledger_id,
                path=ledger_path,
                suggested_action="Use needs_review, accepted, rejected, or superseded.",
            )
        )
    elif item.review_status != "accepted":
        severity = "high" if item.review_status in {"rejected", "superseded"} else "medium"
        findings.append(
            _finding(
                "budget_ledger_not_accepted",
                severity,
                f"Budget ledger item `{item.ledger_id}` is `{item.review_status}`.",
                ledger_id=item.ledger_id,
                path=ledger_path,
                suggested_action="Resolve or disclose ledger review status before audit-sensitive use.",
            )
        )
    if not item.evidence_ids:
        findings.append(
            _finding(
                "budget_ledger_missing_evidence_link",
                "medium",
                f"Budget ledger item `{item.ledger_id}` has no linked evidence IDs.",
                ledger_id=item.ledger_id,
                path=ledger_path,
                suggested_action="Link receipt/invoice/approval evidence IDs from the evidence index.",
            )
        )
    for evidence_id in item.evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            findings.append(
                _finding(
                    "budget_ledger_unknown_evidence",
                    "high",
                    f"Budget ledger item `{item.ledger_id}` references unknown evidence `{evidence_id}`.",
                    ledger_id=item.ledger_id,
                    path=ledger_path,
                    suggested_action="Add the evidence record or remove the stale evidence ID.",
                )
            )
        elif str(evidence.evidence_type) != "budget_evidence":
            findings.append(
                _finding(
                    "budget_ledger_non_budget_evidence",
                    "medium",
                    f"Budget ledger item `{item.ledger_id}` links non-budget evidence `{evidence_id}`.",
                    ledger_id=item.ledger_id,
                    path=ledger_path,
                    suggested_action="Link budget_evidence records for settlement/audit review.",
                )
            )
    return findings


def _duplicate_findings(items: list[BudgetLedgerItem], ledger_path: Path) -> list[BudgetLedgerFinding]:
    groups: dict[tuple[str, str, float, str], list[BudgetLedgerItem]] = {}
    for item in items:
        if not item.vendor or not item.date or item.amount is None:
            continue
        key = (item.vendor.strip().lower(), item.date.strip(), float(item.amount), item.currency.strip().upper())
        groups.setdefault(key, []).append(item)
    findings: list[BudgetLedgerFinding] = []
    for group in groups.values():
        if len(group) < 2:
            continue
        ids = ", ".join(item.ledger_id for item in group)
        findings.append(
            _finding(
                "budget_ledger_duplicate_candidate",
                "medium",
                f"Possible duplicate budget ledger items share vendor/date/amount/currency: {ids}.",
                ledger_id=group[0].ledger_id,
                path=ledger_path,
                suggested_action="Review duplicate candidates before settlement or audit use.",
            )
        )
    return findings


def _result(
    workspace: Path,
    status: str,
    items: list[BudgetLedgerItem],
    findings: list[BudgetLedgerFinding],
    output_path: str | Path | None,
    json_path: str | Path | None,
    warnings: list[str],
) -> WorkspaceBudgetLedgerResult:
    findings = _dedupe_findings(findings)
    result = WorkspaceBudgetLedgerResult(
        root=str(workspace),
        status=status,
        ledger_count=len(items),
        linked_evidence_count=len({evidence_id for item in items for evidence_id in item.evidence_ids}),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        total_by_currency=_total_by_currency(items),
        amount_by_category=_amount_by_category(items),
        items=sorted(items, key=lambda item: item.ledger_id),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_budget_ledger_integrity_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def _detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_LEDGER_SUFFIXES:
        raise ValueError(f"Unsupported budget ledger format: {path.suffix or path.name}")
    return SUPPORTED_LEDGER_SUFFIXES[suffix]


def _stable_ledger_id(row: dict[str, Any], source: Path, index: int) -> str:
    basis = "|".join(str(row.get(key) or "") for key in ("date", "vendor", "amount", "invoice_id", "evidence_ids"))
    digest = hashlib.sha1(f"{source}|{index}|{basis}".encode("utf-8")).hexdigest()[:10].upper()
    return f"BUD-{digest}"


def _row_risk_flags(item: BudgetLedgerItem) -> list[str]:
    flags: list[str] = []
    if not item.proof_type:
        flags.append("proof_type_missing")
    if not item.approval_reference:
        flags.append("approval_reference_missing")
    if not item.evidence_ids:
        flags.append("evidence_link_missing")
    return flags


def _total_by_currency(items: list[BudgetLedgerItem]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in items:
        if item.amount is None:
            continue
        currency = (item.currency or "UNKNOWN").upper()
        totals[currency] = round(totals.get(currency, 0.0) + float(item.amount), 6)
    return dict(sorted(totals.items()))


def _amount_by_category(items: list[BudgetLedgerItem]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in items:
        if item.amount is None:
            continue
        category = item.category or "uncategorized"
        key = f"{(item.currency or 'UNKNOWN').upper()}:{category}"
        totals[key] = round(totals.get(key, 0.0) + float(item.amount), 6)
    return dict(sorted(totals.items()))


def _status_from_findings(findings: list[BudgetLedgerFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    return "ready"


def _finding(
    code: str,
    severity: str,
    message: str,
    ledger_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> BudgetLedgerFinding:
    return BudgetLedgerFinding(
        code=code,
        severity=severity,
        message=message,
        ledger_id=ledger_id,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _dedupe_findings(findings: list[BudgetLedgerFinding]) -> list[BudgetLedgerFinding]:
    seen: set[tuple[str, str, str | None, str | None]] = set()
    result: list[BudgetLedgerFinding] = []
    for finding in findings:
        key = (finding.code, finding.message, finding.ledger_id, finding.path)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.code, item.message))


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _import_warnings(items: list[BudgetLedgerItem]) -> list[str]:
    warnings: list[str] = []
    if not items:
        warnings.append("no_budget_ledger_items_detected")
    for item in items:
        warnings.extend(item.risk_flags)
    return _unique(warnings)


def _get(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _normalize_key(value: object) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _amount(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace(";", ",").split(",") if part.strip()]


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip() != "needs_review"
    return True


def _format_amount(value: float | None) -> str:
    if value is None:
        return "-"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _format_counts(counts: dict[str, float]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"{key}: {_format_amount(value)}" for key, value in counts.items())


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
