from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .artifact_authority import generate_artifact_authority
from .models import (
    ReviewPackArtifact,
    ReviewPackVerificationItem,
    WorkspaceReviewPackResult,
    WorkspaceReviewPackVerificationResult,
)
from .approval_coverage import generate_workspace_approval_coverage
from .bibliography_integrity import generate_workspace_bibliography_integrity
from .budget_ledger import generate_workspace_budget_ledger
from .citation_support import generate_workspace_citation_support_integrity
from .profile_promotion import summarize_profile_promotions
from .profile_promotion_apply import generate_profile_promotion_apply_plan, load_profile_promotion_apply_result
from .profile_promotion_revoke import load_profile_promotion_revoke_plan
from .profile_review import generate_profile_review
from .profile_sources import generate_profile_integrity
from .project_goals import generate_goals_review
from .reference_corpus import build_reference_corpus
from .research_claims import generate_research_claim_matrix
from .report_integrity import generate_workspace_report_integrity
from .source_verification import verify_evidence_sources
from .trace_passport import generate_trace_passport
from .workspace import run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan
from .workspace_discovery import discover_workspace
from .workspace_summary import generate_workspace_summary
from .workspace_trace import generate_workspace_trace
from .weekly_review import generate_weekly_review, generate_workspace_dashboard


