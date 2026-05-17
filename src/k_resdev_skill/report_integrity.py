from __future__ import annotations

from pathlib import Path

from .claim_checker import check_unsupported_claims
from .evidence_index import load_evidence_index
from .models import CheckFinding, KPI, ProjectState, WorkspaceReportIntegrityItem, WorkspaceReportIntegrityResult

OPERATIONAL_MARKDOWN_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "budget-checklist.md",
    "evidence-bundle-index.md",
    "next-actions.md",
    "readiness.md",
    "report-integrity.md",
    "source-verification.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
}


def generate_workspace_report_integrity(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceReportIntegrityResult:
    """Check local Markdown report drafts against indexed evidence."""

    workspace = Path(root)
    warnings: list[str] = []
    report_paths = _report_drafts(workspace)
    evidence = []
    kpis: list[KPI] = []
    evidence_unreadable = False

    try:
        evidence = load_evidence_index(workspace / "state" / "evidence-index.json")
    except Exception as exc:
        if report_paths:
            warnings.append(f"evidence_index_unreadable:{exc}")
            evidence_unreadable = True

    state_path = workspace / "state" / "project-state.json"
    if state_path.exists():
        try:
            kpis = ProjectState.model_validate_json(state_path.read_text(encoding="utf-8")).kpis
        except Exception as exc:
            warnings.append(f"project_state_unreadable:{exc}")

    items: list[WorkspaceReportIntegrityItem] = []
    for path in report_paths:
        items.append(_check_report(path, evidence, kpis, skip_claim_check=evidence_unreadable))

    high_count = sum(item.high_count for item in items)
    medium_count = sum(item.medium_count for item in items)
    low_count = sum(item.low_count for item in items)
    finding_count = sum(item.finding_count for item in items)
    if not items:
        status = "no_reports"
    elif evidence_unreadable:
        status = "blocked"
    elif high_count:
        status = "blocked"
    elif medium_count or low_count or warnings:
        status = "needs_review"
    else:
        status = "ready"

    result = WorkspaceReportIntegrityResult(
        root=str(workspace),
        status=status,
        report_count=len(items),
        finding_count=finding_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        items=items,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=warnings,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_report_integrity_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_report_integrity_markdown(result: WorkspaceReportIntegrityResult) -> str:
    lines = [
        "# Workspace Report Integrity",
        "",
        "> Report integrity projection only. This checks local Markdown report drafts against indexed evidence; it does not certify official compliance, scientific validity, or human approval.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Report count | {result.report_count} |",
        f"| Finding count | {result.finding_count} |",
        f"| High | {result.high_count} |",
        f"| Medium | {result.medium_count} |",
        f"| Low | {result.low_count} |",
        f"| Warnings | {_escape(', '.join(result.warnings) or '-')} |",
        "",
        "## Reports",
        "",
        "| Report | Findings | High | Medium | Low | Warnings |",
        "|---|---:|---:|---:|---:|---|",
    ]
    if not result.items:
        lines.append("| no_reports | 0 | 0 | 0 | 0 | no_markdown_report_drafts |")
    for item in result.items:
        lines.append(
            "| {path} | {findings} | {high} | {medium} | {low} | {warnings} |".format(
                path=_escape(item.path),
                findings=item.finding_count,
                high=item.high_count,
                medium=item.medium_count,
                low=item.low_count,
                warnings=_escape(", ".join(item.warnings) or "-"),
            )
        )

    lines.extend(["", "## Findings", "", "| Severity | Code | Report | Claim | Evidence IDs | Suggested Action |", "|---|---|---|---|---|---|"])
    if not any(item.findings for item in result.items):
        lines.append("| ok | no_findings | - | - | - | Continue human review. |")
    for item in result.items:
        for finding in item.findings:
            lines.append(
                "| {severity} | {code} | {path} | {claim} | {evidence} | {action} |".format(
                    severity=_escape(finding.severity),
                    code=_escape(finding.code),
                    path=_escape(item.path),
                    claim=_escape(finding.claim),
                    evidence=_escape(", ".join(finding.evidence_ids) or "-"),
                    action=_escape(finding.suggested_action or "-"),
                )
            )
    lines.append("")
    return "\n".join(lines)


def _check_report(
    path: Path,
    evidence: object,
    kpis: list[KPI],
    skip_claim_check: bool,
) -> WorkspaceReportIntegrityItem:
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return WorkspaceReportIntegrityItem(path=str(path), warnings=[f"report_unreadable:{exc}"])

    if skip_claim_check:
        warnings.append("claim_check_skipped")
        findings: list[CheckFinding] = []
    else:
        findings = check_unsupported_claims(text, evidence, kpis)
    high_count = sum(1 for finding in findings if finding.severity == "high")
    medium_count = sum(1 for finding in findings if finding.severity == "medium")
    low_count = sum(1 for finding in findings if finding.severity == "low")
    return WorkspaceReportIntegrityItem(
        path=str(path),
        finding_count=len(findings),
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        findings=findings,
        warnings=warnings,
    )


def _report_drafts(workspace: Path) -> list[Path]:
    reports_dir = workspace / "reports"
    if not reports_dir.exists():
        return []
    return [path for path in sorted(reports_dir.glob("*.md")) if path.name not in OPERATIONAL_MARKDOWN_NAMES]


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
