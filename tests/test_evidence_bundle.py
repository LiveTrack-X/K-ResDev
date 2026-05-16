from k_resdev_skill.approval import create_approval_record
from k_resdev_skill.cli import main
from k_resdev_skill.evidence_bundle import generate_evidence_bundle_index
from k_resdev_skill.models import EvidenceItem, Provenance


def test_evidence_bundle_index_summarizes_unresolved_items(tmp_path):
    accepted = EvidenceItem(
        evidence_id="EVI-2026-ACCEPTED",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Metric accepted.",
        status="accepted",
        provenance=Provenance(line_range="2"),
    )
    needs_review = EvidenceItem(
        evidence_id="EVI-2026-REVIEW",
        source_file="receipt.xlsx",
        evidence_type="budget_evidence",
        claim="Budget evidence needs review.",
        risk_flags=["budget_metadata_incomplete"],
    )
    approval = create_approval_record(
        "evidence",
        "EVI-2026-ACCEPTED",
        "approved",
        "Reviewer",
        evidence_ids=["EVI-2026-ACCEPTED"],
        reviewed_at="2026-05-17T09:00:00Z",
    )

    rendered = generate_evidence_bundle_index([needs_review, accepted], [approval], tmp_path / "bundle.md")

    assert "Accepted evidence: 1" in rendered
    assert "approved" in rendered
    assert "EVI-2026-REVIEW" in rendered
    assert "budget_metadata_incomplete" in (tmp_path / "bundle.md").read_text(encoding="utf-8")


def test_bundle_index_cli(tmp_path, capsys):
    evidence_path = tmp_path / "evidence.json"
    approvals_dir = tmp_path / "approvals"
    output_path = tmp_path / "bundle.md"
    evidence_path.write_text(
        """[
          {
            "evidence_id": "EVI-2026-ACCEPTED",
            "source_file": "metrics.csv",
            "evidence_type": "experiment_result",
            "claim": "Metric accepted.",
            "status": "accepted"
          }
        ]""",
        encoding="utf-8",
    )
    approvals_dir.mkdir()
    approvals_dir.joinpath("approval.json").write_text(
        """{
          "approval_id": "APR-2026-ABCD1234",
          "target_type": "evidence",
          "target_id": "EVI-2026-ACCEPTED",
          "decision": "approved",
          "reviewer": "Reviewer",
          "reviewed_at": "2026-05-17T09:00:00Z",
          "evidence_ids": ["EVI-2026-ACCEPTED"],
          "risk_flags": []
        }""",
        encoding="utf-8",
    )

    assert main(["bundle-index", str(evidence_path), "--approval-records", str(approvals_dir), "--output", str(output_path)]) == 0

    assert "Evidence Bundle Index" in capsys.readouterr().out
    assert "Approval records supplied: 1" in output_path.read_text(encoding="utf-8")
