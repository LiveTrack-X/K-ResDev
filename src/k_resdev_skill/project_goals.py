from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

from .approval_coverage import generate_workspace_approval_coverage
from .evidence_index import load_evidence_index
from .models import (
    EvidenceItem,
    GoalsReviewFinding,
    ProjectDeadline,
    ProjectGoalsFile,
    ProjectObjective,
    ProjectState,
    WorkspaceGoalsReviewResult,
)

TERMINAL_DEADLINE_STATUSES = {"submitted", "approved", "completed"}
PROJECT_GOALS_PATH = Path("state") / "project-goals.json"


def initialize_project_goals(
    root: str | Path,
    output_path: str | Path | None = None,
    overwrite: bool = False,
) -> ProjectGoalsFile:
    """Create a local goals/deadlines operating file without inventing official schedules."""

    workspace = Path(root)
    path = Path(output_path) if output_path is not None else workspace / PROJECT_GOALS_PATH
    if path.exists() and not overwrite:
        existing = load_project_goals(path)
        return existing.model_copy(update={"warnings": _unique([*existing.warnings, "skipped_existing"])})

    state = _load_project_state(workspace)
    warnings: list[str] = []
    objectives: list[ProjectObjective] = []
    deadlines: list[ProjectDeadline] = []
    if state is None:
        warnings.append("project_state_missing")
    else:
        objectives.extend(_objectives_from_project_state(state))
        deadlines.extend(_deadlines_from_project_state(state))
    if not objectives:
        warnings.append("no_objectives_seeded")
    if not deadlines:
        warnings.append("no_deadlines_seeded")

    goals = ProjectGoalsFile(
        project_id=state.project_id if state else None,
        title=state.title if state else None,
        status="needs_review",
        objectives=objectives,
        deadlines=deadlines,
        notes="Local K-ResDev operating file. Review and edit before relying on goals, deadlines, or report-readiness projections.",
        warnings=_unique(warnings),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(goals.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return goals


def generate_goals_review(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    today: date | str | None = None,
    due_soon_days: int = 14,
) -> WorkspaceGoalsReviewResult:
    """Review local goals/deadline readiness from K-ResDev metadata only."""

    workspace = Path(root)
    review_date = _coerce_date(today) or date.today()
    path = workspace / PROJECT_GOALS_PATH
    warnings: list[str] = []
    findings: list[GoalsReviewFinding] = []
    if not path.exists():
        result = WorkspaceGoalsReviewResult(
            root=str(workspace),
            status="not_configured",
            findings=[
                _finding(
                    "project_goals_missing",
                    "low",
                    "No project goals operating file found.",
                    path=path,
                    suggested_action="Run goals-init to create state/project-goals.json, then review local objectives and deadlines.",
                )
            ],
            finding_count=1,
            low_count=1,
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
            warnings=["project_goals_missing"],
        )
        _write_result(result, output_path, json_path)
        return result

    try:
        goals = load_project_goals(path)
    except Exception as exc:
        result = WorkspaceGoalsReviewResult(
            root=str(workspace),
            status="blocked",
            findings=[
                _finding(
                    "project_goals_unreadable",
                    "high",
                    f"Project goals file could not be read: {exc}",
                    path=path,
                    suggested_action="Fix state/project-goals.json before using deadline readiness checks.",
                )
            ],
            finding_count=1,
            high_count=1,
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
            warnings=[f"project_goals_unreadable:{exc}"],
        )
        _write_result(result, output_path, json_path)
        return result

    state = _load_project_state(workspace)
    evidence_by_id = _load_evidence_by_id(workspace, warnings)
    coverage_by_path = _approval_coverage_by_path(workspace)
    findings.extend(_review_goals_file(goals, path))
    findings.extend(_review_objectives(goals.objectives, state, evidence_by_id, path))
    findings.extend(_review_deadlines(goals.deadlines, goals.objectives, state, evidence_by_id, coverage_by_path, workspace, review_date, due_soon_days, path))

    findings = sorted(_dedupe_findings(findings), key=lambda item: (_severity_rank(item.severity), item.code, item.objective_id or "", item.deadline_id or "", item.path or ""))
    high_count = sum(1 for finding in findings if finding.severity == "high")
    medium_count = sum(1 for finding in findings if finding.severity == "medium")
    low_count = sum(1 for finding in findings if finding.severity == "low")
    active_deadlines = [deadline for deadline in goals.deadlines if deadline.status not in TERMINAL_DEADLINE_STATUSES]
    due_soon_count = sum(1 for deadline in active_deadlines if 0 <= (deadline.due_date - review_date).days <= due_soon_days)
    overdue_count = sum(1 for deadline in active_deadlines if deadline.due_date < review_date)
    at_risk_count = sum(1 for deadline in goals.deadlines if deadline.status in {"at_risk", "missed"} or any(f.deadline_id == deadline.deadline_id and f.severity in {"high", "medium"} for f in findings))
    status = "blocked" if high_count else "needs_review" if medium_count else "ready_with_notes" if low_count or warnings else "ready"
    result = WorkspaceGoalsReviewResult(
        root=str(workspace),
        status=status,
        project_id=goals.project_id,
        title=goals.title,
        objective_count=len(goals.objectives),
        deadline_count=len(goals.deadlines),
        due_soon_count=due_soon_count,
        overdue_count=overdue_count,
        at_risk_deadline_count=at_risk_count,
        finding_count=len(findings),
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        objectives=goals.objectives,
        deadlines=goals.deadlines,
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique([*goals.warnings, *warnings]),
    )
    _write_result(result, output_path, json_path)
    return result


def render_goals_review_markdown(result: WorkspaceGoalsReviewResult) -> str:
    lines = [
        "# K-ResDev Goals Review",
        "",
        "> Operating projection only. Goals and deadlines are local planning aids; this does not certify official schedules, agency compliance, submission readiness, or scientific validity.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Project | {_escape(result.project_id or '-')} |",
        f"| Title | {_escape(result.title or '-')} |",
        f"| Objectives | {result.objective_count} |",
        f"| Deadlines | {result.deadline_count} |",
        f"| Due soon | {result.due_soon_count} |",
        f"| Overdue | {result.overdue_count} |",
        f"| At-risk deadlines | {result.at_risk_deadline_count} |",
        f"| Findings | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        f"| Warnings | {_format_list(result.warnings)} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Objective | Deadline | Path | Message | Suggested Action |",
        "|---|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | goals_ready | - | - | - | No goals/deadline findings detected. | Continue human review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {objective} | {deadline} | {path} | {message} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                objective=_escape(finding.objective_id or "-"),
                deadline=_escape(finding.deadline_id or "-"),
                path=_escape(finding.path or "-"),
                message=_escape(finding.message),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(["", "## Objectives", "", "| ID | Status | Review | Weight | Links | Title |", "|---|---|---|---:|---|---|"])
    if not result.objectives:
        lines.append("| - | - | - | - | - | No objectives configured. |")
    for objective in result.objectives:
        links = _format_links(objective.linked_kpis, objective.linked_milestones, objective.linked_evidence_ids, objective.linked_report_paths)
        weight = "-" if objective.weight is None else _format_float(objective.weight)
        lines.append(f"| {_escape(objective.objective_id)} | {_escape(objective.status)} | {_escape(objective.review_status)} | {weight} | {links} | {_escape(objective.title)} |")
    lines.extend(["", "## Deadlines", "", "| ID | Due Date | Status | Review | Type | Links | Title |", "|---|---|---|---|---|---|---|"])
    if not result.deadlines:
        lines.append("| - | - | - | - | - | - | No deadlines configured. |")
    for deadline in result.deadlines:
        links = _format_links(deadline.linked_kpis, deadline.linked_milestones, deadline.linked_evidence_ids, deadline.linked_report_paths)
        if deadline.linked_objective_ids:
            links = f"objectives: {', '.join(deadline.linked_objective_ids)}; {links}"
        lines.append(
            f"| {_escape(deadline.deadline_id)} | {deadline.due_date.isoformat()} | {_escape(deadline.status)} | {_escape(deadline.review_status)} | {_escape(deadline.deliverable_type)} | {_escape(links)} | {_escape(deadline.title)} |"
        )
    lines.append("")
    return "\n".join(lines)


def load_project_goals(path: str | Path) -> ProjectGoalsFile:
    return ProjectGoalsFile.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def _write_result(result: WorkspaceGoalsReviewResult, output_path: str | Path | None, json_path: str | Path | None) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_goals_review_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _review_goals_file(goals: ProjectGoalsFile, path: Path) -> list[GoalsReviewFinding]:
    findings: list[GoalsReviewFinding] = []
    if not goals.objectives:
        findings.append(
            _finding("project_goals_no_objectives", "low", "No project objectives are configured.", path=path, suggested_action="Add local objectives linked to KPIs, milestones, evidence, or reports.")
        )
    if not goals.deadlines:
        findings.append(
            _finding("project_goals_no_deadlines", "low", "No project deadlines are configured.", path=path, suggested_action="Add local report, review, or milestone deadlines when known.")
        )
    if goals.status != "accepted":
        findings.append(
            _finding("project_goals_needs_review", "medium", f"Project goals file status is `{goals.status}`.", path=path, suggested_action="Have a human review state/project-goals.json before using it as an operating plan.")
        )
    weights = [objective.weight for objective in goals.objectives if objective.weight is not None]
    if weights:
        total = sum(weights)
        if not (_near(total, 1.0, 0.01) or _near(total, 100.0, 0.5)):
            findings.append(
                _finding(
                    "objective_weight_sum_unusual",
                    "medium",
                    f"Objective weights sum to {total:g}, not approximately 1.0 or 100.",
                    path=path,
                    suggested_action="Normalize objective weights or leave them blank if weighting is not used.",
                )
            )
    return findings


def _review_objectives(
    objectives: list[ProjectObjective],
    state: ProjectState | None,
    evidence_by_id: dict[str, EvidenceItem],
    path: Path,
) -> list[GoalsReviewFinding]:
    findings: list[GoalsReviewFinding] = []
    kpis = {item.kpi_id for item in state.kpis} if state else set()
    milestones = {item.milestone_id for item in state.milestones} if state else set()
    for objective in objectives:
        if objective.review_status != "accepted":
            findings.append(
                _finding(
                    "objective_needs_review",
                    "medium",
                    f"Objective `{objective.objective_id}` review_status is `{objective.review_status}`.",
                    objective_id=objective.objective_id,
                    path=path,
                    suggested_action="Review the objective, then mark it accepted or keep it visibly needs_review.",
                )
            )
        if objective.status in {"paused", "dormant"}:
            findings.append(
                _finding(
                    "objective_inactive",
                    "low",
                    f"Objective `{objective.objective_id}` is `{objective.status}`.",
                    objective_id=objective.objective_id,
                    path=path,
                    suggested_action="Confirm whether inactive objectives should stay in the current operating plan.",
                )
            )
        if not any([objective.linked_kpis, objective.linked_milestones, objective.linked_evidence_ids, objective.linked_report_paths]):
            findings.append(
                _finding(
                    "objective_missing_links",
                    "low",
                    f"Objective `{objective.objective_id}` is not linked to KPI, milestone, evidence, or report artifacts.",
                    objective_id=objective.objective_id,
                    path=path,
                    suggested_action="Link objectives to local K-ResDev artifacts so progress can be traced.",
                )
            )
        findings.extend(_missing_link_findings("objective_linked_kpi_missing", objective.linked_kpis, kpis, objective.objective_id, None, path, "KPI"))
        findings.extend(_missing_link_findings("objective_linked_milestone_missing", objective.linked_milestones, milestones, objective.objective_id, None, path, "milestone"))
        findings.extend(_evidence_link_findings(objective.linked_evidence_ids, evidence_by_id, objective.objective_id, None, path))
    return findings


def _review_deadlines(
    deadlines: list[ProjectDeadline],
    objectives: list[ProjectObjective],
    state: ProjectState | None,
    evidence_by_id: dict[str, EvidenceItem],
    coverage_by_path: dict[str, object],
    workspace: Path,
    today: date,
    due_soon_days: int,
    path: Path,
) -> list[GoalsReviewFinding]:
    findings: list[GoalsReviewFinding] = []
    objective_ids = {item.objective_id for item in objectives}
    kpis = {item.kpi_id for item in state.kpis} if state else set()
    milestones = {item.milestone_id for item in state.milestones} if state else set()
    for deadline in deadlines:
        terminal = deadline.status in TERMINAL_DEADLINE_STATUSES
        days_left = (deadline.due_date - today).days
        if deadline.review_status != "accepted":
            findings.append(
                _finding(
                    "deadline_needs_review",
                    "medium",
                    f"Deadline `{deadline.deadline_id}` review_status is `{deadline.review_status}`.",
                    deadline_id=deadline.deadline_id,
                    path=path,
                    suggested_action="Review deadline source and assumptions before relying on readiness checks.",
                )
            )
        if deadline.status == "missed":
            findings.append(
                _finding(
                    "deadline_marked_missed",
                    "high",
                    f"Deadline `{deadline.deadline_id}` is marked missed.",
                    deadline_id=deadline.deadline_id,
                    path=path,
                    suggested_action="Update the operating plan and downstream report expectations.",
                )
            )
        elif deadline.status == "at_risk":
            findings.append(
                _finding(
                    "deadline_marked_at_risk",
                    "medium",
                    f"Deadline `{deadline.deadline_id}` is marked at_risk.",
                    deadline_id=deadline.deadline_id,
                    path=path,
                    suggested_action="Resolve blockers or keep the risk visible in weekly/project review.",
                )
            )
        if not terminal and deadline.due_date < today:
            findings.append(
                _finding(
                    "deadline_overdue",
                    "high",
                    f"Deadline `{deadline.deadline_id}` was due on {deadline.due_date.isoformat()} and is not terminal.",
                    deadline_id=deadline.deadline_id,
                    path=path,
                    suggested_action="Mark the deadline submitted/approved only with supplied records, or keep it at_risk/missed.",
                )
            )
        elif not terminal and 0 <= days_left <= due_soon_days:
            findings.append(
                _finding(
                    "deadline_due_soon",
                    "medium",
                    f"Deadline `{deadline.deadline_id}` is due in {days_left} day(s).",
                    deadline_id=deadline.deadline_id,
                    path=path,
                    suggested_action="Review linked reports, evidence, and approvals before the due date.",
                )
            )
        findings.extend(_missing_link_findings("deadline_linked_objective_missing", deadline.linked_objective_ids, objective_ids, None, deadline.deadline_id, path, "objective"))
        findings.extend(_missing_link_findings("deadline_linked_kpi_missing", deadline.linked_kpis, kpis, None, deadline.deadline_id, path, "KPI"))
        findings.extend(_missing_link_findings("deadline_linked_milestone_missing", deadline.linked_milestones, milestones, None, deadline.deadline_id, path, "milestone"))
        findings.extend(_evidence_link_findings(deadline.linked_evidence_ids, evidence_by_id, None, deadline.deadline_id, path))
        findings.extend(_deadline_report_findings(deadline, workspace, coverage_by_path, path, terminal))
    return findings


def _deadline_report_findings(
    deadline: ProjectDeadline,
    workspace: Path,
    coverage_by_path: dict[str, object],
    goals_path: Path,
    terminal: bool,
) -> list[GoalsReviewFinding]:
    findings: list[GoalsReviewFinding] = []
    for report_path in deadline.linked_report_paths:
        resolved = _resolve_path(workspace, report_path)
        if not resolved.exists():
            findings.append(
                _finding(
                    "deadline_linked_report_missing",
                    "high" if deadline.status == "missed" else "medium",
                    f"Deadline `{deadline.deadline_id}` links missing report `{report_path}`.",
                    deadline_id=deadline.deadline_id,
                    path=goals_path,
                    suggested_action="Create the report draft or update the deadline link.",
                )
            )
            continue
        if deadline.approval_required and not terminal:
            coverage = coverage_by_path.get(_normalize_path(resolved))
            approved = bool(getattr(coverage, "approved", False)) if coverage is not None else False
            if not approved:
                findings.append(
                    _finding(
                        "deadline_report_approval_missing",
                        "medium",
                        f"Deadline `{deadline.deadline_id}` links report `{report_path}` without current approved coverage.",
                        deadline_id=deadline.deadline_id,
                        path=goals_path,
                        suggested_action="Record a supplied human approval for the linked report or keep the deadline at risk.",
                    )
                )
    return findings


def _missing_link_findings(
    code: str,
    values: list[str],
    known: set[str],
    objective_id: str | None,
    deadline_id: str | None,
    path: Path,
    label: str,
) -> list[GoalsReviewFinding]:
    if not values or known:
        missing = [value for value in values if value not in known]
    else:
        missing = values
    return [
        _finding(
            code,
            "high",
            f"Linked {label} `{value}` was not found in project state.",
            objective_id=objective_id,
            deadline_id=deadline_id,
            path=path,
            suggested_action="Update the link or refresh state/project-state.json from reviewed project metadata.",
        )
        for value in missing
    ]


def _evidence_link_findings(
    evidence_ids: list[str],
    evidence_by_id: dict[str, EvidenceItem],
    objective_id: str | None,
    deadline_id: str | None,
    path: Path,
) -> list[GoalsReviewFinding]:
    findings: list[GoalsReviewFinding] = []
    for evidence_id in evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            findings.append(
                _finding(
                    "goals_linked_evidence_missing",
                    "high",
                    f"Linked evidence `{evidence_id}` was not found in the evidence index.",
                    objective_id=objective_id,
                    deadline_id=deadline_id,
                    path=path,
                    suggested_action="Run intake or update the evidence link.",
                )
            )
            continue
        status = str(evidence.status)
        if status in {"rejected", "superseded"}:
            findings.append(
                _finding(
                    "goals_linked_evidence_invalid",
                    "high",
                    f"Linked evidence `{evidence_id}` is `{status}`.",
                    objective_id=objective_id,
                    deadline_id=deadline_id,
                    path=path,
                    suggested_action="Remove rejected/superseded evidence links from goals and deadlines.",
                )
            )
        elif status != "accepted":
            findings.append(
                _finding(
                    "goals_linked_evidence_needs_review",
                    "medium",
                    f"Linked evidence `{evidence_id}` is `{status}`.",
                    objective_id=objective_id,
                    deadline_id=deadline_id,
                    path=path,
                    suggested_action="Review linked evidence before treating the objective/deadline as ready.",
                )
            )
    return findings


def _objectives_from_project_state(state: ProjectState) -> list[ProjectObjective]:
    objectives: list[ProjectObjective] = []
    for index, goal in enumerate(state.goals, start=1):
        if not isinstance(goal, dict):
            continue
        title = str(goal.get("title") or goal.get("name") or "").strip()
        if not title:
            continue
        objective_id = str(goal.get("objective_id") or goal.get("goal_id") or f"OBJ-{index:04d}").strip()
        objectives.append(
            ProjectObjective(
                objective_id=objective_id,
                title=title,
                status=str(goal.get("status") or "active"),
                review_status=str(goal.get("review_status") or "needs_review"),
                linked_kpis=[str(value) for value in goal.get("linked_kpis", [])],
                linked_milestones=[str(value) for value in goal.get("linked_milestones", [])],
                linked_evidence_ids=[str(value) for value in goal.get("linked_evidence_ids", [])],
                notes=goal.get("notes"),
            )
        )
    return objectives


def _deadlines_from_project_state(state: ProjectState) -> list[ProjectDeadline]:
    deadlines: list[ProjectDeadline] = []
    for milestone in state.milestones:
        if milestone.due_date is None:
            continue
        deadlines.append(
            ProjectDeadline(
                deadline_id=f"DL-{milestone.milestone_id}",
                due_date=milestone.due_date,
                title=milestone.name,
                deliverable_type=milestone.deliverable or "milestone",
                linked_milestones=[milestone.milestone_id],
                linked_evidence_ids=list(milestone.evidence_ids),
                status="planned" if str(milestone.status) in {"planned", "in_progress", "needs_review"} else str(milestone.status),
                review_status="needs_review",
                notes=milestone.notes,
            )
        )
    return deadlines


def _load_project_state(workspace: Path) -> ProjectState | None:
    path = workspace / "state" / "project-state.json"
    if not path.exists():
        return None
    try:
        return ProjectState.model_validate_json(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _load_evidence_by_id(workspace: Path, warnings: list[str]) -> dict[str, EvidenceItem]:
    path = workspace / "state" / "evidence-index.json"
    if not path.exists():
        return {}
    try:
        return {item.evidence_id: item for item in load_evidence_index(path)}
    except Exception as exc:
        warnings.append(f"evidence_index_unreadable:{exc}")
        return {}


def _approval_coverage_by_path(workspace: Path) -> dict[str, object]:
    result = generate_workspace_approval_coverage(workspace)
    return {_normalize_path(Path(item.path)): item for item in result.items}


def _resolve_path(workspace: Path, path: str) -> Path:
    target = Path(path)
    if target.is_absolute():
        return target
    return workspace / target


def _normalize_path(path: Path) -> str:
    try:
        return str(path.resolve()).lower()
    except OSError:
        return str(path).lower()


def _coerce_date(value: date | str | None) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return None


def _finding(
    code: str,
    severity: str,
    message: str,
    objective_id: str | None = None,
    deadline_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> GoalsReviewFinding:
    return GoalsReviewFinding(
        code=code,
        severity=severity,
        message=message,
        objective_id=objective_id,
        deadline_id=deadline_id,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _dedupe_findings(findings: Iterable[GoalsReviewFinding]) -> list[GoalsReviewFinding]:
    seen: set[tuple[str, str | None, str | None, str]] = set()
    result: list[GoalsReviewFinding] = []
    for finding in findings:
        key = (finding.code, finding.objective_id, finding.deadline_id, finding.message)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _near(value: float, target: float, tolerance: float) -> bool:
    return abs(value - target) <= tolerance


def _format_links(kpis: list[str], milestones: list[str], evidence_ids: list[str], report_paths: list[str]) -> str:
    parts = []
    if kpis:
        parts.append(f"kpis: {', '.join(kpis)}")
    if milestones:
        parts.append(f"milestones: {', '.join(milestones)}")
    if evidence_ids:
        parts.append(f"evidence: {', '.join(evidence_ids)}")
    if report_paths:
        parts.append(f"reports: {', '.join(report_paths)}")
    return "; ".join(parts) or "-"


def _format_list(values: list[str]) -> str:
    if not values:
        return "-"
    return ", ".join(f"`{_escape(value)}`" for value in values[:20])


def _format_float(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()
