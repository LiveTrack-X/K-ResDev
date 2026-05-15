from __future__ import annotations

import re
from typing import Iterable

from .models import CheckFinding, EvidenceItem, KPI

EVIDENCE_ID_RE = re.compile(r"\b(?:EVI|DATA|INS|PAPER)-\d{4}-[A-Z0-9]{4,12}\b")
ANY_TRACKED_ID_RE = re.compile(r"\b[A-Z]{2,10}-\d{2,4}(?:-\d{1,4})?\b")
NUMERIC_RE = re.compile(r"(?<![A-Z]-)\b\d+(?:,\d{3})*(?:\.\d+)?\s*%?\b")
SUPERLATIVE_RE = re.compile(
    r"\b(best|first|only|leading|highest|lowest|unprecedented|state[- ]of[- ]the[- ]art)\b"
    r"|최고|최초|유일|세계\s*최고|국내\s*최초|압도적|획기적"
)
CLAIM_VERB_RE = re.compile(
    r"\b(achieved|reached|exceeded|surpassed|improved|reduced|validated|proved)\b"
    r"|달성|초과|상회|개선|감소|증가|검증|입증|성공"
)
OVERCLAIM_RE = re.compile(
    r"\b(achieved|met|exceeded|surpassed|satisfied|completed|successfully)\b"
    r"|달성|충족|초과|상회|완료|성공"
)
METADATA_LINE_RE = re.compile(r"^-\s*(period|project|project id|prepared by)\s*:", re.IGNORECASE)


def check_unsupported_claims(
    report_text: str,
    evidence_items: Iterable[EvidenceItem | dict],
    kpis: Iterable[KPI | dict] | None = None,
) -> list[CheckFinding]:
    """Flag unsupported or overclaimed report sentences."""

    evidence = [_to_evidence_item(item) for item in evidence_items]
    evidence_by_id = {item.evidence_id: item for item in evidence}
    kpi_by_id = {kpi.kpi_id: kpi for kpi in (_to_kpi(item) for item in (kpis or []))}
    findings: list[CheckFinding] = []

    for sentence in _iter_sentences(report_text):
        evidence_ids = EVIDENCE_ID_RE.findall(sentence)
        known_evidence_ids = [item for item in evidence_ids if item in evidence_by_id]

        for missing_id in [item for item in evidence_ids if item not in evidence_by_id]:
            findings.append(
                CheckFinding(
                    code="missing_evidence_id",
                    severity="high",
                    message=f"Referenced evidence ID is not in the evidence index: {missing_id}",
                    claim=sentence,
                    evidence_ids=[missing_id],
                    suggested_action="Add the evidence item to the index or remove the unsupported reference.",
                )
            )

        if NUMERIC_RE.search(sentence) and not known_evidence_ids:
            findings.append(
                CheckFinding(
                    code="unsupported_numeric_claim",
                    severity="high",
                    message="Numeric claim has no linked evidence ID.",
                    claim=sentence,
                    suggested_action="Attach an evidence ID or mark the number as needs_evidence.",
                )
            )

        if SUPERLATIVE_RE.search(sentence) and not known_evidence_ids:
            findings.append(
                CheckFinding(
                    code="unsupported_superlative",
                    severity="medium",
                    message="Superlative claim has no linked evidence ID.",
                    claim=sentence,
                    suggested_action="Replace the superlative with evidence-backed wording or add evidence.",
                )
            )

        if CLAIM_VERB_RE.search(sentence) and not known_evidence_ids:
            findings.append(
                CheckFinding(
                    code="missing_evidence_for_claim",
                    severity="medium",
                    message="Outcome or performance claim is not linked to evidence.",
                    claim=sentence,
                    suggested_action="Link a relevant evidence ID or downgrade the wording.",
                )
            )

        if known_evidence_ids and NUMERIC_RE.search(sentence):
            findings.extend(_numeric_mismatch_findings(sentence, known_evidence_ids, evidence_by_id))

        if OVERCLAIM_RE.search(sentence):
            findings.extend(_below_target_findings(sentence, known_evidence_ids, evidence_by_id))
            findings.extend(_kpi_mismatch_findings(sentence, evidence, kpi_by_id))

    return _dedupe(findings)


def _below_target_findings(
    sentence: str,
    evidence_ids: list[str],
    evidence_by_id: dict[str, EvidenceItem],
) -> list[CheckFinding]:
    findings: list[CheckFinding] = []
    for evidence_id in evidence_ids:
        item = evidence_by_id[evidence_id]
        if _is_below_target(item):
            findings.append(
                CheckFinding(
                    code="below_target_overclaim",
                    severity="high",
                    message="Sentence claims success while linked evidence is below target.",
                    claim=sentence,
                    evidence_ids=[evidence_id],
                    suggested_action="State the below-target result plainly and add follow-up checks.",
                )
            )
    return findings


