import hashlib
import json

from k_resdev_skill.approval import create_approval_record, write_approval_record
from k_resdev_skill.bibliography import import_bibliography
from k_resdev_skill.citation_support import create_citation_support_record, write_citation_support_record
from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack, render_workspace_review_pack_markdown
from k_resdev_skill.workspace_summary import generate_workspace_summary, render_workspace_summary_markdown
from k_resdev_skill.workspace_trace import generate_workspace_trace, render_workspace_trace_markdown


def test_workspace_trace_links_sources_evidence_reports_approvals_and_citation_support(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    source = tmp_path / "inbox" / "metrics.csv"
    source.write_text("case_id,dice\nA,0.81\n", encoding="utf-8")
    report = tmp_path / "reports" / "monthly-report-2026-05.md"
    report.write_text("Dice reached 0.81 [EVI-2026-ABCD1234]. See [@kim2026].\n", encoding="utf-8")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-ABCD1234",
                source_file="inbox/metrics.csv",
                source_hash=_sha256(source),
                evidence_type="experiment_result",
                claim="Dice reached 0.81.",
                value={"dice": 0.81},
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
        evidence_ids=["EVI-2026-ABCD1234"],
        reviewed_at="2026-05-17T09:00:00Z",
    )
    write_approval_record(approval, tmp_path / "state" / "approvals")
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
    import_result = import_bibliography(bib, tmp_path / "state")
    bibliography_id = json.loads((tmp_path / "state" / "bibliography-index.json").read_text(encoding="utf-8"))["items"][0]["bibliography_id"]
    support = create_citation_support_record(
        bibliography_id=bibliography_id,
        citation_key="kim2026",
        claim="Dice reached 0.81.",
        decision="supports",
        reviewer="Reviewer",
        evidence_ids=["EVI-2026-ABCD1234"],
        locator="p. 1",
        quote="Dice reached 0.81.",
        reviewed_at="2026-05-17T10:00:00Z",
    )
    write_citation_support_record(support, tmp_path / "state" / "citation-support")

    result = generate_workspace_trace(tmp_path, tmp_path / "reports" / "workspace-trace.md", tmp_path / "state" / "workspace-trace.json")
    rendered = render_workspace_trace_markdown(result)
    node_types = {node.node_type for node in result.nodes}
    relations = {edge.relation for edge in result.edges}

    assert result.node_count >= 6
    assert {"source", "evidence", "report", "approval", "bibliography", "citation_support"}.issubset(node_types)
    assert {"source_of", "cites", "approves", "supports_claim", "references_evidence"}.issubset(relations)
    assert result.high_count == 0
    assert "Trace projection only" in rendered
    assert (tmp_path / "reports" / "workspace-trace.md").exists()
    assert json.loads((tmp_path / "state" / "workspace-trace.json").read_text(encoding="utf-8"))["node_count"] == result.node_count
    assert import_result.entry_count == 1


def test_workspace_trace_flags_source_and_approval_drift(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    source = tmp_path / "inbox" / "metrics.csv"
    source.write_text("case_id,dice\nA,0.81\n", encoding="utf-8")
    report = tmp_path / "reports" / "monthly-report-2026-05.md"
    report.write_text("Dice reached 0.81 [EVI-2026-ABCD1234].\n", encoding="utf-8")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-ABCD1234",
                source_file="inbox/metrics.csv",
                source_hash=_sha256(source),
                evidence_type="experiment_result",
                claim="Dice reached 0.81.",
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
        reviewed_at="2026-05-17T09:00:00Z",
    )
    write_approval_record(approval, tmp_path / "state" / "approvals")

    source.write_text("case_id,dice\nA,0.12\n", encoding="utf-8")
    report.write_text("Dice reached 0.12 [EVI-2026-ABCD1234].\n", encoding="utf-8")

    result = generate_workspace_trace(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "impacted"
    assert "trace_evidence_source_hash_mismatch" in codes
    assert "trace_approval_target_hash_mismatch" in codes


def test_workspace_trace_integrates_with_doctor_actions_summary_and_review_pack(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    source = tmp_path / "inbox" / "metrics.csv"
    source.write_text("case_id,dice\nA,0.81\n", encoding="utf-8")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-ABCD1234",
                source_file="inbox/metrics.csv",
                source_hash=_sha256(source),
                evidence_type="experiment_result",
                claim="Dice reached 0.81.",
                status="accepted",
            )
        ],
        tmp_path / "state",
    )
    source.write_text("case_id,dice\nA,0.12\n", encoding="utf-8")

    doctor = run_workspace_doctor(tmp_path)
    action_plan = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor, action_plan=action_plan)
    pack = generate_workspace_review_pack(tmp_path)
    rendered_pack = render_workspace_review_pack_markdown(pack)
    codes = {finding.code for finding in doctor.findings}

    assert "workspace_trace_high_findings" in codes
    assert any(action.title == "Review workspace trace impact" for action in action_plan.actions)
    assert summary.trace_finding_count > 0
    assert "Workspace trace" in render_workspace_summary_markdown(summary)
    assert pack.workspace_trace_high_count > 0
    assert (tmp_path / "reports" / "workspace-trace.md").exists()
    assert (tmp_path / "state" / "workspace-trace.json").exists()
    assert "Workspace trace status" in rendered_pack
    assert "workspace-trace.md" in {path.split("\\")[-1].split("/")[-1] for path in pack.generated_paths}


def test_workspace_trace_cli_writes_outputs(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    output = tmp_path / "reports" / "workspace-trace.md"
    json_output = tmp_path / "state" / "workspace-trace.json"

    assert main(["workspace-trace", "--root", str(tmp_path), "--output", str(output), "--json", str(json_output)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["root"] == str(tmp_path)
    assert output.exists()
    assert json_output.exists()


def _sha256(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
