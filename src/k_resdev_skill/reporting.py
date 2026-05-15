from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .claim_checker import check_unsupported_claims
from .models import CheckFinding, EvidenceItem, ProjectState, ReportDraftPaths


def draft_monthly_report(
    evidence_items: list[EvidenceItem],
    project_state: ProjectState | None = None,
    period: str | None = None,
) -> str:
    """Create a non-final monthly report projection from evidence items."""

    project_title = project_state.title if project_state else "needs_review"
    project_id = project_state.project_id if project_state else "needs_review"
    report_period = period or "needs_review"
    linked_by_kpi: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in evidence_items:
        linked_by_kpi[item.linked_kpi or "unmapped"].append(item)

    lines = [
        "# Monthly R&D Report Draft",
        "",
        "> Draft projection only. Human approval is required before submission.",
        "",
        "## 1. Reporting Period",
        "",
        f"- Period: {report_period}",
        f"- Project: {project_title}",
        f"- Project ID: {project_id}",
        "- Prepared by: K-ResDev draft",
        "",
        "## 2. Progress Against Plan",
        "",
        "| Goal/KPI | Current Evidence | Status | Notes |",
        "|---|---|---|---|",
    ]

    if project_state and project_state.kpis:
        for kpi in project_state.kpis:
            items = linked_by_kpi.get(kpi.kpi_id, [])
            evidence_ids = ", ".join(item.evidence_id for item in items) or "needs_evidence"
            lines.append(
                f"| {_escape(kpi.name)} ({_escape(kpi.kpi_id)}) | {_escape(evidence_ids)} | {_escape(_enum_value(kpi.status))} | target: {_escape(str(kpi.target))} |"
            )
    else:
        for key, items in linked_by_kpi.items():
            evidence_ids = ", ".join(item.evidence_id for item in items)
            lines.append(f"| {_escape(key)} | {_escape(evidence_ids)} | needs_review | KPI map missing |")

    lines.extend(
        [
            "",
            "## 3. Key Results",
            "",
            "| Claim | Evidence ID | Metric/Value | Review Status |",
            "|---|---|---|---|",
        ]
    )
    for item in evidence_items:
        if item.evidence_type in {"experiment_result", "outcome", "data_profile", "research_insight"}:
            lines.append(
                f"| {_escape(item.claim)} | {_escape(item.evidence_id)} | {_escape(_metric_value(item))} | {_escape(_enum_value(item.status))} |"
            )

    lines.extend(
        [
            "",
            "## 4. Issues and Risks",
            "",
            "| Issue | Evidence ID | Impact | Required Action |",
            "|---|---|---|---|",
        ]
    )
    risk_rows = 0
    for item in evidence_items:
        if item.risk_flags:
            risk_rows += 1
            lines.append(
                f"| {_escape(', '.join(item.risk_flags))} | {_escape(item.evidence_id)} | needs_review | Human review before reporting. |"
            )
    if risk_rows == 0:
        lines.append("| - | - | No risk flags in evidence index. | Still require human review. |")

    lines.extend(
        [
            "",
            "## 5. Budget / Evidence Status",
            "",
            "| Budget Item | Evidence | Status | Missing Items |",
            "|---|---|---|---|",
        ]
    )
    budget_items = [item for item in evidence_items if item.evidence_type == "budget_evidence"]
    if budget_items:
        for item in budget_items:
            lines.append(f"| needs_review | {_escape(item.evidence_id)} | {_escape(_enum_value(item.status))} | approval/proof fields need review |")
    else:
        lines.append("| needs_review | needs_evidence | missing | Budget evidence not mapped. |")

    lines.extend(
        [
            "",
            "## 6. Next Month Plan",
            "",
            "| Action | Owner | Due | Linked Milestone |",
            "|---|---|---|---|",
            "| Review all `needs_review` evidence and approve reportable claims. | human_owner | needs_review | needs_review |",
            "",
            "## 7. Human Decision Required",
            "",
            "- Confirm which evidence items are accepted.",
            "- Confirm whether any draft claim can be used in an official report.",
            "- Confirm agency-specific template requirements before export/submission.",
            "",
        ]
    )
    return "\n".join(lines)


def write_monthly_report(
    evidence_items: list[EvidenceItem],
    reports_dir: str | Path = "reports",
    project_state: ProjectState | None = None,
    period: str | None = None,
    filename: str | None = None,
) -> ReportDraftPaths:
    report = draft_monthly_report(evidence_items, project_state, period)
    reports = Path(reports_dir)
    reports.mkdir(parents=True, exist_ok=True)
    target = reports / (filename or "monthly-report-draft.md")
    target.write_text(report, encoding="utf-8")

    findings = check_unsupported_claims(report, evidence_items, project_state.kpis if project_state else None)
    review_path = reports / (target.stem + "-claim-review.md")
    review_path.write_text(_render_claim_review(findings), encoding="utf-8")
    return ReportDraftPaths(report_path=str(target), review_path=str(review_path))


def _render_claim_review(findings: list[CheckFinding]) -> str:
    lines = [
        "# Report Claim Review",
        "",
        "| Severity | Code | Claim | Evidence | Suggested Action |",
        "|---|---|---|---|---|",
    ]
    if not findings:
        lines.append("| - | - | No unsupported claim patterns detected. | - | Human review still required. |")
    for finding in findings:
        lines.append(
            f"| {_escape(finding.severity)} | {_escape(finding.code)} | {_escape(finding.claim)} | {_escape(', '.join(finding.evidence_ids))} | {_escape(finding.suggested_action or '')} |"
        )
    lines.append("")
    return "\n".join(lines)


def _metric_value(item: EvidenceItem) -> str:
    if not item.value:
        return "needs_review"
    for key in ("score", "actual", "current", "target"):
        if key in item.value:
            return f"{key}: {item.value[key]}"
    if "data_profile" in item.value:
        profile = item.value["data_profile"]
        if isinstance(profile, dict):
            return f"rows: {profile.get('row_count', 'needs_review')}, columns: {profile.get('column_count', 'needs_review')}"
    return "see evidence value"


def _escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _enum_value(value: object) -> str:
    return getattr(value, "value", str(value))
