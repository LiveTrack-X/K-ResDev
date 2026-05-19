from __future__ import annotations

import json
import shutil
import zipfile
from datetime import date
from pathlib import Path

from .admin_operating import (
    generate_settlement_binder,
    review_admin_calendar,
    review_admin_change_ledger,
    review_admin_obligation_profile_pack,
    review_admin_obligations,
)
from .admin_profile_pack_reviews import summarize_admin_profile_pack_reviews
from .admin_profile_pack_gate import generate_admin_profile_pack_promotion_gate
from .admin_reviewed_seed_drift import generate_admin_reviewed_seed_drift_dashboard
from .artifact_authority import generate_artifact_authority
from .approval import load_approval_records
from .approval_coverage import generate_workspace_approval_coverage
from .bibliography_integrity import generate_workspace_bibliography_integrity
from .budget import budget_evidence_gaps
from .budget_ledger import generate_workspace_budget_ledger
from .citation_support import generate_workspace_citation_support_integrity
from .evidence_index import load_evidence_index
from .models import (
    ProjectGoalsFile,
    ProjectProfile,
    ProjectState,
    WorkspaceDoctorFinding,
    WorkspaceDoctorResult,
    WorkspaceInitResult,
)
from .profile_promotion import summarize_profile_promotions
from .profile_promotion_apply import generate_profile_promotion_apply_plan, load_profile_promotion_apply_result
from .profile_promotion_revoke import load_profile_promotion_revoke_plan, load_profile_promotion_revoke_result
from .profile_lifecycle import generate_profile_lifecycle_ledger
from .profile_pack_investigation import generate_profile_pack_investigation_bundle
from .profile_pack_investigation_package import generate_profile_pack_investigation_package, load_profile_pack_investigation_package
from .profile_pack_package_receipt import summarize_profile_pack_package_receipts
from .profile_pack_drilldown import generate_profile_pack_readiness_drilldown
from .profile_pack_readiness import generate_profile_pack_readiness
from .profile_registry import default_agency_templates_root, load_project_profile
from .profile_review import generate_profile_review
from .profile_source_fix_plan import generate_profile_source_fix_plan
from .profile_source_fix_review import summarize_profile_source_fix_reviews
from .profile_source_queue import generate_profile_source_queue
from .profile_sources import generate_profile_integrity, load_profile_sources
from .project_goals import generate_goals_review
from .reference_corpus import build_reference_corpus
from .research_claims import generate_research_claim_matrix
from .report_integrity import generate_workspace_report_integrity
from .schema_tools import validate_json_file
from .source_verification import verify_evidence_sources
from .trace_passport import generate_trace_passport
from .workspace_discovery import discover_workspace
from .workspace_trace import generate_workspace_trace

DRAFT_NOTICE = "Draft projection only"
STANDARD_DIRS = (
    "inbox",
    "state",
    "evidence",
    "references",
    "reports",
    "reports/analysis",
    "state/approvals",
    "state/admin-profile-pack-reviews",
    "state/bibliography-reviews",
    "state/citation-support",
    "state/checkpoints",
    "state/profile-backups",
    "state/profile-pack-package-receipts",
    "state/profile-promotions",
    "state/profile-source-fix-reviews",
)
OPERATIONAL_MARKDOWN_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "artifact-authority.md",
    "admin-calendar.md",
    "admin-change-ledger.md",
    "admin-obligations.md",
    "admin-profile-pack.md",
    "admin-profile-pack-gate.md",
    "admin-profile-pack-review-summary.md",
    "admin-reviewed-seed-drift.md",
    "bibliography-integrity.md",
    "budget-ledger.md",
    "budget-checklist.md",
    "checkpoint-resume-plan.md",
    "citation-support.md",
    "citation-support-summary.md",
    "evidence-bundle-index.md",
    "goals-review.md",
    "next-actions.md",
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
    "profile-pack-investigation-bundle.md",
    "profile-pack-investigation-package.md",
    "profile-pack-package-receipt-summary.md",
    "profile-pack-readiness-drilldown.md",
    "profile-pack-readiness.md",
    "profile-source-queue.md",
    "profile-source-summary.md",
    "readiness.md",
    "reference-corpus-summary.md",
    "research-claim-matrix.md",
    "research-claims.md",
    "report-integrity.md",
    "settlement-binder.md",
    "source-verification.md",
    "trace-passport.md",
    "workspace-discovery.md",
    "workspace-dashboard.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
    "workspace-trace.md",
}
OPERATIONAL_MARKDOWN_PREFIXES = ("weekly-review-", "workflow-")


def initialize_workspace(
    root: str | Path,
    project_id: str,
    title: str,
    profile_id: str = "national-rnd-basic",
) -> WorkspaceInitResult:
    """Create a K-ResDev workspace skeleton without overwriting existing files."""

    workspace = Path(root)
    created: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []

    for relative in STANDARD_DIRS:
        target = workspace / relative
        if target.exists():
            skipped.append(str(target))
        else:
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))

    project_state = ProjectState(
        project_id=project_id,
        title=title,
        period="needs_review",
        status="planning",
    )
    _write_if_missing(
        workspace / "state" / "project-state.json",
        project_state.model_dump_json(indent=2) + "\n",
        created,
        skipped,
    )

    profile = _profile_for_id(profile_id, warnings)
    _write_if_missing(
        workspace / "state" / "project-profile.json",
        profile.model_dump_json(indent=2) + "\n",
        created,
        skipped,
    )
    profile_sources_path = workspace / "state" / "profile-sources.json"
    if profile_sources_path.exists():
        skipped.append(str(profile_sources_path))
    else:
        profile_sources_text = _profile_sources_for_id(profile.profile_id, workspace, warnings, created, skipped)
        profile_sources_path.write_text(profile_sources_text, encoding="utf-8")
        created.append(str(profile_sources_path))
    _write_if_missing(
        workspace / "state" / "project-goals.json",
        ProjectGoalsFile(
            project_id=project_id,
            title=title,
            status="needs_review",
            notes="Local goals/deadlines operating file. Add reviewed objectives and deadlines before relying on goals-review.",
            warnings=["starter_needs_review"],
        ).model_dump_json(indent=2)
        + "\n",
        created,
        skipped,
    )

    _write_if_missing(
        workspace / "README.k-resdev.md",
        _starter_readme(project_id, title, profile.profile_id),
        created,
        skipped,
    )

    if profile.status == "needs_review":
        warnings.append("profile_needs_review")

    return WorkspaceInitResult(
        root=str(workspace),
        project_id=project_id,
        profile_id=profile.profile_id,
        created_paths=created,
        skipped_existing=skipped,
        warnings=_unique(warnings),
    )


