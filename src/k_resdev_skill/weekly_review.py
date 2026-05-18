from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

from .approval import load_approval_records
from .artifact_authority import generate_artifact_authority
from .budget_ledger import generate_workspace_budget_ledger
from .evidence_index import load_evidence_index
from .models import (
    DashboardCard,
    EvidenceItem,
    WorkspaceActionPlan,
    WorkspaceDashboardResult,
    WorkspaceDoctorResult,
    WorkspaceWeeklyReviewResult,
    WeeklyReviewItem,
)
from .project_goals import generate_goals_review
from .reference_corpus import build_reference_corpus
from .research_claims import generate_research_claim_matrix
from .trace_passport import generate_trace_passport
from .workspace import is_operational_markdown, run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan
from .workspace_trace import generate_workspace_trace


def generate_weekly_review(
    root: str | Path,
    review_date: str | date | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    max_actions: int = 5,
    doctor_result: WorkspaceDoctorResult | None = None,
    action_plan: WorkspaceActionPlan | None = None,
) -> WorkspaceWeeklyReviewResult:
    """Generate a local weekly operating review from saved K-ResDev artifacts."""

    workspace = Path(root)
    current_date = _coerce_date(review_date) or date.today()
    doctor = doctor_result or run_workspace_doctor(workspace)
    if json_path is not None:
        doctor = _without_finding_codes(doctor, {"weekly_review_missing", "weekly_review_stale", "weekly_review_unreadable"})
    actions = action_plan or generate_workspace_action_plan(workspace, doctor_result=doctor)
    evidence = _load_evidence(workspace)
    approvals = _load_approvals(workspace)
    reports = _report_paths(workspace)
    goals = generate_goals_review(workspace)

    items: list[WeeklyReviewItem] = []
    for finding in doctor.findings:
        items.append(
            _item(
                category="readiness",
                title=finding.code,
                severity=finding.severity,
                message=finding.message,
                artifact_paths=[finding.path] if finding.path else [],
                suggested_action=finding.suggested_action,
            )
        )

    for action in actions.actions[: max(0, max_actions)]:
        items.append(
            _item(
                category="next_action",
                title=action.title,
                severity=_severity_from_priority(action.priority),
                status=action.status,
                message=action.rationale,
                suggested_action=action.command,
            )
        )

    closed_deadline_statuses = {"done", "accepted", "completed", "superseded"}
    for deadline in goals.deadlines:
        if str(deadline.status).lower() in closed_deadline_statuses:
            continue
        if deadline.due_date < current_date:
            items.append(
                _item(
                    category="deadline",
                    title=deadline.title,
                    severity="high",
                    message=f"Deadline `{deadline.deadline_id}` is overdue.",
                    evidence_ids=list(deadline.linked_evidence_ids),
                    artifact_paths=list(deadline.linked_report_paths),
                    due_date=deadline.due_date,
                    suggested_action="Review the deadline, evidence links, report drafts, and approval records.",
                )
            )
        elif (deadline.due_date - current_date).days <= 14:
            items.append(
                _item(
                    category="deadline",
                    title=deadline.title,
                    severity="medium",
                    message=f"Deadline `{deadline.deadline_id}` is due within 14 days.",
                    evidence_ids=list(deadline.linked_evidence_ids),
                    artifact_paths=list(deadline.linked_report_paths),
                    due_date=deadline.due_date,
                    suggested_action="Prepare evidence, draft projections, and human review before the due date.",
                )
            )

    needs_review = [item for item in evidence if str(item.status) == "needs_review"]
    if needs_review:
        items.append(
            _item(
                category="evidence",
                title="Evidence needs review",
                severity="medium",
                message=f"{len(needs_review)} evidence item(s) still need human review.",
                evidence_ids=[item.evidence_id for item in needs_review[:10]],
                artifact_paths=[workspace / "state" / "evidence-index.json"],
                suggested_action="Accept, reject, or explicitly keep unresolved evidence as draft before external use.",
            )
        )

    items = _dedupe_items(items)
    high_actions = sum(1 for action in actions.actions if action.priority == "high")
    result = WorkspaceWeeklyReviewResult(
        root=str(workspace),
        review_date=current_date,
        status=_status_from_severities(item.severity for item in items),
        evidence_count=len(evidence),
        report_count=len(reports),
        approval_count=len(approvals),
        action_count=actions.action_count,
        high_action_count=high_actions,
        objective_count=goals.objective_count,
        deadline_count=goals.deadline_count,
        due_soon_count=goals.due_soon_count,
        overdue_count=goals.overdue_count,
        open_finding_count=doctor.finding_count,
        high_finding_count=sum(1 for finding in doctor.findings if finding.severity == "high"),
        item_count=len(items),
        items=items,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=list(goals.warnings),
    )
    _write_outputs(result, render_weekly_review_markdown(result), output_path, json_path)
    return result


