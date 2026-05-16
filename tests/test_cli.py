import pytest

from k_resdev_skill.cli import main


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])

    assert exc.value.code == 0
    assert "k-resdev 0.1.0b4" in capsys.readouterr().out
