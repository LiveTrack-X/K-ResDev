from k_resdev_skill.models import EvidenceItem, KPI, ProjectState, ResearchInsight


def test_core_models_validate():
    evidence = EvidenceItem(
        evidence_id="EVI-2026-0001",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Validation Dice reached 0.83.",
        value={"score": 0.83, "target": 0.85},
        confidence="high",
        status="needs_review",
        linked_kpi="KPI-01",
    )
    kpi = KPI(kpi_id="KPI-01", name="Validation Dice", target=0.85, metric="dice")
    state = ProjectState(
        project_id="PRJ-001",
        title="Ultrasound AI",
        period="2026-01-01/2026-12-31",
        status="active",
        kpis=[kpi],
    )
    insight = ResearchInsight(
        insight_id="INS-2026-0001",
        claim="Small-lesion performance may need stratified analysis.",
        basis=[evidence.evidence_id],
        confidence="medium",
        next_checks=["Bootstrap confidence interval"],
    )

    assert state.kpis[0].kpi_id == "KPI-01"
    assert insight.status == "hypothesis"
