from __future__ import annotations

import re

from .models import KPI, Milestone, ProjectState

TITLE_RE = re.compile(r"^(?:project|title|과제명|연구과제명)\s*[:：]\s*(.+)$", re.IGNORECASE)
PERIOD_RE = re.compile(r"^(?:period|기간|연구기간|사업기간)\s*[:：]\s*(.+)$", re.IGNORECASE)
KPI_RE = re.compile(
    r"(?:KPI|성과지표|지표)\s*[:：-]?\s*(?P<name>[^,\n;]+?)\s*(?:target|목표|기준)?\s*[:：]?\s*(?P<target>\d+(?:\.\d+)?%?)",
    re.IGNORECASE,
)
MILESTONE_RE = re.compile(
    r"(?:milestone|마일스톤|단계|일정)\s*[:：-]?\s*(?P<name>[^,\n;]+?)(?:\s+|,\s*)(?P<date>\d{4}[-.]\d{1,2}[-.]\d{1,2})",
    re.IGNORECASE,
)


def extract_project_state_from_text(
    text: str,
    project_id: str = "PRJ-NEEDS-REVIEW",
) -> ProjectState:
    """Extract a conservative project-state draft from plan text."""

    title = "needs_review"
    period = "needs_review"
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line:
            continue
        title_match = TITLE_RE.match(line)
        if title_match:
            title = title_match.group(1).strip()
        period_match = PERIOD_RE.match(line)
        if period_match:
            period = period_match.group(1).strip()

    kpis = [
        KPI(
            kpi_id=f"KPI-{index:02d}",
            name=match.group("name").strip(),
            target=match.group("target"),
            status="needs_review",
        )
        for index, match in enumerate(KPI_RE.finditer(text), start=1)
    ]
    milestones = [
        Milestone(
            milestone_id=f"MIL-{index:02d}",
            name=match.group("name").strip(),
            due_date=match.group("date").replace(".", "-"),
            status="needs_review",
        )
        for index, match in enumerate(MILESTONE_RE.finditer(text), start=1)
    ]

    return ProjectState(
        project_id=project_id,
        title=title,
        period=period,
        status="planning",
        kpis=kpis,
        milestones=milestones,
    )
