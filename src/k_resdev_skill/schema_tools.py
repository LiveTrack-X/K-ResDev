from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCHEMA_ALIASES = {
    "approval": "approval_record.schema.json",
    "artifact-authority": "artifact_authority.schema.json",
    "artifact_authority": "artifact_authority.schema.json",
    "artifact-authority-record": "artifact_authority_record.schema.json",
    "artifact_authority_record": "artifact_authority_record.schema.json",
    "artifact-authority-finding": "artifact_authority_finding.schema.json",
    "artifact_authority_finding": "artifact_authority_finding.schema.json",
    "bibliography": "bibliography_entry.schema.json",
    "bibliography-entry": "bibliography_entry.schema.json",
    "bibliography-review": "bibliography_review_record.schema.json",
    "bibliography_review": "bibliography_review_record.schema.json",
    "budget-ledger": "budget_ledger_item.schema.json",
    "budget_ledger": "budget_ledger_item.schema.json",
    "budget-ledger-item": "budget_ledger_item.schema.json",
    "citation-support": "citation_support_record.schema.json",
    "citation_support": "citation_support_record.schema.json",
    "evidence": "evidence.schema.json",
    "goals-review": "goals_review.schema.json",
    "goals_review": "goals_review.schema.json",
    "profile-source": "profile_source.schema.json",
    "profile_source": "profile_source.schema.json",
    "profile-source-fix-plan": "profile_source_fix_plan.schema.json",
    "profile_source_fix_plan": "profile_source_fix_plan.schema.json",
    "profile-source-fix-plan-action": "profile_source_fix_plan_action.schema.json",
    "profile_source_fix_plan_action": "profile_source_fix_plan_action.schema.json",
    "profile-source-fix-review": "profile_source_fix_review_record.schema.json",
    "profile_source_fix_review": "profile_source_fix_review_record.schema.json",
    "profile-source-fix-review-record": "profile_source_fix_review_record.schema.json",
    "profile_source_fix_review_record": "profile_source_fix_review_record.schema.json",
    "profile-source-fix-review-finding": "profile_source_fix_review_finding.schema.json",
    "profile_source_fix_review_finding": "profile_source_fix_review_finding.schema.json",
    "profile-source-fix-summary": "profile_source_fix_review_summary.schema.json",
    "profile_source_fix_summary": "profile_source_fix_review_summary.schema.json",
    "profile-source-fix-review-summary": "profile_source_fix_review_summary.schema.json",
    "profile_source_fix_review_summary": "profile_source_fix_review_summary.schema.json",
    "profile-pack-readiness": "profile_pack_readiness.schema.json",
    "profile_pack_readiness": "profile_pack_readiness.schema.json",
    "profile-pack-readiness-profile": "profile_pack_readiness_profile.schema.json",
    "profile_pack_readiness_profile": "profile_pack_readiness_profile.schema.json",
    "profile-pack-readiness-finding": "profile_pack_readiness_finding.schema.json",
    "profile_pack_readiness_finding": "profile_pack_readiness_finding.schema.json",
    "profile-pack-readiness-drilldown": "profile_pack_readiness_drilldown.schema.json",
    "profile_pack_readiness_drilldown": "profile_pack_readiness_drilldown.schema.json",
    "profile-pack-readiness-drilldown-artifact": "profile_pack_readiness_drilldown_artifact.schema.json",
    "profile_pack_readiness_drilldown_artifact": "profile_pack_readiness_drilldown_artifact.schema.json",
    "profile-pack-readiness-drilldown-item": "profile_pack_readiness_drilldown_item.schema.json",
    "profile_pack_readiness_drilldown_item": "profile_pack_readiness_drilldown_item.schema.json",
    "profile-pack-investigation-bundle": "profile_pack_investigation_bundle.schema.json",
    "profile_pack_investigation_bundle": "profile_pack_investigation_bundle.schema.json",
    "profile-pack-investigation-artifact": "profile_pack_investigation_artifact.schema.json",
    "profile_pack_investigation_artifact": "profile_pack_investigation_artifact.schema.json",
    "profile-pack-investigation-item": "profile_pack_investigation_item.schema.json",
    "profile_pack_investigation_item": "profile_pack_investigation_item.schema.json",
    "profile-source-queue": "profile_source_queue.schema.json",
    "profile_source_queue": "profile_source_queue.schema.json",
    "profile-source-queue-item": "profile_source_queue_item.schema.json",
    "profile_source_queue_item": "profile_source_queue_item.schema.json",
    "profile-review": "profile_review.schema.json",
    "profile_review": "profile_review.schema.json",
    "profile-review-check": "profile_review_check.schema.json",
    "profile_review_check": "profile_review_check.schema.json",
    "profile-promotion": "profile_promotion_record.schema.json",
    "profile_promotion": "profile_promotion_record.schema.json",
    "profile-promotion-record": "profile_promotion_record.schema.json",
    "profile_promotion_record": "profile_promotion_record.schema.json",
    "profile-promotion-summary": "profile_promotion_summary.schema.json",
    "profile_promotion_summary": "profile_promotion_summary.schema.json",
    "profile-promotion-apply-plan": "profile_promotion_apply_plan.schema.json",
    "profile_promotion_apply_plan": "profile_promotion_apply_plan.schema.json",
    "profile-promotion-apply-result": "profile_promotion_apply_result.schema.json",
    "profile_promotion_apply_result": "profile_promotion_apply_result.schema.json",
    "profile-promotion-revoke-plan": "profile_promotion_revoke_plan.schema.json",
    "profile_promotion_revoke_plan": "profile_promotion_revoke_plan.schema.json",
    "profile-promotion-revoke-result": "profile_promotion_revoke_result.schema.json",
    "profile_promotion_revoke_result": "profile_promotion_revoke_result.schema.json",
    "profile-lifecycle-ledger": "profile_lifecycle_ledger.schema.json",
    "profile_lifecycle_ledger": "profile_lifecycle_ledger.schema.json",
    "profile-lifecycle-entry": "profile_lifecycle_entry.schema.json",
    "profile_lifecycle_entry": "profile_lifecycle_entry.schema.json",
    "profile-lifecycle-finding": "profile_lifecycle_finding.schema.json",
    "profile_lifecycle_finding": "profile_lifecycle_finding.schema.json",
    "project-deadline": "project_deadline.schema.json",
    "project_deadline": "project_deadline.schema.json",
    "project-goals": "project_goals.schema.json",
    "project_goals": "project_goals.schema.json",
    "project-objective": "project_objective.schema.json",
    "project_objective": "project_objective.schema.json",
    "project-profile": "project_profile.schema.json",
    "project_state": "project_state.schema.json",
    "project-state": "project_state.schema.json",
    "reference-corpus": "reference_corpus.schema.json",
    "reference_corpus": "reference_corpus.schema.json",
    "reference-corpus-item": "reference_corpus_item.schema.json",
    "reference_corpus_item": "reference_corpus_item.schema.json",
    "reference-rejection": "reference_rejection.schema.json",
    "reference_rejection": "reference_rejection.schema.json",
    "research-insight": "research_insight.schema.json",
    "research_insight": "research_insight.schema.json",
    "research-claim": "research_claim.schema.json",
    "research_claim": "research_claim.schema.json",
    "trace-passport": "trace_passport.schema.json",
    "trace_passport": "trace_passport.schema.json",
    "checkpoint": "trace_passport_entry.schema.json",
    "trace-passport-entry": "trace_passport_entry.schema.json",
    "trace_passport_entry": "trace_passport_entry.schema.json",
    "weekly-review": "weekly_review.schema.json",
    "weekly_review": "weekly_review.schema.json",
    "weekly-review-item": "weekly_review_item.schema.json",
    "weekly_review_item": "weekly_review_item.schema.json",
    "workspace-dashboard": "workspace_dashboard.schema.json",
    "workspace_dashboard": "workspace_dashboard.schema.json",
    "dashboard-card": "dashboard_card.schema.json",
    "dashboard_card": "dashboard_card.schema.json",
    "workflow-plan": "workflow_plan.schema.json",
    "workflow_plan": "workflow_plan.schema.json",
    "workflow-step": "workflow_step.schema.json",
    "workflow_step": "workflow_step.schema.json",
    "workspace-discovery": "workspace_discovery.schema.json",
    "workspace_discovery": "workspace_discovery.schema.json",
    "workspace-discovery-item": "workspace_discovery_item.schema.json",
    "workspace_discovery_item": "workspace_discovery_item.schema.json",
    "workspace-setup-proposal": "workspace_setup_proposal.schema.json",
    "workspace_setup_proposal": "workspace_setup_proposal.schema.json",
}