def generate_workspace_review_pack(
    root: str | Path,
    reports_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
    max_actions: int = 5,
) -> WorkspaceReviewPackResult:
    """Generate a bundled local review pack for discovery, authority, goals, weekly/dashboard, readiness, traceability, checkpoint, budget, profile, source, approval, report, bibliography, reference corpus, citation-support, and research-claim checks."""

    workspace = Path(root)
    reports = Path(reports_dir) if reports_dir is not None else workspace / "reports"
    state = Path(state_dir) if state_dir is not None else workspace / "state"
    reports.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)

    readiness_md = reports / "readiness.md"
    readiness_json = state / "readiness.json"
    discovery_md = reports / "workspace-discovery.md"
    discovery_json = state / "workspace-discovery.json"
    actions_md = reports / "next-actions.md"
    actions_json = state / "next-actions.json"
    summary_md = reports / "workspace-summary.md"
    summary_json = state / "workspace-summary.json"
    source_md = reports / "source-verification.md"
    source_json = state / "source-verification.json"
    authority_md = reports / "artifact-authority.md"
    authority_json = state / "artifact-authority.json"
    goals_md = reports / "goals-review.md"
    goals_json = state / "goals-review.json"
    weekly_date = date.today().isoformat()
    weekly_md = reports / f"weekly-review-{weekly_date}.md"
    weekly_json = state / f"weekly-review-{weekly_date}.json"
    dashboard_md = reports / "workspace-dashboard.md"
    dashboard_json = state / "workspace-dashboard.json"
    approval_md = reports / "approval-coverage.md"
    approval_json = state / "approval-coverage.json"
    report_integrity_md = reports / "report-integrity.md"
    report_integrity_json = state / "report-integrity.json"
    budget_ledger_md = reports / "budget-ledger.md"
    budget_ledger_json = state / "budget-ledger-integrity.json"
    bibliography_integrity_md = reports / "bibliography-integrity.md"
    bibliography_integrity_json = state / "bibliography-integrity.json"
    reference_corpus_md = reports / "reference-corpus-summary.md"
    reference_corpus_json = state / "literature-corpus.json"
    reference_rejections_json = state / "reference-rejection-log.json"
    citation_support_md = reports / "citation-support.md"
    citation_support_json = state / "citation-support.json"
    research_claim_md = reports / "research-claim-matrix.md"
    research_claim_json = state / "research-claim-matrix.json"
    profile_integrity_md = reports / "profile-integrity.md"
    profile_integrity_json = state / "profile-integrity.json"
    profile_review_md = reports / "profile-review.md"
    profile_review_json = state / "profile-review.json"
    profile_promotion_md = reports / "profile-promotion-summary.md"
    profile_promotion_json = state / "profile-promotion-summary.json"
    profile_apply_md = reports / "profile-promotion-apply-plan.md"
    profile_apply_json = state / "profile-promotion-apply-plan.json"
    profile_apply_result_md = reports / "profile-promotion-apply-result.md"
    profile_apply_result_json = state / "profile-promotion-apply-result.json"
    profile_revoke_md = reports / "profile-promotion-revoke-plan.md"
    profile_revoke_json = state / "profile-promotion-revoke-plan.json"
    workspace_trace_md = reports / "workspace-trace.md"
    workspace_trace_json = state / "workspace-trace.json"
    trace_passport_md = reports / "trace-passport.md"
    trace_passport_json = state / "trace-passport.json"
    index_md = reports / "workspace-review-pack.md"
    index_json = state / "workspace-review-pack.json"

    discovery = discover_workspace(workspace, output_path=discovery_md, json_path=discovery_json)
    doctor = run_workspace_doctor(workspace)
    source_verification = verify_evidence_sources(state / "evidence-index.json", root=workspace, output_path=source_md, json_path=source_json)
    artifact_authority = generate_artifact_authority(workspace, output_path=authority_md, json_path=authority_json)
    goals_review = generate_goals_review(workspace, output_path=goals_md, json_path=goals_json)
    approval_coverage = generate_workspace_approval_coverage(workspace, output_path=approval_md, json_path=approval_json)
    report_integrity = generate_workspace_report_integrity(workspace, output_path=report_integrity_md, json_path=report_integrity_json)
    budget_ledger = generate_workspace_budget_ledger(workspace, output_path=budget_ledger_md, json_path=budget_ledger_json)
    bibliography_integrity = generate_workspace_bibliography_integrity(workspace, output_path=bibliography_integrity_md, json_path=bibliography_integrity_json)
    reference_corpus = build_reference_corpus(workspace, output_path=reference_corpus_md, json_path=reference_corpus_json, rejection_json_path=reference_rejections_json)
    citation_support = generate_workspace_citation_support_integrity(workspace, output_path=citation_support_md, json_path=citation_support_json)
    research_claim_matrix = generate_research_claim_matrix(workspace, output_path=research_claim_md, json_path=research_claim_json)
    profile_integrity = generate_profile_integrity(workspace, output_path=profile_integrity_md, json_path=profile_integrity_json)
    profile_review = generate_profile_review(workspace, output_path=profile_review_md, json_path=profile_review_json)
    profile_promotion = summarize_profile_promotions(workspace, output_path=profile_promotion_md, json_path=profile_promotion_json)
    profile_apply = generate_profile_promotion_apply_plan(workspace, output_path=profile_apply_md, json_path=profile_apply_json)
    profile_apply_result = _load_profile_apply_result(profile_apply_result_json)
    profile_revoke_plan = _load_profile_revoke_plan(profile_revoke_json)
    weekly_review = generate_weekly_review(
        workspace,
        review_date=weekly_date,
        output_path=weekly_md,
        json_path=weekly_json,
        max_actions=max_actions,
        doctor_result=doctor,
    )
    dashboard = generate_workspace_dashboard(
        workspace,
        output_path=dashboard_md,
        json_path=dashboard_json,
        doctor_result=doctor,
    )
    workspace_trace = generate_workspace_trace(workspace, output_path=workspace_trace_md, json_path=workspace_trace_json)
    trace_passport = generate_trace_passport(workspace, output_path=trace_passport_md, json_path=trace_passport_json)
    doctor = run_workspace_doctor(workspace, readiness_md, readiness_json)
    actions = generate_workspace_action_plan(workspace, doctor_result=doctor, output_path=actions_md, json_path=actions_json)
    summary = generate_workspace_summary(
        workspace,
        output_path=summary_md,
        json_path=summary_json,
        max_actions=max_actions,
        doctor_result=doctor,
        action_plan=actions,
    )
    generated_paths = [
        str(readiness_md),
        str(readiness_json),
        str(discovery_md),
        str(discovery_json),
        str(actions_md),
        str(actions_json),
        str(summary_md),
        str(summary_json),
        str(source_md),
        str(source_json),
        str(authority_md),
        str(authority_json),
        str(goals_md),
        str(goals_json),
        str(weekly_md),
        str(weekly_json),
        str(dashboard_md),
        str(dashboard_json),
        str(approval_md),
        str(approval_json),
        str(report_integrity_md),
        str(report_integrity_json),
        str(budget_ledger_md),
        str(budget_ledger_json),
        str(bibliography_integrity_md),
        str(bibliography_integrity_json),
        str(reference_corpus_md),
        str(reference_corpus_json),
        str(reference_rejections_json),
        str(citation_support_md),
        str(citation_support_json),
        str(research_claim_md),
        str(research_claim_json),
        str(profile_integrity_md),
        str(profile_integrity_json),
        str(profile_review_md),
        str(profile_review_json),
        str(profile_promotion_md),
        str(profile_promotion_json),
        str(profile_apply_md),
        str(profile_apply_json),
        str(workspace_trace_md),
        str(workspace_trace_json),
        str(trace_passport_md),
        str(trace_passport_json),
        str(index_md),
        str(index_json),
    ]
    result = WorkspaceReviewPackResult(
        root=str(workspace),
        status=doctor.status,
        evidence_count=summary.evidence_count,
        approval_count=summary.approval_count,
        finding_count=doctor.finding_count,
        action_count=actions.action_count,
        source_verification_valid=source_verification.valid,
        source_missing_count=source_verification.missing_count,
        source_mismatch_count=source_verification.mismatch_count,
        artifact_authority_status=artifact_authority.status,
        artifact_authority_count=artifact_authority.artifact_count,
        artifact_authority_finding_count=artifact_authority.finding_count,
        artifact_authority_high_count=artifact_authority.high_count,
        goals_review_status=goals_review.status,
        objective_count=goals_review.objective_count,
        deadline_count=goals_review.deadline_count,
        goals_review_finding_count=goals_review.finding_count,
        goals_review_high_count=goals_review.high_count,
        goals_due_soon_count=goals_review.due_soon_count,
        goals_overdue_count=goals_review.overdue_count,
        goals_at_risk_deadline_count=goals_review.at_risk_deadline_count,
        weekly_review_status=weekly_review.status,
        weekly_review_item_count=weekly_review.item_count,
        weekly_review_high_count=sum(1 for item in weekly_review.items if item.severity == "high"),
        dashboard_status=dashboard.status,
        dashboard_card_count=dashboard.card_count,
        approval_coverage_status=approval_coverage.status,
        approval_missing_count=approval_coverage.missing_count,
        approval_not_approved_count=approval_coverage.not_approved_count,
        approval_hash_mismatch_count=approval_coverage.hash_mismatch_count,
        approval_hash_unverified_count=approval_coverage.hash_unverified_count,
        report_integrity_status=report_integrity.status,
        report_integrity_finding_count=report_integrity.finding_count,
        report_integrity_high_count=report_integrity.high_count,
        discovery_status=discovery.status,
        discovery_scanned_count=discovery.scanned_count,
        discovery_missing_standard_dir_count=len(discovery.missing_standard_dirs),
        discovery_loose_candidate_count=discovery.loose_candidate_count,
        discovery_setup_proposal_count=len(discovery.proposals),
        budget_ledger_status=budget_ledger.status,
        budget_ledger_count=budget_ledger.ledger_count,
        budget_ledger_finding_count=budget_ledger.finding_count,
        budget_ledger_high_count=budget_ledger.high_count,
        bibliography_integrity_status=bibliography_integrity.status,
        bibliography_entry_count=bibliography_integrity.entry_count,
        bibliography_review_count=bibliography_integrity.review_count,
        bibliography_citation_count=bibliography_integrity.citation_count,
        bibliography_integrity_finding_count=bibliography_integrity.finding_count,
        bibliography_integrity_high_count=bibliography_integrity.high_count,
        reference_corpus_status=reference_corpus.status,
        reference_corpus_count=reference_corpus.item_count,
        reference_rejection_count=reference_corpus.rejection_count,
        reference_corpus_high_count=reference_corpus.high_count,
        citation_support_status=citation_support.status,
        citation_support_count=citation_support.support_count,
        citation_support_citation_count=citation_support.citation_count,
        citation_support_finding_count=citation_support.finding_count,
        citation_support_high_count=citation_support.high_count,
        research_claim_matrix_status=research_claim_matrix.status,
        research_claim_count=research_claim_matrix.claim_count,
        research_claim_matrix_finding_count=research_claim_matrix.finding_count,
        research_claim_matrix_high_count=research_claim_matrix.high_count,
        profile_integrity_status=profile_integrity.status,
        profile_source_count=profile_integrity.source_count,
        profile_verified_source_count=profile_integrity.verified_source_count,
        profile_integrity_finding_count=profile_integrity.finding_count,
        profile_integrity_high_count=profile_integrity.high_count,
        profile_review_status=profile_review.status,
        profile_review_can_promote=profile_review.can_promote,
        profile_review_failed_count=profile_review.failed_count,
        profile_promotion_status=profile_promotion.status,
        profile_promotion_record_count=profile_promotion.record_count,
        latest_profile_promotion_decision=profile_promotion.latest_decision,
        profile_promotion_apply_status=profile_apply.status,
        profile_promotion_apply_can_apply=profile_apply.can_apply,
        profile_promotion_apply_change_count=profile_apply.change_count,
        profile_promotion_apply_result_status=profile_apply_result.status if profile_apply_result else None,
        profile_promotion_applied=profile_apply_result.applied if profile_apply_result else False,
        profile_promotion_apply_backup_path=profile_apply_result.backup_path if profile_apply_result else None,
        profile_promotion_revoke_status=profile_revoke_plan.status if profile_revoke_plan else None,
        profile_promotion_revoke_can_revoke=profile_revoke_plan.can_revoke if profile_revoke_plan else False,
        profile_promotion_revoke_change_count=profile_revoke_plan.change_count if profile_revoke_plan else 0,
        workspace_trace_status=workspace_trace.status,
        workspace_trace_node_count=workspace_trace.node_count,
        workspace_trace_edge_count=workspace_trace.edge_count,
        workspace_trace_finding_count=workspace_trace.finding_count,
        workspace_trace_high_count=workspace_trace.high_count,
        trace_passport_status=trace_passport.status,
        checkpoint_count=trace_passport.checkpoint_count,
        latest_checkpoint_id=trace_passport.latest_checkpoint_id,
        trace_passport_finding_count=trace_passport.finding_count,
        trace_passport_high_count=trace_passport.high_count,
        generated_paths=generated_paths,
        index_path=str(index_md),
        json_path=str(index_json),
    )
    if profile_apply_result_md.exists():
        generated_paths.append(str(profile_apply_result_md))
    if profile_apply_result_json.exists():
        generated_paths.append(str(profile_apply_result_json))
    if profile_revoke_md.exists():
        generated_paths.append(str(profile_revoke_md))
    if profile_revoke_json.exists():
        generated_paths.append(str(profile_revoke_json))
    result = result.model_copy(
        update={
            "generated_paths": generated_paths,
            "artifacts": _artifact_manifest(generated_paths, exclude={str(index_md), str(index_json)}),
        }
    )
    index_md.write_text(render_workspace_review_pack_markdown(result), encoding="utf-8")
    index_json.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def verify_workspace_review_pack(manifest_json: str | Path) -> WorkspaceReviewPackVerificationResult:
    """Verify review-pack generated artifacts against the saved manifest hashes."""

    manifest_path = Path(manifest_json)
    warnings: list[str] = []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        pack = WorkspaceReviewPackResult.model_validate(payload)
    except Exception as exc:
        return WorkspaceReviewPackVerificationResult(
            manifest_path=str(manifest_path),
            valid=False,
            warnings=[f"manifest_unreadable:{exc}"],
        )

    if not pack.artifacts:
        warnings.append("manifest_has_no_artifact_hashes")
    items = [_verify_artifact(artifact) for artifact in pack.artifacts]
    ok_count = sum(1 for item in items if item.status == "ok")
    missing_count = sum(1 for item in items if item.status == "missing")
    mismatch_count = sum(1 for item in items if item.status == "mismatch")
    unchecked_count = len(pack.generated_paths) - len(pack.artifacts)
    if str(manifest_path) in pack.generated_paths:
        unchecked_count = max(unchecked_count, 1)
        warnings.append("manifest_file_hash_not_self_checked")
    if unchecked_count:
        warnings.append("some_generated_paths_are_not_hash_checked")
    return WorkspaceReviewPackVerificationResult(
        manifest_path=str(manifest_path),
        valid=bool(items) and missing_count == 0 and mismatch_count == 0,
        checked_count=len(items),
        ok_count=ok_count,
        missing_count=missing_count,
        mismatch_count=mismatch_count,
        unchecked_count=unchecked_count,
        items=items,
        warnings=warnings,
    )


