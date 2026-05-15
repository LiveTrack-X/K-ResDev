from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path

from .models import Confidence, EvidenceItem, EvidenceStatus, EvidenceType, ExtractedDocument, ExtractedSegment, Provenance

KPI_LINE_RE = re.compile(
    r"(?:KPI|성과지표|지표)\s*[:：-]?\s*(?P<name>[^,\n;]+?)\s*(?:target|목표|기준)?\s*[:：]?\s*(?P<value>\d+(?:\.\d+)?%?)",
    re.IGNORECASE,
)
MILESTONE_LINE_RE = re.compile(
    r"(?:milestone|마일스톤|단계|일정)\s*[:：-]?\s*(?P<name>[^,\n;]+?)(?:\s+|,\s*)(?P<date>\d{4}[-.]\d{1,2}[-.]\d{1,2})",
    re.IGNORECASE,
)
BUDGET_LINE_RE = re.compile(r"예산|연구비|비목|세목|인건비|학생인건비|장비비|재료비|budget|invoice|receipt", re.IGNORECASE)
METRIC_LINE_RE = re.compile(r"dice|iou|auc|accuracy|f1|recall|precision|loss|latency|정확도|성능|평가", re.IGNORECASE)
DECISION_LINE_RE = re.compile(r"decision|action item|decided|회의|결정|조치|담당|기한", re.IGNORECASE)
NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?%?")


def extract_evidence_items_from_document(
    document: ExtractedDocument,
    source_hash: str,
    base_suffix: str,
    project: str | None = None,
    run_date: date | None = None,
) -> list[EvidenceItem]:
    year = (run_date or date.today()).year
    items: list[EvidenceItem] = []
    for segment in document.segments:
        items.extend(_items_for_segment(segment, document.source_file, source_hash, base_suffix, year, project))
    return _dedupe_items(items)


def _items_for_segment(
    segment: ExtractedSegment,
    source_file: str,
    source_hash: str,
    base_suffix: str,
    year: int,
    project: str | None,
) -> list[EvidenceItem]:
    text = segment.text.strip()
    if not text:
        return []
    candidates: list[EvidenceItem] = []
    kpi_match = KPI_LINE_RE.search(text)
    if kpi_match:
        candidates.append(
            _item(
                year,
                base_suffix,
                "KPI",
                source_file,
                source_hash,
                EvidenceType.KPI,
                f"KPI candidate `{kpi_match.group('name').strip()}` has target `{kpi_match.group('value')}`.",
                {"name": kpi_match.group("name").strip(), "target": kpi_match.group("value")},
                segment,
                project,
            )
        )
    milestone_match = MILESTONE_LINE_RE.search(text)
    if milestone_match:
        candidates.append(
            _item(
                year,
                base_suffix,
                "MS",
                source_file,
                source_hash,
                EvidenceType.MILESTONE,
                f"Milestone candidate `{milestone_match.group('name').strip()}` is dated `{milestone_match.group('date')}`.",
                {"name": milestone_match.group("name").strip(), "due_date": milestone_match.group("date").replace(".", "-")},
                segment,
                project,
            )
        )
    if BUDGET_LINE_RE.search(text) and NUMBER_RE.search(text):
        candidates.append(
            _item(
                year,
                base_suffix,
                "BUD",
                source_file,
                source_hash,
                EvidenceType.BUDGET_EVIDENCE,
                "Budget evidence candidate extracted from document text.",
                {"raw_numbers": NUMBER_RE.findall(text)},
                segment,
                project,
            )
        )
    if METRIC_LINE_RE.search(text) and NUMBER_RE.search(text):
        candidates.append(
            _item(
                year,
                base_suffix,
                "MET",
                source_file,
                source_hash,
                EvidenceType.EXPERIMENT_RESULT,
                "Metric/result evidence candidate extracted from document text.",
                {"raw_numbers": NUMBER_RE.findall(text)},
                segment,
                project,
            )
        )
    if DECISION_LINE_RE.search(text):
        candidates.append(
            _item(
                year,
                base_suffix,
                "DEC",
                source_file,
                source_hash,
                EvidenceType.MEETING_DECISION,
                "Decision/action evidence candidate extracted from document text.",
                {},
                segment,
                project,
            )
        )
    return candidates


def _item(
    year: int,
    base_suffix: str,
    kind: str,
    source_file: str,
    source_hash: str,
    evidence_type: EvidenceType,
    claim: str,
    value: dict[str, object],
    segment: ExtractedSegment,
    project: str | None,
) -> EvidenceItem:
    segment_hash = hashlib.sha256(f"{kind}|{segment.text}|{segment.line_range}|{segment.cell_range}|{segment.page}".encode("utf-8")).hexdigest()
    evidence_id = f"EVI-{year}-{(base_suffix + segment_hash)[:10].upper()}"
    return EvidenceItem(
        evidence_id=evidence_id,
        source_file=source_file,
        source_hash=source_hash,
        evidence_type=evidence_type,
        project=project,
        claim=claim,
        value=value,
        confidence=Confidence.MEDIUM,
        status=EvidenceStatus.NEEDS_REVIEW,
        risk_flags=["auto_extracted", "needs_human_review", "provenance_candidate"],
        provenance=Provenance(
            page=segment.page,
            sheet=segment.sheet,
            cell_range=segment.cell_range,
            line_range=segment.line_range,
            quote=segment.quote or segment.text[:500],
        ),
    )


def _dedupe_items(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[str] = set()
    unique: list[EvidenceItem] = []
    for item in items:
        key = f"{item.evidence_type}|{Path(item.source_file).as_posix()}|{item.provenance.line_range}|{item.provenance.cell_range}|{item.provenance.page}|{item.claim}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
