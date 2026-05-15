from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .models import PaperRecord


def generate_literature_matrix(
    papers: Iterable[PaperRecord | dict],
    output_path: str | Path | None = None,
) -> str:
    """Generate a literature matrix from supplied metadata without inventing citations."""

    records = [_to_paper_record(paper) for paper in papers]
    lines = [
        "# Literature Review Matrix",
        "",
        "| Paper | Citation | Method | Dataset | Metrics | Key Claims | Limitations | Evidence | Status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for paper in records:
        lines.append(
            "| {paper} | {citation} | {method} | {dataset} | {metrics} | {claims} | {limitations} | {evidence} | {status} |".format(
                paper=_escape(paper.paper_id),
                citation=_escape(_citation(paper)),
                method=_escape(paper.method or "needs_review"),
                dataset=_escape(paper.dataset or "needs_review"),
                metrics=_escape(_metrics(paper.metrics)),
                claims=_escape("; ".join(paper.key_claims) or "needs_review"),
                limitations=_escape("; ".join(paper.limitations) or "needs_review"),
                evidence=_escape(", ".join(paper.evidence_ids) or "needs_review"),
                status=_escape(paper.status),
            )
        )
    lines.append("")
    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def _to_paper_record(paper: PaperRecord | dict) -> PaperRecord:
    if isinstance(paper, PaperRecord):
        return paper
    return PaperRecord.model_validate(paper)


def _citation(paper: PaperRecord) -> str:
    author_text = ", ".join(paper.authors) if paper.authors else "authors_needs_review"
    year = str(paper.year) if paper.year is not None else "year_needs_review"
    venue = paper.venue or "venue_needs_review"
    doi = f" DOI: {paper.doi}" if paper.doi else ""
    url = f" URL: {paper.url}" if paper.url else ""
    return f"{author_text} ({year}). {paper.title}. {venue}.{doi}{url}"


def _metrics(metrics: dict[str, object]) -> str:
    if not metrics:
        return "needs_review"
    return "; ".join(f"{key}: {value}" for key, value in metrics.items())


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