def render_workspace_review_pack_markdown(result: WorkspaceReviewPackResult) -> str:
    lines = [
        "# K-ResDev Workspace Review Pack",
        "",
        "> Review pack projection only. It bundles local discovery, authority, goals, weekly-review, dashboard, readiness, next-action, summary, source-verification, budget-ledger, approval-coverage, report-integrity, bibliography-integrity, reference-corpus, citation-support, research-claim-matrix, trace-passport, profile-integrity, and trace artifacts; it does not certify official agency compliance.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Evidence count | {result.evidence_count} |",
        f"| Approval count | {result.approval_count} |",
        f"| Finding count | {result.finding_count} |",
        f"| Action count | {result.action_count} |",
        f"| Source verification valid | {result.source_verification_valid} |",
        f"| Source missing count | {result.source_missing_count} |",
        f"| Source mismatch count | {result.source_mismatch_count} |",
        f"| Artifact authority status | {_escape(result.artifact_authority_status or '-')} |",
        f"| Artifact authority count | {result.artifact_authority_count} |",
        f"| Artifact authority finding count | {result.artifact_authority_finding_count} |",
        f"| Artifact authority high count | {result.artifact_authority_high_count} |",
        f"| Goals review status | {_escape(result.goals_review_status or '-')} |",
        f"| Objective count | {result.objective_count} |",
        f"| Deadline count | {result.deadline_count} |",
        f"| Goals review finding count | {result.goals_review_finding_count} |",
        f"| Goals review high count | {result.goals_review_high_count} |",
        f"| Due soon deadlines | {result.goals_due_soon_count} |",
        f"| Overdue deadlines | {result.goals_overdue_count} |",
        f"| At-risk deadlines | {result.goals_at_risk_deadline_count} |",
        f"| Weekly review status | {_escape(result.weekly_review_status or '-')} |",
        f"| Weekly review item count | {result.weekly_review_item_count} |",
        f"| Weekly review high count | {result.weekly_review_high_count} |",
        f"| Workspace dashboard status | {_escape(result.dashboard_status or '-')} |",
        f"| Workspace dashboard card count | {result.dashboard_card_count} |",
        f"| Approval coverage status | {_escape(result.approval_coverage_status or '-')} |",
        f"| Approval missing count | {result.approval_missing_count} |",
        f"| Approval not approved count | {result.approval_not_approved_count} |",
        f"| Approval hash mismatch count | {result.approval_hash_mismatch_count} |",
        f"| Approval hash unverified count | {result.approval_hash_unverified_count} |",
        f"| Report integrity status | {_escape(result.report_integrity_status or '-')} |",
        f"| Report integrity finding count | {result.report_integrity_finding_count} |",
        f"| Report integrity high count | {result.report_integrity_high_count} |",
        f"| Workspace discovery status | {_escape(result.discovery_status or '-')} |",
        f"| Discovery scanned paths | {result.discovery_scanned_count} |",
        f"| Discovery missing standard dirs | {result.discovery_missing_standard_dir_count} |",
        f"| Discovery loose candidates | {result.discovery_loose_candidate_count} |",
        f"| Discovery setup proposals | {result.discovery_setup_proposal_count} |",
        f"| Budget ledger status | {_escape(result.budget_ledger_status or '-')} |",
        f"| Budget ledger count | {result.budget_ledger_count} |",
        f"| Budget ledger finding count | {result.budget_ledger_finding_count} |",
        f"| Budget ledger high count | {result.budget_ledger_high_count} |",
        f"| Bibliography integrity status | {_escape(result.bibliography_integrity_status or '-')} |",
        f"| Bibliography entry count | {result.bibliography_entry_count} |",
        f"| Bibliography review count | {result.bibliography_review_count} |",
        f"| Bibliography citation count | {result.bibliography_citation_count} |",
        f"| Bibliography integrity finding count | {result.bibliography_integrity_finding_count} |",
        f"| Bibliography integrity high count | {result.bibliography_integrity_high_count} |",
        f"| Reference corpus status | {_escape(result.reference_corpus_status or '-')} |",
        f"| Reference corpus count | {result.reference_corpus_count} |",
        f"| Reference rejection count | {result.reference_rejection_count} |",
        f"| Reference corpus high count | {result.reference_corpus_high_count} |",
        f"| Citation support status | {_escape(result.citation_support_status or '-')} |",
        f"| Citation support records | {result.citation_support_count} |",
        f"| Citation support citation count | {result.citation_support_citation_count} |",
        f"| Citation support finding count | {result.citation_support_finding_count} |",
        f"| Citation support high count | {result.citation_support_high_count} |",
        f"| Research claim matrix status | {_escape(result.research_claim_matrix_status or '-')} |",
        f"| Research claim count | {result.research_claim_count} |",
        f"| Research claim matrix finding count | {result.research_claim_matrix_finding_count} |",
        f"| Research claim matrix high count | {result.research_claim_matrix_high_count} |",
        f"| Profile integrity status | {_escape(result.profile_integrity_status or '-')} |",
        f"| Profile source count | {result.profile_source_count} |",
        f"| Profile verified source count | {result.profile_verified_source_count} |",
        f"| Profile integrity finding count | {result.profile_integrity_finding_count} |",
        f"| Profile integrity high count | {result.profile_integrity_high_count} |",
        f"| Profile review status | {_escape(result.profile_review_status or '-')} |",
        f"| Profile review can promote | {result.profile_review_can_promote} |",
        f"| Profile review failed count | {result.profile_review_failed_count} |",
        f"| Profile promotion status | {_escape(result.profile_promotion_status or '-')} |",
        f"| Profile promotion record count | {result.profile_promotion_record_count} |",
        f"| Latest profile promotion decision | {_escape(result.latest_profile_promotion_decision or '-')} |",
        f"| Profile promotion apply-plan status | {_escape(result.profile_promotion_apply_status or '-')} |",
        f"| Profile promotion apply-plan can apply | {result.profile_promotion_apply_can_apply} |",
        f"| Profile promotion apply-plan change count | {result.profile_promotion_apply_change_count} |",
        f"| Profile promotion apply-result status | {_escape(result.profile_promotion_apply_result_status or '-')} |",
        f"| Profile promotion applied | {result.profile_promotion_applied} |",
        f"| Profile promotion apply backup | {_escape(result.profile_promotion_apply_backup_path or '-')} |",
        f"| Profile promotion revoke-plan status | {_escape(result.profile_promotion_revoke_status or '-')} |",
        f"| Profile promotion revoke-plan can revoke | {result.profile_promotion_revoke_can_revoke} |",
        f"| Profile promotion revoke-plan change count | {result.profile_promotion_revoke_change_count} |",
        f"| Workspace trace status | {_escape(result.workspace_trace_status or '-')} |",
        f"| Workspace trace nodes | {result.workspace_trace_node_count} |",
        f"| Workspace trace edges | {result.workspace_trace_edge_count} |",
        f"| Workspace trace finding count | {result.workspace_trace_finding_count} |",
        f"| Workspace trace high count | {result.workspace_trace_high_count} |",
        f"| Trace passport status | {_escape(result.trace_passport_status or '-')} |",
        f"| Checkpoint count | {result.checkpoint_count} |",
        f"| Latest checkpoint | {_escape(result.latest_checkpoint_id or '-')} |",
        f"| Trace passport finding count | {result.trace_passport_finding_count} |",
        f"| Trace passport high count | {result.trace_passport_high_count} |",
        "",
        "## Generated Artifacts",
        "",
        "| Artifact | Path |",
        "|---|---|",
    ]
    for path in result.generated_paths:
        lines.append(f"| {_artifact_label(path)} | `{_escape(path)}` |")
    lines.append("")
    lines.extend(
        [
            "## Manifest",
            "",
            f"- Hashed artifacts: {len(result.artifacts)}",
            f"- Manifest JSON: `{_escape(result.json_path)}`",
            "- The manifest JSON is not self-hashed; use `verify-review-pack` to check the other generated artifacts.",
            "",
            "## Use",
            "",
            "- Start with `workspace-discovery.md` when the folder is new, messy, or has not been initialized.",
            "- Start with `readiness.md` for blockers and warnings.",
            "- Use `next-actions.md` as a reviewable command plan.",
            "- Use `workspace-summary.md` as a one-page handoff/status snapshot.",
            "- Use `source-verification.md` to check local source presence and hash drift.",
            "- Use `artifact-authority.md` to check whether artifacts are raw sources, extracted candidates, accepted evidence, drafts, reviewed projections, or approved projections.",
            "- Use `goals-review.md` to check local objectives, deadlines, evidence links, report drafts, and approval readiness.",
            "- Use the dated `weekly-review-YYYY-MM-DD.md` artifact for a compact weekly operating slice.",
            "- Use `workspace-dashboard.md` for a compact dashboard across evidence, approvals, goals, budget, research, and trace state.",
            "- Use `approval-coverage.md` to check report artifacts against supplied human decisions.",
            "- Use `report-integrity.md` to check draft report claims against indexed evidence.",
            "- Use `budget-ledger.md` to check budget ledger proof, approval, duplicate, and evidence-link gaps.",
            "- Use `bibliography-integrity.md` to check local citation keys and bibliography source hashes.",
            "- Use `reference-corpus-summary.md` to review local PDFs, Zotero JSON exports, and Markdown note metadata before bibliography promotion.",
            "- Use `citation-support.md` to check cited papers against supplied paper-claim support records.",
            "- Use `research-claim-matrix.md` to check supplied research claims against evidence, bibliography, and citation-support records.",
            "- Use `profile-integrity.md` to check project/agency profile source records and drift.",
            "- Use `profile-review.md` before promoting any source-backed profile to verified.",
            "- Use `profile-promotion-summary.md` to inspect supplied human profile-promotion decisions.",
            "- Use `profile-promotion-apply-plan.md` to review proposed profile field changes before any profile status is changed.",
            "- Use `profile-promotion-apply-result.md` to inspect guarded profile status mutations and backup paths.",
            "- Use `profile-promotion-revoke-plan.md` to review whether an applied profile promotion can be rolled back cleanly.",
            "- Use `workspace-trace.md` to inspect cross-artifact traceability and impact findings.",
            "- Use `trace-passport.md` to inspect checkpoint freshness before resuming long-running work.",
            "- Run `verify-review-pack state/workspace-review-pack.json` before relying on a saved pack.",
            "- Keep official reports and scientific claims human-approved.",
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_label(path: str) -> str:
    name = Path(path).name
    if name.startswith("weekly-review-") and name.endswith(".md"):
        return "Weekly review"
    if name.startswith("weekly-review-") and name.endswith(".json"):
        return "Weekly review JSON"
    labels = {
        "readiness.md": "Readiness report",
        "readiness.json": "Readiness JSON",
        "workspace-discovery.md": "Workspace discovery",
        "workspace-discovery.json": "Workspace discovery JSON",
        "next-actions.md": "Next actions",
        "next-actions.json": "Next actions JSON",
        "workspace-summary.md": "Workspace summary",
        "workspace-summary.json": "Workspace summary JSON",
        "source-verification.md": "Evidence source verification",
        "source-verification.json": "Evidence source verification JSON",
        "artifact-authority.md": "Artifact authority",
        "artifact-authority.json": "Artifact authority JSON",
        "goals-review.md": "Goals review",
        "goals-review.json": "Goals review JSON",
        "workspace-dashboard.md": "Workspace dashboard",
        "workspace-dashboard.json": "Workspace dashboard JSON",
        "approval-coverage.md": "Approval coverage",
        "approval-coverage.json": "Approval coverage JSON",
        "report-integrity.md": "Report integrity",
        "report-integrity.json": "Report integrity JSON",
        "budget-ledger.md": "Budget ledger integrity",
        "budget-ledger-integrity.json": "Budget ledger integrity JSON",
        "bibliography-integrity.md": "Bibliography integrity",
        "bibliography-integrity.json": "Bibliography integrity JSON",
        "reference-corpus-summary.md": "Reference corpus summary",
        "literature-corpus.json": "Reference corpus JSON",
        "reference-rejection-log.json": "Reference rejection log JSON",
        "citation-support.md": "Citation support",
        "citation-support.json": "Citation support JSON",
        "research-claim-matrix.md": "Research claim matrix",
        "research-claim-matrix.json": "Research claim matrix JSON",
        "profile-integrity.md": "Profile integrity",
        "profile-integrity.json": "Profile integrity JSON",
        "profile-review.md": "Profile review",
        "profile-review.json": "Profile review JSON",
        "profile-promotion-summary.md": "Profile promotion summary",
        "profile-promotion-summary.json": "Profile promotion summary JSON",
        "profile-promotion-apply-plan.md": "Profile promotion apply plan",
        "profile-promotion-apply-plan.json": "Profile promotion apply plan JSON",
        "profile-promotion-apply-result.md": "Profile promotion apply result",
        "profile-promotion-apply-result.json": "Profile promotion apply result JSON",
        "profile-promotion-revoke-plan.md": "Profile promotion revocation plan",
        "profile-promotion-revoke-plan.json": "Profile promotion revocation plan JSON",
        "workspace-trace.md": "Workspace trace",
        "workspace-trace.json": "Workspace trace JSON",
        "trace-passport.md": "Trace passport",
        "trace-passport.json": "Trace passport JSON",
        "workspace-review-pack.md": "Review pack index",
        "workspace-review-pack.json": "Review pack JSON",
    }
    return labels.get(name, name)


def _artifact_manifest(paths: list[str], exclude: set[str]) -> list[ReviewPackArtifact]:
    artifacts: list[ReviewPackArtifact] = []
    for path in paths:
        if path in exclude:
            continue
        target = Path(path)
        if not target.exists():
            continue
        artifacts.append(
            ReviewPackArtifact(
                path=str(target),
                artifact_type=_artifact_label(str(target)),
                sha256=_sha256_file(target),
                byte_count=target.stat().st_size,
            )
        )
    return artifacts


def _verify_artifact(artifact: ReviewPackArtifact) -> ReviewPackVerificationItem:
    path = Path(artifact.path)
    if not path.exists():
        return ReviewPackVerificationItem(
            path=artifact.path,
            artifact_type=artifact.artifact_type,
            expected_sha256=artifact.sha256,
            status="missing",
        )
    actual = _sha256_file(path)
    status = "ok" if actual == artifact.sha256 else "mismatch"
    return ReviewPackVerificationItem(
        path=artifact.path,
        artifact_type=artifact.artifact_type,
        expected_sha256=artifact.sha256,
        actual_sha256=actual,
        byte_count=path.stat().st_size,
        status=status,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_profile_apply_result(path: Path):
    if not path.exists():
        return None
    try:
        return load_profile_promotion_apply_result(path)
    except Exception:
        return None


def _load_profile_revoke_plan(path: Path):
    if not path.exists():
        return None
    try:
        return load_profile_promotion_revoke_plan(path)
    except Exception:
        return None


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
