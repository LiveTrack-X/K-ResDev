import json

from k_resdev_skill.approval import create_approval_record, write_approval_record
from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor


def test_workspace_doctor_empty_workspace_flags_missing_operational_artifacts(tmp_path):
    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "missing_evidence_index" in codes
    assert "approval_missing" in codes
    assert "profile_missing" in codes
    assert "analysis_manifest_missing" in codes


def test_workspace_doctor_reports_evidence_count_and_review_gaps(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    evidence = EvidenceItem(
        evidence_id="EVI-2026-ABCD1234",
        source_file="receipt.xlsx",
        evidence_type="budget_evidence",
        claim="Invoice candidate.",
        value={"amount": 1000, "category": "supplies"},
        risk_flags=["budget_metadata_incomplete"],
    )
    write_evidence_index([evidence], tmp_path / "state")

    result = run_workspace_doctor(tmp_path, tmp_path / "reports" / "readiness.md", tmp_path / "state" / "readiness.json")
    codes = [finding.code for finding in result.findings]

    assert result.evidence_count == 1
    assert result.status == "needs_review"
    assert "evidence_needs_review" in codes
    assert "evidence_risk_flags" in codes
    assert "budget_metadata_gap" in codes
    assert (tmp_path / "reports" / "readiness.md").read_text(encoding="utf-8").startswith("# K-ResDev Workspace Readiness")
    assert json.loads((tmp_path / "state" / "readiness.json").read_text(encoding="utf-8"))["evidence_count"] == 1


def test_workspace_doctor_approval_record_reduces_approval_missing(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-ABCD1234",
                source_file="metrics.csv",
                evidence_type="experiment_result",
                claim="Metric candidate.",
                status="accepted",
            )
        ],
        tmp_path / "state",
    )
    approval = create_approval_record(
        "report",
        "monthly-2026-05",
        "approved",
        "Reviewer",
        evidence_ids=["EVI-2026-ABCD1234"],
        reviewed_at="2026-05-17T09:00:00Z",
    )
    write_approval_record(approval, tmp_path / "state" / "approvals")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.approval_count == 1
    assert "approval_missing" not in codes


def test_doctor_cli_writes_outputs(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "readiness.md"
    json_output = tmp_path / "state" / "readiness.json"

    assert main(["doctor", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["root"] == str(tmp_path)
    assert output.exists()
    assert json_output.exists()
