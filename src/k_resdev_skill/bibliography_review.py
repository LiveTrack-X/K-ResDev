from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .models import BibliographyReviewDecision, BibliographyReviewRecord


def create_bibliography_review_record(
    bibliography_id: str,
    decision: str | BibliographyReviewDecision,
    reviewer: str,
    citation_key: str | None = None,
    paper_id: str | None = None,
    notes: str | None = None,
    risk_flags: list[str] | None = None,
    reviewed_at: str | None = None,
) -> BibliographyReviewRecord:
    """Create a supplied human bibliography metadata review decision."""

    reviewed = reviewed_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    decision_value = BibliographyReviewDecision(decision)
    review_id = _review_id(bibliography_id, decision_value.value, reviewer, reviewed)
    return BibliographyReviewRecord(
        review_id=review_id,
        bibliography_id=bibliography_id,
        decision=decision_value,
        reviewer=reviewer,
        reviewed_at=reviewed,
        citation_key=citation_key,
        paper_id=paper_id,
        notes=notes,
        risk_flags=risk_flags or [],
    )


def write_bibliography_review_record(
    record: BibliographyReviewRecord,
    reviews_dir: str | Path = "state/bibliography-reviews",
) -> Path:
    target_dir = Path(reviews_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{record.review_id}.json"
    target.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


def load_bibliography_review_records(path: str | Path) -> list[BibliographyReviewRecord]:
    source = Path(path)
    if source.is_dir():
        records: list[BibliographyReviewRecord] = []
        for record_path in sorted(source.glob("*.json")):
            records.extend(load_bibliography_review_records(record_path))
        return records
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [BibliographyReviewRecord.model_validate(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [BibliographyReviewRecord.model_validate(item) for item in payload["items"]]
    return [BibliographyReviewRecord.model_validate(payload)]


def latest_bibliography_review(
    records: list[BibliographyReviewRecord],
    bibliography_id: str,
) -> BibliographyReviewRecord | None:
    matches = [record for record in records if record.bibliography_id == bibliography_id]
    return max(matches, key=lambda record: record.reviewed_at, default=None)


def bibliography_review_status(
    records: list[BibliographyReviewRecord],
    bibliography_id: str,
) -> dict[str, object]:
    latest = latest_bibliography_review(records, bibliography_id)
    if latest is None:
        return {
            "bibliography_id": bibliography_id,
            "accepted": False,
            "decision": "missing",
            "message": "No bibliography review record found.",
            "review_id": None,
        }
    accepted = latest.decision == BibliographyReviewDecision.ACCEPTED.value
    return {
        "bibliography_id": latest.bibliography_id,
        "accepted": accepted,
        "decision": latest.decision,
        "message": "Human bibliography metadata review recorded." if accepted else "Latest human review does not accept this bibliography entry.",
        "review_id": latest.review_id,
        "reviewer": latest.reviewer,
        "reviewed_at": latest.reviewed_at,
        "citation_key": latest.citation_key,
        "paper_id": latest.paper_id,
    }


def generate_bibliography_review_summary(
    records: list[BibliographyReviewRecord],
    output_path: str | Path | None = None,
) -> str:
    lines = [
        "# Bibliography Review Summary",
        "",
        "> Human bibliography metadata review log only. This records supplied review decisions; it does not certify citation correctness or paper relevance.",
        "",
        "| Review | Bibliography ID | Citation Key | Paper ID | Decision | Reviewer | Reviewed At | Risk Flags |",
        "|---|---|---|---|---|---|---|---|",
    ]
    if not records:
        lines.append("| needs_review | needs_review | - | - | missing | needs_review | needs_review | bibliography_review_missing |")
    for record in sorted(records, key=lambda item: (item.bibliography_id, item.reviewed_at)):
        lines.append(
            "| {review} | {bib_id} | {key} | {paper_id} | {decision} | {reviewer} | {reviewed} | {risk} |".format(
                review=_escape(record.review_id),
                bib_id=_escape(record.bibliography_id),
                key=_escape(record.citation_key or "-"),
                paper_id=_escape(record.paper_id or "-"),
                decision=_escape(str(record.decision)),
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


def _review_id(bibliography_id: str, decision: str, reviewer: str, reviewed_at: str) -> str:
    digest = hashlib.sha256(f"{bibliography_id}|{decision}|{reviewer}|{reviewed_at}".encode("utf-8")).hexdigest()
    year = reviewed_at[:4] if reviewed_at[:4].isdigit() else datetime.now(UTC).strftime("%Y")
    return f"BIBREV-{year}-{digest[:8].upper()}"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
