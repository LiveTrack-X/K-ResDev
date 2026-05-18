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
        tmp_path / "reports" / "workspace-discovery.md",
        tmp_path / "state" / "workspace-discovery.json",
        tmp_path / "reports" / "next-actions.md",
        tmp_path / "state" / "next-actions.json",
        tmp_path / "reports" / "workspace-summary.md",
        tmp_path / "state" / "workspace-summary.json",
        tmp_path / "reports" / "source-verification.md",
        tmp_path / "state" / "source-verification.json",
        tmp_path / "reports" / "artifact-authority.md",
        tmp_path / "state" / "artifact-authority.json",
        tmp_path / "reports" / "goals-review.md",
        tmp_path / "state" / "goals-review.json",
        tmp_path / "reports" / "workspace-dashboard.md",
        tmp_path / "state" / "workspace-dashboard.json",
        tmp_path / "reports" / "approval-coverage.md",
        tmp_path / "state" / "approval-coverage.json",
        tmp_path / "reports" / "report-integrity.md",
        tmp_path / "state" / "report-integrity.json",
        tmp_path / "reports" / "budget-ledger.md",
        tmp_path / "state" / "budget-ledger-integrity.json",
        tmp_path / "reports" / "bibliography-integrity.md",
        tmp_path / "state" / "bibliography-integrity.json",
        tmp_path / "reports" / "reference-corpus-summary.md",
        tmp_path / "state" / "literature-corpus.json",
        tmp_path / "state" / "reference-rejection-log.json",
        tmp_path / "reports" / "citation-support.md",
        tmp_path / "state" / "citation-support.json",
        tmp_path / "reports" / "research-claim-matrix.md",
        tmp_path / "state" / "research-claim-matrix.json",
        tmp_path / "reports" / "profile-integrity.md",
        tmp_path / "state" / "profile-integrity.json",
        tmp_path / "reports" / "profile-promotion-apply-plan.md",
        tmp_path / "state" / "profile-promotion-apply-plan.json",
        tmp_path / "reports" / "workspace-trace.md",
        tmp_path / "state" / "workspace-trace.json",
        tmp_path / "reports" / "trace-passport.md",
        tmp_path / "state" / "trace-passport.json",
        tmp_path / "reports" / "workspace-review-pack.md",
        tmp_path / "state" / "workspace-review-pack.json",
    ]

    assert result.status == "blocked"
    assert result.action_count > 0
    assert result.source_verification_valid is False
    assert result.approval_coverage_status == "no_artifacts"
    assert result.approval_hash_mismatch_count == 0
    assert result.approval_hash_unverified_count == 0
    assert result.report_integrity_status == "no_reports"
    assert result.discovery_status == "ready_with_notes"
    assert result.discovery_scanned_count >= 1
    assert result.discovery_missing_standard_dir_count == 0
    assert result.discovery_loose_candidate_count == 0
    assert result.discovery_setup_proposal_count >= 1
    assert result.artifact_authority_status in {"ready", "ready_with_notes"}
    assert result.artifact_authority_count >= 0
    assert result.artifact_authority_finding_count == 0
    assert result.artifact_authority_high_count == 0
    assert result.goals_review_status == "needs_review"
    assert result.objective_count == 0
    assert result.deadline_count == 0
    assert result.goals_review_finding_count >= 1
    assert result.goals_review_high_count == 0
    assert result.weekly_review_status == "blocked"
    assert result.weekly_review_item_count > 0
    assert result.weekly_review_high_count >= 1
    assert result.dashboard_status == "blocked"
    assert result.dashboard_card_count > 0
    assert result.budget_ledger_status == "not_configured"
    assert result.budget_ledger_count == 0
    assert result.budget_ledger_finding_count == 0
    assert result.bibliography_integrity_status == "not_configured"
    assert result.bibliography_review_count == 0
    assert result.bibliography_integrity_finding_count == 0
    assert result.reference_corpus_status == "not_configured"
    assert result.reference_corpus_count == 0
    assert result.reference_rejection_count == 0
    assert result.citation_support_status == "not_configured"
    assert result.citation_support_count == 0
    assert result.citation_support_finding_count == 0
    assert result.research_claim_matrix_status == "not_configured"
    assert result.research_claim_count == 0
    assert result.research_claim_matrix_finding_count == 0
    assert result.profile_integrity_status == "needs_review"
    assert result.profile_source_count == 0
    assert result.profile_integrity_finding_count >= 1
    assert result.workspace_trace_node_count >= 0
    assert result.trace_passport_status == "not_configured"
    assert result.checkpoint_count == 0
    assert result.trace_passport_finding_count == 0
    assert result.artifacts
    assert all(len(artifact.sha256) == 64 for artifact in result.artifacts)
    assert all(path.exists() for path in expected)
    assert "Review pack projection only" in rendered
    assert "Source verification valid" in rendered
    assert "Approval coverage status" in rendered
    assert "Approval hash mismatch count" in rendered
    assert "Report integrity status" in rendered
    assert "Workspace discovery status" in rendered
    assert "Artifact authority status" in rendered
    assert "Goals review status" in rendered
    assert "Weekly review status" in rendered
    assert "Workspace dashboard status" in rendered
    assert "Budget ledger status" in rendered
    assert "Bibliography integrity status" in rendered
    assert "Reference corpus status" in rendered
    assert "Citation support status" in rendered
    assert "Research claim matrix status" in rendered
    assert "Profile integrity status" in rendered
    assert "Profile promotion apply-plan status" in rendered
    assert "Profile promotion apply-result status" in rendered
    assert "Workspace trace status" in rendered
    assert "Trace passport status" in rendered
    assert "Hashed artifacts" in rendered
    assert json.loads((tmp_path / "state" / "workspace-review-pack.json").read_text(encoding="utf-8"))["index_path"] == str(
        tmp_path / "reports" / "workspace-review-pack.md"
    )
    assert json.loads((tmp_path / "state" / "workspace-summary.json").read_text(encoding="utf-8"))["report_paths"] == []
    assert json.loads((tmp_path / "state" / "source-verification.json").read_text(encoding="utf-8"))["valid"] is False
    assert json.loads((tmp_path / "state" / "approval-coverage.json").read_text(encoding="utf-8"))["status"] == "no_artifacts"
    assert json.loads((tmp_path / "state" / "artifact-authority.json").read_text(encoding="utf-8"))["status"] in {"ready", "ready_with_notes"}
    assert json.loads((tmp_path / "state" / "goals-review.json").read_text(encoding="utf-8"))["status"] == "needs_review"
    assert json.loads(next((tmp_path / "state").glob("weekly-review-*.json")).read_text(encoding="utf-8"))["item_count"] > 0
    assert json.loads((tmp_path / "state" / "workspace-dashboard.json").read_text(encoding="utf-8"))["card_count"] > 0
    assert json.loads((tmp_path / "state" / "report-integrity.json").read_text(encoding="utf-8"))["status"] == "no_reports"
    assert json.loads((tmp_path / "state" / "workspace-discovery.json").read_text(encoding="utf-8"))["status"] == "ready_with_notes"
    assert json.loads((tmp_path / "state" / "budget-ledger-integrity.json").read_text(encoding="utf-8"))["status"] == "not_configured"
    assert json.loads((tmp_path / "state" / "bibliography-integrity.json").read_text(encoding="utf-8"))["status"] == "not_configured"
    assert json.loads((tmp_path / "state" / "literature-corpus.json").read_text(encoding="utf-8"))["status"] == "not_configured"
    assert json.loads((tmp_path / "state" / "citation-support.json").read_text(encoding="utf-8"))["status"] == "not_configured"
    assert json.loads((tmp_path / "state" / "research-claim-matrix.json").read_text(encoding="utf-8"))["status"] == "not_configured"
    assert json.loads((tmp_path / "state" / "profile-integrity.json").read_text(encoding="utf-8"))["status"] == "needs_review"
    assert json.loads((tmp_path / "state" / "profile-review.json").read_text(encoding="utf-8"))["status"] == "needs_review"
    assert json.loads((tmp_path / "state" / "profile-promotion-summary.json").read_text(encoding="utf-8"))["status"] == "not_recorded"
    assert json.loads((tmp_path / "state" / "profile-promotion-apply-plan.json").read_text(encoding="utf-8"))["status"] == "missing_promotion_record"
    assert json.loads((tmp_path / "state" / "workspace-trace.json").read_text(encoding="utf-8"))["node_count"] == result.workspace_trace_node_count
    assert json.loads((tmp_path / "state" / "trace-passport.json").read_text(encoding="utf-8"))["status"] == "not_configured"
    assert verify_workspace_review_pack(tmp_path / "state" / "workspace-review-pack.json").valid is True


