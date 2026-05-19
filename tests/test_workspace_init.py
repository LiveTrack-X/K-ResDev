import json

from k_resdev_skill.cli import main
from k_resdev_skill.profile_sources import generate_profile_integrity
from k_resdev_skill.workspace import initialize_workspace


def test_initialize_workspace_creates_standard_layout(tmp_path):
    result = initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    for relative in [
        "inbox",
        "state",
        "evidence",
        "references",
        "reports",
        "reports/analysis",
        "state/approvals",
        "state/bibliography-reviews",
        "state/citation-support",
        "state/checkpoints",
        "state/profile-backups",
        "state/profile-promotions",
        "state/profile-source-fix-reviews",
    ]:
        assert (tmp_path / relative).is_dir()

    state = json.loads((tmp_path / "state" / "project-state.json").read_text(encoding="utf-8"))
    profile = json.loads((tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8"))
    profile_sources = json.loads((tmp_path / "state" / "profile-sources.json").read_text(encoding="utf-8"))
    project_goals = json.loads((tmp_path / "state" / "project-goals.json").read_text(encoding="utf-8"))
    readme = (tmp_path / "README.k-resdev.md").read_text(encoding="utf-8")

    assert state["project_id"] == "PRJ-2026-0001"
    assert state["title"] == "Demo Project"
    assert state["period"] == "needs_review"
    assert profile["profile_id"] == "national-rnd-basic"
    assert profile["status"] == "needs_review"
    assert profile_sources == []
    assert project_goals["project_id"] == "PRJ-2026-0001"
    assert project_goals["status"] == "needs_review"
    assert "profile_needs_review" in result.warnings
    assert "Evidence is source of truth" in readme
    assert "discover-workspace" in readme
    assert "artifact-authority" in readme
    assert "goals-review" in readme
    assert "bib-import" in readme
    assert "reference-corpus" in readme
    assert "bib-review-record" in readme
    assert "bib-integrity" in readme
    assert "citation-support-record" in readme
    assert "citation-support-integrity" in readme
    assert "research-claim-import" in readme
    assert "research-claim-matrix" in readme
    assert "profile-source-record" in readme
    assert "profile-integrity" in readme
    assert "profile-promotion-record" in readme
    assert "profile-promotion-apply-plan" in readme
    assert "profile-promotion-apply --root" in readme
    assert "profile-promotion-revoke-plan" in readme
    assert "profile-promotion-revoke --root" in readme
    assert "profile-lifecycle-ledger" in readme
    assert "profile-source-queue" in readme
    assert "profile-source-fix-plan" in readme
    assert "profile-source-fix-summary" in readme
    assert "profile-pack-readiness" in readme
    assert "profile-pack-readiness-drilldown" in readme
    assert "budget-ledger-import" in readme
    assert "budget-ledger-integrity" in readme
    assert "checkpoint-create" in readme
    assert "checkpoint-summary" in readme
    assert "checkpoint-resume-plan" in readme
    assert "workspace-summary" in readme
    assert "workspace-review-pack" in readme
    assert "verify-review-pack" in readme
    assert "verify-evidence-sources" in readme
    assert "approval-coverage" in readme
    assert "report-integrity" in readme


def test_initialize_workspace_does_not_overwrite_existing_files(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    existing = state_dir / "project-state.json"
    existing.write_text('{"existing": true}\n', encoding="utf-8")

    result = initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    assert existing.read_text(encoding="utf-8") == '{"existing": true}\n'
    assert str(existing) in result.skipped_existing


def test_initialize_workspace_installs_template_profile_sources(tmp_path):
    result = initialize_workspace(
        tmp_path,
        "PRJ-2026-0002",
        "IRIS Seed Project",
        profile_id="iris-innopolis-2026-017795",
    )

    profile = json.loads((tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8"))
    profile_sources = json.loads((tmp_path / "state" / "profile-sources.json").read_text(encoding="utf-8"))
    copied_source = tmp_path / "state" / "profile-sources" / "iris-announcement-017795-source-note.md"
    integrity = generate_profile_integrity(tmp_path)
    codes = {finding.code for finding in integrity.findings}

    assert result.profile_id == "iris-innopolis-2026-017795"
    assert profile["status"] == "needs_review"
    assert profile_sources[0]["profile_id"] == "iris-innopolis-2026-017795"
    assert profile_sources[0]["source_file"].replace("\\", "/") == "state/profile-sources/iris-announcement-017795-source-note.md"
    assert copied_source.exists()
    assert "profile_source_hash_mismatch" not in codes
    assert "profile_source_not_verified" in codes
    assert "profile_needs_review" in codes


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
    assert (tmp_path / "state" / "profile-sources.json").exists()
    assert (tmp_path / "state" / "project-goals.json").exists()