def bundled_schema_path(schema: str) -> Path:
    candidate = SCHEMA_ALIASES.get(schema, schema)
    path = Path(candidate)
    if path.exists():
        return path
    repo_root = Path(__file__).resolve().parents[2]
    bundled = repo_root / "schemas" / candidate
    if bundled.exists():
        return bundled
    raise FileNotFoundError(f"Schema not found: {schema}")


def validate_json_file(json_path: str | Path, schema: str | Path) -> dict[str, object]:
    document_path = Path(json_path)
    schema_path = bundled_schema_path(str(schema))
    document = json.loads(document_path.read_text(encoding="utf-8"))
    schema_payload = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema_payload)
    errors = []
    for path_prefix, item in _validation_targets(document, schema_payload):
        for error in validator.iter_errors(item):
            errors.append(_format_error(error, path_prefix))
    errors.sort(key=lambda item: item["path"])
    return {
        "valid": not errors,
        "json_path": str(document_path),
        "schema_path": str(schema_path),
        "error_count": len(errors),
        "errors": errors,
    }


def validate_json_files(json_paths: list[str | Path], schema: str | Path) -> dict[str, object]:
    results = [validate_json_file(path, schema) for path in json_paths]
    return {
        "valid": all(result["valid"] for result in results),
        "schema": str(schema),
        "file_count": len(results),
        "results": results,
    }


