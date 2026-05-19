import json

from k_resdev_skill.admin_operating import review_admin_calendar, review_admin_change_ledger
from k_resdev_skill.project_goals import initialize_project_goals
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor


def test_admin_change_ledger_distinguishes_approved_and_unapproved_changes(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    target = tmp_path / "state" / "project-state.json"
    target_hash = _sha256(target)
    (tmp_path / "state" / "admin-change-ledger.json").write_text(
        json.dumps(
            {
                "changes": [
                    {
                        "change_id": "CHG-APPROVED",
                        "change_type": "budget_change",
                        "target_id": "BUD-2026-001",
                        "decision": "approved",
                        "reviewer": "Reviewer",
                        "approved_at": "2026-05-19T00:00:00Z",
                        "approval_id": "APR-2026-001",
                        "target_path": str(target),
                        "target_hash": target_hash,
                    },
                    {
                        "change_id": "CHG-PENDING",
                        "change_type": "kpi_change",
                        "target_id": "KPI-001",
                        "decision": "needs_review",
                    },
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = review_admin_change_ledger(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.change_count == 2
    assert result.approved_count == 1
    assert result.pending_count == 1
    assert "admin_change_unresolved" in codes
    assert not any(finding.change_id == "CHG-APPROVED" for finding in result.findings)


def test_admin_change_ledger_flags_unapproved_change_referenced_in_report(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    (tmp_path / "reports" / "monthly-report.md").write_text("Changed value uses CHG-PENDING.\n", encoding="utf-8")
    (tmp_path / "state" / "admin-change-ledger.json").write_text(
        json.dumps(
            {
                "changes": [
                    {
                        "change_id": "CHG-PENDING",
                        "change_type": "period_change",
                        "target_id": "PERIOD",
                        "decision": "needs_review",
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = review_admin_change_ledger(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "admin_change_unapproved_referenced" in codes

    doctor = run_workspace_doctor(tmp_path)
    assert "admin_change_ledger_high_findings" in {finding.code for finding in doctor.findings}


def test_admin_calendar_links_obligations_to_project_deadlines(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    initialize_project_goals(tmp_path)
    (tmp_path / "state" / "project-goals.json").write_text(
        json.dumps(
            {
                "project_id": "PRJ-2026-0001",
                "title": "Demo Project",
                "status": "needs_review",
                "deadlines": [
                    {
                        "deadline_id": "DL-REPORT-001",
                        "due_date": "2026-05-25",
                        "title": "Monthly report",
                        "deliverable_type": "report",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "state" / "admin-obligations.json").write_text(
        json.dumps(
            {
                "obligations": [
                    {
                        "obligation_id": "ADM-REPORT-001",
                        "title": "Report",
                        "obligation_type": "reporting",
                        "source_system": "IRIS",
                        "linked_deadline_id": "DL-REPORT-001",
                        "status": "needs_review",
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = review_admin_calendar(tmp_path, today=__import__("datetime").date(2026, 5, 19))

    assert result.linked_deadline_count == 1
    assert result.due_soon_count == 1
    assert "admin_calendar_deadline_missing" not in {finding.code for finding in result.findings}


def _sha256(path):
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
