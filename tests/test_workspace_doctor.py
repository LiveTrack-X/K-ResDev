import hashlib
import json

from k_resdev_skill.approval import create_approval_record, write_approval_record
from k_resdev_skill.bibliography import import_bibliography
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


def test_workspace_doctor_flags_report_approval_coverage(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    (tmp_path / "reports" / "monthly-report-2026-05.md").write_text("# Monthly Report\n", encoding="utf-8")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert "report_approval_missing" in codes

    approval = create_approval_record(
        "report",
        "monthly-2026-05",
        "approved",
        "Reviewer",
        target_path="reports/monthly-report-2026-05.md",
        reviewed_at="2026-05-17T09:00:00Z",
    )
    write_approval_record(approval, tmp_path / "state" / "approvals")

    approved_result = run_workspace_doctor(tmp_path)
    approved_codes = {finding.code for finding in approved_result.findings}

    assert "report_approval_missing" not in approved_codes


def test_workspace_doctor_flags_approval_target_hash_mismatch(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report-2026-05.md"
    report.write_text("# Monthly Report\n", encoding="utf-8")
    approval = create_approval_record(
        "report",
        "monthly-2026-05",
        "approved",
        "Reviewer",
        target_path=str(report),
        reviewed_at="2026-05-17T09:00:00Z",
    )
    write_approval_record(approval, tmp_path / "state" / "approvals")
    report.write_text("# Monthly Report\n\nChanged.\n", encoding="utf-8")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "approval_target_hash_mismatch" in codes


def test_workspace_doctor_flags_report_integrity_findings(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-ABCD1234",
                source_file="metrics.csv",
                evidence_type="experiment_result",
                claim="Metric candidate.",
                value={"score": 0.81},
                status="accepted",
            )
        ],
        tmp_path / "state",
    )
    (tmp_path / "reports" / "monthly-report-2026-05.md").write_text("Accuracy reached 95%.\n", encoding="utf-8")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "report_integrity_high_findings" in codes


def test_workspace_doctor_flags_bibliography_integrity_findings(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    (tmp_path / "reports" / "manuscript.md").write_text("See [@missing2024].\n", encoding="utf-8")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "bibliography_integrity_high_findings" in codes


def test_workspace_doctor_flags_citation_support_findings(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    bib = tmp_path / "references" / "library.bib"
    bib.write_text(
        """@article{kim2026,
  title = {Small Lesion Evidence},
  author = {Kim, Mina},
  year = {2026},
  journal = {Journal of Research Operations}
}
""",
        encoding="utf-8",
    )
    import_bibliography(bib, tmp_path / "state")
    (tmp_path / "reports" / "manuscript.md").write_text("See [@kim2026].\n", encoding="utf-8")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert "citation_support_review_findings" in codes


def test_workspace_doctor_flags_source_hash_mismatch(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    source = tmp_path / "inbox" / "metrics.csv"
    source.write_text("case_id,dice\nA,0.81\n", encoding="utf-8")
    original_hash = _sha256(source)
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-ABCD1234",
                source_file="inbox/metrics.csv",
                source_hash=original_hash,
                evidence_type="experiment_result",
                claim="Metric candidate.",
                status="accepted",
            )
        ],
        tmp_path / "state",
    )

    source.write_text("case_id,dice\nA,0.12\n", encoding="utf-8")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "source_hash_mismatch" in codes


def test_workspace_doctor_flags_missing_hashed_source(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-ABCD1234",
                source_file="inbox/missing.csv",
                source_hash="sha256:" + "0" * 64,
                evidence_type="experiment_result",
                claim="Metric candidate.",
                status="accepted",
            )
        ],
        tmp_path / "state",
    )

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "source_file_missing" in codes


def test_doctor_cli_writes_outputs(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "readiness.md"
    json_output = tmp_path / "state" / "readiness.json"

    assert main(["doctor", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["root"] == str(tmp_path)
    assert output.exists()
    assert json_output.exists()


def _sha256(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