def generate_workspace_dashboard(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    doctor_result: WorkspaceDoctorResult | None = None,
    action_plan: WorkspaceActionPlan | None = None,
) -> WorkspaceDashboardResult:
    """Generate a compact local dashboard from K-ResDev operating artifacts."""

    workspace = Path(root)
    doctor = doctor_result or run_workspace_doctor(workspace)
    if json_path is not None:
        doctor = _without_finding_codes(doctor, {"workspace_dashboard_missing", "workspace_dashboard_unreadable"})
    actions = action_plan or generate_workspace_action_plan(workspace, doctor_result=doctor)
    evidence = _load_evidence(workspace)
    approvals = _load_approvals(workspace)
    reports = _report_paths(workspace)
    goals = generate_goals_review(workspace)
    budget = generate_workspace_budget_ledger(workspace)
    authority = generate_artifact_authority(workspace)
    references = build_reference_corpus(workspace)
    research_claims = generate_research_claim_matrix(workspace)
    trace = generate_workspace_trace(workspace)
    passport = generate_trace_passport(workspace)

    high_findings = sum(1 for finding in doctor.findings if finding.severity == "high")
    high_actions = sum(1 for action in actions.actions if action.priority == "high")
    cards = [
        _card(
            "readiness",
            "Readiness",
            doctor.status,
            doctor.finding_count,
            _severity_from_status(doctor.status, high=high_findings),
            f"{high_findings} high finding(s), {doctor.finding_count} total finding(s).",
            [doctor.markdown_path, doctor.json_path],
        ),
        _card(
            "evidence",
            "Evidence",
            "ready" if evidence else "blocked",
            len(evidence),
            "low" if evidence else "high",
            "Evidence items indexed locally.",
            [workspace / "state" / "evidence-index.json"],
        ),
        _card(
            "reports",
            "Report Drafts",
            "ready" if reports else "ready_with_notes",
            len(reports),
            "low" if reports else "low",
            "Submission-style Markdown drafts only; operating summaries are excluded.",
            reports[:5],
        ),
        _card(
            "approvals",
            "Approvals",
            "ready" if approvals else "needs_review",
            len(approvals),
            "low" if approvals else "medium",
            "Supplied human approval records, not inferred approvals.",
            [workspace / "state" / "approvals"],
        ),
        _card(
            "actions",
            "Next Actions",
            actions.status,
            actions.action_count,
            "high" if high_actions else "medium" if actions.action_count else "low",
            f"{high_actions} high-priority action(s).",
            [actions.markdown_path, actions.json_path],
        ),
        _card(
            "goals",
            "Goals And Deadlines",
            goals.status,
            goals.deadline_count,
            _severity_from_status(goals.status, high=goals.high_count, medium=goals.medium_count),
            f"{goals.objective_count} objective(s), {goals.overdue_count} overdue deadline(s), {goals.due_soon_count} due soon.",
            [goals.markdown_path, goals.json_path, workspace / "state" / "project-goals.json"],
        ),
        _card(
            "budget",
            "Budget Ledger",
            budget.status,
            budget.ledger_count,
            _severity_from_status(budget.status, high=budget.high_count, medium=budget.medium_count),
            f"{budget.finding_count} budget finding(s).",
            [budget.markdown_path, budget.json_path],
        ),
        _card(
            "authority",
            "Artifact Authority",
            authority.status,
            authority.artifact_count,
            _severity_from_status(authority.status, high=authority.high_count, medium=authority.medium_count),
            f"{authority.finding_count} authority finding(s).",
            [authority.markdown_path, authority.json_path],
        ),
        _card(
            "references",
            "Reference Corpus",
            references.status,
            references.item_count,
            _severity_from_status(references.status, high=references.high_count, medium=references.medium_count),
            f"{references.rejection_count} local reference rejection(s).",
            [references.summary_markdown_path, references.corpus_json_path],
        ),
        _card(
            "research_claims",
            "Research Claims",
            research_claims.status,
            research_claims.claim_count,
            _severity_from_status(research_claims.status, high=research_claims.high_count, medium=research_claims.medium_count),
            f"{research_claims.finding_count} research-claim finding(s).",
            [research_claims.markdown_path, research_claims.json_path],
        ),
        _card(
            "trace",
            "Workspace Trace",
            trace.status,
            trace.node_count,
            _severity_from_status(trace.status, high=trace.high_count, medium=trace.medium_count),
            f"{trace.edge_count} edge(s), {trace.finding_count} trace finding(s).",
            [trace.markdown_path, trace.json_path],
        ),
        _card(
            "checkpoints",
            "Trace Passport",
            passport.status,
            passport.checkpoint_count,
            _severity_from_status(passport.status, high=passport.high_count, medium=passport.medium_count),
            f"Latest checkpoint: {passport.latest_checkpoint_id or '-'}",
            [passport.markdown_path, passport.json_path],
        ),
    ]
    cards = [card for card in cards if card is not None]
    result = WorkspaceDashboardResult(
        root=str(workspace),
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        status=_status_from_severities(card.severity for card in cards),
        evidence_count=len(evidence),
        report_count=len(reports),
        approval_count=len(approvals),
        finding_count=doctor.finding_count,
        high_finding_count=high_findings,
        action_count=actions.action_count,
        high_action_count=high_actions,
        objective_count=goals.objective_count,
        deadline_count=goals.deadline_count,
        due_soon_count=goals.due_soon_count,
        overdue_count=goals.overdue_count,
        budget_ledger_status=budget.status,
        artifact_authority_status=authority.status,
        reference_corpus_status=references.status,
        research_claim_matrix_status=research_claims.status,
        trace_status=trace.status,
        checkpoint_count=passport.checkpoint_count,
        card_count=len(cards),
        cards=cards,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(budget.warnings + authority.warnings + references.warnings + research_claims.warnings + trace.warnings + passport.warnings),
    )
    _write_outputs(result, render_workspace_dashboard_markdown(result), output_path, json_path)
    return result


