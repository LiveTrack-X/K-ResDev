import hashlib
import json
from pathlib import Path

from k_resdev_skill.cli import main
from k_resdev_skill.profile_source_queue import generate_profile_source_queue, load_profile_source_queue
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def _write_profile_pack(root: Path, profile_id: str = "demo-profile", with_sources: bool = True, review_status: str = "needs_review") -> Path:
    profile_dir = root / profile_id
    profile_dir.mkdir(parents=True)
    (profile_dir / "project-profile.json").write_text(
        json.dumps(
            {
                "profile_id": profile_id,
                "agency": "Demo Agency",
                "program": "Demo Program",
                "report_cycle": "annual",
                "required_outputs": [],
                "budget_categories": [],
                "field_map": {},
                "status": "needs_review",
                "notes": "Test profile.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if with_sources:
        source_file = profile_dir / "source-note.md"
        source_file.write_text("official source note\n", encoding="utf-8")
        (profile_dir / "profile-sources.json").write_text(
            json.dumps(
                [
                    {
                        "source_id": "PSRC-DEMO",
                        "profile_id": profile_id,
                        "title": "Demo source",
                        "source_url": "https://example.org/source",
                        "source_file": "source-note.md",
                        "retrieved_at": "2026-05-19",
                        "source_hash": hashlib.sha256(source_file.read_bytes()).hexdigest(),
                        "source_size_bytes": source_file.stat().st_size,
                        "verified_by": "reviewer" if review_status == "verified" else None,
                        "review_status": review_status,
                        "validity_notes": "Needs human review.",
                        "risk_flags": [] if review_status == "verified" else ["human_verification_required"],
                    }
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return profile_dir


def test_profile_source_queue_flags_template_missing_sources(tmp_path):
    templates_root = tmp_path / "templates" / "agencies"
    _write_profile_pack(templates_root, with_sources=False)

    result = generate_profile_source_queue(tmp_path, templates_root=templates_root)

    assert result.status == "needs_review"
    assert result.template_profile_count == 1
    assert "profile_source_records_missing" in {item.issue_code for item in result.items}


def test_profile_source_queue_detects_missing_file_and_hash_mismatch(tmp_path):
    templates_root = tmp_path / "templates" / "agencies"
    profile_dir = _write_profile_pack(templates_root, review_status="verified")
    (profile_dir / "source-note.md").write_text("changed source note\n", encoding="utf-8")

    mismatch = generate_profile_source_queue(tmp_path, templates_root=templates_root)
    codes = {item.issue_code for item in mismatch.items}

    assert mismatch.status == "blocked"
    assert "profile_source_hash_mismatch" in codes

    (profile_dir / "source-note.md").unlink()
    missing = generate_profile_source_queue(tmp_path, templates_root=templates_root)
    assert "profile_source_file_missing" in {item.issue_code for item in missing.items}


def test_profile_source_queue_ready_for_verified_source_with_empty_template_root(tmp_path):
    templates_root = tmp_path / "empty-templates"
    templates_root.mkdir()
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project", profile_id="iris-innopolis-2026-017795")
    sources_path = tmp_path / "state" / "profile-sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    sources[0]["review_status"] = "verified"
    sources[0]["verified_by"] = "project-owner"
    sources[0]["risk_flags"] = []
    sources_path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")

    result = generate_profile_source_queue(tmp_path, templates_root=templates_root)

    assert result.status == "ready"
    assert result.workspace_profile_count == 1
    assert result.queue_item_count == 0


def test_profile_source_queue_cli_and_schema_validation(tmp_path, capsys):
    templates_root = tmp_path / "templates" / "agencies"
    _write_profile_pack(templates_root, review_status="needs_review")
    output = tmp_path / "reports" / "profile-source-queue.md"
    json_path = tmp_path / "state" / "profile-source-queue.json"

    assert main(["profile-source-queue", "--root", str(tmp_path), "--templates-root", str(templates_root), "--output", str(output), "--json", str(json_path)]) == 0
    assert main(["validate-json", "profile-source-queue", str(json_path)]) == 0
    assert "profile-source-queue.json" in capsys.readouterr().out
    assert load_profile_source_queue(json_path).queue_item_count >= 1


def test_profile_source_queue_flows_into_doctor_actions_summary_review_and_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    generate_profile_source_queue(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-queue.md",
        json_path=tmp_path / "state" / "profile-source-queue.json",
    )

    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor, action_plan=actions)
    review_pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)

    assert "profile_source_queue_review_findings" in {finding.code for finding in doctor.findings}
    assert any(action.title == "Review profile source pack queue" for action in actions.actions)
    assert summary.profile_source_queue_status in {"needs_review", "blocked"}
    assert summary.profile_source_queue_item_count >= 1
    assert str(tmp_path / "reports" / "profile-source-queue.md") in review_pack.generated_paths
    assert review_pack.profile_source_queue_item_count >= 1
    assert "profile_source_queue" in {node.node_type for node in trace.nodes}