def _validation_targets(document: Any, schema_payload: dict[str, Any]) -> list[tuple[str, Any]]:
    title = schema_payload.get("title")
    if title in {
        "ApprovalRecord",
        "ArtifactAuthorityFinding",
        "ArtifactAuthorityRecord",
        "BibliographyEntry",
        "BibliographyReviewRecord",
        "BudgetLedgerItem",
        "CitationSupportRecord",
        "DashboardCard",
        "EvidenceItem",
        "ProfileSource",
        "ProfilePackReadinessFinding",
        "ProfilePackReadinessProfile",
        "ProfilePackReadinessDrilldownArtifact",
        "ProfilePackReadinessDrilldownItem",
        "ProfilePackInvestigationArtifact",
        "ProfilePackInvestigationItem",
        "ProfileSourceFixPlanAction",
        "ProfileSourceFixReviewFinding",
        "ProfileSourceFixReviewRecord",
        "ProfileSourceQueueItem",
        "ProfileLifecycleLedgerEntry",
        "ProfileLifecycleLedgerFinding",
        "ProjectDeadline",
        "ProjectObjective",
        "ReferenceCorpusItem",
        "ReferenceCorpusRejection",
        "ResearchClaim",
        "ResearchInsight",
        "TracePassportEntry",
        "WorkspaceDiscoveryItem",
        "WeeklyReviewItem",
        "WorkflowStep",
        "WorkspaceSetupProposal",
    }:
        if isinstance(document, list):
            return [(f"$[{index}]", item) for index, item in enumerate(document)]
        if title == "WorkspaceSetupProposal" and isinstance(document, dict) and isinstance(document.get("proposals"), list):
            return [(f"$.proposals[{index}]", item) for index, item in enumerate(document["proposals"])]
        if title == "ArtifactAuthorityRecord" and isinstance(document, dict) and isinstance(document.get("records"), list):
            return [(f"$.records[{index}]", item) for index, item in enumerate(document["records"])]
        if title == "ArtifactAuthorityFinding" and isinstance(document, dict) and isinstance(document.get("findings"), list):
            return [(f"$.findings[{index}]", item) for index, item in enumerate(document["findings"])]
        if title == "ProjectObjective" and isinstance(document, dict) and isinstance(document.get("objectives"), list):
            return [(f"$.objectives[{index}]", item) for index, item in enumerate(document["objectives"])]
        if title == "ProjectDeadline" and isinstance(document, dict) and isinstance(document.get("deadlines"), list):
            return [(f"$.deadlines[{index}]", item) for index, item in enumerate(document["deadlines"])]
        if title == "ProfileLifecycleLedgerEntry" and isinstance(document, dict) and isinstance(document.get("entries"), list):
            return [(f"$.entries[{index}]", item) for index, item in enumerate(document["entries"])]
        if title == "ProfileLifecycleLedgerFinding" and isinstance(document, dict) and isinstance(document.get("findings"), list):
            return [(f"$.findings[{index}]", item) for index, item in enumerate(document["findings"])]
        if title == "ProfileSourceQueueItem" and isinstance(document, dict) and isinstance(document.get("items"), list):
            return [(f"$.items[{index}]", item) for index, item in enumerate(document["items"])]
        if title == "ProfileSourceFixReviewRecord" and isinstance(document, dict) and isinstance(document.get("records"), list):
            return [(f"$.records[{index}]", item) for index, item in enumerate(document["records"])]
        if title == "ProfileSourceFixReviewFinding" and isinstance(document, dict) and isinstance(document.get("findings"), list):
            return [(f"$.findings[{index}]", item) for index, item in enumerate(document["findings"])]
        if title == "ProfilePackReadinessProfile" and isinstance(document, dict) and isinstance(document.get("profiles"), list):
            return [(f"$.profiles[{index}]", item) for index, item in enumerate(document["profiles"])]
        if title == "ProfilePackReadinessFinding" and isinstance(document, dict) and isinstance(document.get("findings"), list):
            return [(f"$.findings[{index}]", item) for index, item in enumerate(document["findings"])]
        if title == "ProfilePackReadinessDrilldownArtifact" and isinstance(document, dict) and isinstance(document.get("artifacts"), list):
            return [(f"$.artifacts[{index}]", item) for index, item in enumerate(document["artifacts"])]
        if title == "ProfilePackReadinessDrilldownItem" and isinstance(document, dict) and isinstance(document.get("items"), list):
            return [(f"$.items[{index}]", item) for index, item in enumerate(document["items"])]
        if title == "ProfilePackInvestigationArtifact" and isinstance(document, dict) and isinstance(document.get("artifacts"), list):
            return [(f"$.artifacts[{index}]", item) for index, item in enumerate(document["artifacts"])]
        if title == "ProfilePackInvestigationItem" and isinstance(document, dict) and isinstance(document.get("items"), list):
            return [(f"$.items[{index}]", item) for index, item in enumerate(document["items"])]
        if isinstance(document, dict) and isinstance(document.get("items"), list):
            return [(f"$.items[{index}]", item) for index, item in enumerate(document["items"])]
        if title == "DashboardCard" and isinstance(document, dict) and isinstance(document.get("cards"), list):
            return [(f"$.cards[{index}]", item) for index, item in enumerate(document["cards"])]
    return [("$", document)]


def _format_error(error, path_prefix: str = "$") -> dict[str, str]:
    suffix = ".".join(str(part) for part in error.path)
    path = path_prefix if not suffix else f"{path_prefix}.{suffix}"
    schema_path = ".".join(str(part) for part in error.schema_path) or "$"
    return {
        "path": path,
        "schema_path": schema_path,
        "message": error.message,
    }
