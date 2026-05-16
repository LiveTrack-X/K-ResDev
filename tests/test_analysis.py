import json

from k_resdev_skill.analysis import generate_analysis_script, run_data_analysis
from k_resdev_skill.cli import main


def test_run_data_analysis_writes_manifest_without_altering_raw_file(tmp_path):
    data_path = tmp_path / "metrics.csv"
    raw = "case_id,dice,accuracy\nA,0.81,0.90\nB,,0.87\n"
    data_path.write_text(raw, encoding="utf-8")
    output_dir = tmp_path / "analysis"

    result = run_data_analysis(data_path, output_dir, ["EVI-2026-ABCD1234"])
    manifest = json.loads((output_dir / "metrics-analysis-run.json").read_text(encoding="utf-8"))

    assert result.analysis_id.startswith("ANL-")
    assert data_path.read_text(encoding="utf-8") == raw
    assert (output_dir / "metrics-profile.json").exists()
    assert (output_dir / "metrics-insights.md").exists()
    assert (output_dir / "metrics-analysis.py").exists()
    assert manifest["safety"]["raw_file_modified"] is False
    assert manifest["safety"]["human_review_required"] is True
    assert "missing_values:dice" in manifest["warnings"]


def test_generate_analysis_script_is_replayable_shape():
    rendered = generate_analysis_script("inbox/metrics.csv", "reports/analysis", ["EVI-2026-ABCD1234"])

    assert "run_data_analysis" in rendered
    assert "write_script=False" in rendered
    assert "EVI-2026-ABCD1234" in rendered


def test_analysis_cli_commands(tmp_path, capsys):
    data_path = tmp_path / "metrics.csv"
    data_path.write_text("case_id,auc\nA,0.91\nB,0.89\n", encoding="utf-8")
    output_dir = tmp_path / "analysis"
    script_path = tmp_path / "analysis.py"

    assert main(["analysis-script", str(data_path), "--output-dir", str(output_dir), "--output", str(script_path)]) == 0
    assert "run_data_analysis" in script_path.read_text(encoding="utf-8")
    capsys.readouterr()

    assert main(["run-analysis", str(data_path), "--output-dir", str(output_dir), "--evidence-id", "EVI-2026-ABCD1234"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile_path"].endswith("metrics-profile.json")
    assert (output_dir / "metrics-analysis-run.json").exists()
