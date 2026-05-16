from __future__ import annotations

from k_resdev_skill.analysis import run_data_analysis


if __name__ == "__main__":
    result = run_data_analysis(
        data_file="inbox/metrics.csv",
        output_dir="reports/analysis",
        evidence_ids=[],
        write_script=False,
    )
    print(result.model_dump_json(indent=2))
