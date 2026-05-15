import json

from k_resdev_skill import (
    extract_project_state_from_text,
    generate_audit_qna,
    write_monthly_report,
)
from k_resdev_skill.models import EvidenceItem


def test_extract_project_state_from_plan_text():
    state = extract_project_state_from_text(
        "\ufeff과제명: AI 초음파 진단\n"
        "연구기간: 2026-01-01 ~ 2026-12-31\n"
        "KPI: Validation Dice 목표: 0.85\n"
        "마일스톤: Prototype freeze 2026-06-30\n",
        project_id="PRJ-001",
    )

    assert state.project_id == "PRJ-001"
    assert state.title == "AI 초음파 진단"
    assert state.kpis[0].name == "Validation Dice"
    assert state.kpis[0].target == "0.85"
    assert state.milestones[0].due_date.isoformat() == "2026-06-30"


def test_write_monthly_report_and_review(tmp_path):
    evidence = EvidenceItem(
        evidence_id="EVI-2026-0001",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Validation Dice reached 0.83.",
        value={"score": 0.83, "target": 0.85},
        linked_kpi="KPI-01",
        risk_flags=["below_target"],
    )
    state = extract_project_state_from_text(
        "과제명: AI 초음파 진단\nKPI: Validation Dice 목표: 0.85\n",
        project_id="PRJ-001",
    )

    paths = write_monthly_report([evidence], tmp_path / "reports", state, "2026-05")
    report = (tmp_path / "reports" / "monthly-report-draft.md").read_text(encoding="utf-8")
    review = (tmp_path / "reports" / "monthly-report-draft-claim-review.md").read_text(encoding="utf-8")

    assert "Draft projection only" in report
    assert "EVI-2026-0001" in report
    assert "EvidenceStatus." not in report
    assert paths.review_path.endswith("monthly-report-draft-claim-review.md")
    assert "No unsupported claim patterns detected" in review


def test_generate_audit_qna_uses_evidence_metadata_only(tmp_path):
    evidence = EvidenceItem(
        evidence_id="EVI-2026-0001",
        source_file="receipt.pdf",
        evidence_type="budget_evidence",
        claim="Receipt candidate requires review.",
        risk_flags=["auto_extracted"],
    )

    rendered = generate_audit_qna([evidence], tmp_path / "audit.md")

    assert "Audit Defense Q&A Draft" in rendered
    assert "EVI-2026-0001" in rendered
    assert "auto_extracted" in (tmp_path / "audit.md").read_text(encoding="utf-8")
