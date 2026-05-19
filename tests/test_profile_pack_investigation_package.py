import json
import zipfile
from pathlib import Path

from k_resdev_skill.cli import main
from k_resdev_skill.profile_lifecycle import generate_profile_lifecycle_ledger
from k_resdev_skill.profile_pack_drilldown import generate_profile_pack_readiness_drilldown
from k_resdev_skill.profile_pack_investigation import generate_profile_pack_investigation_bundle
from k_resdev_skill.profile_pack_investigation_package import (
    generate_profile_pack_investigation_package,
    load_profile_pack_investigation_package,
)
from k_resdev_skill.profile_pack_readiness import generate_profile_pack_readiness
from k_resdev_skill.profile_promotion import summarize_profile_promotions
from k_resdev_skill.profile_promotion_apply import generate_profile_promotion_apply_plan
from k_resdev_skill.profile_review import generate_profile_review
from k_resdev_skill.profile_source_fix_plan import generate_profile_source_fix_plan
from k_resdev_skill.profile_source_fix_review import summarize_profile_source_fix_reviews
from k_resdev_skill.profile_source_queue import generate_profile_source_queue
from k_resdev_skill.profile_sources import generate_profile_integrity
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_profile_pack_investigation_package_manifest_excludes_raw_sources(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    profile_before = (tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8")
    _write_profile_pack_inputs(tmp_path)

    result = generate_profile_pack_investigation_package(
        tmp_path,
        profile_id="national-rnd-basic",
        output_path=tmp_path / "reports" / "profile-pack-investigation-package.md",
        json_path=tmp_path / "state" / "profile-pack-investigation-package.json",
    )

    assert result.status in {"needs_review", "ready_with_notes"}
    assert result.selected_item_count >= 1
    assert result.included_artifact_count >= 1
    assert result.missing_artifact_count == 0
    assert result.excluded_artifact_count >= 1
    assert any(exclusion.reason == "raw_or_upstream_source_body_excluded" for exclusion in result.exclusions)
    assert all(_is_generated_metadata_artifact(tmp_path, artifact.path) for artifact in result.artifacts if artifact.included)
    assert (tmp_path / "reports" / "profile-pack-investigation-package.md").read_text(encoding="utf-8").startswith(
        "# Profile Pack Investigation Package"
    )
    assert load_profile_pack_investigation_package(tmp_path / "state" / "profile-pack-investigation-package.json").package_id == result.package_id
    assert (tmp_path / "state" / "project-profile.json").read_text(encoding="utf-8") == profile_before


def test_profile_pack_investigation_package_cli_schema_and_zip(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    _write_profile_pack_inputs(tmp_path)
    output = tmp_path / "reports" / "profile-pack-investigation-package.md"
    json_path = tmp_path / "state" / "profile-pack-investigation-package.json"
    zip_path = tmp_path / "reports" / "profile-pack-investigation-package.zip"

    assert (
        main(
            [
                "profile-pack-investigation-package",
                "--root",
                str(tmp_path),
                "--profile-id",
                "national-rnd-basic",
                "--output",
                str(output),
                "--json",
                str(json_path),
                "--zip",
                str(zip_path),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["selected_item_count"] >= 1
    assert payload["zip_hash"].startswith("sha256:")
    assert output.exists()
    assert json_path.exists()
    assert zip_path.exists()
    assert main(["validate-json", "profile-pack-investigation-package", str(json_path)]) == 0
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
    assert names
    assert all(name.startswith(("state/", "reports/")) for name in names)
    assert all(Path(name).suffix in {".json", ".md"} for name in names)
    assert not any("sources/" in name or name.startswith("inbox/") for name in names)


def test_profile_pack_investigation_package_flows_into_doctor_actions_summary_review_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    _write_profile_pack_inputs(tmp_path)

    doctor_before = run_workspace_doctor(tmp_path)
    actions_before = generate_workspace_action_plan(tmp_path, doctor_result=doctor_before)
    before_codes = {finding.code for finding in doctor_before.findings}

    assert "profile_pack_investigation_package_missing" in before_codes
    assert any(action.title == "Package profile pack investigation handoff" for action in actions_before.actions)

    generate_profile_pack_investigation_package(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-investigation-package.md",
        json_path=tmp_path / "state" / "profile-pack-investigation-package.json",
    )
    doctor_after = run_workspace_doctor(tmp_path)
    actions_after = generate_workspace_action_plan(tmp_path, doctor_result=doctor_after)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor_after, action_plan=actions_after)
    review_pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    after_codes = {finding.code for finding in doctor_after.findings}

    assert "profile_pack_investigation_package_missing" not in after_codes
    assert summary.profile_pack_package_included_artifact_count >= 1
    assert review_pack.profile_pack_package_included_artifact_count >= 1
    assert str(tmp_path / "reports" / "profile-pack-investigation-package.md") in review_pack.generated_paths
    assert "profile_pack_investigation_package" in {node.node_type for node in trace.nodes}


def _write_profile_pack_inputs(tmp_path):
    generate_profile_integrity(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-integrity.md",
        json_path=tmp_path / "state" / "profile-integrity.json",
    )
    generate_profile_source_queue(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-queue.md",
        json_path=tmp_path / "state" / "profile-source-queue.json",
    )
    generate_profile_source_fix_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-fix-plan.md",
        json_path=tmp_path / "state" / "profile-source-fix-plan.json",
    )
    summarize_profile_source_fix_reviews(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-fix-summary.md",
        json_path=tmp_path / "state" / "profile-source-fix-summary.json",
    )
    generate_profile_review(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-review.md",
        json_path=tmp_path / "state" / "profile-review.json",
    )
    summarize_profile_promotions(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-summary.md",
        json_path=tmp_path / "state" / "profile-promotion-summary.json",
    )
    generate_profile_promotion_apply_plan(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-promotion-apply-plan.md",
        json_path=tmp_path / "state" / "profile-promotion-apply-plan.json",
    )
    generate_profile_lifecycle_ledger(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-lifecycle-ledger.md",
        json_path=tmp_path / "state" / "profile-lifecycle-ledger.json",
    )
    generate_profile_pack_readiness(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-readiness.md",
        json_path=tmp_path / "state" / "profile-pack-readiness.json",
    )
    generate_profile_pack_readiness_drilldown(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-readiness-drilldown.md",
        json_path=tmp_path / "state" / "profile-pack-readiness-drilldown.json",
    )
    generate_profile_pack_investigation_bundle(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-pack-investigation-bundle.md",
        json_path=tmp_path / "state" / "profile-pack-investigation-bundle.json",
    )


def _is_generated_metadata_artifact(root, path):
    target = Path(path)
    relative = target.resolve().relative_to(Path(root).resolve())
    return relative.parts[0] in {"state", "reports"} and target.suffix in {".json", ".md"}
