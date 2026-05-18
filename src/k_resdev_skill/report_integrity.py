from __future__ import annotations

import re
from pathlib import Path

from .claim_checker import check_unsupported_claims
from .evidence_index import load_evidence_index
from .models import CheckFinding, EvidenceItem, KPI, ProjectState, WorkspaceReportIntegrityItem, WorkspaceReportIntegrityResult

EVIDENCE_ID_RE = re.compile(r"\b(?:EVI|DATA|INS|PAPER)-\d{4}-[A-Z0-9]{4,12}\b")
BLOCKING_EVIDENCE_STATUSES = {"rejected", "superseded"}
REVIEW_EVIDENCE_STATUSES = {"draft", "needs_review"}

OPERATIONAL_MARKDOWN_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "artifact-authority.md",
    "bibliography-integrity.md",
    "bibliography-review-summary.md",
    "budget-ledger.md",
    "budget-checklist.md",
    "checkpoint-resume-plan.md",
    "citation-support.md",
    "citation-support-summary.md",
    "evidence-bundle-index.md",
    "goals-review.md",
    "next-actions.md",
    "profile-integrity.md",
    "profile-promotion-apply-plan.md",
    "profile-promotion-apply-result.md",
    "profile-lifecycle-ledger.md",
    "profile-promotion-revoke-plan.md",
    "profile-promotion-revoke-result.md",
    "profile-promotion-summary.md",
    "profile-review.md",
    "profile-source-fix-plan.md",
    "profile-source-fix-summary.md",
    "profile-source-queue.md",
    "profile-source-summary.md",
    "readiness.md",
    "reference-corpus-summary.md",
    "research-claim-matrix.md",
    "research-claims.md",
    "report-integrity.md",
    "source-verification.md",
    "trace-passport.md",
    "workspace-discovery.md",
    "workspace-dashboard.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
    "workspace-trace.md",
}
OPERATIONAL_MARKDOWN_PREFIXES = ("weekly-review-", "workflow-")


def generate_workspace_report_integrity(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceReportIntegrityResult:
    """Check local Markdown report drafts against indexed evidence."""

    workspace = Path(root)
    warnings: list[str] = []
    report_paths = _report_drafts(workspace)
    evidence: list[EvidenceItem] = []
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
        findings.extend(_evidence_status_findings(text, evidence))
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
    return [path for path in sorted(reports_dir.glob("*.md")) if not _is_operational_markdown(path)]


def _is_operational_markdown(path: str | Path) -> bool:
    name = Path(path).name
    return name in OPERATIONAL_MARKDOWN_NAMES or any(name.startswith(prefix) for prefix in OPERATIONAL_MARKDOWN_PREFIXES)


def _evidence_status_findings(text: str, evidence: list[EvidenceItem]) -> list[CheckFinding]:
    evidence_by_id = {item.evidence_id: item for item in evidence}
    findings: list[CheckFinding] = []
    for line in _claim_lines_with_ids(text):
        for evidence_id in EVIDENCE_ID_RE.findall(line):
            item = evidence_by_id.get(evidence_id)
            if item is None:
                continue
            status = str(item.status)
            if status in BLOCKING_EVIDENCE_STATUSES:
                findings.append(
                    CheckFinding(
                        code="invalid_evidence_status_citation",
                        severity="high",
                        message=f"Report cites {status} evidence: {evidence_id}",
                        claim=line,
                        evidence_ids=[evidence_id],
                        suggested_action="Remove the claim, replace the evidence, or document why the rejected/superseded evidence is no longer cited.",
                    )
                )
            elif status in REVIEW_EVIDENCE_STATUSES:
                findings.append(
                    CheckFinding(
                        code="unreviewed_evidence_citation",
                        severity="medium",
                        message=f"Report cites evidence that is not accepted yet: {evidence_id} ({status}).",
                        claim=line,
                        evidence_ids=[evidence_id],
                        suggested_action="Accept, reject, or disclose the evidence review state before official use.",
                    )
                )
    return _dedupe_findings(findings)


def _claim_lines_with_ids(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        if EVIDENCE_ID_RE.search(line):
            lines.append(line)
    return lines


def _dedupe_findings(findings: list[CheckFinding]) -> list[CheckFinding]:
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    unique: list[CheckFinding] = []
    for finding in findings:
        key = (finding.code, finding.claim, tuple(finding.evidence_ids))
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
