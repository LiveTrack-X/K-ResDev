import json

from k_resdev_skill.approval import create_approval_record, write_approval_record
from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.workspace import initialize_workspace
from k_resdev_skill.workspace_summary import generate_workspace_summary, render_workspace_summary_markdown


def test_workspace_summary_combines_operational_counts(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-EXPA1234",
                source_file="metrics.csv",
                evidence_type="experiment_result",
                claim="Dice result candidate.",
                status="accepted",
            ),
            EvidenceItem(
                evidence_id="EVI-2026-BUDG1234",
                source_file="receipt.xlsx",
                evidence_type="budget_evidence",
                claim="Receipt candidate.",
                value={"amount": 1000, "category": "supplies"},
                risk_flags=["budget_metadata_incomplete"],
            ),
        ],
        tmp_path / "state",
    )
    approval = create_approval_record(
        "report",
        "monthly-2026-05",
        "approved",
        "Reviewer",
        evidence_ids=["EVI-2026-EXPA1234"],
        reviewed_at="2026-05-17T09:00:00Z",
    )
    write_approval_record(approval, tmp_path / "state" / "approvals")
    (tmp_path / "reports" / "monthly-report.md").write_text("# Monthly Report\n", encoding="utf-8")
    (tmp_path / "reports" / "monthly-report.html").write_text("Draft projection only\n", encoding="utf-8")
    (tmp_path / "reports" / "analysis" / "metrics-analysis-run.json").write_text("{}\n", encoding="utf-8")

    output = tmp_path / "reports" / "workspace-summary.md"
    json_output = tmp_path / "state" / "workspace-summary.json"
    summary = generate_workspace_summary(tmp_path, output_path=output, json_path=json_output, max_actions=3)

    assert summary.evidence_count == 2
    assert summary.approval_count == 1
    assert summary.profile_id == "national-rnd-basic"
    assert summary.profile_integrity_status == "needs_review"
    assert summary.profile_source_count == 0
    assert summary.goals_review_status == "needs_review"
    assert summary.objective_count == 0
    assert summary.deadline_count == 0
    assert summary.goals_review_finding_count >= 1
    assert summary.budget_ledger_status == "needs_review"
    assert summary.budget_ledger_finding_count >= 1
    assert summary.evidence_by_type["budget_evidence"] == 1
    assert summary.evidence_by_status["needs_review"] == 1
    assert summary.risk_flag_counts["budget_metadata_incomplete"] == 1
    assert len(summary.report_paths) == 1
    assert len(summary.export_paths) == 1
    assert len(summary.analysis_manifest_paths) == 1
    assert len(summary.top_actions) <= 3
    assert output.read_text(encoding="utf-8").startswith("# K-ResDev Workspace Summary")
    assert json.loads(json_output.read_text(encoding="utf-8"))["evidence_count"] == 2


def test_workspace_summary_empty_workspace_surfaces_blocked_handoff(tmp_path):
    summary = generate_workspace_summary(tmp_path)
    rendered = render_workspace_summary_markdown(summary)

    assert summary.status == "blocked"
    assert summary.evidence_count == 0
    assert summary.actions_by_priority["high"] >= 1
    assert "Initialize the workspace skeleton" in rendered


def test_workspace_summary_cli_writes_outputs(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "workspace-summary.md"
    json_output = tmp_path / "state" / "workspace-summary.json"

    assert (
        main(
            [
                "workspace-summary",
                "--root",
                str(tmp_path),
                "--output",
                str(output),
                "--json",
                str(json_output),
                "--max-actions",
                "2",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["root"] == str(tmp_path)
    assert len(payload["top_actions"]) <= 2
    assert output.exists()
    assert json_output.exists()
