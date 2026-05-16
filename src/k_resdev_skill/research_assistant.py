from __future__ import annotations

import re
from pathlib import Path

from .models import DataProfile, EvidenceItem, PaperRecord, ResearchInsight

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
CLAIM_PREFIX_RE = re.compile(r"^(?:claim|key claim|주장|핵심 주장)\s*[:：]\s*(.+)$", re.IGNORECASE)
LIMITATION_PREFIX_RE = re.compile(r"^(?:limitation|limitations|한계|제한점)\s*[:：]\s*(.+)$", re.IGNORECASE)
AUTHORS_RE = re.compile(r"^(?:authors?|저자)\s*[:：]\s*(.+)$", re.IGNORECASE)
VENUE_RE = re.compile(r"^(?:venue|journal|conference|학회|저널)\s*[:：]\s*(.+)$", re.IGNORECASE)


def paper_card_from_text(
    text: str,
    paper_id: str = "PAPER-NEEDS-REVIEW",
    evidence_ids: list[str] | None = None,
) -> PaperRecord:
    """Create a conservative paper card from supplied text without inventing metadata."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = _first_title_like_line(lines)
    authors: list[str] = []
    venue: str | None = None
    key_claims: list[str] = []
    limitations: list[str] = []
    doi_match = DOI_RE.search(text)
    year_match = YEAR_RE.search(text)

    for line in lines:
        if match := AUTHORS_RE.match(line):
            authors = [part.strip() for part in re.split(r",|;", match.group(1)) if part.strip()]
        if match := VENUE_RE.match(line):
            venue = match.group(1).strip()
        if match := CLAIM_PREFIX_RE.match(line):
            key_claims.append(match.group(1).strip())
        if match := LIMITATION_PREFIX_RE.match(line):
            limitations.append(match.group(1).strip())

    return PaperRecord(
        paper_id=paper_id,
        title=title,
        authors=authors,
        year=int(year_match.group(0)) if year_match else None,
        venue=venue,
        doi=doi_match.group(0) if doi_match else None,
        key_claims=key_claims,
        limitations=limitations,
        evidence_ids=evidence_ids or [],
        status="needs_review",
    )


def generate_paper_card_markdown(paper: PaperRecord, output_path: str | Path | None = None) -> str:
    lines = [
        f"# Paper Card: {paper.paper_id}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Title | {_escape(paper.title)} |",
        f"| Authors | {_escape(', '.join(paper.authors) or 'needs_review')} |",
        f"| Year | {_escape(str(paper.year) if paper.year is not None else 'needs_review')} |",
        f"| Venue | {_escape(paper.venue or 'needs_review')} |",
        f"| DOI | {_escape(paper.doi or 'needs_review')} |",
        f"| Evidence | {_escape(', '.join(paper.evidence_ids) or 'needs_review')} |",
        f"| Status | {_escape(paper.status)} |",
        "",
        "## Key Claims",
        "",
    ]
    lines.extend([f"- {_escape(claim)}" for claim in paper.key_claims] or ["- needs_review"])
    lines.extend(["", "## Limitations", ""])
    lines.extend([f"- {_escape(item)}" for item in paper.limitations] or ["- needs_review"])
    lines.append("")
    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def generate_data_insight_candidates(
    profile: DataProfile,
    basis: list[str] | None = None,
) -> list[ResearchInsight]:
    insights: list[ResearchInsight] = []
    basis_ids = basis or []
    if profile.row_count < 30:
        insights.append(
            ResearchInsight(
                insight_id="INS-DATA-SMALL-SAMPLE",
                claim=f"Dataset has only {profile.row_count} rows, so derived findings may be sample-size limited.",
                basis=basis_ids,
                confidence="medium",
                risk_flags=["small_sample", "needs_statistical_test"],
                next_checks=["Report sample size by split", "Use bootstrap confidence intervals where appropriate"],
            )
        )
    for column, missingness in profile.missingness.items():
        if missingness.missing_count > 0:
            insights.append(
                ResearchInsight(
                    insight_id=f"INS-MISSING-{_slug(column)}",
                    claim=f"Column `{column}` has {missingness.missing_count} missing values.",
                    basis=basis_ids,
                    confidence="medium",
                    risk_flags=["missing_data", "needs_data_quality_review"],
                    next_checks=[f"Inspect missingness mechanism for `{column}`", "Document exclusion/imputation policy"],
                )
            )
    for metric in profile.possible_metrics:
        summary = _summary_for_metric(profile, metric)
        if summary:
            insights.append(
                ResearchInsight(
                    insight_id=f"INS-METRIC-{_slug(metric)}",
                    claim=f"Metric candidate `{metric}` is present with observed range {summary.min} to {summary.max}.",
                    basis=basis_ids,
                    confidence="low",
                    risk_flags=["metric_candidate", "needs_baseline_comparison"],
                    next_checks=[f"Confirm `{metric}` definition", "Compare against baseline and target", "Check split and sample size"],
                )
            )
    return insights


def generate_data_insight_report(
    profile: DataProfile,
    basis: list[str] | None = None,
    output_path: str | Path | None = None,
) -> str:
    insights = generate_data_insight_candidates(profile, basis)
    lines = [
        "# Data Insight Candidate Report",
        "",
        "> Draft candidates only. Human review and statistical validation are required.",
        "",
        f"- Source: `{profile.source_file}`",
        f"- Rows: {profile.row_count}",
        f"- Columns: {profile.column_count}",
        f"- Possible metrics: {', '.join(profile.possible_metrics) or 'needs_review'}",
        "",
        "| Insight ID | Claim | Confidence | Risk Flags | Next Checks |",
        "|---|---|---|---|---|",
    ]
    if not insights:
        lines.append("| - | No automatic insight candidates detected. | - | - | Continue manual review. |")
    for insight in insights:
        lines.append(
            f"| {_escape(insight.insight_id)} | {_escape(insight.claim)} | {_escape(insight.confidence)} | {_escape(', '.join(insight.risk_flags))} | {_escape('; '.join(insight.next_checks))} |"
        )
    lines.append("")
    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def generate_experiment_comparison_table(
    evidence_items: list[EvidenceItem],
    output_path: str | Path | None = None,
) -> str:
    rows = [item for item in evidence_items if item.evidence_type == "experiment_result"]
    lines = [
        "# Experiment Comparison Table",
        "",
        "| Evidence | Metric | Score | Baseline | Target | Dataset | Status | Risk Flags |",
        "|---|---|---|---|---|---|---|---|",
    ]
    if not rows:
        lines.append("| needs_evidence | needs_review | needs_review | needs_review | needs_review | needs_review | needs_review | No experiment evidence indexed. |")
    for item in rows:
        value = item.value or {}
        lines.append(
            "| {evidence} | {metric} | {score} | {baseline} | {target} | {dataset} | {status} | {risk} |".format(
                evidence=_escape(item.evidence_id),
                metric=_escape(str(value.get("metric", "needs_review"))),
                score=_escape(str(value.get("score", value.get("actual", "needs_review")))),
                baseline=_escape(str(value.get("baseline", "needs_review"))),
                target=_escape(str(value.get("target", "needs_review"))),
                dataset=_escape(str(value.get("dataset", "needs_review"))),
                status=_escape(str(item.status)),
                risk=_escape(", ".join(item.risk_flags) or "needs_review"),
            )
        )
    lines.append("")
    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def generate_reproducibility_checklist(
    evidence_items: list[EvidenceItem],
    output_path: str | Path | None = None,
) -> str:
    value_keys = {key for item in evidence_items for key in (item.value or {}).keys()}
    checks = [
        ("dataset", "Dataset identity/version is recorded."),
        ("split", "Train/validation/test split is recorded."),
        ("metric", "Metric definition is recorded."),
        ("baseline", "Baseline comparison is recorded."),
        ("score", "Primary result score is recorded."),
        ("target", "Target threshold is recorded."),
        ("sample_size", "Sample size is recorded."),
        ("seed", "Random seed or deterministic setting is recorded."),
        ("code_version", "Code/model version is recorded."),
        ("environment", "Runtime environment is recorded."),
    ]
    lines = [
        "# Reproducibility Checklist",
        "",
        "> Checklist projection only. Mark unresolved items before reporting or publication.",
        "",
        "| Status | Check | Evidence Hint |",
        "|---|---|---|",
    ]
    for key, label in checks:
        status = "present" if key in value_keys else "missing"
        lines.append(f"| {status} | {_escape(label)} | `{key}` |")
    lines.append("")
    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def _first_title_like_line(lines: list[str]) -> str:
    for line in lines:
        if ":" not in line and not DOI_RE.search(line):
            return line
    return lines[0] if lines else "title_needs_review"


def _summary_for_metric(profile: DataProfile, metric: str):
    for column, summary in profile.numeric_summary.items():
        if metric.lower() in column.lower():
            return summary
    return None


def _slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-") or "UNKNOWN"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