def run_workspace_doctor(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceDoctorResult:
    """Inspect workspace readiness using local metadata only."""

    workspace = Path(root)
    findings: list[WorkspaceDoctorFinding] = []
    _check_workspace_discovery(workspace, findings)
    evidence_count = _check_evidence(workspace, findings)
    approval_count = _check_approvals(workspace, findings)
    _check_approval_coverage(workspace, findings)
    _check_budget_ledger(workspace, findings)
    _check_profile(workspace, findings)
    _check_profile_source_queue(workspace, findings)
    _check_profile_source_fix_plan(workspace, findings)
    _check_profile_source_fix_reviews(workspace, findings)
    _check_profile_integrity(workspace, findings)
    _check_profile_review(workspace, findings)
    _check_profile_promotion(workspace, findings)
    _check_profile_promotion_apply(workspace, findings)
    _check_profile_promotion_revoke(workspace, findings)
    _check_profile_promotion_revoke_result(workspace, findings)
    _check_profile_lifecycle(workspace, findings)
    _check_profile_pack_readiness(workspace, findings)
    _check_profile_pack_readiness_drilldown(workspace, findings)
    _check_profile_pack_investigation_bundle(workspace, findings)
    _check_profile_pack_investigation_package(workspace, findings)
    _check_profile_pack_package_receipts(workspace, findings)
    _check_admin_profile_pack_review(workspace, findings)
    _check_admin_profile_pack_reviews(workspace, findings)
    _check_admin_profile_pack_gate(workspace, findings)
    _check_admin_obligations(workspace, findings)
    _check_admin_reviewed_seed_drift(workspace, findings)
    _check_settlement_binder(workspace, findings)
    _check_admin_change_ledger(workspace, findings)
    _check_admin_calendar(workspace, findings)
    _check_reports(workspace, findings)
    _check_report_integrity(workspace, findings)
    _check_artifact_authority(workspace, findings)
    _check_goals_review(workspace, findings)
    _check_bibliography_integrity(workspace, findings)
    _check_reference_corpus(workspace, findings)
    _check_citation_support_integrity(workspace, findings)
    _check_research_claim_matrix(workspace, findings)
    _check_workspace_trace(workspace, findings)
    _check_trace_passport(workspace, findings)
    _check_weekly_dashboard(workspace, findings)
    _check_exports(workspace, findings)
    _check_analysis(workspace, findings)

    status = _status_from_findings(findings)
    result = WorkspaceDoctorResult(
        root=str(workspace),
        status=status,
        evidence_count=evidence_count,
        approval_count=approval_count,
        finding_count=len(findings),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
    )

    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_doctor_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_doctor_markdown(result: WorkspaceDoctorResult) -> str:
    lines = [
        "# K-ResDev Workspace Readiness",
        "",
        "> Readiness projection only. This does not certify official agency compliance.",
        "",
        f"- Root: `{result.root}`",
        f"- Status: `{result.status}`",
        f"- Evidence count: {result.evidence_count}",
        f"- Approval count: {result.approval_count}",
        f"- Finding count: {result.finding_count}",
        "",
        "| Severity | Code | Message | Path | Suggested Action |",
        "|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | ready | No readiness findings detected. | - | Continue evidence review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {message} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                message=_escape(finding.message),
                path=_escape(finding.path or "-"),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _check_evidence(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> int:
    index_path = workspace / "state" / "evidence-index.json"
    if not index_path.exists():
        findings.append(
            _finding(
                "missing_evidence_index",
                "high",
                "No evidence index found.",
                index_path,
                "Run intake or index evidence before reporting.",
            )
        )
        return 0

    try:
        validation = validate_json_file(index_path, "evidence")
        if not validation["valid"]:
            findings.append(
                _finding(
                    "invalid_evidence_index_schema",
                    "high",
                    f"Evidence index schema validation failed with {validation['error_count']} error(s).",
                    index_path,
                    "Run validate-json evidence and fix invalid metadata.",
                )
            )
        evidence = load_evidence_index(index_path)
    except Exception as exc:  # pragma: no cover - defensive path
        findings.append(_finding("unreadable_evidence_index", "high", str(exc), index_path, "Regenerate the evidence index."))
        return 0

    if not evidence:
        findings.append(_finding("empty_evidence_index", "high", "Evidence index contains no items.", index_path, "Add evidence via intake."))
    for item in evidence:
        if item.status == "needs_review":
            findings.append(
                _finding(
                    "evidence_needs_review",
                    "medium",
                    f"{item.evidence_id} is still needs_review.",
                    index_path,
                    "Review, accept, reject, or keep disclosed as draft.",
                )
            )
        if item.risk_flags:
            findings.append(
                _finding(
                    "evidence_risk_flags",
                    "medium",
                    f"{item.evidence_id} has risk flags: {', '.join(item.risk_flags)}.",
                    index_path,
                    "Resolve or disclose risk flags before official use.",
                )
            )
    for evidence_id, missing_fields in budget_evidence_gaps(evidence).items():
        findings.append(
            _finding(
                "budget_metadata_gap",
                "medium",
                f"{evidence_id} is missing budget fields: {', '.join(missing_fields)}.",
                index_path,
                "Complete generic budget metadata and verify official agency guidance.",
            )
        )
    _check_source_integrity(workspace, index_path, findings)
    return len(evidence)


def _check_workspace_discovery(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = discover_workspace(workspace)
    if result.status == "blocked":
        findings.append(
            _finding(
                "workspace_discovery_blocked",
                "high",
                "Workspace discovery could not inspect the selected root.",
                workspace,
                "Choose a directory root before running K-ResDev setup or intake.",
            )
        )
        return
    if result.status == "needs_setup":
        findings.append(
            _finding(
                "workspace_discovery_setup_needed",
                "high",
                f"{len(result.missing_standard_dirs)} standard folder(s) and {len(result.missing_starter_files)} starter file(s) are missing.",
                workspace,
                "Run discover-workspace, review the setup proposal, then run init-workspace if appropriate.",
            )
        )
    if result.loose_candidate_count:
        findings.append(
            _finding(
                "workspace_discovery_review_needed",
                "medium",
                f"{result.loose_candidate_count} loose source candidate(s) were found outside standard K-ResDev folders.",
                workspace,
                "Run discover-workspace and manually place raw source files before intake.",
            )
        )


def _check_source_integrity(workspace: Path, index_path: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = verify_evidence_sources(index_path, root=workspace)
    if result.warnings:
        findings.append(
            _finding(
                "source_verification_unreadable",
                "high",
                "Evidence source verification could not read the evidence index.",
                index_path,
                "Regenerate the evidence index before reporting.",
            )
        )
        return

    missing_hashed = [item for item in result.items if item.status == "missing" and item.expected_hashes]
    missing_unhashed = [item for item in result.items if item.status == "missing" and not item.expected_hashes]
    no_hash_existing = [item for item in result.items if item.status == "no_expected_hash"]

    if missing_hashed:
        findings.append(
            _finding(
                "source_file_missing",
                "high",
                f"{len(missing_hashed)} indexed hashed source file(s) are missing.",
                index_path,
                "Restore raw sources, rerun intake, or document source replacement before reporting.",
            )
        )
    if result.mismatch_count:
        findings.append(
            _finding(
                "source_hash_mismatch",
                "high",
                f"{result.mismatch_count} indexed source file(s) changed after evidence indexing.",
                index_path,
                "Restore the original raw file or rerun intake and review changed evidence.",
            )
        )
    if result.conflict_count:
        findings.append(
            _finding(
                "source_hash_conflict",
                "medium",
                f"{result.conflict_count} source file(s) have conflicting expected hashes across evidence items.",
                index_path,
                "Split or regenerate conflicting evidence records before relying on the index.",
            )
        )
    if no_hash_existing or missing_unhashed:
        unverified_count = len(no_hash_existing) + len(missing_unhashed)
        findings.append(
            _finding(
                "source_hash_unverified",
                "low",
                f"{unverified_count} source file(s) cannot be verified with a saved source hash.",
                index_path,
                "Prefer intake-generated evidence with source hashes for audit-sensitive use.",
            )
        )


def _check_approvals(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> int:
    approvals_dir = workspace / "state" / "approvals"
    if not approvals_dir.exists():
        findings.append(
            _finding(
                "approval_missing",
                "medium",
                "No approvals directory found.",
                approvals_dir,
                "Record supplied human review decisions before submission.",
            )
        )
        return 0
    try:
        approvals = load_approval_records(approvals_dir)
    except Exception as exc:
        findings.append(_finding("approval_unreadable", "medium", str(exc), approvals_dir, "Fix or remove invalid approval JSON."))
        return 0
    if not approvals:
        findings.append(
            _finding(
                "approval_missing",
                "medium",
                "No approval records found.",
                approvals_dir,
                "Record supplied human review decisions before submission.",
            )
        )
    return len(approvals)


def _check_approval_coverage(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_workspace_approval_coverage(workspace)
    if result.warnings and result.artifact_count:
        findings.append(
            _finding(
                "approval_coverage_unreadable",
                "medium",
                "Report approval coverage could not read approval records.",
                workspace / "state" / "approvals",
                "Fix approval records, then regenerate approval coverage.",
            )
        )
        return
    if result.missing_count:
        findings.append(
            _finding(
                "report_approval_missing",
                "medium",
                f"{result.missing_count} report artifact(s) have no supplied human approval record.",
                workspace / "reports",
                "Record supplied human decisions or keep artifacts clearly disclosed as draft.",
            )
        )
    if result.not_approved_count:
        findings.append(
            _finding(
                "report_approval_not_approved",
                "medium",
                f"{result.not_approved_count} report artifact(s) have latest decisions that are not approved.",
                workspace / "state" / "approvals",
                "Resolve requested changes before official use.",
            )
        )
    if result.hash_mismatch_count:
        findings.append(
            _finding(
                "approval_target_hash_mismatch",
                "high",
                f"{result.hash_mismatch_count} approved report artifact(s) changed after approval.",
                workspace / "reports",
                "Re-review changed artifacts and record a new supplied human approval decision.",
            )
        )
    if result.hash_unverified_count:
        findings.append(
            _finding(
                "approval_target_hash_unverified",
                "medium",
                f"{result.hash_unverified_count} approved report artifact(s) are not bound to a saved target hash.",
                workspace / "state" / "approvals",
                "Record approval decisions with target_path so the artifact hash is captured.",
            )
        )


def _check_budget_ledger(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_workspace_budget_ledger(workspace)
    path = workspace / "state" / "budget-ledger.json"
    if result.status == "not_configured":
        return
    if result.high_count:
        findings.append(
            _finding(
                "budget_ledger_high_findings",
                "high",
                f"{result.high_count} high-severity budget ledger finding(s) were detected.",
                path,
                "Run budget-ledger-integrity and resolve ledger/evidence mismatches before settlement or audit use.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "budget_ledger_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} budget ledger review finding(s) or warnings were detected.",
                path,
                "Review budget-ledger-integrity output before settlement or audit use.",
            )
        )


def _check_profile(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    profile_path = workspace / "state" / "project-profile.json"
    if not profile_path.exists():
        findings.append(_finding("profile_missing", "medium", "No project profile found.", profile_path, "Run init-workspace or add a profile."))
        return
    try:
        profile = load_project_profile(profile_path)
    except Exception as exc:
        findings.append(_finding("profile_unreadable", "medium", str(exc), profile_path, "Fix project profile JSON."))
        return
    if profile.status == "needs_review":
        findings.append(
            _finding(
                "profile_needs_review",
                "medium",
                f"Profile {profile.profile_id} is marked needs_review.",
                profile_path,
                "Verify agency/program templates before official use.",
            )
        )


def _check_profile_integrity(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_profile_integrity(workspace)
    path = workspace / "state" / "profile-sources.json"
    if result.high_count:
        findings.append(
            _finding(
                "profile_integrity_high_findings",
                "high",
                f"{result.high_count} high-severity profile source finding(s) were detected.",
                path,
                "Run profile-integrity and resolve profile source drift or invalid verified state.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "profile_integrity_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} profile source review finding(s) or warnings were detected.",
                path,
                "Review profile-integrity output before treating any agency/profile template as verified.",
            )
        )


def _check_profile_source_queue(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_profile_source_queue(workspace)
    if result.status == "not_configured":
        return
    path = workspace / "state" / "profile-source-queue.json"
    if result.high_count:
        findings.append(
            _finding(
                "profile_source_queue_high_findings",
                "high",
                f"{result.high_count} high-severity profile source queue item(s) were detected.",
                path,
                "Run profile-source-queue and resolve missing files, hash drift, or invalid verified source state before profile promotion.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "profile_source_queue_review_findings",
                "medium" if result.medium_count else "low",
                f"{result.medium_count + result.low_count} profile source queue item(s) or warnings were detected.",
                path,
                "Review profile-source-queue before adding or promoting agency profile packs.",
            )
        )


def _check_profile_source_fix_plan(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    queue_path = workspace / "state" / "profile-source-queue.json"
    plan_path = workspace / "state" / "profile-source-fix-plan.json"
    if not queue_path.exists():
        return
    result = generate_profile_source_fix_plan(workspace)
    if result.status == "ready":
        return
    if not plan_path.exists() and result.action_count:
        findings.append(
            _finding(
                "profile_source_fix_plan_missing",
                "medium",
                f"{result.action_count} profile source queue remediation action(s) are available but no fix-plan artifact exists.",
                plan_path,
                "Run profile-source-fix-plan to turn queue items into reviewable local commands and manual steps.",
            )
        )
    if plan_path.exists() and result.high_count:
        findings.append(
            _finding(
                "profile_source_fix_plan_high_actions",
                "high",
                f"{result.high_count} high-severity profile source fix action(s) require manual/source review.",
                plan_path,
                "Review profile-source-fix-plan before profile promotion or agency pack work.",
            )
        )
    if plan_path.exists() and (result.medium_count or result.low_count or result.warnings):
        findings.append(
            _finding(
                "profile_source_fix_plan_review_actions",
                "medium" if result.medium_count else "low",
                f"{result.medium_count + result.low_count} profile source fix action(s) or warnings remain.",
                plan_path,
                "Review suggested local commands and manual official-source checks before changing profile-source metadata.",
            )
        )


def _check_profile_source_fix_reviews(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    plan_path = workspace / "state" / "profile-source-fix-plan.json"
    summary_path = workspace / "state" / "profile-source-fix-summary.json"
    if not plan_path.exists():
        return
    result = summarize_profile_source_fix_reviews(workspace)
    if result.status == "ready":
        return
    if not summary_path.exists() and result.action_count:
        findings.append(
            _finding(
                "profile_source_fix_summary_missing",
                "medium",
                f"{result.action_count} profile source fix action(s) exist but no fix review summary artifact exists.",
                summary_path,
                "Run profile-source-fix-summary to compare supplied review records with the current fix plan.",
            )
        )
    if result.high_count:
        findings.append(
            _finding(
                "profile_source_fix_review_high_findings",
                "high",
                f"{result.high_count} high-severity profile source fix review finding(s) were detected.",
                summary_path,
                "Review stale hashes, missing action IDs, and high-severity unresolved fix actions.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "profile_source_fix_review_findings",
                "medium" if result.medium_count else "low",
                f"{result.medium_count + result.low_count} profile source fix review finding(s) or warnings remain.",
                summary_path,
                "Record supplied review decisions or keep unresolved source/profile items in needs_review.",
            )
        )


def _check_profile_review(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_profile_review(workspace)
    path = workspace / "state" / "profile-review.json"
    if result.status == "blocked":
        findings.append(
            _finding(
                "profile_review_blocked",
                "high",
                f"{result.failed_count} profile promotion review check(s) failed, including at least one high-severity check.",
                path,
                "Run profile-review and resolve high-severity profile promotion blockers.",
            )
        )
    elif not result.can_promote:
        findings.append(
            _finding(
                "profile_review_incomplete",
                "medium",
                f"{result.failed_count} profile promotion review check(s) still require human/source metadata.",
                path,
                "Run profile-review before marking any profile as verified.",
            )
        )


def _check_profile_promotion(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    review = generate_profile_review(workspace)
    summary = summarize_profile_promotions(workspace)
    profile_path = workspace / "state" / "project-profile.json"
    profile: ProjectProfile | None = None
    if profile_path.exists():
        try:
            profile = load_project_profile(profile_path)
        except Exception:
            profile = None
    path = workspace / "state" / "profile-promotions"
    if profile is not None and profile.status == "verified" and summary.status != "verified_recorded":
        findings.append(
            _finding(
                "profile_verified_without_promotion_record",
                "high",
                f"Profile {profile.profile_id} is marked verified but no current verified promotion record was found.",
                path,
                "Record a supplied human profile-promotion decision or set the profile back to needs_review.",
            )
        )
    if summary.status == "stale_review_hash":
        findings.append(
            _finding(
                "profile_promotion_review_hash_mismatch",
                "high",
                "The latest profile promotion record points to a stale profile-review hash.",
                path,
                "Re-run profile-review and record a fresh supplied human promotion decision.",
            )
        )
    if review.can_promote and summary.status != "verified_recorded":
        findings.append(
            _finding(
                "profile_promotion_record_missing",
                "medium",
                "Profile review is ready for human promotion but no verified promotion record exists.",
                path,
                "Run profile-promotion-record with the profile-review hash after supplied human verification.",
            )
        )


def _check_profile_promotion_apply(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    plan = generate_profile_promotion_apply_plan(workspace)
    path = workspace / "state" / "profile-promotion-apply-plan.json"
    if plan.status == "ready_to_apply" and not path.exists():
        findings.append(
            _finding(
                "profile_promotion_apply_plan_missing",
                "medium",
                "A current verified profile promotion record exists, but no non-destructive apply plan has been generated.",
                path,
                "Run profile-promotion-apply-plan before changing state/project-profile.json.",
            )
        )
    result_path = workspace / "state" / "profile-promotion-apply-result.json"
    profile_path = workspace / "state" / "project-profile.json"
    profile: ProjectProfile | None = None
    if profile_path.exists():
        try:
            profile = load_project_profile(profile_path)
        except Exception:
            profile = None
    if plan.status == "ready_to_apply" and path.exists() and not result_path.exists():
        findings.append(
            _finding(
                "profile_promotion_apply_pending",
                "medium",
                "A profile promotion apply plan is ready, but the guarded apply command has not been run.",
                result_path,
                "Run profile-promotion-apply with the apply-plan hash, or leave the profile in needs_review.",
            )
        )
    if plan.current_profile_status == "verified" and plan.promotion_id and not path.exists():
        findings.append(
            _finding(
                "profile_verified_without_apply_plan",
                "low",
                "The project profile is already verified, but no profile promotion apply-plan artifact was found.",
                path,
                "Generate profile-promotion-apply-plan to preserve the promotion decision trail.",
            )
        )
    if profile is not None and profile.status == "verified" and not result_path.exists():
        findings.append(
            _finding(
                "profile_verified_without_apply_result",
                "high",
                "The project profile is marked verified, but no guarded profile promotion apply result was found.",
                result_path,
                "Restore the profile to needs_review or record/apply the promotion through the guarded workflow.",
            )
        )
    if result_path.exists():
        try:
            result = load_profile_promotion_apply_result(result_path)
        except Exception as exc:
            findings.append(
                _finding(
                    "profile_promotion_apply_result_unreadable",
                    "medium",
                    f"Profile promotion apply result could not be read: {exc}",
                    result_path,
                    "Fix state/profile-promotion-apply-result.json before relying on profile status.",
                )
            )
            return
        backup = Path(result.backup_path) if result.backup_path else None
        if backup is not None and not backup.exists():
            findings.append(
                _finding(
                    "profile_promotion_apply_backup_missing",
                    "medium",
                    "Profile promotion apply result refers to a missing backup file.",
                    backup,
                    "Restore the backup artifact or review version control before relying on rollback instructions.",
                )
            )
        revoke_result_path = workspace / "state" / "profile-promotion-revoke-result.json"
        revoke_result = None
        if revoke_result_path.exists():
            try:
                revoke_result = load_profile_promotion_revoke_result(revoke_result_path)
            except Exception:
                revoke_result = None
        if (
            profile is not None
            and result.after_profile
            and profile.model_dump() != result.after_profile
            and not (revoke_result is not None and revoke_result.after_profile and profile.model_dump() == revoke_result.after_profile)
        ):
            findings.append(
                _finding(
                    "profile_promotion_apply_result_drift",
                    "high",
                    "Current project profile no longer matches the saved profile promotion apply result.",
                    profile_path,
                    "Regenerate profile promotion review/plan or inspect profile changes before relying on verified status.",
                )
            )


def _check_profile_promotion_revoke(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    path = workspace / "state" / "profile-promotion-revoke-plan.json"
    if not path.exists():
        return
    try:
        plan = load_profile_promotion_revoke_plan(path)
    except Exception as exc:
        findings.append(
            _finding(
                "profile_promotion_revoke_plan_unreadable",
                "medium",
                f"Profile promotion revoke plan could not be read: {exc}",
                path,
                "Regenerate profile-promotion-revoke-plan before relying on rollback readiness.",
            )
        )
        return
    if plan.status in {"ready_to_revoke", "already_restored"}:
        return
    severity = "high" if plan.status in {"missing_backup", "backup_unreadable", "backup_mismatch", "current_profile_drift"} else "medium"
    findings.append(
        _finding(
            f"profile_promotion_revoke_{plan.status}",
            severity,
            f"Profile promotion revoke plan is not ready_to_revoke: {plan.status}.",
            path,
            "Review backup, apply result, and current profile drift before any rollback operation.",
        )
    )


def _check_profile_promotion_revoke_result(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    plan_path = workspace / "state" / "profile-promotion-revoke-plan.json"
    result_path = workspace / "state" / "profile-promotion-revoke-result.json"
    profile_path = workspace / "state" / "project-profile.json"
    profile: ProjectProfile | None = None
    if profile_path.exists():
        try:
            profile = load_project_profile(profile_path)
        except Exception:
            profile = None
    if plan_path.exists() and not result_path.exists():
        try:
            plan = load_profile_promotion_revoke_plan(plan_path)
        except Exception:
            plan = None
        if plan is not None and plan.status == "ready_to_revoke" and plan.can_revoke:
            findings.append(
                _finding(
                    "profile_promotion_revoke_pending",
                    "medium",
                    "A profile promotion revocation plan is ready, but the guarded revoke command has not been run.",
                    result_path,
                    "Run profile-promotion-revoke with the revoke-plan hash, or leave the verified profile state unchanged.",
                )
            )
    if not result_path.exists():
        return
    try:
        result = load_profile_promotion_revoke_result(result_path)
    except Exception as exc:
        findings.append(
            _finding(
                "profile_promotion_revoke_result_unreadable",
                "medium",
                f"Profile promotion revoke result could not be read: {exc}",
                result_path,
                "Fix state/profile-promotion-revoke-result.json before relying on profile rollback state.",
            )
        )
        return
    pre_backup = Path(result.pre_revoke_backup_path) if result.pre_revoke_backup_path else None
    if pre_backup is not None and not pre_backup.exists():
        findings.append(
            _finding(
                "profile_promotion_revoke_pre_backup_missing",
                "medium",
                "Profile promotion revoke result refers to a missing pre-revoke backup file.",
                pre_backup,
                "Restore the pre-revoke backup artifact or review version control before relying on rollback instructions.",
            )
        )
    restore_backup = Path(result.restore_backup_path) if result.restore_backup_path else None
    if restore_backup is not None and not restore_backup.exists():
        findings.append(
            _finding(
                "profile_promotion_revoke_restore_backup_missing",
                "medium",
                "Profile promotion revoke result refers to a missing original restore backup file.",
                restore_backup,
                "Restore the original profile backup artifact or review version control before relying on profile lifecycle history.",
            )
        )
    if profile is not None and result.after_profile and profile.model_dump() != result.after_profile:
        findings.append(
            _finding(
                "profile_promotion_revoke_result_drift",
                "high",
                "Current project profile no longer matches the saved profile promotion revoke result.",
                profile_path,
                "Inspect profile changes before relying on reverted profile status.",
            )
        )


def _check_profile_lifecycle(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_profile_lifecycle_ledger(workspace)
    if result.status == "not_configured":
        return
    path = workspace / "state" / "profile-lifecycle-ledger.json"
    if result.high_count:
        findings.append(
            _finding(
                "profile_lifecycle_high_findings",
                "high",
                f"{result.high_count} high-severity profile lifecycle finding(s) were detected.",
                path,
                "Run profile-lifecycle-ledger and resolve profile lifecycle drift before relying on profile status.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "profile_lifecycle_review_findings",
                "medium" if result.medium_count else "low",
                f"{result.medium_count + result.low_count} profile lifecycle review finding(s) or warnings were detected.",
                path,
                "Review profile-lifecycle-ledger before relying on review/promotion/apply/revoke history.",
            )
        )


def _check_profile_pack_readiness(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_profile_pack_readiness(workspace)
    path = workspace / "state" / "profile-pack-readiness.json"
    if result.status == "not_configured":
        return
    if not path.exists() and result.profile_count:
        findings.append(
            _finding(
                "profile_pack_readiness_missing",
                "low",
                f"{result.profile_count} profile pack readiness profile(s) were detected but no readiness dashboard artifact exists.",
                path,
                "Run profile-pack-readiness to create a scan-friendly profile/source readiness dashboard.",
            )
        )
    if result.high_count:
        findings.append(
            _finding(
                "profile_pack_readiness_high_findings",
                "high",
                f"{result.high_count} high-severity profile pack readiness finding(s) were detected.",
                path,
                "Review profile-pack-readiness before adding or promoting agency profile packs.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "profile_pack_readiness_findings",
                "medium" if result.medium_count else "low",
                f"{result.medium_count + result.low_count} profile pack readiness finding(s) or warnings were detected.",
                path,
                "Use profile-pack-readiness to review source, fix-plan, fix-review, promotion, apply/revoke, and lifecycle blockers together.",
            )
        )


def _check_profile_pack_readiness_drilldown(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_profile_pack_readiness_drilldown(workspace)
    path = workspace / "state" / "profile-pack-readiness-drilldown.json"
    if result.status == "not_configured" or result.readiness_finding_count == 0:
        return
    if not path.exists():
        findings.append(
            _finding(
                "profile_pack_readiness_drilldown_missing",
                "low",
                f"{result.readiness_finding_count} profile pack readiness finding(s) exist but no drilldown artifact exists.",
                path,
                "Run profile-pack-readiness-drilldown to link readiness blockers to upstream artifacts and hashes.",
            )
        )
        return
    if result.missing_artifact_count:
        findings.append(
            _finding(
                "profile_pack_readiness_drilldown_missing_artifacts",
                "medium",
                f"{result.missing_artifact_count} profile pack readiness drilldown item(s) are missing upstream artifacts.",
                path,
                "Regenerate profile-source queue/fix/review/lifecycle artifacts, then rerun profile-pack-readiness-drilldown.",
            )
        )
    if result.unmatched_count:
        findings.append(
            _finding(
                "profile_pack_readiness_drilldown_unmatched",
                "medium",
                f"{result.unmatched_count} profile pack readiness drilldown item(s) could not be matched to upstream rows.",
                path,
                "Regenerate profile-pack-readiness and its upstream artifacts before relying on drilldown links.",
            )
        )


def _check_profile_pack_investigation_bundle(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_profile_pack_investigation_bundle(workspace)
    path = workspace / "state" / "profile-pack-investigation-bundle.json"
    if result.status == "not_configured" or result.drilldown_item_count == 0:
        return
    if not path.exists():
        findings.append(
            _finding(
                "profile_pack_investigation_bundle_missing",
                "low",
                f"{result.drilldown_item_count} profile pack drilldown item(s) exist but no investigation bundle artifact exists.",
                path,
                "Run profile-pack-investigation-bundle to create a compact handoff for profile-pack remediation review.",
            )
        )
        return
    if result.human_review_missing_count:
        findings.append(
            _finding(
                "profile_pack_investigation_bundle_human_review_missing",
                "medium",
                f"{result.human_review_missing_count} profile pack investigation item(s) still need supplied human review.",
                path,
                "Record supplied profile-source fix or promotion decisions, then rerun profile-pack-investigation-bundle.",
            )
        )
    if result.official_source_check_count:
        findings.append(
            _finding(
                "profile_pack_investigation_bundle_official_source_checks",
                "medium",
                f"{result.official_source_check_count} profile pack investigation item(s) require official-source checks.",
                path,
                "Check current official sources outside this tool before treating profile-pack blockers as resolved.",
            )
        )


def _check_profile_pack_investigation_package(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    path = workspace / "state" / "profile-pack-investigation-package.json"
    bundle_path = workspace / "state" / "profile-pack-investigation-bundle.json"
    if not bundle_path.exists():
        return
    try:
        preview = generate_profile_pack_investigation_package(workspace, bundle_path=bundle_path)
    except Exception as exc:
        findings.append(
            _finding(
                "profile_pack_investigation_package_schema_invalid",
                "medium",
                f"Profile pack investigation package preview could not be generated: {exc}",
                bundle_path,
                "Regenerate profile-pack-investigation-bundle, then run profile-pack-investigation-package.",
            )
        )
        return
    if preview.bundle_status == "not_configured" or preview.selected_item_count == 0:
        return
    if not path.exists():
        findings.append(
            _finding(
                "profile_pack_investigation_package_missing",
                "low",
                f"{preview.selected_item_count} profile pack investigation item(s) are selected for handoff but no package manifest exists.",
                path,
                "Run profile-pack-investigation-package to create a generated-metadata-only reviewer package manifest.",
            )
        )
        return
    try:
        validation = validate_json_file(path, "profile-pack-investigation-package")
        package = load_profile_pack_investigation_package(path)
    except Exception as exc:
        findings.append(
            _finding(
                "profile_pack_investigation_package_schema_invalid",
                "medium",
                f"Profile pack investigation package could not be read or validated: {exc}",
                path,
                "Regenerate profile-pack-investigation-package before sharing reviewer handoff metadata.",
            )
        )
        return
    if not validation["valid"]:
        findings.append(
            _finding(
                "profile_pack_investigation_package_schema_invalid",
                "medium",
                f"Profile pack investigation package schema validation failed with {validation['error_count']} error(s).",
                path,
                "Run validate-json profile-pack-investigation-package and regenerate the package manifest.",
            )
        )
    if package.missing_artifact_count:
        findings.append(
            _finding(
                "profile_pack_investigation_package_missing_artifacts",
                "medium",
                f"{package.missing_artifact_count} generated metadata artifact(s) referenced by the package are missing.",
                path,
                "Regenerate readiness, drilldown, bundle, and review-pack artifacts, then rerun profile-pack-investigation-package.",
            )
        )


def _check_profile_pack_package_receipts(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    package_path = workspace / "state" / "profile-pack-investigation-package.json"
    if not package_path.exists():
        return
    try:
        result = summarize_profile_pack_package_receipts(workspace)
    except Exception as exc:
        findings.append(
            _finding(
                "profile_pack_package_receipts_unreadable",
                "medium",
                f"Profile pack package receipts could not be summarized: {exc}",
                workspace / "state" / "profile-pack-package-receipts",
                "Fix receipt records or regenerate profile-pack-investigation-package before relying on handoff state.",
            )
        )
        return
    if result.high_count:
        findings.append(
            _finding(
                "profile_pack_package_receipts_high_findings",
                "high",
                f"Profile pack package receipt summary has {result.high_count} high-severity finding(s).",
                workspace / "state" / "profile-pack-package-receipts",
                "Review stale, rejected, or mismatched package receipts before treating the handoff as reviewed.",
            )
        )
    elif result.unresolved_count or result.medium_count:
        findings.append(
            _finding(
                "profile_pack_package_receipts_unresolved",
                "medium",
                f"Profile pack package receipt summary has {result.unresolved_count} unresolved receipt finding(s).",
                workspace / "state" / "profile-pack-package-receipts",
                "Record a supplied reviewer receipt or address package receipt needs_changes findings.",
            )
        )


def _check_admin_profile_pack_review(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    profile_path = workspace / "state" / "project-profile.json"
    if not profile_path.exists():
        return
    try:
        profile = load_project_profile(profile_path)
        result = review_admin_obligation_profile_pack(profile.profile_id)
    except Exception as exc:
        findings.append(
            _finding(
                "admin_profile_pack_review_unreadable",
                "medium",
                f"Admin profile pack review could not run: {exc}",
                profile_path,
                "Fix the project profile or bundled admin profile pack before relying on profile-driven obligations.",
            )
        )
        return
    if result.status == "not_configured":
        findings.append(
            _finding(
                "admin_profile_pack_missing",
                "low",
                f"No admin obligation profile pack was found for `{profile.profile_id}`.",
                profile_path,
                "Use the generic starter or add templates/agencies/<profile-id>/admin-obligations.json as a needs-review pack.",
            )
        )
    elif result.high_count:
        findings.append(
            _finding(
                "admin_profile_pack_high_findings",
                "high",
                f"Admin profile pack review has {result.high_count} high-severity finding(s).",
                result.pack_path or profile_path,
                "Run admin-profile-pack-review and fix source bindings before seeding obligations.",
            )
        )
    elif result.medium_count:
        findings.append(
            _finding(
                "admin_profile_pack_review_findings",
                "medium",
                f"Admin profile pack review has {result.medium_count} medium-severity finding(s).",
                result.pack_path or profile_path,
                "Keep profile-driven admin obligations as needs_review until official-source and human review are complete.",
            )
        )


def _check_admin_profile_pack_reviews(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    profile_path = workspace / "state" / "project-profile.json"
    if not profile_path.exists():
        return
    try:
        profile = load_project_profile(profile_path)
        result = summarize_admin_profile_pack_reviews(workspace, profile.profile_id)
    except Exception as exc:
        findings.append(
            _finding(
                "admin_profile_pack_reviews_unreadable",
                "medium",
                f"Admin profile-pack human review summary could not run: {exc}",
                profile_path,
                "Fix state/admin-profile-pack-reviews or the bundled admin profile pack before relying on profile-driven obligations.",
            )
        )
        return
    if result.status == "not_configured":
        return
    if result.high_count:
        findings.append(
            _finding(
                "admin_profile_pack_reviews_high_findings",
                "high",
                f"Admin profile-pack human review summary has {result.high_count} high-severity finding(s).",
                workspace / "state" / "admin-profile-pack-reviews",
                "Record fresh hash-bound review decisions or fix rejected/stale row reviews before promotion.",
            )
        )
    elif result.medium_count:
        findings.append(
            _finding(
                "admin_profile_pack_reviews_unresolved",
                "medium",
                f"Admin profile-pack human review summary has {result.medium_count} unresolved review finding(s).",
                workspace / "state" / "admin-profile-pack-reviews",
                "Record pack-level or row-level human review decisions before treating profile-driven obligations as reviewed.",
            )
        )


def _check_admin_profile_pack_gate(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    profile_path = workspace / "state" / "project-profile.json"
    if not profile_path.exists():
        return
    try:
        result = generate_admin_profile_pack_promotion_gate(workspace)
    except Exception as exc:
        findings.append(
            _finding(
                "admin_profile_pack_gate_unreadable",
                "medium",
                f"Admin profile-pack promotion gate could not run: {exc}",
                profile_path,
                "Fix profile review, profile promotion, or admin profile-pack review metadata before relying on reviewed-seed eligibility.",
            )
        )
        return
    if result.status == "blocked":
        findings.append(
            _finding(
                "admin_profile_pack_gate_blocked",
                "high",
                f"Admin profile-pack promotion gate is blocked with {result.high_count} high issue(s).",
                result.json_path or workspace / "state" / "admin-profile-pack-gate.json",
                "Run admin-profile-pack-gate and fix high-severity profile/admin pack review issues before trusted seeding.",
            )
        )
    elif result.status == "needs_review":
        findings.append(
            _finding(
                "admin_profile_pack_gate_needs_review",
                "medium",
                f"Admin profile-pack promotion gate is not ready; can_use_reviewed_seed={result.can_use_reviewed_seed}.",
                result.json_path or workspace / "state" / "admin-profile-pack-gate.json",
                "Complete profile-review, profile-promotion, and admin-profile-pack-review receipts before reviewed seeding.",
            )
        )


def _check_admin_obligations(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = review_admin_obligations(workspace)
    if result.high_count:
        findings.append(
            _finding(
                "admin_obligations_high_findings",
                "high",
                f"Admin obligation review has {result.high_count} high-severity finding(s).",
                workspace / "state" / "admin-obligations.json",
                "Run admin-obligations-review and resolve stale evidence, approval, or submission links.",
            )
        )
    elif result.medium_count:
        findings.append(
            _finding(
                "admin_obligations_review_findings",
                "medium",
                f"Admin obligation review has {result.medium_count} medium-severity finding(s).",
                workspace / "state" / "admin-obligations.json",
                "Run admin-obligations-init/review and keep profile-driven admin obligations as needs_review until verified.",
            )
        )


def _check_admin_reviewed_seed_drift(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_admin_reviewed_seed_drift_dashboard(workspace)
    if result.status == "not_configured":
        return
    if result.high_count:
        findings.append(
            _finding(
                "admin_reviewed_seed_drift_high_findings",
                "high",
                f"Reviewed-seed drift dashboard has {result.high_count} high-severity drift item(s).",
                workspace / "state" / "admin-reviewed-seed-drift.json",
                "Run admin-reviewed-seed-drift and refresh hash-bound review artifacts before relying on reviewed-seed obligations.",
            )
        )
    elif result.medium_count:
        findings.append(
            _finding(
                "admin_reviewed_seed_drift_review_findings",
                "medium",
                f"Reviewed-seed drift dashboard has {result.medium_count} medium-severity drift item(s).",
                workspace / "state" / "admin-reviewed-seed-drift.json",
                "Run admin-reviewed-seed-drift and resolve review receipt or metadata gaps.",
            )
        )


def _check_settlement_binder(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_settlement_binder(workspace)
    if result.status == "not_configured":
        return
    if result.high_count:
        findings.append(
            _finding(
                "settlement_binder_high_findings",
                "high",
                f"Settlement binder has {result.high_count} high-severity finding(s).",
                workspace / "state" / "budget-ledger.json",
                "Run settlement-binder and resolve missing or mismatched settlement evidence links.",
            )
        )
    elif result.medium_count:
        findings.append(
            _finding(
                "settlement_binder_review_findings",
                "medium",
                f"Settlement binder has {result.medium_count} medium-severity finding(s).",
                workspace / "state" / "budget-ledger.json",
                "Run settlement-binder and complete proof, approval, and evidence metadata before settlement review.",
            )
        )


def _check_admin_change_ledger(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = review_admin_change_ledger(workspace)
    if result.status == "not_configured":
        return
    if result.high_count:
        findings.append(
            _finding(
                "admin_change_ledger_high_findings",
                "high",
                f"Admin change ledger has {result.high_count} high-severity finding(s).",
                workspace / "state" / "admin-change-ledger.json",
                "Review rejected, stale, or report-referenced unapproved changes before using changed values.",
            )
        )
    elif result.medium_count:
        findings.append(
            _finding(
                "admin_change_ledger_review_findings",
                "medium",
                f"Admin change ledger has {result.medium_count} medium-severity finding(s).",
                workspace / "state" / "admin-change-ledger.json",
                "Complete reviewer, timestamp, approval, and target-hash metadata for admin changes.",
            )
        )


def _check_admin_calendar(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    obligations_path = workspace / "state" / "admin-obligations.json"
    if not obligations_path.exists():
        return
    result = review_admin_calendar(workspace)
    if result.high_count:
        findings.append(
            _finding(
                "admin_calendar_high_findings",
                "high",
                f"Admin calendar review has {result.high_count} high-severity finding(s).",
                obligations_path,
                "Review overdue admin obligations and update local submission/approval state.",
            )
        )
    elif result.medium_count:
        findings.append(
            _finding(
                "admin_calendar_review_findings",
                "medium",
                f"Admin calendar review has {result.medium_count} medium-severity finding(s).",
                obligations_path,
                "Link admin obligations to reviewed project-goals deadlines and prepare due-soon evidence.",
            )
        )


def _check_reports(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    reports_dir = workspace / "reports"
    reports = [path for path in reports_dir.glob("*.md") if not is_operational_markdown(path)] if reports_dir.exists() else []
    if not reports:
        findings.append(_finding("report_missing", "low", "No report Markdown drafts found.", reports_dir, "Generate a draft report when evidence is ready."))


def _check_report_integrity(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_workspace_report_integrity(workspace)
    if result.report_count == 0:
        return
    if any(warning.startswith("evidence_index_unreadable:") for warning in result.warnings):
        findings.append(
            _finding(
                "report_integrity_unchecked",
                "high",
                "Report integrity could not be checked because the evidence index is unavailable.",
                workspace / "state" / "evidence-index.json",
                "Regenerate the evidence index, then rerun report-integrity.",
            )
        )
        return
    if result.high_count:
        findings.append(
            _finding(
                "report_integrity_high_findings",
                "high",
                f"{result.high_count} high-severity report integrity finding(s) were detected.",
                workspace / "reports",
                "Run report-integrity and fix unsupported or mismatched claims before approval.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "report_integrity_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} report integrity review finding(s) or warnings were detected.",
                workspace / "reports",
                "Review report-integrity output before external use.",
            )
        )


def _check_artifact_authority(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_artifact_authority(workspace)
    if result.status == "not_configured":
        return
    path = workspace / "state" / "artifact-authority.json"
    if result.high_count:
        findings.append(
            _finding(
                "artifact_authority_high_findings",
                "high",
                f"{result.high_count} high-severity artifact authority finding(s) were detected.",
                path,
                "Run artifact-authority and resolve invalid or falsely-final projection authority.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "artifact_authority_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} artifact authority review finding(s) or warnings were detected.",
                path,
                "Review artifact-authority before treating generated artifacts as approved or externally ready.",
            )
        )


def _check_goals_review(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_goals_review(workspace)
    path = workspace / "state" / "project-goals.json"
    if result.status == "not_configured":
        findings.append(
            _finding(
                "project_goals_missing",
                "low",
                "No project goals/deadlines operating file found.",
                path,
                "Run goals-init, then review local objectives and deadlines before weekly/project review.",
            )
        )
        return
    if result.high_count:
        findings.append(
            _finding(
                "goals_review_high_findings",
                "high",
                f"{result.high_count} high-severity goals/deadline finding(s) were detected.",
                path,
                "Run goals-review and resolve overdue or broken objective/deadline links.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "goals_review_findings",
                "medium" if result.medium_count else "low",
                f"{result.medium_count + result.low_count} goals/deadline review finding(s) or warnings were detected.",
                path,
                "Review goals-review before relying on local objectives, deadlines, or weekly project status.",
            )
        )


def _check_bibliography_integrity(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_workspace_bibliography_integrity(workspace)
    if result.status == "not_configured":
        return
    path = workspace / "state" / "bibliography-index.json"
    if result.high_count:
        findings.append(
            _finding(
                "bibliography_integrity_high_findings",
                "high",
                f"{result.high_count} high-severity bibliography integrity finding(s) were detected.",
                path,
                "Run bib-integrity and resolve missing citations or bibliography source drift.",
            )
        )
    if result.medium_count or result.low_count:
        findings.append(
            _finding(
                "bibliography_integrity_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} bibliography integrity review finding(s) were detected.",
                path,
                "Review bib-integrity output before external manuscript or report use.",
            )
        )


def _check_reference_corpus(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = build_reference_corpus(workspace)
    if result.status == "not_configured":
        return
    path = workspace / "state" / "literature-corpus.json"
    if result.high_count:
        findings.append(
            _finding(
                "reference_corpus_high_findings",
                "high",
                f"{result.high_count} high-severity reference corpus rejection(s) were detected.",
                path,
                "Run reference-corpus and resolve unreadable or invalid local reference files before using the corpus.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "reference_corpus_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} reference corpus review rejection(s) or warnings were detected.",
                path,
                "Review reference-corpus-summary and reference-rejection-log before using imported metadata.",
            )
        )


def _check_citation_support_integrity(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_workspace_citation_support_integrity(workspace)
    if result.status == "not_configured":
        return
    path = workspace / "state" / "citation-support"
    if result.high_count:
        findings.append(
            _finding(
                "citation_support_high_findings",
                "high",
                f"{result.high_count} high-severity citation support finding(s) were detected.",
                path,
                "Run citation-support-integrity and resolve unsupported paper-claim links before external manuscript or report use.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "citation_support_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} citation support review finding(s) or warnings were detected.",
                path,
                "Review citation-support output before external manuscript or report use.",
            )
        )


def _check_research_claim_matrix(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_research_claim_matrix(workspace)
    if result.status == "not_configured":
        return
    path = workspace / "state" / "research-claims.json"
    if result.high_count:
        findings.append(
            _finding(
                "research_claim_matrix_high_findings",
                "high",
                f"{result.high_count} high-severity research claim matrix finding(s) were detected.",
                path,
                "Run research-claim-matrix and resolve invalid evidence, citation, or support links before external manuscript/report use.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "research_claim_matrix_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} research claim matrix review finding(s) or warnings were detected.",
                path,
                "Review research-claim-matrix output and keep unresolved claims as hypothesis/candidate items.",
            )
        )


def _check_workspace_trace(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_workspace_trace(workspace)
    path = workspace / "state" / "workspace-trace.json"
    if result.high_count:
        findings.append(
            _finding(
                "workspace_trace_high_findings",
                "high",
                f"{result.high_count} high-severity trace impact finding(s) were detected.",
                path,
                "Run workspace-trace and resolve changed or missing upstream artifacts before relying on downstream projections.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "workspace_trace_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} workspace trace review finding(s) or warnings were detected.",
                path,
                "Review workspace-trace output to understand affected evidence, reports, approvals, bibliography, and citation support.",
            )
        )


def _check_trace_passport(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    result = generate_trace_passport(workspace)
    path = workspace / "state" / "trace-passport.json"
    if result.status == "not_configured":
        findings.append(
            _finding(
                "trace_passport_missing",
                "low",
                "No trace passport checkpoints found.",
                workspace / "state" / "checkpoints",
                "Run checkpoint-create after a meaningful review boundary to preserve a compact resume point.",
            )
        )
        return
    if result.high_count:
        findings.append(
            _finding(
                "trace_passport_high_findings",
                "high",
                f"{result.high_count} high-severity trace passport finding(s) were detected.",
                path,
                "Run checkpoint-summary and refresh stale or missing artifacts before resuming from that checkpoint.",
            )
        )
    if result.medium_count or result.low_count or result.warnings:
        findings.append(
            _finding(
                "trace_passport_review_findings",
                "medium",
                f"{result.medium_count + result.low_count} trace passport review finding(s) or warnings were detected.",
                path,
                "Review checkpoint status and create a fresh accepted checkpoint when the workspace is stable.",
            )
        )


def _check_weekly_dashboard(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    state_dir = workspace / "state"
    weekly_paths = sorted(state_dir.glob("weekly-review-*.json")) if state_dir.exists() else []
    dashboard_path = state_dir / "workspace-dashboard.json"
    if not weekly_paths:
        findings.append(
            _finding(
                "weekly_review_missing",
                "low",
                "No saved weekly operating review found.",
                state_dir,
                "Run weekly-review to create a dated local operating review.",
            )
        )
    else:
        latest = weekly_paths[-1]
        try:
            payload = json.loads(latest.read_text(encoding="utf-8-sig"))
            raw_date = str(payload.get("review_date") or "").strip()
            if raw_date:
                review_date = date.fromisoformat(raw_date)
                if (date.today() - review_date).days > 7:
                    findings.append(
                        _finding(
                            "weekly_review_stale",
                            "low",
                            f"Latest weekly operating review is older than 7 days: {raw_date}.",
                            latest,
                            "Run weekly-review to refresh the local operating review.",
                        )
                    )
        except Exception as exc:
            findings.append(
                _finding(
                    "weekly_review_unreadable",
                    "medium",
                    f"Latest weekly operating review could not be read: {exc}",
                    latest,
                    "Regenerate the weekly review JSON.",
                )
            )
    if not dashboard_path.exists():
        findings.append(
            _finding(
                "workspace_dashboard_missing",
                "low",
                "No saved workspace dashboard found.",
                dashboard_path,
                "Run workspace-dashboard to create a compact local status dashboard.",
            )
        )
    else:
        try:
            json.loads(dashboard_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            findings.append(
                _finding(
                    "workspace_dashboard_unreadable",
                    "medium",
                    f"Workspace dashboard JSON could not be read: {exc}",
                    dashboard_path,
                    "Regenerate the workspace dashboard JSON.",
                )
            )


def _check_exports(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    reports_dir = workspace / "reports"
    if not reports_dir.exists():
        findings.append(_finding("export_missing", "low", "No reports directory found for projection exports.", reports_dir, "Run init-workspace."))
        return
    export_files = [
        path
        for pattern in ("*.docx", "*.html", "*.txt")
        for path in reports_dir.glob(pattern)
    ]
    if not export_files:
        findings.append(
            _finding(
                "export_missing",
                "low",
                "No projection export files found.",
                reports_dir,
                "Run export-projection for review documents when drafts are ready.",
            )
        )
        return
    for path in export_files:
        if not _export_has_draft_notice(path):
            findings.append(
                _finding(
                    "export_notice_missing",
                    "medium",
                    f"Projection export {path.name} does not appear to contain the draft notice.",
                    path,
                    "Regenerate with export-projection.",
                )
            )


def _check_analysis(workspace: Path, findings: list[WorkspaceDoctorFinding]) -> None:
    analysis_dir = workspace / "reports" / "analysis"
    manifests = list(analysis_dir.glob("*-analysis-run.json")) if analysis_dir.exists() else []
    if not manifests:
        findings.append(
            _finding(
                "analysis_manifest_missing",
                "low",
                "No analysis run manifest found.",
                analysis_dir,
                "Run run-analysis for datasets before using generated insights.",
            )
        )


def _export_has_draft_notice(path: Path) -> bool:
    try:
        if path.suffix.lower() == ".docx":
            with zipfile.ZipFile(path) as archive:
                return DRAFT_NOTICE in archive.read("word/document.xml").decode("utf-8", errors="replace")
        return DRAFT_NOTICE in path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False


def _write_if_missing(path: Path, text: str, created: list[str], skipped: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        skipped.append(str(path))
        return
    path.write_text(text, encoding="utf-8")
    created.append(str(path))


def _profile_for_id(profile_id: str, warnings: list[str]) -> ProjectProfile:
    profile_path = default_agency_templates_root() / profile_id / "project-profile.json"
    if profile_path.exists():
        return load_project_profile(profile_path)
    warnings.append(f"profile_not_found:{profile_id}")
    return ProjectProfile(
        profile_id=profile_id,
        status="needs_review",
        notes="Profile template was not found. Add a verified local profile before official use.",
    )


def _profile_sources_for_id(
    profile_id: str,
    workspace: Path,
    warnings: list[str],
    created: list[str],
    skipped: list[str],
) -> str:
    template_dir = default_agency_templates_root() / profile_id
    source_index = template_dir / "profile-sources.json"
    if not source_index.exists():
        return "[]\n"
    try:
        records = load_profile_sources(source_index)
    except Exception as exc:
        warnings.append(f"profile_template_sources_unreadable:{profile_id}:{exc}")
        return "[]\n"

    rendered_records = []
    for record in records:
        updated = record
        if record.source_file:
            source_file = Path(record.source_file)
            template_source = source_file if source_file.is_absolute() else template_dir / source_file
            target = workspace / "state" / "profile-sources" / source_file.name
            risk_flags = list(record.risk_flags)
            if template_source.exists() and template_source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    skipped.append(str(target))
                else:
                    shutil.copyfile(template_source, target)
                    created.append(str(target))
                updated = record.model_copy(
                    update={
                        "source_file": str(target.relative_to(workspace)),
                        "source_size_bytes": target.stat().st_size,
                    }
                )
            else:
                risk_flags.append("template_source_file_missing")
                updated = record.model_copy(update={"risk_flags": _unique(risk_flags)})
        rendered_records.append(updated.model_dump(mode="json"))
    return json.dumps(rendered_records, ensure_ascii=False, indent=2) + "\n"


def _starter_readme(project_id: str, title: str, profile_id: str) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            "> K-ResDev workspace starter. Evidence is source of truth; reports and insights are draft projections until human-approved.",
            "",
            f"- Project ID: `{project_id}`",
            f"- Profile: `{profile_id}`",
            "- Put raw files in `inbox/`.",
            "- Put BibTeX/RIS/CSL JSON bibliography files in `references/`.",
            "- Run `k-resdev discover-workspace --root . --output reports/workspace-discovery.md --json state/workspace-discovery.json` to inspect folder layout before setup or migration.",
            "- Run `k-resdev artifact-authority --root . --output reports/artifact-authority.md --json state/artifact-authority.json` to review local artifact authority levels before external use.",
            "- Run `k-resdev goals-review --root . --output reports/goals-review.md --json state/goals-review.json` to review local objectives, deadlines, evidence, report, and approval readiness.",
            "- Run `k-resdev weekly-review --root .` to create a dated local operating review.",
            "- Run `k-resdev workspace-dashboard --root .` to create a compact local status dashboard.",
            "- Run `k-resdev workflow weekly --root .` to review the local weekly workflow command plan before optional execution.",
            "- Run `k-resdev intake --inbox inbox --state-dir state --evidence-dir evidence` to build evidence metadata.",
            "- Run `k-resdev bib-import references/library.bib --state-dir state --literature-matrix reports/literature-review-matrix.md` to build bibliography metadata.",
            "- Run `k-resdev reference-corpus --root . --output reports/reference-corpus-summary.md --json state/literature-corpus.json --rejections state/reference-rejection-log.json` to scan local PDFs, Zotero JSON exports, and Markdown notes into a reviewable corpus.",
            "- Run `k-resdev bib-review-record --bibliography-id <BIB-ID> --decision accepted --reviewer <reviewer> --reviews-dir state/bibliography-reviews` to record supplied bibliography metadata review decisions.",
            "- Run `k-resdev bib-integrity --root . --output reports/bibliography-integrity.md --json state/bibliography-integrity.json` to check citation keys and bibliography source hashes.",
            "- Run `k-resdev citation-support-record --bibliography-id <BIB-ID> --citation-key <key> --claim \"<claim>\" --decision needs_review --reviewer <reviewer> --support-dir state/citation-support` to record paper-claim support decisions.",
            "- Run `k-resdev citation-support-integrity --root . --output reports/citation-support.md --json state/citation-support.json` to check cited papers against supplied support records.",
            "- Run `k-resdev research-claim-import references/research-claims.csv --state-dir state --markdown reports/research-claims.md` to import supplied research claim records.",
            "- Run `k-resdev research-claim-matrix --root . --output reports/research-claim-matrix.md --json state/research-claim-matrix.json` to check claims against evidence, bibliography, and citation support.",
            "- Run `k-resdev profile-source-record --profile-id <profile-id> --title \"<official source title>\" --source-url <url> --review-status needs_review` to record official-source metadata for profile review.",
            "- Run `k-resdev profile-source-queue --root . --output reports/profile-source-queue.md --json state/profile-source-queue.json` to review source-pack gaps before profile promotion.",
            "- Run `k-resdev profile-source-fix-plan --root . --output reports/profile-source-fix-plan.md --json state/profile-source-fix-plan.json` to turn source-pack gaps into reviewable local commands and manual checks.",
            "- Run `k-resdev profile-source-fix-summary --root . --output reports/profile-source-fix-summary.md --json state/profile-source-fix-summary.json` to summarize supplied fix-action review decisions.",
            "- Run `k-resdev profile-integrity --root . --output reports/profile-integrity.md --json state/profile-integrity.json` to check profile source records.",
            "- Run `k-resdev profile-review --root . --output reports/profile-review.md --json state/profile-review.json` before promoting any profile to verified.",
            "- Run `k-resdev profile-promotion-record --root . --decision verified --reviewer <reviewer> --profile-review-hash <sha256>` only after a supplied human promotion decision.",
            "- Run `k-resdev profile-promotion-apply-plan --root . --output reports/profile-promotion-apply-plan.md --json state/profile-promotion-apply-plan.json` before changing any profile status.",
            "- Run `k-resdev profile-promotion-apply --root . --apply-plan state/profile-promotion-apply-plan.json --apply-plan-hash <sha256>` only after reviewing the apply plan.",
            "- Run `k-resdev profile-promotion-revoke-plan --root . --reviewer <reviewer> --reason \"<reason>\" --output reports/profile-promotion-revoke-plan.md --json state/profile-promotion-revoke-plan.json` before rolling back an applied profile promotion.",
            "- Run `k-resdev profile-promotion-revoke --root . --revoke-plan state/profile-promotion-revoke-plan.json --revoke-plan-hash <sha256>` only after reviewing the revoke plan.",
            "- Run `k-resdev profile-lifecycle-ledger --root . --output reports/profile-lifecycle-ledger.md --json state/profile-lifecycle-ledger.json` to review profile review/promotion/apply/revoke history from one ledger.",
            "- Run `k-resdev profile-pack-readiness --root . --output reports/profile-pack-readiness.md --json state/profile-pack-readiness.json` to scan profile/source readiness across queue, fix-plan, fix-review, promotion, apply/revoke, and lifecycle state.",
            "- Run `k-resdev profile-pack-readiness-drilldown --root . --output reports/profile-pack-readiness-drilldown.md --json state/profile-pack-readiness-drilldown.json` to trace readiness blockers back to upstream artifacts and hashes.",
            "- Run `k-resdev profile-pack-investigation-bundle --root . --output reports/profile-pack-investigation-bundle.md --json state/profile-pack-investigation-bundle.json` to create a compact profile-pack remediation handoff.",
            "- Run `k-resdev profile-pack-investigation-package --root . --output reports/profile-pack-investigation-package.md --json state/profile-pack-investigation-package.json --zip reports/profile-pack-investigation-package.zip` to package generated metadata for reviewer handoff without copying raw official-source bodies.",
            "- Run `k-resdev profile-pack-package-receipt-summary --root . --output reports/profile-pack-package-receipt-summary.md --json state/profile-pack-package-receipt-summary.json` after supplied reviewer package receipts are recorded.",
            "- Run `k-resdev admin-obligations-init --root . --profile <profile-id> --output reports/admin-obligations.md --json state/admin-obligations-review.json` to create and review a local needs-review admin obligation graph.",
            "- Run `k-resdev admin-obligations-review --root . --output reports/admin-obligations.md --json state/admin-obligations-review.json` to check admin submission, approval, evidence, and profile gaps.",
            "- Run `k-resdev budget-ledger-import references/budget-ledger.csv --state-dir state --markdown reports/budget-ledger-import.md` to import a reviewable budget ledger.",
            "- Run `k-resdev budget-ledger-integrity --root . --output reports/budget-ledger.md --json state/budget-ledger-integrity.json` to check ledger proof, approval, duplicate, and evidence-link gaps.",
            "- Run `k-resdev settlement-binder --root . --output reports/settlement-binder.md --json state/settlement-binder.json` to bind budget ledger rows to proof, approval, evidence, and source-hash state.",
            "- Run `k-resdev admin-change-ledger --root . --output reports/admin-change-ledger.md --json state/admin-change-ledger-review.json` to review supplied agreement/change/approval records.",
            "- Run `k-resdev admin-calendar-review --root . --output reports/admin-calendar.md --json state/admin-calendar.json` to connect local admin obligations to reviewed deadline state.",
            "- Run `k-resdev checkpoint-create --root . --stage review-pack --summary \"<summary>\" --status needs_review` to create a hash-backed resume checkpoint.",
            "- Run `k-resdev checkpoint-summary --root . --output reports/trace-passport.md --json state/trace-passport.json` to review checkpoint freshness.",
            "- Run `k-resdev checkpoint-resume-plan --root . --output reports/checkpoint-resume-plan.md --json state/checkpoint-resume-plan.json` before resuming from a saved checkpoint.",
            "- Run `k-resdev doctor --root . --output reports/readiness.md --json state/readiness.json` before reporting.",
            "- Run `k-resdev workspace-summary --root . --output reports/workspace-summary.md --json state/workspace-summary.json` for a one-page status handoff.",
            "- Run `k-resdev workspace-review-pack --root .` to refresh discovery, readiness, next actions, summary, source-verification, artifact-authority, goals-review, weekly-review, workspace-dashboard, budget-ledger, settlement-binder, admin obligations, admin calendar/change checks, approval-coverage, report-integrity, bibliography-integrity, reference-corpus, citation-support, research-claim-matrix, profile-pack package, trace-passport, and trace artifacts together.",
            "- Run `k-resdev verify-review-pack state/workspace-review-pack.json` to check saved review-pack artifact hashes.",
            "- Run `k-resdev verify-evidence-sources state/evidence-index.json --root . --output reports/source-verification.md --json state/source-verification.json` to check indexed source hashes.",
            "- Run `k-resdev approval-coverage --root . --output reports/approval-coverage.md --json state/approval-coverage.json` to check report approval coverage.",
            "- Run `k-resdev report-integrity --root . --output reports/report-integrity.md --json state/report-integrity.json` to check report claims against evidence.",
            "",
        ]
    )


def _status_from_findings(findings: list[WorkspaceDoctorFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    return "ready"


def _finding(
    code: str,
    severity: str,
    message: str,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> WorkspaceDoctorFinding:
    return WorkspaceDoctorFinding(
        code=code,
        severity=severity,
        message=message,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def is_operational_markdown(path: str | Path) -> bool:
    name = Path(path).name
    return name in OPERATIONAL_MARKDOWN_NAMES or any(name.startswith(prefix) for prefix in OPERATIONAL_MARKDOWN_PREFIXES)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
