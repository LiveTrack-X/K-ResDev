import json

from k_resdev_skill.cli import main
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.schema_tools import validate_json_file, validate_json_files
from k_resdev_skill.evidence_index import write_evidence_index


def test_validate_json_file_with_bundled_schema(tmp_path):
    approval = {
        "approval_id": "APR-2026-ABCD1234",
        "target_type": "report",
        "target_id": "monthly-2026-05",
        "target_path": None,
        "decision": "approved",
        "reviewer": "Dr. Kim",
        "reviewed_at": "2026-05-17T09:00:00Z",
        "evidence_ids": ["EVI-2026-ABCD1234"],
        "notes": None,
        "risk_flags": [],
    }
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(approval), encoding="utf-8")

    result = validate_json_file(path, "approval")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_files_reports_errors(tmp_path):
    path = tmp_path / "bad-approval.json"
    path.write_text(json.dumps({"approval_id": "APR-2026-BAD"}), encoding="utf-8")

    result = validate_json_files([path], "approval")

    assert result["valid"] is False
    assert result["results"][0]["error_count"] > 0
    assert any("required" in error["message"] for error in result["results"][0]["errors"])


def test_validate_json_file_accepts_generated_evidence_index(tmp_path):
    item = EvidenceItem(
        evidence_id="EVI-2026-0001",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Validation Dice reached 0.83.",
    )
    paths = write_evidence_index([item], tmp_path / "state")

    result = validate_json_file(paths.json_path, "evidence")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_file_accepts_citation_support_alias():
    result = validate_json_file("templates/citation-support-record.json", "citation-support")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_file_accepts_research_claim_alias():
    result = validate_json_file("templates/research-claim.json", "research-claim")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_file_accepts_checkpoint_alias():
    result = validate_json_file("templates/trace-passport-entry.json", "checkpoint")

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_validate_json_file_accepts_reference_aliases():
    item = validate_json_file("templates/reference-corpus-item.json", "reference-corpus-item")
    rejection = validate_json_file("templates/reference-rejection.json", "reference-rejection")

    assert item["valid"] is True
    assert rejection["valid"] is True


def test_validate_json_file_accepts_workspace_discovery_aliases():
    item = validate_json_file("templates/workspace-discovery-item.json", "workspace-discovery-item")
    proposal = validate_json_file("templates/workspace-setup-proposal.json", "workspace-setup-proposal")

    assert item["valid"] is True
    assert proposal["valid"] is True


def test_validate_json_file_accepts_artifact_authority_aliases():
    record = validate_json_file("templates/artifact-authority-record.json", "artifact-authority-record")
    finding = validate_json_file("templates/artifact-authority-finding.json", "artifact-authority-finding")

    assert record["valid"] is True
    assert finding["valid"] is True


def test_validate_json_file_accepts_project_goals_aliases():
    goals = validate_json_file("templates/project-goals.json", "project-goals")
    objective = validate_json_file("templates/project-objective.json", "project-objective")
    deadline = validate_json_file("templates/project-deadline.json", "project-deadline")

    assert goals["valid"] is True
    assert objective["valid"] is True
    assert deadline["valid"] is True


def test_validate_json_file_accepts_weekly_review_and_dashboard_aliases():
    weekly_item = validate_json_file("templates/weekly-review-item.json", "weekly-review-item")
    dashboard_card = validate_json_file("templates/dashboard-card.json", "dashboard-card")

    assert weekly_item["valid"] is True
    assert dashboard_card["valid"] is True


def test_validate_json_file_accepts_workflow_aliases():
    step = validate_json_file("templates/workflow-step.json", "workflow-step")
    plan = validate_json_file("templates/workflow-plan.json", "workflow-plan")

    assert step["valid"] is True
    assert plan["valid"] is True


