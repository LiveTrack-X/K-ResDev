from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .models import EvidenceItem, ResearchInsight


def generate_experiment_plan(
    insight: ResearchInsight,
    evidence_items: list[EvidenceItem] | None = None,
    output_path: str | Path | None = None,
) -> str:
    """Turn one hypothesis-level insight into a reviewable follow-up experiment plan."""

    evidence_by_id = {item.evidence_id: item for item in evidence_items or []}
    linked_evidence = [evidence_by_id[evidence_id] for evidence_id in insight.basis if evidence_id in evidence_by_id]
    missing_basis = [evidence_id for evidence_id in insight.basis if evidence_id not in evidence_by_id]

    metrics = _ordered_unique(
        str(item.value.get("metric"))
        for item in linked_evidence
        if isinstance(item.value, dict) and item.value.get("metric")
    )
    datasets = _ordered_unique(
        str(item.value.get("dataset"))
        for item in linked_evidence
        if isinstance(item.value, dict) and item.value.get("dataset")
    )
    baselines = _ordered_unique(
        str(item.value.get("baseline"))
        for item in linked_evidence
        if isinstance(item.value, dict) and item.value.get("baseline") is not None
    )

    lines = [
        f"# Hypothesis-to-Experiment Plan: {insight.insight_id}",
        "",
        "> Draft validation plan only. A human researcher must approve scope, protocol, statistics, and interpretation before execution.",
        "",
        "## Hypothesis",
        "",
        f"- Claim: {_escape(insight.claim)}",
        f"- Status: {_escape(str(insight.status))}",
        f"- Confidence: {_escape(str(insight.confidence))}",
        f"- Basis evidence: {_escape(', '.join(insight.basis) or 'needs_evidence')}",
        "",
        "## Evidence Context",
        "",
        "| Evidence | Type | Claim | Metric | Dataset | Status |",
        "|---|---|---|---|---|---|",
    ]
    if not linked_evidence:
        lines.append("| needs_evidence | needs_review | No matching evidence records supplied. | needs_review | needs_review | needs_review |")
    for item in linked_evidence:
        value = item.value or {}
        lines.append(
            "| {evidence} | {etype} | {claim} | {metric} | {dataset} | {status} |".format(
                evidence=_escape(item.evidence_id),
                etype=_escape(str(item.evidence_type)),
                claim=_escape(item.claim),
                metric=_escape(str(value.get("metric", "needs_review"))),
                dataset=_escape(str(value.get("dataset", "needs_review"))),
                status=_escape(str(item.status)),
            )
        )
    if missing_basis:
        lines.extend(["", "Missing basis IDs: " + _escape(", ".join(missing_basis)), ""])
    else:
        lines.append("")

    lines.extend(
        [
            "## Experiment Design",
            "",
            "| Field | Draft Plan |",
            "|---|---|",
            f"| Primary metric | {_escape(', '.join(metrics) or _infer_metric_hint(insight))} |",
            f"| Dataset/split | {_escape(', '.join(datasets) or 'Record dataset version and split before execution.')} |",
            f"| Baseline/control | {_escape(', '.join(baselines) or 'Define baseline/control before execution.')} |",
            "| Minimum sample check | Record sample size per group/split and mark small samples as a risk. |",
            "| Statistical check | Bootstrap confidence interval or appropriate paired test; document assumptions. |",
            "| Reproducibility check | Record code version, data version, seed, environment, and preprocessing. |",
            "| Decision gate | Human review before promoting this hypothesis to accepted finding. |",
            "",
            "## Assumptions",
            "",
        ]
    )
    lines.extend([f"- {_escape(item)}" for item in insight.assumptions] or ["- needs_review"])
    lines.extend(["", "## Risk Flags", ""])
    lines.extend([f"- {_escape(item)}" for item in insight.risk_flags] or ["- needs_review"])
    lines.extend(["", "## Next Checks", ""])
    lines.extend([f"- {_escape(item)}" for item in insight.next_checks] or ["- Define concrete validation checks before execution."])
    lines.extend(["", "## Approval Gate", "", "- Researcher approval required before protocol execution.", "- Report/paper wording must remain hypothesis-level until validation evidence is accepted.", ""])

    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def generate_experiment_plan_bundle(
    insights: list[ResearchInsight],
    evidence_items: list[EvidenceItem] | None = None,
    output_path: str | Path | None = None,
) -> str:
    """Render a bundle of hypothesis validation plans."""

    if not insights:
        rendered = "\n".join(
            [
                "# Hypothesis-to-Experiment Plan Bundle",
                "",
                "> No insight candidates were supplied. Create `ResearchInsight` records before planning experiments.",
                "",
            ]
        )
    else:
        rendered = "\n\n---\n\n".join(generate_experiment_plan(insight, evidence_items) for insight in insights)
        rendered += "\n"
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def _infer_metric_hint(insight: ResearchInsight) -> str:
    text = " ".join([insight.claim, *insight.next_checks]).lower()
    for metric in ("dice", "iou", "auc", "accuracy", "f1", "recall", "precision", "loss", "latency"):
        if metric in text:
            return f"Confirm `{metric}` definition and target before execution."
    return "Define primary metric and target before execution."


def _ordered_unique(values: Iterable[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
