import json

from k_resdev_skill.approval import create_approval_record, write_approval_record
from k_resdev_skill.artifact_authority import generate_artifact_authority, load_artifact_authority, render_artifact_authority_markdown
from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_artifact_authority_flags_final_named_draft_and_low_authority_evidence(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    source = tmp_path / "inbox" / "metrics.csv"
    source.write_text("metric,value\nDice,0.8\n", encoding="utf-8")
    report = tmp_path / "reports" / "final-report.md"
    report.write_text("Final result cites [EVI-2026-LOW1234].\n", encoding="utf-8")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-LOW1234",
                source_file="inbox/metrics.csv",
                evidence_type="experiment_result",
                claim="Dice candidate.",
                status="needs_review",
            )
        ],
        tmp_path / "state",
    )

    result = generate_artifact_authority(tmp_path)
    rendered = render_artifact_authority_markdown(result)
    codes = {finding.code for finding in result.findings}
    levels = {record.authority_level for record in result.records}

    assert result.status == "blocked"
    assert "authority_projection_named_final_without_approval" in codes
    assert "authority_projection_cites_low_authority_evidence" in codes
    assert {"raw_source", "evidence_needs_review", "draft_projection"}.issubset(levels)
    assert "Authority projection only" in rendered


def test_artifact_authority_marks_hash_bound_approved_projection(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    source = tmp_path / "inbox" / "metrics.csv"
    source.write_text("metric,value\nDice,0.8\n", encoding="utf-8")
    report = tmp_path / "reports" / "monthly-report-2026-05.md"
    report.write_text("Accepted result cites [EVI-2026-ACPT1234].\n", encoding="utf-8")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-ACPT1234",
                source_file="inbox/metrics.csv",
                evidence_type="experiment_result",
                claim="Dice accepted.",
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
        target_path=str(report),
        reviewed_at="2026-05-18T09:00:00Z",
    )
    write_approval_record(approval, tmp_path / "state" / "approvals")

    result = generate_artifact_authority(tmp_path)
    report_records = [record for record in result.records if record.path == str(report)]

    assert report_records[0].authority_level == "approved_projection"
    assert "approved_projection" in result.authority_level_counts
    assert all(finding.code != "authority_projection_not_approved" for finding in result.findings)


def test_artifact_authority_flags_projection_citing_rejected_evidence(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report-2026-05.md"
    report.write_text("Rejected result cites [EVI-2026-BAD1234].\n", encoding="utf-8")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-BAD1234",
                source_file="inbox/missing.csv",
                evidence_type="experiment_result",
                claim="Rejected.",
                status="rejected",
            )
        ],
        tmp_path / "state",
    )

    result = generate_artifact_authority(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.high_count >= 1
    assert "authority_projection_cites_invalid_evidence" in codes
    assert "authority_evidence_invalid" in codes


def test_artifact_authority_flags_korean_final_named_projection(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "\uCD5C\uC885-\uC81C\uCD9C-report.md"
    report.write_text("# Final draft without approval\n", encoding="utf-8")

    result = generate_artifact_authority(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert "authority_projection_named_final_without_approval" in codes


def test_artifact_authority_cli_and_schema_round_trip(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "monthly-report-2026-05.md"
    report.write_text("# Draft\n", encoding="utf-8")
    output = tmp_path / "reports" / "artifact-authority.md"
    json_output = tmp_path / "state" / "artifact-authority.json"

    assert main(["artifact-authority", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["root"] == str(tmp_path)
    assert output.exists()
    assert load_artifact_authority(json_output).root == str(tmp_path)
    assert main(["validate-json", "artifact-authority", str(json_output)]) == 0
    assert main(["validate-json", "artifact-authority-record", str(json_output)]) == 0
    assert main(["validate-json", "artifact-authority-finding", str(json_output)]) == 0


def test_artifact_authority_integrates_with_workspace_operations_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    report = tmp_path / "reports" / "final-report.md"
    report.write_text("# Final draft without approval\n", encoding="utf-8")

    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor, action_plan=actions)
    pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    codes = {finding.code for finding in doctor.findings}
    titles = {action.title for action in actions.actions}
    authority_levels = {node.metadata.get("artifact_authority_level") for node in trace.nodes}

    assert "artifact_authority_high_findings" in codes
    assert "Review artifact authority levels" in titles
    assert summary.artifact_authority_high_count >= 1
    assert pack.artifact_authority_high_count >= 1
    assert "draft_projection" in authority_levels
    assert (tmp_path / "reports" / "artifact-authority.md").exists()
    assert (tmp_path / "state" / "artifact-authority.json").exists()
