import json

from k_resdev_skill.approval import (
    approval_gate_status,
    create_approval_record,
    generate_approval_summary,
    load_approval_records,
    write_approval_record,
)
from k_resdev_skill.cli import main


def test_approval_record_round_trip_and_gate(tmp_path):
    record = create_approval_record(
        target_type="report",
        target_id="monthly-2026-05",
        decision="approved",
        reviewer="Dr. Kim",
        evidence_ids=["EVI-2026-ABCD1234"],
        reviewed_at="2026-05-17T09:00:00Z",
    )
    path = write_approval_record(record, tmp_path / "approvals")

    loaded = load_approval_records(path)
    gate = approval_gate_status(loaded, "report", "monthly-2026-05")
    summary = generate_approval_summary(loaded, tmp_path / "approval-summary.md")

    assert record.approval_id.startswith("APR-2026-")
    assert gate["approved"] is True
    assert "Dr. Kim" in summary
    assert "Human decision log only" in (tmp_path / "approval-summary.md").read_text(encoding="utf-8")


def test_approval_cli_print_only_and_summary(tmp_path, capsys):
    approvals_dir = tmp_path / "approvals"
    assert (
        main(
            [
                "approval-record",
                "--target-type",
                "insight",
                "--target-id",
                "INS-2026-0001",
                "--decision",
                "needs_changes",
                "--reviewer",
                "Reviewer",
                "--evidence-id",
                "EVI-2026-ABCD1234",
                "--reviewed-at",
                "2026-05-17T09:00:00Z",
                "--approvals-dir",
                str(approvals_dir),
            ]
        )
        == 0
    )
    created = list(approvals_dir.glob("*.json"))
    assert len(created) == 1
    assert "needs_changes" in capsys.readouterr().out

    summary_path = tmp_path / "summary.md"
    assert main(["approval-summary", str(approvals_dir), "--output", str(summary_path)]) == 0
    assert "INS-2026-0001" in summary_path.read_text(encoding="utf-8")
    capsys.readouterr()

    assert main(["approval-gate", str(approvals_dir), "--target-type", "insight", "--target-id", "INS-2026-0001"]) == 0
    gate = json.loads(capsys.readouterr().out)
    assert gate["approved"] is False
    assert gate["decision"] == "needs_changes"


def test_missing_approval_gate_is_explicit():
    gate = approval_gate_status([], "report", "monthly-2026-05")

    assert gate["approved"] is False
    assert gate["decision"] == "missing"
