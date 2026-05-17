import json

from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.report_integrity import generate_workspace_report_integrity
from k_resdev_skill.workspace import initialize_workspace


def test_workspace_report_integrity_flags_unsupported_and_mismatched_claims(tmp_path):
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
    report = tmp_path / "reports" / "monthly-report-2026-05.md"
    report.write_text(
        "\n".join(
            [
                "# Monthly Report",
                "",
                "Accuracy reached 95%.",
                "The linked metric was 0.92 with EVI-2026-ABCD1234.",
            ]
        ),
        encoding="utf-8",
    )

    result = generate_workspace_report_integrity(
        tmp_path,
        output_path=tmp_path / "reports" / "report-integrity.md",
        json_path=tmp_path / "state" / "report-integrity.json",
    )
    codes = {finding.code for item in result.items for finding in item.findings}

    assert result.status == "blocked"
    assert result.report_count == 1
    assert result.high_count >= 2
    assert "unsupported_numeric_claim" in codes
    assert "numeric_evidence_mismatch" in codes
    assert (tmp_path / "reports" / "report-integrity.md").read_text(encoding="utf-8").startswith("# Workspace Report Integrity")
    assert json.loads((tmp_path / "state" / "report-integrity.json").read_text(encoding="utf-8"))["status"] == "blocked"


def test_workspace_report_integrity_no_reports_is_explicit(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    result = generate_workspace_report_integrity(tmp_path)

    assert result.status == "no_reports"
    assert result.report_count == 0


def test_report_integrity_cli_writes_outputs(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index([], tmp_path / "state")
    (tmp_path / "reports" / "monthly-report-2026-05.md").write_text("Accuracy reached 95%.\n", encoding="utf-8")
    output = tmp_path / "reports" / "report-integrity.md"
    json_output = tmp_path / "state" / "report-integrity.json"

    assert main(["report-integrity", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["root"] == str(tmp_path)
    assert payload["high_count"] >= 1
    assert output.exists()
    assert json_output.exists()
