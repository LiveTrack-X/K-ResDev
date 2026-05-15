from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from .classifier import classify_file
from .data_profiler import profile_data_file
from .document_extractors import extract_document_text
from .evidence_extraction import extract_evidence_items_from_document
from .evidence_index import write_evidence_index
from .models import (
    Confidence,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
    FileCategory,
    IntakeResult,
    SourceRecord,
)

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".jsonl", ".log", ".tsv"}
IGNORED_NAMES = {".ds_store", "thumbs.db"}

CATEGORY_TO_EVIDENCE_TYPE = {
    FileCategory.PLAN: EvidenceType.PLAN_GOAL,
    FileCategory.PROGRESS: EvidenceType.MEETING_DECISION,
    FileCategory.EXPERIMENT: EvidenceType.EXPERIMENT_RESULT,
    FileCategory.BUDGET: EvidenceType.BUDGET_EVIDENCE,
    FileCategory.OUTCOME: EvidenceType.OUTCOME,
    FileCategory.CHANGE: EvidenceType.CHANGE_REQUEST,
    FileCategory.LITERATURE: EvidenceType.PAPER_CLAIM,
    FileCategory.DATA: EvidenceType.DATA_PROFILE,
    FileCategory.UNKNOWN: EvidenceType.RISK,
}


