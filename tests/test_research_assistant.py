from k_resdev_skill.models import DataProfile, EvidenceItem, Missingness, NumericSummary
from k_resdev_skill.research_assistant import (
    generate_data_insight_candidates,
    generate_data_insight_report,
    generate_experiment_comparison_table,
    generate_paper_card_markdown,
    generate_reproducibility_checklist,
    paper_card_from_text,
)


def test_paper_card_from_text_extracts_supplied_metadata_only(tmp_path):
    text = "\n".join(
        [
            "Segmentation Baselines for Ultrasound",
            "Authors: Kim, Lee",
            "Venue: MICCAI Workshop",
            "2025",
            "DOI: 10.1234/example.2025.1",
            "Claim: U-Net remains competitive on large lesions.",
            "Limitation: Small-lesion sample size is limited.",
        ]
    )

    paper = paper_card_from_text(text, "PAPER-2026-0001", ["EVI-2026-ABCD1234"])
    rendered = generate_paper_card_markdown(paper, tmp_path / "paper.md")

    assert paper.title == "Segmentation Baselines for Ultrasound"
    assert paper.authors == ["Kim", "Lee"]
    assert paper.doi == "10.1234/example.2025.1"
    assert "Small-lesion sample size" in rendered
    assert "PAPER-2026-0001" in (tmp_path / "paper.md").read_text(encoding="utf-8")


def test_data_insight_candidates_are_hypotheses():
    profile = DataProfile(
        source_file="metrics.csv",
        file_type="csv",
        row_count=2,
        column_count=2,
        columns=["case_id", "dice"],
        missingness={
            "case_id": Missingness(missing_count=0, missing_ratio=0),
            "dice": Missingness(missing_count=1, missing_ratio=0.5),
        },
        numeric_summary={"dice": NumericSummary(count=1, min=0.81, max=0.81, mean=0.81)},
        possible_metrics=["dice"],
    )

    insights = generate_data_insight_candidates(profile, ["EVI-2026-ABCD1234"])
    report = generate_data_insight_report(profile, ["EVI-2026-ABCD1234"])

    assert any("small_sample" in insight.risk_flags for insight in insights)
    assert all(insight.status == "hypothesis" for insight in insights)
    assert "Draft candidates only" in report


def test_experiment_table_and_repro_check_from_evidence():
    evidence = EvidenceItem(
        evidence_id="EVI-2026-ABCD1234",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Validation Dice reached 0.83.",
        value={
            "metric": "dice",
            "score": 0.83,
            "baseline": 0.78,
            "target": 0.85,
            "dataset": "validation_v2",
        },
        risk_flags=["below_target"],
    )

    table = generate_experiment_comparison_table([evidence])
    checklist = generate_reproducibility_checklist([evidence])

    assert "validation_v2" in table
    assert "below_target" in table
    assert "| present | Metric definition is recorded." in checklist
    assert "| missing | Random seed or deterministic setting is recorded." in checklist
