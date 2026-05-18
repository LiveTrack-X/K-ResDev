import json

from k_resdev_skill.cli import main
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.schema_tools import validate_json_file, validate_json_files
from k_resdev_skill.evidence_index import write_evidence_index


def test_validate_json_file_with_bundled_schema(tmp_path):
    approval = {
        "approval_id": "APR-2026-ABCD1234",
        "target_type": "report",
        "target_id": "monthly-2026-05",
        "target_path": None,
        "decision": "approved",
        "reviewer": "Dr. Kim",
        "reviewed_at": "2026-05-17T09:00:00Z",
        "evidence_ids": ["EVI-2026-ABCD1234"],
        "notes": None,
        "risk_flags": [],
    }
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(approval), encoding="utf-8")

    result = validate_json_file(path, "approval")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_files_reports_errors(tmp_path):
    path = tmp_path / "bad-approval.json"
    path.write_text(json.dumps({"approval_id": "APR-2026-BAD"}), encoding="utf-8")

    result = validate_json_files([path], "approval")

    assert result["valid"] is False
    assert result["results"][0]["error_count"] > 0
    assert any("required" in error["message"] for error in result["results"][0]["errors"])


def test_validate_json_file_accepts_generated_evidence_index(tmp_path):
    item = EvidenceItem(
        evidence_id="EVI-2026-0001",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Validation Dice reached 0.83.",
    )
    paths = write_evidence_index([item], tmp_path / "state")

    result = validate_json_file(paths.json_path, "evidence")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_file_accepts_citation_support_alias():
    result = validate_json_file("templates/citation-support-record.json", "citation-support")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_file_accepts_research_claim_alias():
    result = validate_json_file("templates/research-claim.json", "research-claim")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_file_accepts_checkpoint_alias():
    result = validate_json_file("templates/trace-passport-entry.json", "checkpoint")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_cli_returns_nonzero_for_invalid(tmp_path, capsys):
    path = tmp_path / "bad-approval.json"
    path.write_text(json.dumps({"approval_id": "APR-2026-BAD"}), encoding="utf-8")

    assert main(["validate-json", "approval", str(path)]) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is False
