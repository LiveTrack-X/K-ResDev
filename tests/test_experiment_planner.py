import json

from k_resdev_skill.cli import main
from k_resdev_skill.experiment_planner import generate_experiment_plan, generate_experiment_plan_bundle
from k_resdev_skill.models import EvidenceItem, ResearchInsight


def test_experiment_plan_keeps_hypothesis_review_gate(tmp_path):
    insight = ResearchInsight(
        insight_id="INS-2026-0001",
        claim="Model A appears to underperform on small-lesion cases.",
        basis=["EVI-2026-ABCD1234", "EVI-2026-MISSING"],
        confidence="medium",
        assumptions=["Validation labels are stable."],
        risk_flags=["small_sample"],
        next_checks=["lesion size stratified Dice analysis"],
    )
    evidence = EvidenceItem(
        evidence_id="EVI-2026-ABCD1234",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Small lesion Dice was 0.61.",
        value={"metric": "dice", "dataset": "validation_v2", "baseline": 0.64},
    )

    rendered = generate_experiment_plan(insight, [evidence], tmp_path / "plan.md")

    assert "Draft validation plan only" in rendered
    assert "validation_v2" in rendered
    assert "EVI-2026-MISSING" in rendered
    assert "Researcher approval required" in rendered
    assert "small_sample" in (tmp_path / "plan.md").read_text(encoding="utf-8")


def test_experiment_plan_bundle_cli(tmp_path, capsys):
    insights_path = tmp_path / "insights.json"
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "bundle.md"
    insights_path.write_text(
        json.dumps(
            [
                {
                    "insight_id": "INS-2026-0001",
                    "claim": "AUC may be unstable.",
                    "basis": ["EVI-2026-ABCD1234"],
                    "confidence": "low",
                    "risk_flags": ["needs_statistical_test"],
                    "next_checks": ["bootstrap AUC confidence interval"],
                }
            ]
        ),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps(
            [
                {
                    "evidence_id": "EVI-2026-ABCD1234",
                    "source_file": "metrics.csv",
                    "evidence_type": "experiment_result",
                    "claim": "AUC was 0.87.",
                    "value": {"metric": "auc", "dataset": "holdout"},
                }
            ]
        ),
        encoding="utf-8",
    )

    assert main(["plan-experiment", str(insights_path), "--evidence-index", str(evidence_path), "--output", str(output_path)]) == 0

    captured = capsys.readouterr().out
    assert "Hypothesis-to-Experiment Plan" in captured
    assert "holdout" in output_path.read_text(encoding="utf-8")


def test_empty_experiment_plan_bundle_is_explicit():
    rendered = generate_experiment_plan_bundle([])

    assert "No insight candidates were supplied" in rendered
