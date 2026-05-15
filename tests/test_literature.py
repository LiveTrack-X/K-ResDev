from k_resdev_skill import generate_literature_matrix
from k_resdev_skill.models import PaperRecord


def test_literature_matrix_uses_only_supplied_metadata(tmp_path):
    paper = PaperRecord(
        paper_id="PAPER-2026-0001",
        title="Segmentation Baselines for Ultrasound",
        authors=["Kim", "Lee"],
        year=2025,
        method="U-Net baseline",
        dataset="internal validation set",
        metrics={"dice": 0.82},
        key_claims=["Baseline is competitive on large lesions."],
        evidence_ids=["EVI-2026-0001"],
    )

    output = tmp_path / "literature-review-matrix.md"
    rendered = generate_literature_matrix([paper], output)

    assert "Kim, Lee (2025)." in rendered
    assert "DOI:" not in rendered
    assert "PAPER-2026-0001" in output.read_text(encoding="utf-8")
