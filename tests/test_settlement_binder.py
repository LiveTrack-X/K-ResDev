from k_resdev_skill.admin_operating import generate_settlement_binder
from k_resdev_skill.budget_ledger import write_budget_ledger
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import BudgetLedgerItem, EvidenceItem
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor


def test_settlement_binder_links_budget_ledger_to_evidence(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-BUDGET1",
                source_file="inbox/receipt.pdf",
                evidence_type="budget_evidence",
                claim="Receipt candidate.",
                status="accepted",
            )
        ],
        tmp_path / "state",
    )
    write_budget_ledger(
        [
            BudgetLedgerItem(
                ledger_id="BUD-2026-001",
                date="2026-05-01",
                vendor="Vendor",
                amount=1000,
                category="materials",
                proof_type="receipt",
                approval_reference="APR-2026-001",
                evidence_ids=["EVI-2026-BUDGET1"],
                source_hash="sha256:" + "0" * 64,
                review_status="accepted",
            )
        ],
        tmp_path / "state" / "budget-ledger.json",
    )

    result = generate_settlement_binder(tmp_path)

    assert result.status == "ready"
    assert result.item_count == 1
    assert result.items[0].evidence_count == 1
    assert result.items[0].finding_codes == []


def test_settlement_binder_detects_missing_proof_and_source_hash_drift(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    source = tmp_path / "references" / "ledger.csv"
    source.write_text("ledger_id,amount\nBUD-2026-001,1000\n", encoding="utf-8")
    write_budget_ledger(
        [
            BudgetLedgerItem(
                ledger_id="BUD-2026-001",
                amount=1000,
                evidence_ids=["EVI-MISSING"],
                source_file=str(source),
                source_hash="sha256:" + "0" * 64,
            )
        ],
        tmp_path / "state" / "budget-ledger.json",
    )

    result = generate_settlement_binder(tmp_path)
    codes = set(result.items[0].finding_codes)

    assert result.status == "blocked"
    assert "budget_ledger_missing_proof_type" in codes
    assert "budget_ledger_missing_approval_reference" in codes
    assert "budget_ledger_unknown_evidence" in codes
    assert "budget_ledger_source_hash_mismatch" in codes


def test_workspace_doctor_surfaces_settlement_binder_findings(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    write_budget_ledger([BudgetLedgerItem(ledger_id="BUD-2026-001")], tmp_path / "state" / "budget-ledger.json")

    result = run_workspace_doctor(tmp_path)

    assert "settlement_binder_review_findings" in {finding.code for finding in result.findings}
