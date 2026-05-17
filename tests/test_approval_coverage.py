import json

from k_resdev_skill.approval import create_approval_record, write_approval_record
from k_resdev_skill.approval_coverage import generate_workspace_approval_coverage
from k_resdev_skill.cli import main
from k_resdev_skill.workspace import initialize_workspace


def test_workspace_approval_coverage_flags_missing_report_approval(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report-2026-05.md"
    report.write_text("# Monthly Report\n\nDraft projection only.\n", encoding="utf-8")

    result = generate_workspace_approval_coverage(
        tmp_path,
        output_path=tmp_path / "reports" / "approval-coverage.md",
        json_path=tmp_path / "state" / "approval-coverage.json",
    )

    assert result.status == "needs_review"
    assert result.artifact_count == 1
    assert result.missing_count == 1
    assert result.items[0].target_id == "monthly-report-2026-05"
    assert "monthly-2026-05" in result.items[0].target_id_candidates
    assert (tmp_path / "reports" / "approval-coverage.md").read_text(encoding="utf-8").startswith("# Workspace Approval Coverage")
    assert json.loads((tmp_path / "state" / "approval-coverage.json").read_text(encoding="utf-8"))["missing_count"] == 1


def test_workspace_approval_coverage_matches_target_id_and_target_path(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report-2026-05.md"
    export = tmp_path / "reports" / "monthly-report-2026-05.txt"
    report.write_text("# Monthly Report\n\nDraft projection only.\n", encoding="utf-8")
    export.write_text("Draft projection only.\n", encoding="utf-8")
    target_id_record = create_approval_record(
        "report",
        "monthly-2026-05",
        "approved",
        "Reviewer",
        reviewed_at="2026-05-17T09:00:00Z",
    )
    target_path_record = create_approval_record(
        "report",
        "monthly-report-2026-05-export",
        "approved",
        "Reviewer",
        target_path="reports/monthly-report-2026-05.txt",
        reviewed_at="2026-05-17T10:00:00Z",
    )
    write_approval_record(target_id_record, tmp_path / "state" / "approvals")
    write_approval_record(target_path_record, tmp_path / "state" / "approvals")

    result = generate_workspace_approval_coverage(tmp_path)
    decisions = {item.path: item.approved for item in result.items}

    assert result.status == "ready"
    assert result.approved_count == 2
    assert result.missing_count == 0
    assert decisions[str(report)] is True
    assert decisions[str(export)] is True


def test_approval_coverage_cli_writes_outputs(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    (tmp_path / "reports" / "monthly-report-2026-05.md").write_text("# Monthly Report\n", encoding="utf-8")
    output = tmp_path / "reports" / "approval-coverage.md"
    json_output = tmp_path / "state" / "approval-coverage.json"

    assert main(["approval-coverage", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["root"] == str(tmp_path)
    assert payload["missing_count"] == 1
    assert output.exists()
    assert json_output.exists()