def test_workspace_review_pack_cli(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    assert main(["workspace-review-pack", "--root", str(tmp_path), "--max-actions", "2"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["root"] == str(tmp_path)
    assert (tmp_path / "reports" / "workspace-review-pack.md").exists()
    assert (tmp_path / "state" / "workspace-review-pack.json").exists()
    assert (tmp_path / "reports" / "source-verification.md").exists()
    assert (tmp_path / "reports" / "workspace-discovery.md").exists()
    assert (tmp_path / "reports" / "artifact-authority.md").exists()
    assert (tmp_path / "reports" / "goals-review.md").exists()
    assert any(path.name.startswith("weekly-review-") for path in (tmp_path / "reports").glob("*.md"))
    assert (tmp_path / "reports" / "workspace-dashboard.md").exists()
    assert (tmp_path / "reports" / "approval-coverage.md").exists()
    assert (tmp_path / "reports" / "report-integrity.md").exists()
    assert (tmp_path / "reports" / "budget-ledger.md").exists()
    assert (tmp_path / "reports" / "bibliography-integrity.md").exists()
    assert (tmp_path / "reports" / "reference-corpus-summary.md").exists()
    assert (tmp_path / "reports" / "citation-support.md").exists()
    assert (tmp_path / "reports" / "research-claim-matrix.md").exists()
    assert (tmp_path / "reports" / "profile-integrity.md").exists()
    assert (tmp_path / "reports" / "profile-review.md").exists()
    assert (tmp_path / "reports" / "profile-promotion-summary.md").exists()
    assert (tmp_path / "reports" / "profile-promotion-apply-plan.md").exists()
    assert (tmp_path / "reports" / "workspace-trace.md").exists()
    assert (tmp_path / "reports" / "trace-passport.md").exists()


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
    for name in [
        "readiness.md",
        "next-actions.md",
        "workspace-summary.md",
        "source-verification.md",
        "approval-coverage.md",
        "artifact-authority.md",
        "goals-review.md",
        "weekly-review-2026-05-19.md",
        "workspace-dashboard.md",
        "workflow-weekly.md",
        "report-integrity.md",
        "budget-ledger.md",
        "bibliography-integrity.md",
        "reference-corpus-summary.md",
        "citation-support.md",
        "citation-support-summary.md",
        "research-claim-matrix.md",
        "research-claims.md",
        "trace-passport.md",
        "workspace-discovery.md",
        "checkpoint-resume-plan.md",
        "profile-integrity.md",
        "profile-promotion-apply-plan.md",
        "profile-promotion-apply-result.md",
        "profile-lifecycle-ledger.md",
        "profile-promotion-revoke-plan.md",
        "profile-promotion-revoke-result.md",
        "profile-promotion-summary.md",
        "profile-review.md",
        "profile-source-fix-plan.md",
        "profile-source-fix-summary.md",
        "profile-source-queue.md",
        "profile-source-summary.md",
        "workspace-trace.md",
        "workspace-review-pack.md",
    ]:
        (tmp_path / "reports" / name).write_text("# Operational\n", encoding="utf-8")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert "report_missing" in codes
