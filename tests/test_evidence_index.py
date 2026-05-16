import json

from k_resdev_skill import load_evidence_index, write_evidence_index
from k_resdev_skill.models import EvidenceItem


def test_evidence_index_writer_outputs_markdown_and_json(tmp_path):
    item = EvidenceItem(
        evidence_id="EVI-2026-0001",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Validation Dice reached 0.83.",
        linked_kpi="KPI-01",
        risk_flags=["below_target"],
    )

    paths = write_evidence_index([item], tmp_path / "state")

    markdown = (tmp_path / "state" / "evidence-index.md").read_text(encoding="utf-8")
    payload = json.loads((tmp_path / "state" / "evidence-index.json").read_text(encoding="utf-8"))

    assert paths.markdown_path.endswith("evidence-index.md")
    assert "EVI-2026-0001" in markdown
    assert "experiment_result" in markdown
    assert "needs_review" in markdown
    assert "EvidenceStatus." not in markdown
    assert payload["evidence_count"] == 1
    assert payload["items"][0]["linked_kpi"] == "KPI-01"


def test_load_evidence_index_accepts_raw_list(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(
        json.dumps(
            [
                {
                    "evidence_id": "EVI-2026-0001",
                    "source_file": "metrics.csv",
                    "evidence_type": "experiment_result",
                    "claim": "Validation Dice reached 0.83.",
                }
            ]
        ),
        encoding="utf-8",
    )

    items = load_evidence_index(path)

    assert items[0].evidence_id == "EVI-2026-0001"


def test_load_evidence_index_accepts_single_item(tmp_path):
    path = tmp_path / "single-evidence.json"
    path.write_text(
        json.dumps(
            {
                "evidence_id": "EVI-2026-0001",
                "source_file": "metrics.csv",
                "evidence_type": "experiment_result",
                "claim": "Validation Dice reached 0.83.",
            }
        ),
        encoding="utf-8",
    )

    items = load_evidence_index(path)

    assert len(items) == 1
    assert items[0].claim == "Validation Dice reached 0.83."
