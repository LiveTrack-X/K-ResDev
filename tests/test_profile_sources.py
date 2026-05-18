import hashlib
import json

from k_resdev_skill.cli import main
from k_resdev_skill.models import ProjectProfile
from k_resdev_skill.profile_sources import (
    create_profile_source_record,
    generate_profile_integrity,
    load_profile_sources,
    record_profile_source,
    summarize_profile_sources,
)
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_profile_source_record_captures_local_file_hash_and_summary(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    official = tmp_path / "references" / "official-guidance.md"
    official.write_text("# Official guidance snapshot\n", encoding="utf-8")
    record = create_profile_source_record(
        "national-rnd-basic",
        "Official guidance snapshot",
        source_url="https://example.test/official-guidance",
        source_file="references/official-guidance.md",
        retrieved_at="2026-05-18",
        verified_by="Reviewer",
        review_status="verified",
        root=tmp_path,
    )

    record_profile_source(record, tmp_path / "state" / "profile-sources.json")
    loaded = load_profile_sources(tmp_path / "state" / "profile-sources.json")
    summary = summarize_profile_sources(
        tmp_path,
        output_path=tmp_path / "reports" / "profile-source-summary.md",
        json_path=tmp_path / "state" / "profile-source-summary.json",
    )

    assert loaded[0].source_hash == _sha256(official)
    assert loaded[0].source_size_bytes == official.stat().st_size
    assert summary.source_count == 1
    assert summary.verified_source_count == 1
    assert summary.status == "source_verified_profile_needs_review"
    assert (tmp_path / "reports" / "profile-source-summary.md").read_text(encoding="utf-8").startswith("# Profile Source Summary")


def test_profile_integrity_flags_empty_sources_and_verified_profile_without_source(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    needs_review = generate_profile_integrity(tmp_path)
    codes = {finding.code for finding in needs_review.findings}

    assert needs_review.status == "needs_review"
    assert "profile_sources_empty" in codes
    assert "profile_needs_review" in codes

    verified_profile = ProjectProfile(
        profile_id="national-rnd-basic",
        required_outputs=[],
        budget_categories=[],
        field_map={},
        status="verified",
    )
    (tmp_path / "state" / "project-profile.json").write_text(verified_profile.model_dump_json(indent=2) + "\n", encoding="utf-8")

    blocked = generate_profile_integrity(tmp_path)
    blocked_codes = {finding.code for finding in blocked.findings}

    assert blocked.status == "blocked"
    assert "profile_verified_without_verified_source" in blocked_codes


def test_profile_integrity_detects_source_hash_mismatch(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    official = tmp_path / "references" / "official-guidance.md"
    official.write_text("# Official guidance snapshot\n", encoding="utf-8")
    record = create_profile_source_record(
        "national-rnd-basic",
        "Official guidance snapshot",
        source_file="references/official-guidance.md",
        retrieved_at="2026-05-18",
        verified_by="Reviewer",
        review_status="verified",
        root=tmp_path,
    )
    record_profile_source(record, tmp_path / "state" / "profile-sources.json")
    official.write_text("# Changed guidance snapshot\n", encoding="utf-8")

    result = generate_profile_integrity(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "profile_source_hash_mismatch" in codes


def test_profile_integrity_flows_into_doctor_and_actions(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    doctor = run_workspace_doctor(tmp_path)
    plan = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    codes = {finding.code for finding in doctor.findings}

    assert "profile_integrity_review_findings" in codes
    assert any(action.title == "Review profile source integrity" for action in plan.actions)


def test_profile_source_records_appear_in_workspace_trace(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    record = create_profile_source_record(
        "national-rnd-basic",
        "Unreviewed source",
        source_url="https://example.test/source",
        retrieved_at="2026-05-18",
        review_status="needs_review",
    )
    record_profile_source(record, tmp_path / "state" / "profile-sources.json")

    trace = generate_workspace_trace(tmp_path)
    node_types = {node.node_type for node in trace.nodes}
    codes = {finding.code for finding in trace.findings}

    assert "profile_source" in node_types
    assert "trace_profile_source_not_verified" in codes


def test_profile_source_cli_commands(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    official = tmp_path / "references" / "official-guidance.md"
    official.write_text("# Official guidance snapshot\n", encoding="utf-8")

    assert (
        main(
            [
                "profile-source-record",
                "--root",
                str(tmp_path),
                "--profile-id",
                "national-rnd-basic",
                "--title",
                "Official guidance snapshot",
                "--source-file",
                "references/official-guidance.md",
                "--retrieved-at",
                "2026-05-18",
                "--verified-by",
                "Reviewer",
                "--review-status",
                "verified",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["source_hash"] == _sha256(official)

    summary_md = tmp_path / "reports" / "profile-source-summary.md"
    summary_json = tmp_path / "state" / "profile-source-summary.json"
    assert main(["profile-source-summary", "--root", str(tmp_path), "--output", str(summary_md), "--json", str(summary_json)]) == 0
    assert json.loads(capsys.readouterr().out)["verified_source_count"] == 1
    assert summary_md.exists()
    assert summary_json.exists()

    integrity_md = tmp_path / "reports" / "profile-integrity.md"
    integrity_json = tmp_path / "state" / "profile-integrity.json"
    assert main(["profile-integrity", "--root", str(tmp_path), "--output", str(integrity_md), "--json", str(integrity_json)]) == 0
    assert json.loads(capsys.readouterr().out)["source_count"] == 1
    assert integrity_md.exists()
    assert integrity_json.exists()

    assert main(["validate-json", "profile-source", str(tmp_path / "state" / "profile-sources.json")]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True


def _sha256(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