def render_weekly_review_markdown(result: WorkspaceWeeklyReviewResult) -> str:
    lines = [
        "# K-ResDev Weekly Review",
        "",
        "> Local operating review only. This does not certify official agency compliance, submission readiness, or scientific validity.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Review date | {result.review_date.isoformat()} |",
        f"| Status | {_escape(result.status)} |",
        f"| Evidence count | {result.evidence_count} |",
        f"| Report draft count | {result.report_count} |",
        f"| Approval count | {result.approval_count} |",
        f"| Doctor findings | {result.open_finding_count} |",
        f"| High findings | {result.high_finding_count} |",
        f"| Next actions | {result.action_count} |",
        f"| High-priority actions | {result.high_action_count} |",
        f"| Objectives | {result.objective_count} |",
        f"| Deadlines | {result.deadline_count} |",
        f"| Due soon deadlines | {result.due_soon_count} |",
        f"| Overdue deadlines | {result.overdue_count} |",
        f"| Review items | {result.item_count} |",
        "",
        "## Review Items",
        "",
        "| Severity | Category | Title | Message | Evidence | Artifacts | Due | Suggested Action |",
        "|---|---|---|---|---|---|---|---|",
    ]
    if not result.items:
        lines.append("| ok | weekly_review | No weekly operating items were generated. | - | - | - | - | Continue local review. |")
    for item in result.items:
        lines.append(
            "| {severity} | {category} | {title} | {message} | {evidence} | {artifacts} | {due} | {action} |".format(
                severity=_escape(item.severity),
                category=_escape(item.category),
                title=_escape(item.title),
                message=_escape(item.message or "-"),
                evidence=_escape(", ".join(item.evidence_ids) or "-"),
                artifacts=_format_paths(item.artifact_paths),
                due=item.due_date.isoformat() if item.due_date else "-",
                action=_escape(item.suggested_action or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_workspace_dashboard_markdown(result: WorkspaceDashboardResult) -> str:
    lines = [
        "# K-ResDev Workspace Dashboard",
        "",
        "> Local dashboard projection only. It summarizes generated operating artifacts and does not certify official agency compliance.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Generated at | {_escape(result.generated_at)} |",
        f"| Status | {_escape(result.status)} |",
        f"| Evidence | {result.evidence_count} |",
        f"| Reports | {result.report_count} |",
        f"| Approvals | {result.approval_count} |",
        f"| Findings | {result.finding_count} |",
        f"| High findings | {result.high_finding_count} |",
        f"| Actions | {result.action_count} |",
        f"| High actions | {result.high_action_count} |",
        f"| Objectives | {result.objective_count} |",
        f"| Deadlines | {result.deadline_count} |",
        f"| Due soon | {result.due_soon_count} |",
        f"| Overdue | {result.overdue_count} |",
        f"| Cards | {result.card_count} |",
        "",
        "## Cards",
        "",
        "| Severity | Area | Status | Value | Detail | Artifacts |",
        "|---|---|---:|---:|---|---|",
    ]
    if not result.cards:
        lines.append("| ok | Dashboard | ready | - | No dashboard cards were generated. | - |")
    for card in result.cards:
        lines.append(
            "| {severity} | {title} | {status} | {value} | {detail} | {artifacts} |".format(
                severity=_escape(card.severity),
                title=_escape(card.title),
                status=_escape(card.status),
                value=_escape(str(card.value)) if card.value is not None else "-",
                detail=_escape(card.detail or "-"),
                artifacts=_format_paths(card.artifact_paths),
            )
        )
    lines.append("")
    return "\n".join(lines)


def load_weekly_review(path: str | Path) -> WorkspaceWeeklyReviewResult:
    return WorkspaceWeeklyReviewResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def load_latest_weekly_review(root: str | Path) -> WorkspaceWeeklyReviewResult | None:
    state = Path(root) / "state"
    if not state.exists():
        return None
    for path in sorted(state.glob("weekly-review-*.json"), key=lambda item: item.name, reverse=True):
        try:
            return load_weekly_review(path)
        except Exception:
            continue
    return None


def load_workspace_dashboard(path: str | Path) -> WorkspaceDashboardResult:
    return WorkspaceDashboardResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def load_saved_workspace_dashboard(root: str | Path) -> WorkspaceDashboardResult | None:
    path = Path(root) / "state" / "workspace-dashboard.json"
    if not path.exists():
        return None
    try:
        return load_workspace_dashboard(path)
    except Exception:
        return None


def _item(
    *,
    category: str,
    title: str,
    severity: str,
    message: str | None = None,
    status: str = "needs_review",
    evidence_ids: list[str] | None = None,
    artifact_paths: list[str | Path] | None = None,
    due_date: date | None = None,
    suggested_action: str | None = None,
) -> WeeklyReviewItem:
    paths = [str(path) for path in artifact_paths or [] if path]
    item_id = _stable_id("WRV", category, title, severity, message or "", ",".join(paths))
    return WeeklyReviewItem(
        item_id=item_id,
        category=category,
        title=title,
        severity=severity,
        status=status,
        message=message,
        evidence_ids=evidence_ids or [],
        artifact_paths=paths,
        due_date=due_date,
        suggested_action=suggested_action,
    )


def _card(
    card_id: str,
    title: str,
    status: str,
    value: str | int | float | None,
    severity: str,
    detail: str | None,
    artifact_paths: list[str | Path | None],
) -> DashboardCard:
    return DashboardCard(
        card_id=card_id,
        title=title,
        status=status,
        value=value,
        severity=severity,
        detail=detail,
        artifact_paths=[str(path) for path in artifact_paths if path],
    )


def _write_outputs(result, markdown: str, output_path: str | Path | None, json_path: str | Path | None) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _load_evidence(workspace: Path) -> list[EvidenceItem]:
    path = workspace / "state" / "evidence-index.json"
    if not path.exists():
        return []
    try:
        return load_evidence_index(path)
    except Exception:
        return []


def _load_approvals(workspace: Path) -> list:
    path = workspace / "state" / "approvals"
    if not path.exists():
        return []
    try:
        return load_approval_records(path)
    except Exception:
        return []


def _without_finding_codes(doctor: WorkspaceDoctorResult, codes: set[str]) -> WorkspaceDoctorResult:
    findings = [finding for finding in doctor.findings if finding.code not in codes]
    status = _doctor_status_from_findings(findings)
    return doctor.model_copy(update={"findings": findings, "finding_count": len(findings), "status": status})


def _report_paths(workspace: Path) -> list[str]:
    reports = workspace / "reports"
    if not reports.exists():
        return []
    return [str(path) for path in sorted(reports.glob("*.md"), key=lambda item: item.as_posix()) if not is_operational_markdown(path)]


def _coerce_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _severity_from_priority(priority: str) -> str:
    return {"high": "high", "medium": "medium", "low": "low"}.get(priority, "medium")


def _severity_from_status(status: str, *, high: int = 0, medium: int = 0) -> str:
    if high or status in {"blocked", "impacted"}:
        return "high"
    if medium or status in {"needs_review", "actions_needed"}:
        return "medium"
    if status in {"ready_with_notes", "not_configured", "no_reports", "no_artifacts"}:
        return "low"
    return "low"


def _status_from_severities(severities) -> str:
    values = list(severities)
    if "high" in values:
        return "blocked"
    if "medium" in values:
        return "needs_review"
    if values:
        return "ready_with_notes"
    return "ready"


def _doctor_status_from_findings(findings) -> str:
    severities = [finding.severity for finding in findings]
    if "high" in severities:
        return "blocked"
    if "medium" in severities:
        return "needs_review"
    if severities:
        return "ready_with_notes"
    return "ready"


def _dedupe_items(items: list[WeeklyReviewItem]) -> list[WeeklyReviewItem]:
    seen: set[str] = set()
    result: list[WeeklyReviewItem] = []
    for item in items:
        if item.item_id in seen:
            continue
        seen.add(item.item_id)
        result.append(item)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.category, item.title, item.item_id))


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{digest}"


def _format_paths(paths: list[str]) -> str:
    if not paths:
        return "-"
    return "<br>".join(f"`{_escape(path)}`" for path in paths[:5])


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