def test_validate_json_file_accepts_profile_review_aliases():
    source_fix_plan_action = validate_json_file("templates/profile-source-fix-plan-action.json", "profile-source-fix-plan-action")
    source_fix_plan = validate_json_file("templates/profile-source-fix-plan.json", "profile-source-fix-plan")
    source_fix_review = validate_json_file("templates/profile-source-fix-review-record.json", "profile-source-fix-review")
    source_fix_review_finding = validate_json_file("templates/profile-source-fix-review-finding.json", "profile-source-fix-review-finding")
    source_fix_summary = validate_json_file("templates/profile-source-fix-review-summary.json", "profile-source-fix-summary")
    source_queue_item = validate_json_file("templates/profile-source-queue-item.json", "profile-source-queue-item")
    source_queue = validate_json_file("templates/profile-source-queue.json", "profile-source-queue")
    check = validate_json_file("templates/profile-review-check.json", "profile-review-check")
    promotion = validate_json_file("templates/profile-promotion-record.json", "profile-promotion-record")
    apply_plan = validate_json_file("templates/profile-promotion-apply-plan.json", "profile-promotion-apply-plan")
    apply_result = validate_json_file("templates/profile-promotion-apply-result.json", "profile-promotion-apply-result")
    revoke_plan = validate_json_file("templates/profile-promotion-revoke-plan.json", "profile-promotion-revoke-plan")
    revoke_result = validate_json_file("templates/profile-promotion-revoke-result.json", "profile-promotion-revoke-result")
    lifecycle_entry = validate_json_file("templates/profile-lifecycle-entry.json", "profile-lifecycle-entry")
    lifecycle_finding = validate_json_file("templates/profile-lifecycle-finding.json", "profile-lifecycle-finding")
    lifecycle_ledger = validate_json_file("templates/profile-lifecycle-ledger.json", "profile-lifecycle-ledger")
    profile_pack_readiness_profile = validate_json_file("templates/profile-pack-readiness-profile.json", "profile-pack-readiness-profile")
    profile_pack_readiness_finding = validate_json_file("templates/profile-pack-readiness-finding.json", "profile-pack-readiness-finding")
    profile_pack_readiness = validate_json_file("templates/profile-pack-readiness.json", "profile-pack-readiness")
    profile_pack_drilldown_artifact = validate_json_file("templates/profile-pack-readiness-drilldown-artifact.json", "profile-pack-readiness-drilldown-artifact")
    profile_pack_drilldown_item = validate_json_file("templates/profile-pack-readiness-drilldown-item.json", "profile-pack-readiness-drilldown-item")
    profile_pack_drilldown = validate_json_file("templates/profile-pack-readiness-drilldown.json", "profile-pack-readiness-drilldown")
    profile_pack_investigation_artifact = validate_json_file("templates/profile-pack-investigation-artifact.json", "profile-pack-investigation-artifact")
    profile_pack_investigation_item = validate_json_file("templates/profile-pack-investigation-item.json", "profile-pack-investigation-item")
    profile_pack_investigation = validate_json_file("templates/profile-pack-investigation-bundle.json", "profile-pack-investigation-bundle")
    profile_pack_package_artifact = validate_json_file("templates/profile-pack-investigation-package-artifact.json", "profile-pack-investigation-package-artifact")
    profile_pack_package_exclusion = validate_json_file("templates/profile-pack-investigation-package-exclusion.json", "profile-pack-investigation-package-exclusion")
    profile_pack_package = validate_json_file("templates/profile-pack-investigation-package.json", "profile-pack-investigation-package")

    assert source_fix_plan_action["valid"] is True
    assert source_fix_plan["valid"] is True
    assert source_fix_review["valid"] is True
    assert source_fix_review_finding["valid"] is True
    assert source_fix_summary["valid"] is True
    assert source_queue_item["valid"] is True
    assert source_queue["valid"] is True
    assert check["valid"] is True
    assert promotion["valid"] is True
    assert apply_plan["valid"] is True
    assert apply_result["valid"] is True
    assert revoke_plan["valid"] is True
    assert revoke_result["valid"] is True
    assert lifecycle_entry["valid"] is True
    assert lifecycle_finding["valid"] is True
    assert lifecycle_ledger["valid"] is True
    assert profile_pack_readiness_profile["valid"] is True
    assert profile_pack_readiness_finding["valid"] is True
    assert profile_pack_readiness["valid"] is True
    assert profile_pack_drilldown_artifact["valid"] is True
    assert profile_pack_drilldown_item["valid"] is True
    assert profile_pack_drilldown["valid"] is True
    assert profile_pack_investigation_artifact["valid"] is True
    assert profile_pack_investigation_item["valid"] is True
    assert profile_pack_investigation["valid"] is True
    assert profile_pack_package_artifact["valid"] is True
    assert profile_pack_package_exclusion["valid"] is True
    assert profile_pack_package["valid"] is True


def test_validate_json_cli_returns_nonzero_for_invalid(tmp_path, capsys):
    path = tmp_path / "bad-approval.json"
    path.write_text(json.dumps({"approval_id": "APR-2026-BAD"}), encoding="utf-8")

    assert main(["validate-json", "approval", str(path)]) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is False
