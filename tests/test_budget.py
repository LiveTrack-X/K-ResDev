from k_resdev_skill.budget import budget_evidence_gaps, generate_budget_evidence_checklist
from k_resdev_skill.cli import main
from k_resdev_skill.models import EvidenceItem, Provenance


def test_budget_checklist_flags_generic_missing_fields(tmp_path):
    evidence = EvidenceItem(
        evidence_id="EVI-2026-BUDG1234",
        source_file="receipt.xlsx",
        evidence_type="budget_evidence",
        claim="GPU rental invoice candidate.",
        value={"amount": 1200000, "category": "cloud", "vendor": "Example Cloud"},
        provenance=Provenance(sheet="Sheet1", cell_range="A2:F2"),
    )

    rendered = generate_budget_evidence_checklist([evidence], tmp_path / "budget.md")
    gaps = budget_evidence_gaps([evidence])

    assert "Generic checklist only" in rendered
    assert "date, proof_type, approval_id" in rendered
    assert gaps["EVI-2026-BUDG1234"] == ["date", "proof_type", "approval_id"]
    assert "sheet Sheet1" in (tmp_path / "budget.md").read_text(encoding="utf-8")


def test_budget_checklist_cli(tmp_path, capsys):
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "budget.md"
    evidence_path.write_text(
        """[
          {
            "evidence_id": "EVI-2026-BUDG1234",
            "source_file": "receipt.xlsx",
            "evidence_type": "budget_evidence",
            "claim": "Invoice candidate.",
            "value": {"amount": 1000, "category": "supplies", "date": "2026-05-01"}
          }
        ]""",
        encoding="utf-8",
    )

    assert main(["budget-check", str(evidence_path), "--output", str(output_path)]) == 0

    assert "Budget Evidence Checklist" in capsys.readouterr().out
    assert "budget_metadata_incomplete" in output_path.read_text(encoding="utf-8")


def test_budget_checklist_no_evidence_is_not_silent():
    rendered = generate_budget_evidence_checklist([])

    assert "No budget evidence indexed" in rendered
    assert "budget_evidence_missing" in rendered
