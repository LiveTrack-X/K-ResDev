import pytest

from k_resdev_skill.cli import main


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])

    assert exc.value.code == 0
    assert "k-resdev 0.1.0b18" in capsys.readouterr().out


def test_index_cli_accepts_utf8_bom_json(tmp_path, capsys):
    evidence_json = tmp_path / "evidence.json"
    evidence_json.write_text(
        '\ufeff[{"evidence_id":"EVI-2026-BOM1234","source_file":"metrics.csv","evidence_type":"experiment_result","claim":"Metric candidate."}]\n',
        encoding="utf-8",
    )

    assert main(["index", str(evidence_json), "--state-dir", str(tmp_path / "state")]) == 0

    payload = capsys.readouterr().out
    assert "evidence-index.json" in payload
