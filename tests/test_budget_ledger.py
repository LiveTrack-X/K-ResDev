import hashlib
import json

from k_resdev_skill.budget_ledger import generate_workspace_budget_ledger, import_budget_ledger, load_budget_ledger
from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_budget_ledger_import_csv_writes_json_and_markdown(tmp_path):
    ledger_csv = tmp_path / "budget.csv"
    ledger_csv.write_text(
        "date,vendor,amount,currency,category,proof_type,approval_reference,evidence_ids,review_status\n"
        "2026-05-01,Example Cloud,1200000,KRW,cloud,invoice,APR-1,EVI-2026-BUDG1234,accepted\n",
        encoding="utf-8",
    )

    result = import_budget_ledger(ledger_csv, tmp_path / "state", markdown_path=tmp_path / "reports" / "budget-ledger-import.md")
    items = load_budget_ledger(tmp_path / "state" / "budget-ledger.json")

    assert result.item_count == 1
    assert result.source_hash == _sha256(ledger_csv)
    assert items[0].source_file == str(ledger_csv)
    assert items[0].source_hash == _sha256(ledger_csv)
    assert items[0].amount == 1200000
    assert (tmp_path / "reports" / "budget-ledger-import.md").read_text(encoding="utf-8").startswith("# Budget Evidence Ledger")


def test_budget_ledger_integrity_flags_missing_links_duplicates_and_rollups(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-BUDG1234",
                source_file="receipt.xlsx",
                evidence_type="budget_evidence",
                claim="Receipt candidate.",
                status="accepted",
            ),
            EvidenceItem(
                evidence_id="EVI-2026-EXPA1234",
                source_file="metrics.csv",
                evidence_type="experiment_result",
                claim="Metric candidate.",
                status="accepted",
            ),
        ],
        tmp_path / "state",
    )
    (tmp_path / "state" / "budget-ledger.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "ledger_id": "BUD-1",
                        "date": "2026-05-01",
                        "vendor": "Example Cloud",
                        "amount": 1200000,
                        "currency": "KRW",
                        "category": "cloud",
                        "proof_type": "invoice",
                        "approval_reference": "APR-1",
                        "evidence_ids": ["EVI-2026-BUDG1234"],
                        "review_status": "accepted",
                        "risk_flags": [],
                    },
                    {
                        "ledger_id": "BUD-2",
                        "date": "2026-05-01",
                        "vendor": "Example Cloud",
                        "amount": 1200000,
                        "currency": "KRW",
                        "category": "cloud",
                        "proof_type": None,
                        "approval_reference": None,
                        "evidence_ids": ["EVI-2026-UNKNOWN", "EVI-2026-EXPA1234"],
                        "review_status": "needs_review",
                        "risk_flags": [],
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = generate_workspace_budget_ledger(tmp_path, tmp_path / "reports" / "budget-ledger.md", tmp_path / "state" / "budget-ledger-integrity.json")
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert result.total_by_currency["KRW"] == 2400000
    assert result.amount_by_category["KRW:cloud"] == 2400000
    assert "budget_ledger_duplicate_candidate" in codes
    assert "budget_ledger_missing_proof_type" in codes
    assert "budget_ledger_missing_approval_reference" in codes
    assert "budget_ledger_unknown_evidence" in codes
    assert "budget_ledger_non_budget_evidence" in codes
    assert (tmp_path / "reports" / "budget-ledger.md").exists()
    assert json.loads((tmp_path / "state" / "budget-ledger-integrity.json").read_text(encoding="utf-8"))["ledger_count"] == 2


def test_budget_ledger_missing_when_budget_evidence_exists_flows_to_doctor_and_actions(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-BUDG1234",
                source_file="receipt.xlsx",
                evidence_type="budget_evidence",
                claim="Receipt candidate.",
                status="accepted",
            )
        ],
        tmp_path / "state",
    )

    result = generate_workspace_budget_ledger(tmp_path)
    doctor = run_workspace_doctor(tmp_path)
    action_plan = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    codes = {finding.code for finding in doctor.findings}

    assert result.status == "needs_review"
    assert result.findings[0].code == "budget_ledger_missing"
    assert "budget_ledger_review_findings" in codes
    assert any(action.title == "Review budget ledger integrity" for action in action_plan.actions)


def test_budget_ledger_integrates_with_summary_review_pack_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-BUDG1234",
                source_file="receipt.xlsx",
                evidence_type="budget_evidence",
                claim="Receipt candidate.",
                status="accepted",
            )
        ],
        tmp_path / "state",
    )
    (tmp_path / "state" / "budget-ledger.json").write_text(
        """{
          "items": [
            {
              "ledger_id": "BUD-1",
              "date": "2026-05-01",
              "vendor": "Example Cloud",
              "amount": 1000,
              "currency": "KRW",
              "category": "cloud",
              "proof_type": "invoice",
              "approval_reference": "APR-1",
              "evidence_ids": ["EVI-2026-BUDG1234"],
              "review_status": "accepted",
              "risk_flags": []
            }
          ]
        }""",
        encoding="utf-8",
    )

    summary = generate_workspace_summary(tmp_path)
    pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    node_types = {node.node_type for node in trace.nodes}
    relations = {edge.relation for edge in trace.edges}

    assert summary.budget_ledger_status == "ready"
    assert summary.budget_ledger_count == 1
    assert summary.budget_total_by_currency["KRW"] == 1000
    assert pack.budget_ledger_status == "ready"
    assert pack.budget_ledger_count == 1
    assert (tmp_path / "reports" / "budget-ledger.md").exists()
    assert "budget_ledger" in node_types
    assert "references_evidence" in relations


def test_budget_ledger_cli_commands_and_schema(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    ledger_csv = tmp_path / "budget.csv"
    ledger_csv.write_text(
        "date,vendor,amount,currency,category,proof_type,approval_reference,evidence_ids,review_status\n"
        "2026-05-01,Example Cloud,1000,KRW,cloud,invoice,APR-1,EVI-2026-BUDG1234,accepted\n",
        encoding="utf-8",
    )

    assert main(["budget-ledger-import", str(ledger_csv), "--state-dir", str(tmp_path / "state"), "--markdown", str(tmp_path / "reports" / "budget-ledger-import.md")]) == 0
    assert json.loads(capsys.readouterr().out)["item_count"] == 1

    assert main(["budget-ledger-integrity", "--root", str(tmp_path), "--output", str(tmp_path / "reports" / "budget-ledger.md"), "--json", str(tmp_path / "state" / "budget-ledger-integrity.json")]) == 0
    assert json.loads(capsys.readouterr().out)["ledger_count"] == 1

    assert main(["validate-json", "budget-ledger", str(tmp_path / "state" / "budget-ledger.json")]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True


def _sha256(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
