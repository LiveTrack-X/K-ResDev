import json

from k_resdev_skill.cli import main
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_discovery import discover_workspace, load_workspace_discovery, render_workspace_discovery_markdown
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary


def test_workspace_discovery_scans_messy_folder_without_writing(tmp_path):
    (tmp_path / "plan.docx").write_bytes(b"docx")
    (tmp_path / "metrics.csv").write_text("metric,value\nDice,0.8\n", encoding="utf-8")
    (tmp_path / "library.bib").write_text("@article{kim2026,title={Paper}}\n", encoding="utf-8")

    result = discover_workspace(tmp_path)
    rendered = render_workspace_discovery_markdown(result)

    assert result.status == "needs_setup"
    assert result.file_count == 3
    assert result.loose_candidate_count == 3
    assert "inbox" in result.missing_standard_dirs
    assert result.role_counts["plan_candidate"] == 1
    assert result.role_counts["data_source"] == 1
    assert result.role_counts["reference_source"] == 1
    assert {proposal.destructive for proposal in result.proposals} == {False}
    assert any(proposal.title == "Initialize a K-ResDev workspace skeleton" for proposal in result.proposals)
    assert any(proposal.title == "Review loose source candidates before intake" for proposal in result.proposals)
    assert "does not move, rename, delete, or modify raw files" in rendered
    assert not (tmp_path / "state").exists()
    assert not (tmp_path / "reports").exists()


def test_workspace_discovery_initialized_workspace_proposes_generation_only(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    (tmp_path / "inbox" / "metrics.csv").write_text("metric,value\nDice,0.8\n", encoding="utf-8")
    (tmp_path / "references" / "library.bib").write_text("@article{kim2026,title={Paper}}\n", encoding="utf-8")

    output = tmp_path / "reports" / "workspace-discovery.md"
    json_output = tmp_path / "state" / "workspace-discovery.json"
    result = discover_workspace(tmp_path, output_path=output, json_path=json_output)
    titles = {proposal.title for proposal in result.proposals}

    assert result.status == "ready_with_notes"
    assert result.missing_standard_dirs == []
    assert result.loose_candidate_count == 0
    assert "Run evidence intake on inbox sources" in titles
    assert "Build the reference corpus review index" in titles
    assert output.exists()
    assert load_workspace_discovery(json_output).root == str(tmp_path)


def test_workspace_discovery_cli_and_schema_round_trip(tmp_path, capsys):
    (tmp_path / "proposal.pdf").write_bytes(b"%PDF-1.4")
    output = tmp_path / "reports" / "workspace-discovery.md"
    json_output = tmp_path / "state" / "workspace-discovery.json"

    assert main(["discover-workspace", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output), "--max-items", "20"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["root"] == str(tmp_path)
    assert output.exists()
    assert json_output.exists()
    assert main(["validate-json", "workspace-discovery", str(json_output)]) == 0
    assert main(["validate-json", "workspace-discovery-item", "templates/workspace-discovery-item.json"]) == 0
    assert main(["validate-json", "workspace-setup-proposal", "templates/workspace-setup-proposal.json"]) == 0


def test_workspace_discovery_integrates_with_doctor_actions_summary_and_review_pack(tmp_path):
    (tmp_path / "plan.pdf").write_bytes(b"%PDF-1.4")

    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor, action_plan=actions)
    pack = generate_workspace_review_pack(tmp_path)

    codes = {finding.code for finding in doctor.findings}
    titles = {action.title for action in actions.actions}

    assert "workspace_discovery_setup_needed" in codes
    assert "workspace_discovery_review_needed" in codes
    assert "Review workspace discovery proposal" in titles
    assert summary.discovery_status == "needs_setup"
    assert summary.discovery_loose_candidate_count == 1
    assert pack.discovery_status == "needs_setup"
    assert pack.discovery_loose_candidate_count == 1
    assert (tmp_path / "reports" / "workspace-discovery.md").exists()
    assert (tmp_path / "state" / "workspace-discovery.json").exists()