def _kpi_mismatch_findings(
    sentence: str,
    evidence: list[EvidenceItem],
    kpi_by_id: dict[str, KPI],
) -> list[CheckFinding]:
    findings: list[CheckFinding] = []
    tracked_ids = ANY_TRACKED_ID_RE.findall(sentence)
    for tracked_id in tracked_ids:
        if tracked_id not in kpi_by_id:
            continue
        linked_below_target = [
            item.evidence_id
            for item in evidence
            if item.linked_kpi == tracked_id and _is_below_target(item)
        ]
        if linked_below_target:
            findings.append(
                CheckFinding(
                    code="kpi_mismatch",
                    severity="high",
                    message=f"KPI {tracked_id} is overclaimed while linked evidence is below target.",
                    claim=sentence,
                    evidence_ids=linked_below_target,
                    suggested_action="Update KPI status or rewrite the claim as partial/provisional.",
                )
            )
    return findings


def _numeric_mismatch_findings(
    sentence: str,
    evidence_ids: list[str],
    evidence_by_id: dict[str, EvidenceItem],
) -> list[CheckFinding]:
    claim_numbers = _claim_numbers(sentence)
    if not claim_numbers:
        return []
    evidence_numbers: list[float] = []
    for evidence_id in evidence_ids:
        evidence_numbers.extend(_nested_numbers(evidence_by_id[evidence_id].value))
    if not evidence_numbers:
        return []

    unsupported = [
        number
        for number in claim_numbers
        if not any(_numbers_match(number, evidence_number) for evidence_number in evidence_numbers)
    ]
    if not unsupported:
        return []
    return [
        CheckFinding(
            code="numeric_evidence_mismatch",
            severity="high",
            message="Numeric claim does not match numeric values in linked evidence.",
            claim=sentence,
            evidence_ids=evidence_ids,
            suggested_action="Check the report number against the evidence value or add the supporting evidence.",
        )
    ]


def _is_below_target(item: EvidenceItem) -> bool:
    if "below_target" in item.risk_flags:
        return True
    value = item.value or {}
    score = _to_float(value.get("score", value.get("actual", value.get("current"))))
    target = _to_float(value.get("target"))
    return score is not None and target is not None and score < target


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip().replace("%", ""))
    except ValueError:
        return None


def _claim_numbers(sentence: str) -> list[float]:
    without_ids = ANY_TRACKED_ID_RE.sub(" ", EVIDENCE_ID_RE.sub(" ", sentence))
    numbers: list[float] = []
    for match in NUMERIC_RE.finditer(without_ids):
        value = _to_float(match.group(0))
        if value is not None:
            numbers.append(value)
    return numbers


def _nested_numbers(value: object) -> list[float]:
    if isinstance(value, dict):
        numbers: list[float] = []
        for nested in value.values():
            numbers.extend(_nested_numbers(nested))
        return numbers
    if isinstance(value, list):
        numbers: list[float] = []
        for nested in value:
            numbers.extend(_nested_numbers(nested))
        return numbers
    number = _to_float(value)
    return [number] if number is not None else []


def _numbers_match(left: float, right: float) -> bool:
    if abs(left - right) <= 1e-9:
        return True
    if abs((left / 100.0) - right) <= 1e-9:
        return True
    if abs(left - (right * 100.0)) <= 1e-9:
        return True
    return False


def _iter_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for line in _claim_relevant_lines(text):
        if line.startswith("|"):
            sentences.append(line)
            continue
        sentences.extend(chunk.strip() for chunk in re.split(r"(?<=[.!?。])\s+", line) if chunk.strip())
    return sentences


def _claim_relevant_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith(">"):
            continue
        if METADATA_LINE_RE.match(line):
            continue
        if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", line):
            continue
        lines.append(line)
    return lines


def _to_evidence_item(item: EvidenceItem | dict) -> EvidenceItem:
    if isinstance(item, EvidenceItem):
        return item
    return EvidenceItem.model_validate(item)


def _to_kpi(item: KPI | dict) -> KPI:
    if isinstance(item, KPI):
        return item
    return KPI.model_validate(item)


def _dedupe(findings: list[CheckFinding]) -> list[CheckFinding]:
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    unique: list[CheckFinding] = []
    for finding in findings:
        key = (finding.code, finding.claim, tuple(finding.evidence_ids))
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
