import json

from k_resdev_skill.cli import main
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_review import (
    generate_workspace_review_pack,
    render_workspace_review_pack_markdown,
    verify_workspace_review_pack,
)


def test_workspace_review_pack_writes_all_review_artifacts(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    result = generate_workspace_review_pack(tmp_path, max_actions=2)
    rendered = render_workspace_review_pack_markdown(result)

    expected = [
        tmp_path / "reports" / "readiness.md",
        tmp_path / "state" / "readiness.json",
        tmp_path / "reports" / "next-actions.md",
        tmp_path / "state" / "next-actions.json",
        tmp_path / "reports" / "workspace-summary.md",
        tmp_path / "state" / "workspace-summary.json",
        tmp_path / "reports" / "source-verification.md",
        tmp_path / "state" / "source-verification.json",
        tmp_path / "reports" / "approval-coverage.md",
        tmp_path / "state" / "approval-coverage.json",
        tmp_path / "reports" / "report-integrity.md",
        tmp_path / "state" / "report-integrity.json",
        tmp_path / "reports" / "workspace-review-pack.md",
        tmp_path / "state" / "workspace-review-pack.json",
    ]

    assert result.status == "blocked"
    assert result.action_count > 0
    assert result.source_verification_valid is False
    assert result.approval_coverage_status == "no_artifacts"
    assert result.report_integrity_status == "no_reports"
    assert result.artifacts
    assert all(len(artifact.sha256) == 64 for artifact in result.artifacts)
    assert all(path.exists() for path in expected)
    assert "Review pack projection only" in rendered
    assert "Source verification valid" in rendered
    assert "Approval coverage status" in rendered
    assert "Report integrity status" in rendered
    assert "Hashed artifacts" in rendered
    assert json.loads((tmp_path / "state" / "workspace-review-pack.json").read_text(encoding="utf-8"))["index_path"] == str(
        tmp_path / "reports" / "workspace-review-pack.md"
    )
    assert json.loads((tmp_path / "state" / "workspace-summary.json").read_text(encoding="utf-8"))["report_paths"] == []
    assert json.loads((tmp_path / "state" / "source-verification.json").read_text(encoding="utf-8"))["valid"] is False
    assert json.loads((tmp_path / "state" / "approval-coverage.json").read_text(encoding="utf-8"))["status"] == "no_artifacts"
    assert json.loads((tmp_path / "state" / "report-integrity.json").read_text(encoding="utf-8"))["status"] == "no_reports"
    assert verify_workspace_review_pack(tmp_path / "state" / "workspace-review-pack.json").valid is True


def test_workspace_review_pack_cli(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    assert main(["workspace-review-pack", "--root", str(tmp_path), "--max-actions", "2"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["root"] == str(tmp_path)
    assert (tmp_path / "reports" / "workspace-review-pack.md").exists()
    assert (tmp_path / "state" / "workspace-review-pack.json").exists()
    assert (tmp_path / "reports" / "source-verification.md").exists()
    assert (tmp_path / "reports" / "approval-coverage.md").exists()
    assert (tmp_path / "reports" / "report-integrity.md").exists()


def test_verify_review_pack_cli_detects_tampering(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    generate_workspace_review_pack(tmp_path)
    manifest = tmp_path / "state" / "workspace-review-pack.json"

    assert main(["verify-review-pack", str(manifest)]) == 0
    valid_payload = json.loads(capsys.readouterr().out)
    assert valid_payload["valid"] is True

    (tmp_path / "reports" / "next-actions.md").write_text("# changed\n", encoding="utf-8")

    assert main(["verify-review-pack", str(manifest)]) == 1
    invalid_payload = json.loads(capsys.readouterr().out)
    assert invalid_payload["valid"] is False
    assert invalid_payload["mismatch_count"] == 1


def test_operational_markdown_does_not_satisfy_report_draft_check(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    for name in ["readiness.md", "next-actions.md", "workspace-summary.md", "source-verification.md", "approval-coverage.md", "report-integrity.md", "workspace-review-pack.md"]:
        (tmp_path / "reports" / name).write_text("# Operational\n", encoding="utf-8")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert "report_missing" in codes
