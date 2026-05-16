from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .models import ApprovalDecision, ApprovalRecord, ApprovalTargetType


def create_approval_record(
    target_type: str | ApprovalTargetType,
    target_id: str,
    decision: str | ApprovalDecision,
    reviewer: str,
    evidence_ids: list[str] | None = None,
    target_path: str | None = None,
    notes: str | None = None,
    risk_flags: list[str] | None = None,
    reviewed_at: str | None = None,
) -> ApprovalRecord:
    """Create a human decision record without changing the target artifact."""

    reviewed = reviewed_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    target_type_value = ApprovalTargetType(target_type)
    decision_value = ApprovalDecision(decision)
    approval_id = _approval_id(target_type_value.value, target_id, decision_value.value, reviewer, reviewed)
    return ApprovalRecord(
        approval_id=approval_id,
        target_type=target_type_value,
        target_id=target_id,
        target_path=target_path,
        decision=decision_value,
        reviewer=reviewer,
        reviewed_at=reviewed,
        evidence_ids=evidence_ids or [],
        notes=notes,
        risk_flags=risk_flags or [],
    )


def write_approval_record(record: ApprovalRecord, approvals_dir: str | Path = "state/approvals") -> Path:
    target_dir = Path(approvals_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{record.approval_id}.json"
    target.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


def load_approval_records(path: str | Path) -> list[ApprovalRecord]:
    source = Path(path)
    if source.is_dir():
        records: list[ApprovalRecord] = []
        for record_path in sorted(source.glob("*.json")):
            records.extend(load_approval_records(record_path))
        return records
    payload = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [ApprovalRecord.model_validate(item) for item in payload]
    if isinstance(payload, dict) and "items" in payload:
        return [ApprovalRecord.model_validate(item) for item in payload["items"]]
    return [ApprovalRecord.model_validate(payload)]


def latest_approval_for_target(
    records: list[ApprovalRecord],
    target_type: str | ApprovalTargetType,
    target_id: str,
) -> ApprovalRecord | None:
    target_type_value = ApprovalTargetType(target_type).value
    matches = [
        record
        for record in records
        if str(record.target_type) == target_type_value and record.target_id == target_id
    ]
    return max(matches, key=lambda record: record.reviewed_at, default=None)


def approval_gate_status(
    records: list[ApprovalRecord],
    target_type: str | ApprovalTargetType,
    target_id: str,
) -> dict[str, object]:
    latest = latest_approval_for_target(records, target_type, target_id)
    if latest is None:
        return {
            "target_type": ApprovalTargetType(target_type).value,
            "target_id": target_id,
            "approved": False,
            "decision": "missing",
            "message": "No approval record found for target.",
            "approval_id": None,
        }
    approved = latest.decision == ApprovalDecision.APPROVED.value
    return {
        "target_type": latest.target_type,
        "target_id": latest.target_id,
        "approved": approved,
        "decision": latest.decision,
        "message": "Human approval recorded." if approved else "Latest human decision does not approve this target.",
        "approval_id": latest.approval_id,
        "reviewer": latest.reviewer,
        "reviewed_at": latest.reviewed_at,
    }


def generate_approval_summary(
    records: list[ApprovalRecord],
    output_path: str | Path | None = None,
) -> str:
    lines = [
        "# Approval Summary",
        "",
        "> Human decision log only. This file records supplied review decisions; it does not approve anything by itself.",
        "",
        "| Approval | Target | Decision | Reviewer | Reviewed At | Evidence | Risk Flags |",
        "|---|---|---|---|---|---|---|",
    ]
    if not records:
        lines.append("| needs_approval | needs_review | missing | needs_review | needs_review | needs_evidence | approval_missing |")
    for record in sorted(records, key=lambda item: (item.target_type, item.target_id, item.reviewed_at)):
        lines.append(
            "| {approval} | {target} | {decision} | {reviewer} | {reviewed} | {evidence} | {risk} |".format(
                approval=_escape(record.approval_id),
                target=_escape(f"{record.target_type}:{record.target_id}"),
                decision=_escape(str(record.decision)),
                reviewer=_escape(record.reviewer),
                reviewed=_escape(record.reviewed_at),
                evidence=_escape(", ".join(record.evidence_ids) or "needs_evidence"),
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


def _approval_id(target_type: str, target_id: str, decision: str, reviewer: str, reviewed_at: str) -> str:
    digest = hashlib.sha256(f"{target_type}|{target_id}|{decision}|{reviewer}|{reviewed_at}".encode("utf-8")).hexdigest()
    year = reviewed_at[:4] if reviewed_at[:4].isdigit() else datetime.now(UTC).strftime("%Y")
    return f"APR-{year}-{digest[:8].upper()}"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
