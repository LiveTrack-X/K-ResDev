import json

from k_resdev_skill.cli import main
from k_resdev_skill.workspace import initialize_workspace


def test_initialize_workspace_creates_standard_layout(tmp_path):
    result = initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    for relative in [
        "inbox",
        "state",
        "evidence",
        "reports",
        "reports/analysis",
        "state/approvals",
    ]:
        assert (tmp_path / relative).is_dir()

    state = json.loads((tmp_path / "state" / "project-state.json").read_text(encoding="utf-8"))
    profile = json.loads((tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8"))
    readme = (tmp_path / "README.k-resdev.md").read_text(encoding="utf-8")

    assert state["project_id"] == "PRJ-2026-0001"
    assert state["title"] == "Demo Project"
    assert state["period"] == "needs_review"
    assert profile["profile_id"] == "national-rnd-basic"
    assert profile["status"] == "needs_review"
    assert "profile_needs_review" in result.warnings
    assert "Evidence is source of truth" in readme


def test_initialize_workspace_does_not_overwrite_existing_files(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    existing = state_dir / "project-state.json"
    existing.write_text('{"existing": true}\n', encoding="utf-8")

    result = initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    assert existing.read_text(encoding="utf-8") == '{"existing": true}\n'
    assert str(existing) in result.skipped_existing


def test_init_workspace_cli(tmp_path, capsys):
    assert (
        main(
            [
                "init-workspace",
                "--root",
                str(tmp_path),
                "--project-id",
                "PRJ-2026-0001",
                "--title",
                "Demo Project",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["project_id"] == "PRJ-2026-0001"
    assert (tmp_path / "state" / "project-profile.json").exists()