def run_intake(
    inbox_dir: str | Path = "inbox",
    state_dir: str | Path = "state",
    evidence_dir: str | Path = "evidence",
    project: str | None = None,
    run_date: date | None = None,
) -> IntakeResult:
    """Scan inbox files and write derived registry/evidence outputs.

    This never mutates raw source files. It creates conservative `needs_review`
    evidence items so a human can decide what is actually reportable.
    """

    inbox = Path(inbox_dir)
    if not inbox.exists():
        raise FileNotFoundError(f"Inbox directory does not exist: {inbox}")
    if not inbox.is_dir():
        raise NotADirectoryError(f"Inbox path is not a directory: {inbox}")

    state = Path(state_dir)
    evidence_root = Path(evidence_dir)
    state.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)

    today = run_date or date.today()
    sources: list[SourceRecord] = []
    evidence_items: list[EvidenceItem] = []

    for path in _iter_files(inbox, excluded_roots=[state, evidence_root]):
        document = extract_document_text(path, limit=65536)
        sample_text = document.text
        classification = classify_file(path, sample_text)
        source_hash = _sha256(path)
        stable_suffix = _stable_suffix(source_hash, path, inbox)
        source_id = f"SRC-{today.year}-{stable_suffix}"
        evidence_id = f"EVI-{today.year}-{stable_suffix}"

        source_evidence_item = _candidate_evidence(
            evidence_id=evidence_id,
            path=path,
            source_hash=source_hash,
            category=FileCategory(classification.category),
            confidence_score=classification.confidence,
            project=project,
            document_warnings=document.warnings,
            segment_count=len(document.segments),
            text_char_count=len(document.text),
        )
        extracted_items = extract_evidence_items_from_document(
            document=document,
            source_hash=source_hash,
            base_suffix=stable_suffix,
            project=project,
            run_date=today,
        )
        source_items = [source_evidence_item, *extracted_items]
        evidence_items.extend(source_items)
        for evidence_item in source_items:
            _write_evidence_json(evidence_root, evidence_item)

        stat = path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        sources.append(
            SourceRecord(
                source_id=source_id,
                path=str(path),
                source_hash=source_hash,
                size_bytes=stat.st_size,
                modified_time_utc=modified,
                classification=classification,
                evidence_ids=[item.evidence_id for item in source_items],
            )
        )

    raw_registry_path = state / "raw-registry.json"
    raw_registry_path.write_text(
        json.dumps(
            {
                "generated_by": "k-resdev-skill",
                "source_count": len(sources),
                "sources": [source.model_dump(mode="json") for source in sources],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    index_paths = write_evidence_index(evidence_items, state)
    open_issues_path = state / "open-issues.md"
    open_issues_path.write_text(_render_open_issues(sources, evidence_items), encoding="utf-8")

    return IntakeResult(
        source_count=len(sources),
        evidence_count=len(evidence_items),
        raw_registry_path=str(raw_registry_path),
        evidence_dir=str(evidence_root),
        evidence_index_markdown_path=index_paths.markdown_path,
        evidence_index_json_path=index_paths.json_path,
        open_issues_path=str(open_issues_path),
    )


def _iter_files(root: Path, excluded_roots: Iterable[Path] = ()) -> Iterable[Path]:
    excluded = [path.resolve() for path in excluded_roots]
    for path in sorted(root.rglob("*")):
        resolved = path.resolve()
        if any(_is_relative_to(resolved, excluded_root) for excluded_root in excluded):
            continue
        if path.is_file() and path.name.lower() not in IGNORED_NAMES:
            yield path


def _candidate_evidence(
    evidence_id: str,
    path: Path,
    source_hash: str,
    category: FileCategory,
    confidence_score: float,
    project: str | None,
    document_warnings: list[str] | None = None,
    segment_count: int = 0,
    text_char_count: int = 0,
) -> EvidenceItem:
    evidence_type = CATEGORY_TO_EVIDENCE_TYPE[category]
    value: dict[str, object] = {
        "category": category.value,
        "classification_confidence": confidence_score,
        "extracted_segment_count": segment_count,
        "extracted_text_chars": text_char_count,
    }
    risk_flags = ["auto_extracted", "needs_human_review"]
    if document_warnings:
        value["extraction_warnings"] = document_warnings
        risk_flags.append("text_extraction_warning")

    if category == FileCategory.DATA:
        try:
            profile = profile_data_file(path)
            value["data_profile"] = profile.model_dump(mode="json")
            risk_flags.append("data_profile_only")
        except ValueError as exc:
            risk_flags.extend(["data_profile_failed", "needs_review"])
            value["profile_error"] = str(exc)
    if category == FileCategory.UNKNOWN:
        risk_flags.append("unknown_file_type")

    return EvidenceItem(
        evidence_id=evidence_id,
        source_file=str(path),
        source_hash=source_hash,
        evidence_type=evidence_type,
        project=project,
        claim=_candidate_claim(category, path),
        value=value,
        confidence=_confidence_from_score(confidence_score),
        status=EvidenceStatus.NEEDS_REVIEW,
        risk_flags=risk_flags,
    )


def _candidate_claim(category: FileCategory, path: Path) -> str:
    source = path.name
    if category == FileCategory.DATA:
        return f"Data file `{source}` was profiled as candidate dataset evidence."
    if category == FileCategory.PLAN:
        return f"Plan-like source `{source}` may contain goals, KPIs, milestones, or obligations."
    if category == FileCategory.BUDGET:
        return f"Budget-like source `{source}` may contain cost or proof-of-spend evidence."
    if category == FileCategory.EXPERIMENT:
        return f"Experiment-like source `{source}` may contain metric or result evidence."
    if category == FileCategory.LITERATURE:
        return f"Literature-like source `{source}` may contain paper claims or method comparison evidence."
    if category == FileCategory.UNKNOWN:
        return f"Source `{source}` could not be classified and needs human review."
    return f"Source `{source}` was classified as `{category.value}` and needs evidence review."


def _confidence_from_score(score: float) -> Confidence:
    if score >= 0.75:
        return Confidence.HIGH
    if score >= 0.45:
        return Confidence.MEDIUM
    if score > 0.0:
        return Confidence.LOW
    return Confidence.UNKNOWN


def _write_evidence_json(evidence_dir: Path, item: EvidenceItem) -> None:
    target = evidence_dir / f"{item.evidence_id}.json"
    target.write_text(item.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _render_open_issues(sources: list[SourceRecord], evidence_items: list[EvidenceItem]) -> str:
    lines = [
        "# Open Issues",
        "",
        "| Source | Issue | Required Action |",
        "|---|---|---|",
    ]
    by_id = {item.evidence_id: item for item in evidence_items}
    issue_count = 0
    for source in sources:
        classification = source.classification
        item = by_id[source.evidence_ids[0]]
        if classification.category == FileCategory.UNKNOWN.value or classification.confidence < 0.45:
            issue_count += 1
            lines.append(
                f"| {_escape(source.path)} | Low-confidence or unknown classification. | Review source and set evidence type/status manually. |"
            )
        if "data_profile_failed" in item.risk_flags:
            issue_count += 1
            lines.append(
                f"| {_escape(source.path)} | Data profile failed. | Inspect file format and profile manually. |"
            )
    if issue_count == 0:
        lines.append("| - | No blocking intake issues detected. | Continue human review before using outputs. |")
    lines.append("")
    return "\n".join(lines)


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _stable_suffix(source_hash: str, path: Path, inbox_root: Path) -> str:
    try:
        relative_path = path.resolve().relative_to(inbox_root.resolve()).as_posix()
    except ValueError:
        relative_path = path.name
    digest = hashlib.sha256(f"{source_hash}|{relative_path}".encode("utf-8")).hexdigest()
    return digest[:8].upper()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
