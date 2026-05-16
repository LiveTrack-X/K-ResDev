import json

from k_resdev_skill.cli import main
from k_resdev_skill.profile_registry import generate_profile_registry, list_project_profiles, load_project_profile


def test_profile_registry_lists_templates(tmp_path):
    profile_dir = tmp_path / "agencies" / "national-rnd-basic"
    profile_dir.mkdir(parents=True)
    (profile_dir / "project-profile.json").write_text(
        json.dumps(
            {
                "profile_id": "national-rnd-basic",
                "agency": None,
                "program": None,
                "report_cycle": "annual/interim/final needs_review",
                "required_outputs": ["annual-report"],
                "budget_categories": [],
                "field_map": {"project_title": "needs_review"},
                "status": "needs_review",
                "notes": "Skeleton only.",
            }
        ),
        encoding="utf-8",
    )
    (profile_dir / "annual-report.md").write_text("# Annual\n", encoding="utf-8")

    profiles = list_project_profiles(tmp_path / "agencies")
    rendered = generate_profile_registry(tmp_path / "agencies")

    assert profiles[0]["profile_id"] == "national-rnd-basic"
    assert profiles[0]["template_files"] == ["annual-report.md"]
    assert "not official agency rules" in rendered


def test_validate_profile_cli(tmp_path, capsys):
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        """{
          "profile_id": "test-profile",
          "required_outputs": [],
          "budget_categories": [],
          "field_map": {},
          "status": "needs_review"
        }""",
        encoding="utf-8",
    )

    assert main(["validate-profile", str(profile_path)]) == 0

    assert "test-profile" in capsys.readouterr().out
    assert load_project_profile(profile_path).profile_id == "test-profile"


def test_profiles_cli_json_and_markdown(tmp_path, capsys):
    profile_dir = tmp_path / "agencies" / "profile-a"
    profile_dir.mkdir(parents=True)
    (profile_dir / "project-profile.json").write_text(
        """{
          "profile_id": "profile-a",
          "required_outputs": [],
          "budget_categories": [],
          "field_map": {},
          "status": "needs_review"
        }""",
        encoding="utf-8",
    )
    output_path = tmp_path / "profiles.md"

    assert main(["profiles", "--templates-root", str(tmp_path / "agencies")]) == 0
    assert "profile-a" in capsys.readouterr().out
    assert main(["profiles", "--templates-root", str(tmp_path / "agencies"), "--markdown", "--output", str(output_path)]) == 0

    assert "Agency Profile Registry" in output_path.read_text(encoding="utf-8")
