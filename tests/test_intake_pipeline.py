from __future__ import annotations

import json
from datetime import date

from k_resdev_skill import run_intake


def test_run_intake_creates_registry_evidence_and_indexes(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "plan.md").write_text("과제명: AI 진단\n연구개발계획서 KPI 목표 협약", encoding="utf-8")
    (inbox / "metrics.csv").write_text("case_id,dice\nA,0.81\nB,0.86\n", encoding="utf-8")

    result = run_intake(
        inbox,
        tmp_path / "state",
        tmp_path / "evidence",
        project="demo-project",
        run_date=date(2026, 5, 15),
    )

    registry = json.loads((tmp_path / "state" / "raw-registry.json").read_text(encoding="utf-8"))
    index = json.loads((tmp_path / "state" / "evidence-index.json").read_text(encoding="utf-8"))
    evidence_files = sorted((tmp_path / "evidence").glob("*.json"))
    open_issues = (tmp_path / "state" / "open-issues.md").read_text(encoding="utf-8")

    assert result.source_count == 2
    assert result.evidence_count == 2
    assert registry["source_count"] == 2
    assert index["evidence_count"] == 2
    assert len(evidence_files) == 2
    assert "No blocking intake issues" in open_issues
    assert any(item["evidence_type"] == "data_profile" for item in index["items"])


def test_run_intake_records_unknown_files_as_open_issues(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "artifact.bin").write_bytes(b"\x00\x01")

    run_intake(inbox, tmp_path / "state", tmp_path / "evidence", run_date=date(2026, 5, 15))

    open_issues = (tmp_path / "state" / "open-issues.md").read_text(encoding="utf-8")
    evidence_path = next((tmp_path / "evidence").glob("EVI-2026-*.json"))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert "Low-confidence or unknown classification" in open_issues
    assert evidence["evidence_type"] == "risk"
    assert "unknown_file_type" in evidence["risk_flags"]


def test_run_intake_uses_stable_hash_ids_when_file_order_changes(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    metrics = inbox / "metrics.csv"
    metrics.write_text("case_id,dice\nA,0.81\n", encoding="utf-8")

    run_intake(inbox, tmp_path / "state1", tmp_path / "evidence1", run_date=date(2026, 5, 15))
    first_index = json.loads((tmp_path / "state1" / "evidence-index.json").read_text(encoding="utf-8"))
    metrics_id = first_index["items"][0]["evidence_id"]

    (inbox / "aaa-plan.txt").write_text("과제명: 새 계획", encoding="utf-8")
    run_intake(inbox, tmp_path / "state2", tmp_path / "evidence2", run_date=date(2026, 5, 15))
    second_index = json.loads((tmp_path / "state2" / "evidence-index.json").read_text(encoding="utf-8"))
    ids_by_source = {item["source_file"]: item["evidence_id"] for item in second_index["items"]}

    assert ids_by_source[str(metrics)] == metrics_id


def test_run_intake_does_not_reingest_derived_outputs_inside_inbox(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "metrics.csv").write_text("case_id,dice\nA,0.81\n", encoding="utf-8")

    run_intake(
        inbox,
        inbox / "state",
        inbox / "evidence",
        run_date=date(2026, 5, 15),
    )
    result = run_intake(
        inbox,
        inbox / "state",
        inbox / "evidence",
        run_date=date(2026, 5, 15),
    )

    assert result.source_count == 1
    assert result.evidence_count == 1


def test_run_intake_extracts_document_level_evidence_with_provenance(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "plan.txt").write_text(
        "과제명: AI 진단\nKPI: Validation Dice 목표: 0.85\n마일스톤: Prototype freeze 2026-06-30\n",
        encoding="utf-8",
    )

    run_intake(inbox, tmp_path / "state", tmp_path / "evidence", run_date=date(2026, 5, 15))
    index = json.loads((tmp_path / "state" / "evidence-index.json").read_text(encoding="utf-8"))
    evidence_types = {item["evidence_type"] for item in index["items"]}
    extracted = [item for item in index["items"] if item["evidence_type"] in {"kpi", "milestone"}]

    assert "plan_goal" in evidence_types
    assert "kpi" in evidence_types
    assert "milestone" in evidence_types
    assert all(item["provenance"]["line_range"] for item in extracted)


def test_run_intake_distinguishes_duplicate_content_files(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "metrics-a.csv").write_text("case_id,dice\nA,0.81\n", encoding="utf-8")
    (inbox / "metrics-b.csv").write_text("case_id,dice\nA,0.81\n", encoding="utf-8")

    run_intake(inbox, tmp_path / "state", tmp_path / "evidence", run_date=date(2026, 5, 15))
    index = json.loads((tmp_path / "state" / "evidence-index.json").read_text(encoding="utf-8"))
    evidence_ids = [item["evidence_id"] for item in index["items"]]

    assert len(evidence_ids) == 2
    assert len(set(evidence_ids)) == 2
