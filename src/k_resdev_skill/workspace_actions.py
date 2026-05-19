from __future__ import annotations

import hashlib
from pathlib import Path

from .models import WorkspaceActionItem, WorkspaceActionPlan, WorkspaceDoctorFinding, WorkspaceDoctorResult
from .workspace import STANDARD_DIRS, run_workspace_doctor


def generate_workspace_action_plan(
    root: str | Path,
    doctor_result: WorkspaceDoctorResult | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceActionPlan:
    """Convert doctor findings into a deterministic next-action plan."""

    workspace = Path(root)
    result = doctor_result or run_workspace_doctor(workspace)
    actions = _actions_for_findings(workspace, result.findings)
    plan = WorkspaceActionPlan(
        root=str(workspace),
        status="ready" if not actions else "actions_needed",
        action_count=len(actions),
        actions=actions,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_action_plan_markdown(plan), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(plan.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return plan


def render_action_plan_markdown(plan: WorkspaceActionPlan) -> str:
    lines = [
        "# K-ResDev Next Actions",
        "",
        "> Action plan projection only. Review commands before running and keep official submissions human-approved.",
        "",
        f"- Root: `{plan.root}`",
        f"- Status: `{plan.status}`",
        f"- Action count: {plan.action_count}",
        "",
        "| Priority | Action | Rationale | Command | Related Findings |",
        "|---|---|---|---|---|",
    ]
    if not plan.actions:
        lines.append("| ok | No action needed | Doctor did not report readiness findings. | - | - |")
    for action in plan.actions:
        command = f"`{_escape(action.command)}`" if action.command else "-"
        lines.append(
            "| {priority} | {title} | {rationale} | {command} | {findings} |".format(
                priority=_escape(action.priority),
                title=_escape(action.title),
                rationale=_escape(action.rationale),
                command=command,
                findings=_escape(", ".join(action.related_findings) or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _actions_for_findings(root: Path, findings: list[WorkspaceDoctorFinding]) -> list[WorkspaceActionItem]:
    by_code: dict[str, list[WorkspaceDoctorFinding]] = {}
    for finding in findings:
        by_code.setdefault(finding.code, []).append(finding)

    candidates = [
        _action_for_workspace_skeleton(root, by_code),
        _action_for_workspace_discovery(root, by_code),
        _action_for_missing_evidence(root, by_code),
        _action_for_invalid_evidence(root, by_code),
        _action_for_source_integrity(root, by_code),
        _action_for_review_evidence(root, by_code),
        _action_for_budget_gaps(root, by_code),
        _action_for_budget_ledger(root, by_code),
        _action_for_profile(root, by_code),
        _action_for_profile_source_queue(root, by_code),
        _action_for_profile_source_fix_plan(root, by_code),
        _action_for_profile_source_fix_reviews(root, by_code),
        _action_for_profile_integrity(root, by_code),
        _action_for_profile_review(root, by_code),
        _action_for_profile_promotion(root, by_code),
        _action_for_profile_promotion_apply(root, by_code),
        _action_for_profile_promotion_apply_result(root, by_code),
        _action_for_profile_promotion_revoke(root, by_code),
        _action_for_profile_promotion_revoke_result(root, by_code),
        _action_for_profile_lifecycle(root, by_code),
        _action_for_profile_pack_readiness(root, by_code),
        _action_for_profile_pack_readiness_drilldown(root, by_code),
        _action_for_profile_pack_investigation_bundle(root, by_code),
        _action_for_profile_pack_investigation_package(root, by_code),
        _action_for_profile_pack_package_receipts(root, by_code),
        _action_for_admin_profile_pack(root, by_code),
        _action_for_admin_obligations(root, by_code),
        _action_for_settlement_binder(root, by_code),
        _action_for_admin_change_ledger(root, by_code),
        _action_for_admin_calendar(root, by_code),
        _action_for_approval_coverage(root, by_code),
        _action_for_report_integrity(root, by_code),
        _action_for_artifact_authority(root, by_code),
        _action_for_goals_review(root, by_code),
        _action_for_bibliography_integrity(root, by_code),
        _action_for_reference_corpus(root, by_code),
        _action_for_citation_support_integrity(root, by_code),
        _action_for_research_claim_matrix(root, by_code),
        _action_for_workspace_trace(root, by_code),
        _action_for_trace_passport(root, by_code),
        _action_for_weekly_review(root, by_code),
        _action_for_workspace_dashboard(root, by_code),
        _action_for_reports(root, by_code),
        _action_for_analysis(root, by_code),
        _action_for_exports(root, by_code),
        _action_for_approvals(root, by_code),
    ]
    actions = [(index, action) for index, action in enumerate(candidates) if action is not None]
    return [action for _, action in sorted(actions, key=lambda item: (_priority_rank(item[1].priority), item[0]))]


def _action_for_workspace_skeleton(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("approval_missing", "profile_missing", "export_missing", "analysis_manifest_missing")):
        return None
    missing_dirs = [relative for relative in STANDARD_DIRS if not (root / relative).exists()]
    if not missing_dirs:
        return None
    return _action(
        root,
        "high",
        "Initialize the workspace skeleton",
        "Standard K-ResDev folders are missing; initialize them before intake or report generation.",
        f'python -m k_resdev_skill init-workspace --root "{root}" --project-id "<project-id>" --title "<project-title>"',
        by_code,
        ["missing_evidence_index", "approval_missing", "profile_missing", "export_missing", "analysis_manifest_missing"],
    )


def _action_for_workspace_discovery(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["workspace_discovery_blocked", "workspace_discovery_setup_needed", "workspace_discovery_review_needed"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if any(code in by_code for code in ("workspace_discovery_blocked", "workspace_discovery_setup_needed")) else "medium"
    return _action(
        root,
        priority,
        "Review workspace discovery proposal",
        "Discovery shows missing setup or loose source candidates; review the additive setup plan before intake or migration.",
        f'python -m k_resdev_skill discover-workspace --root "{root}" --output "{root / "reports" / "workspace-discovery.md"}" --json "{root / "state" / "workspace-discovery.json"}"',
        by_code,
        codes,
    )


def _action_for_missing_evidence(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("missing_evidence_index", "empty_evidence_index", "unreadable_evidence_index")):
        return None
    return _action(
        root,
        "high",
        "Build or regenerate the evidence index",
        "Evidence metadata is required before reports, bundles, and claim checks are meaningful.",
        f'python -m k_resdev_skill intake --inbox "{root / "inbox"}" --state-dir "{root / "state"}" --evidence-dir "{root / "evidence"}"',
        by_code,
        ["missing_evidence_index", "empty_evidence_index", "unreadable_evidence_index"],
    )


def _action_for_invalid_evidence(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if "invalid_evidence_index_schema" not in by_code:
        return None
    return _action(
        root,
        "high",
        "Validate and repair evidence metadata",
        "The evidence index exists but does not match the expected schema.",
        f'python -m k_resdev_skill validate-json evidence "{root / "state" / "evidence-index.json"}"',
        by_code,
        ["invalid_evidence_index_schema"],
    )


def _action_for_source_integrity(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "source_verification_unreadable",
        "source_file_missing",
        "source_hash_mismatch",
        "source_hash_conflict",
        "source_hash_unverified",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if any(code in by_code for code in ("source_verification_unreadable", "source_file_missing", "source_hash_mismatch")) else "medium"
    if priority == "medium" and "source_hash_conflict" not in by_code:
        priority = "low"
    return _action(
        root,
        priority,
        "Verify indexed source files",
        "Evidence source files should be present and hash-consistent before audit-sensitive reports or bundles are used.",
        f'python -m k_resdev_skill verify-evidence-sources "{root / "state" / "evidence-index.json"}" --root "{root}" --output "{root / "reports" / "source-verification.md"}" --json "{root / "state" / "source-verification.json"}"',
        by_code,
        codes,
    )


def _action_for_review_evidence(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("evidence_needs_review", "evidence_risk_flags")):
        return None
    return _action(
        root,
        "medium",
        "Review unresolved evidence and risk flags",
        "Evidence marked needs_review or risk-flagged should be accepted, rejected, or disclosed as draft before official use.",
        f'python -m k_resdev_skill bundle-index "{root / "state" / "evidence-index.json"}" --approval-records "{root / "state" / "approvals"}" --output "{root / "reports" / "evidence-bundle-index.md"}"',
        by_code,
        ["evidence_needs_review", "evidence_risk_flags"],
    )


def _action_for_budget_gaps(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if "budget_metadata_gap" not in by_code:
        return None
    return _action(
        root,
        "medium",
        "Complete generic budget evidence metadata",
        "Budget evidence is missing generic metadata fields such as date, vendor, proof type, or approval reference.",
        f'python -m k_resdev_skill budget-check "{root / "state" / "evidence-index.json"}" --output "{root / "reports" / "budget-checklist.md"}"',
        by_code,
        ["budget_metadata_gap"],
    )


def _action_for_budget_ledger(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["budget_ledger_high_findings", "budget_ledger_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "budget_ledger_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review budget ledger integrity",
        "Budget ledger rows should have proof metadata, approval references, and valid budget evidence links before settlement or audit use.",
        f'python -m k_resdev_skill budget-ledger-integrity --root "{root}" --output "{root / "reports" / "budget-ledger.md"}" --json "{root / "state" / "budget-ledger-integrity.json"}"',
        by_code,
        codes,
    )


def _action_for_profile(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("profile_missing", "profile_unreadable", "profile_needs_review")):
        return None
    return _action(
        root,
        "medium",
        "Verify the project profile",
        "Agency profiles remain local needs-review skeletons until a human verifies the official program form.",
        f'python -m k_resdev_skill validate-profile "{root / "state" / "project-profile.json"}"',
        by_code,
        ["profile_missing", "profile_unreadable", "profile_needs_review"],
    )


def _action_for_profile_integrity(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["profile_integrity_high_findings", "profile_integrity_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "profile_integrity_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review profile source integrity",
        "Agency/project profiles should stay needs_review until official-source records are hash-backed and human-reviewed.",
        f'python -m k_resdev_skill profile-integrity --root "{root}" --output "{root / "reports" / "profile-integrity.md"}" --json "{root / "state" / "profile-integrity.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_source_queue(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["profile_source_queue_high_findings", "profile_source_queue_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "profile_source_queue_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review profile source pack queue",
        "Profile source packs should have URL/file locators, retrieval dates, hashes, reviewers, and resolved risk flags before promotion.",
        f'python -m k_resdev_skill profile-source-queue --root "{root}" --output "{root / "reports" / "profile-source-queue.md"}" --json "{root / "state" / "profile-source-queue.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_source_fix_plan(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_source_fix_plan_missing",
        "profile_source_fix_plan_high_actions",
        "profile_source_fix_plan_review_actions",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "profile_source_fix_plan_high_actions" in by_code else "medium"
    return _action(
        root,
        priority,
        "Plan profile source queue fixes",
        "Profile-source queue findings should be translated into explicit local commands and manual official-source checks before metadata changes.",
        f'python -m k_resdev_skill profile-source-fix-plan --root "{root}" --output "{root / "reports" / "profile-source-fix-plan.md"}" --json "{root / "state" / "profile-source-fix-plan.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_source_fix_reviews(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_source_fix_summary_missing",
        "profile_source_fix_review_high_findings",
        "profile_source_fix_review_findings",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "profile_source_fix_review_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Summarize profile source fix reviews",
        "Profile-source fix actions should have supplied human decisions bound to the current fix-plan hash.",
        f'python -m k_resdev_skill profile-source-fix-summary --root "{root}" --output "{root / "reports" / "profile-source-fix-summary.md"}" --json "{root / "state" / "profile-source-fix-summary.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_review(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["profile_review_blocked", "profile_review_incomplete"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "profile_review_blocked" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review profile promotion readiness",
        "Source-backed profiles should not be promoted until source hashes, reviewer identity, applicability notes, and risk flags are resolved.",
        f'python -m k_resdev_skill profile-review --root "{root}" --output "{root / "reports" / "profile-review.md"}" --json "{root / "state" / "profile-review.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_promotion(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_verified_without_promotion_record",
        "profile_promotion_review_hash_mismatch",
        "profile_promotion_record_missing",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if any(code in by_code for code in codes[:2]) else "medium"
    return _action(
        root,
        priority,
        "Record profile promotion decision",
        "Profile promotion should be a supplied human decision bound to a passing profile-review artifact hash.",
        f'python -m k_resdev_skill profile-promotion-summary --root "{root}" --output "{root / "reports" / "profile-promotion-summary.md"}" --json "{root / "state" / "profile-promotion-summary.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_promotion_apply(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["profile_promotion_apply_plan_missing", "profile_verified_without_apply_plan"]
    if not any(code in by_code for code in codes):
        return None
    priority = "medium" if "profile_promotion_apply_plan_missing" in by_code else "low"
    return _action(
        root,
        priority,
        "Generate profile promotion apply plan",
        "Profile status changes should be reviewed as a non-destructive plan before state/project-profile.json is changed.",
        f'python -m k_resdev_skill profile-promotion-apply-plan --root "{root}" --output "{root / "reports" / "profile-promotion-apply-plan.md"}" --json "{root / "state" / "profile-promotion-apply-plan.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_promotion_apply_result(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_promotion_apply_pending",
        "profile_verified_without_apply_result",
        "profile_promotion_apply_result_unreadable",
        "profile_promotion_apply_backup_missing",
        "profile_promotion_apply_result_drift",
    ]
    if not any(code in by_code for code in codes):
        return None
    plan_path = root / "state" / "profile-promotion-apply-plan.json"
    plan_hash = _sha256_file(plan_path) if plan_path.exists() else "<sha256>"
    priority = "high" if any(code in by_code for code in codes[1:]) else "medium"
    return _action(
        root,
        priority,
        "Apply or review profile promotion plan",
        "Profile status changes should go through the guarded apply command with a current apply-plan hash and backup.",
        f'python -m k_resdev_skill profile-promotion-apply --root "{root}" --apply-plan "{plan_path}" --apply-plan-hash "{plan_hash}" --output "{root / "reports" / "profile-promotion-apply-result.md"}" --json "{root / "state" / "profile-promotion-apply-result.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_promotion_revoke(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_promotion_revoke_plan_unreadable",
        "profile_promotion_revoke_missing_backup",
        "profile_promotion_revoke_backup_unreadable",
        "profile_promotion_revoke_backup_mismatch",
        "profile_promotion_revoke_current_profile_drift",
        "profile_promotion_revoke_missing_apply_result",
        "profile_promotion_revoke_apply_result_unreadable",
        "profile_promotion_revoke_apply_result_profile_invalid",
        "profile_promotion_revoke_apply_result_not_applied",
        "profile_promotion_revoke_missing_profile",
        "profile_promotion_revoke_profile_unreadable",
        "profile_promotion_revoke_blocked",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if any(code in by_code for code in codes[1:5]) else "medium"
    return _action(
        root,
        priority,
        "Review profile promotion revocation plan",
        "A saved revocation plan is blocked or stale; inspect backup, apply-result, and current profile state before any rollback.",
        f'python -m k_resdev_skill profile-promotion-revoke-plan --root "{root}" --reviewer "<reviewer>" --reason "<reason>" --output "{root / "reports" / "profile-promotion-revoke-plan.md"}" --json "{root / "state" / "profile-promotion-revoke-plan.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_promotion_revoke_result(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_promotion_revoke_pending",
        "profile_promotion_revoke_result_unreadable",
        "profile_promotion_revoke_pre_backup_missing",
        "profile_promotion_revoke_restore_backup_missing",
        "profile_promotion_revoke_result_drift",
    ]
    if not any(code in by_code for code in codes):
        return None
    plan_path = root / "state" / "profile-promotion-revoke-plan.json"
    plan_hash = _sha256_file(plan_path) if plan_path.exists() else "<sha256>"
    priority = "high" if any(code in by_code for code in codes[1:]) else "medium"
    return _action(
        root,
        priority,
        "Apply or review profile promotion revocation plan",
        "Profile rollback should go through the guarded revoke command with a current revoke-plan hash and pre-revoke backup.",
        f'python -m k_resdev_skill profile-promotion-revoke --root "{root}" --revoke-plan "{plan_path}" --revoke-plan-hash "{plan_hash}" --output "{root / "reports" / "profile-promotion-revoke-result.md"}" --json "{root / "state" / "profile-promotion-revoke-result.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_lifecycle(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["profile_lifecycle_high_findings", "profile_lifecycle_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "profile_lifecycle_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review profile lifecycle ledger",
        "Profile review, promotion, apply, and revoke artifacts should line up before relying on current profile status.",
        f'python -m k_resdev_skill profile-lifecycle-ledger --root "{root}" --output "{root / "reports" / "profile-lifecycle-ledger.md"}" --json "{root / "state" / "profile-lifecycle-ledger.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_pack_readiness(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_pack_readiness_missing",
        "profile_pack_readiness_high_findings",
        "profile_pack_readiness_findings",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "profile_pack_readiness_high_findings" in by_code else "medium" if "profile_pack_readiness_findings" in by_code else "low"
    return _action(
        root,
        priority,
        "Review profile pack readiness",
        "Profile/source queue, fix-plan, fix-review, promotion, apply/revoke, and lifecycle state should be scanned together before agency pack expansion.",
        f'python -m k_resdev_skill profile-pack-readiness --root "{root}" --output "{root / "reports" / "profile-pack-readiness.md"}" --json "{root / "state" / "profile-pack-readiness.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_pack_readiness_drilldown(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_pack_readiness_drilldown_missing",
        "profile_pack_readiness_drilldown_missing_artifacts",
        "profile_pack_readiness_drilldown_unmatched",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "medium" if any(code in by_code for code in codes[1:]) else "low"
    return _action(
        root,
        priority,
        "Review profile pack readiness drilldown",
        "Readiness blockers should point back to the queue, fix-plan, review, promotion, apply/revoke, or lifecycle artifact that produced them.",
        f'python -m k_resdev_skill profile-pack-readiness-drilldown --root "{root}" --output "{root / "reports" / "profile-pack-readiness-drilldown.md"}" --json "{root / "state" / "profile-pack-readiness-drilldown.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_pack_investigation_bundle(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_pack_investigation_bundle_missing",
        "profile_pack_investigation_bundle_human_review_missing",
        "profile_pack_investigation_bundle_official_source_checks",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "medium" if any(code in by_code for code in codes[1:]) else "low"
    return _action(
        root,
        priority,
        "Prepare profile pack investigation bundle",
        "Profile-pack remediation should be easy to hand off with readiness rows, drilldown rows, artifact hashes, commands, and human-review status in one compact bundle.",
        f'python -m k_resdev_skill profile-pack-investigation-bundle --root "{root}" --output "{root / "reports" / "profile-pack-investigation-bundle.md"}" --json "{root / "state" / "profile-pack-investigation-bundle.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_pack_investigation_package(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_pack_investigation_package_missing",
        "profile_pack_investigation_package_schema_invalid",
        "profile_pack_investigation_package_missing_artifacts",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "medium" if any(code in by_code for code in codes[1:]) else "low"
    return _action(
        root,
        priority,
        "Package profile pack investigation handoff",
        "Profile-pack investigation handoff should include generated metadata hashes and explicit raw-source exclusions before reviewer transfer.",
        f'python -m k_resdev_skill profile-pack-investigation-package --root "{root}" --output "{root / "reports" / "profile-pack-investigation-package.md"}" --json "{root / "state" / "profile-pack-investigation-package.json"}"',
        by_code,
        codes,
    )


def _action_for_profile_pack_package_receipts(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "profile_pack_package_receipts_unreadable",
        "profile_pack_package_receipts_high_findings",
        "profile_pack_package_receipts_unresolved",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "profile_pack_package_receipts_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review profile pack package receipts",
        "Reviewer receipt records should stay hash-bound to the generated profile-pack package before the handoff is treated as reviewed.",
        f'python -m k_resdev_skill profile-pack-package-receipt-summary --root "{root}" --output "{root / "reports" / "profile-pack-package-receipt-summary.md"}" --json "{root / "state" / "profile-pack-package-receipt-summary.json"}"',
        by_code,
        codes,
    )


def _action_for_admin_profile_pack(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "admin_profile_pack_review_unreadable",
        "admin_profile_pack_missing",
        "admin_profile_pack_high_findings",
        "admin_profile_pack_review_findings",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "admin_profile_pack_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review admin profile pack",
        "Profile-driven admin obligation seeds should remain source-bound and needs_review before they are copied into a workspace.",
        f'python -m k_resdev_skill admin-profile-pack-review --profile "<profile-id>" --output "{root / "reports" / "admin-profile-pack.md"}" --json "{root / "state" / "admin-profile-pack-review.json"}"',
        by_code,
        codes,
    )


def _action_for_admin_obligations(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["admin_obligations_high_findings", "admin_obligations_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "admin_obligations_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review admin obligation graph",
        "Local submission, approval, evidence, settlement, and profile gaps should be visible before report or settlement work.",
        f'python -m k_resdev_skill admin-obligations-review --root "{root}" --output "{root / "reports" / "admin-obligations.md"}" --json "{root / "state" / "admin-obligations-review.json"}"',
        by_code,
        codes,
    )


def _action_for_settlement_binder(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["settlement_binder_high_findings", "settlement_binder_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "settlement_binder_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review settlement binder",
        "Budget ledger rows should be tied to proof metadata, approval references, evidence IDs, and source hashes before settlement review.",
        f'python -m k_resdev_skill settlement-binder --root "{root}" --output "{root / "reports" / "settlement-binder.md"}" --json "{root / "state" / "settlement-binder.json"}"',
        by_code,
        codes,
    )


def _action_for_admin_change_ledger(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["admin_change_ledger_high_findings", "admin_change_ledger_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "admin_change_ledger_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review admin change ledger",
        "Agreement, KPI, budget, and period changes should be approved and hash-bound before changed values appear in reports or settlement records.",
        f'python -m k_resdev_skill admin-change-ledger --root "{root}" --output "{root / "reports" / "admin-change-ledger.md"}" --json "{root / "state" / "admin-change-ledger-review.json"}"',
        by_code,
        codes,
    )


def _action_for_admin_calendar(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["admin_calendar_high_findings", "admin_calendar_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "admin_calendar_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review admin calendar",
        "Local reporting, settlement, performance, and equipment obligations should link to reviewed project deadlines before being used operationally.",
        f'python -m k_resdev_skill admin-calendar-review --root "{root}" --output "{root / "reports" / "admin-calendar.md"}" --json "{root / "state" / "admin-calendar.json"}"',
        by_code,
        codes,
    )


def _action_for_approval_coverage(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = [
        "approval_coverage_unreadable",
        "report_approval_missing",
        "report_approval_not_approved",
        "approval_target_hash_mismatch",
        "approval_target_hash_unverified",
    ]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "approval_target_hash_mismatch" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review report approval coverage",
        "Report artifacts should be linked to supplied human approval records before official use.",
        f'python -m k_resdev_skill approval-coverage --root "{root}" --output "{root / "reports" / "approval-coverage.md"}" --json "{root / "state" / "approval-coverage.json"}"',
        by_code,
        codes,
    )


def _action_for_report_integrity(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["report_integrity_unchecked", "report_integrity_high_findings", "report_integrity_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if any(code in by_code for code in ("report_integrity_unchecked", "report_integrity_high_findings")) else "medium"
    return _action(
        root,
        priority,
        "Review report claim integrity",
        "Report drafts should not contain unsupported numbers, missing evidence IDs, or evidence-mismatched claims.",
        f'python -m k_resdev_skill report-integrity --root "{root}" --output "{root / "reports" / "report-integrity.md"}" --json "{root / "state" / "report-integrity.json"}"',
        by_code,
        codes,
    )


def _action_for_artifact_authority(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["artifact_authority_high_findings", "artifact_authority_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "artifact_authority_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review artifact authority levels",
        "Generated reports, exports, evidence, and operating summaries should not be treated as approved unless supplied human approval records support that authority.",
        f'python -m k_resdev_skill artifact-authority --root "{root}" --output "{root / "reports" / "artifact-authority.md"}" --json "{root / "state" / "artifact-authority.json"}"',
        by_code,
        codes,
    )


def _action_for_goals_review(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["project_goals_missing", "goals_review_high_findings", "goals_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    if "project_goals_missing" in by_code:
        return _action(
            root,
            "low",
            "Create a project goals operating file",
            "Local objectives and deadlines should be explicit before weekly/project review.",
            f'python -m k_resdev_skill goals-init --root "{root}"',
            by_code,
            codes,
        )
    priority = "high" if "goals_review_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review project goals and deadlines",
        "Objectives and deadlines should link to valid KPIs, milestones, evidence, reports, and approvals before being used for project status.",
        f'python -m k_resdev_skill goals-review --root "{root}" --output "{root / "reports" / "goals-review.md"}" --json "{root / "state" / "goals-review.json"}"',
        by_code,
        codes,
    )


def _action_for_bibliography_integrity(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["bibliography_integrity_high_findings", "bibliography_integrity_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "bibliography_integrity_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review bibliography integrity",
        "Bibliography metadata and Markdown citation keys should be present, reviewed, and source-hash-consistent before external manuscript or report use.",
        f'python -m k_resdev_skill bib-integrity --root "{root}" --output "{root / "reports" / "bibliography-integrity.md"}" --json "{root / "state" / "bibliography-integrity.json"}"',
        by_code,
        codes,
    )


def _action_for_reference_corpus(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["reference_corpus_high_findings", "reference_corpus_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "reference_corpus_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review reference corpus import",
        "Local reference adapters may have unsupported files, duplicate metadata, or omitted copyright-risk text.",
        f'python -m k_resdev_skill reference-corpus --root "{root}" --output "{root / "reports" / "reference-corpus-summary.md"}" --json "{root / "state" / "literature-corpus.json"}" --rejections "{root / "state" / "reference-rejection-log.json"}"',
        by_code,
        codes,
    )


def _action_for_citation_support_integrity(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["citation_support_high_findings", "citation_support_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "citation_support_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review citation support",
        "Cited papers should have supplied human paper-claim support records before external manuscript or report use.",
        f'python -m k_resdev_skill citation-support-integrity --root "{root}" --output "{root / "reports" / "citation-support.md"}" --json "{root / "state" / "citation-support.json"}"',
        by_code,
        codes,
    )


def _action_for_research_claim_matrix(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["research_claim_matrix_high_findings", "research_claim_matrix_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "research_claim_matrix_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review research claim matrix",
        "Research claims should resolve to reviewed local evidence, bibliography metadata, and supplied citation-support decisions before external manuscript or report use.",
        f'python -m k_resdev_skill research-claim-matrix --root "{root}" --output "{root / "reports" / "research-claim-matrix.md"}" --json "{root / "state" / "research-claim-matrix.json"}"',
        by_code,
        codes,
    )


def _action_for_workspace_trace(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["workspace_trace_high_findings", "workspace_trace_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    priority = "high" if "workspace_trace_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review workspace trace impact",
        "Trace impact review shows changed, missing, or unresolved upstream artifacts that may affect downstream reports, approvals, bibliography, or citation support.",
        f'python -m k_resdev_skill workspace-trace --root "{root}" --output "{root / "reports" / "workspace-trace.md"}" --json "{root / "state" / "workspace-trace.json"}"',
        by_code,
        codes,
    )


def _action_for_trace_passport(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["trace_passport_missing", "trace_passport_high_findings", "trace_passport_review_findings"]
    if not any(code in by_code for code in codes):
        return None
    if "trace_passport_missing" in by_code:
        return _action(
            root,
            "low",
            "Create a trace passport checkpoint",
            "A compact checkpoint helps future sessions resume without loading every workspace artifact.",
            f'python -m k_resdev_skill checkpoint-create --root "{root}" --stage review-pack --summary "<summary>" --status needs_review',
            by_code,
            codes,
        )
    priority = "high" if "trace_passport_high_findings" in by_code else "medium"
    return _action(
        root,
        priority,
        "Review trace passport checkpoints",
        "Checkpoint artifacts may be stale, missing, or still waiting for review.",
        f'python -m k_resdev_skill checkpoint-summary --root "{root}" --output "{root / "reports" / "trace-passport.md"}" --json "{root / "state" / "trace-passport.json"}"',
        by_code,
        codes,
    )


def _action_for_weekly_review(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["weekly_review_missing", "weekly_review_stale", "weekly_review_unreadable"]
    if not any(code in by_code for code in codes):
        return None
    priority = "medium" if "weekly_review_unreadable" in by_code else "low"
    return _action(
        root,
        priority,
        "Refresh the weekly operating review",
        "A dated weekly review gives the team a compact local status slice without turning it into an official report.",
        f'python -m k_resdev_skill weekly-review --root "{root}"',
        by_code,
        codes,
    )


def _action_for_workspace_dashboard(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    codes = ["workspace_dashboard_missing", "workspace_dashboard_unreadable"]
    if not any(code in by_code for code in codes):
        return None
    priority = "medium" if "workspace_dashboard_unreadable" in by_code else "low"
    return _action(
        root,
        priority,
        "Refresh the workspace dashboard",
        "The dashboard summarizes readiness, evidence, approvals, goals, budget, research, and trace state from local artifacts.",
        f'python -m k_resdev_skill workspace-dashboard --root "{root}"',
        by_code,
        codes,
    )


def _action_for_reports(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if "report_missing" not in by_code:
        return None
    return _action(
        root,
        "low",
        "Generate a draft report when evidence is ready",
        "No report draft was found; draft reports should be projections from evidence metadata.",
        f'python -m k_resdev_skill draft-report "{root / "state" / "evidence-index.json"}" --project-state "{root / "state" / "project-state.json"}" --reports-dir "{root / "reports"}"',
        by_code,
        ["report_missing"],
    )


def _action_for_analysis(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if "analysis_manifest_missing" not in by_code:
        return None
    return _action(
        root,
        "low",
        "Run reproducible analysis for tabular datasets",
        "No analysis manifest was found; dataset insights should have profile, script, and manifest traces.",
        f'python -m k_resdev_skill run-analysis "{root / "inbox" / "metrics.csv"}" --output-dir "{root / "reports" / "analysis"}"',
        by_code,
        ["analysis_manifest_missing"],
    )


def _action_for_exports(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("export_missing", "export_notice_missing")):
        return None
    return _action(
        root,
        "low",
        "Create review exports from Markdown drafts",
        "Projection exports should include the draft/human-approval notice before external review.",
        f'python -m k_resdev_skill export-projection "{root / "reports" / "monthly-report.md"}" --output "{root / "reports" / "monthly-report.docx"}" --format docx',
        by_code,
        ["export_missing", "export_notice_missing"],
    )


def _action_for_approvals(root: Path, by_code: dict[str, list[WorkspaceDoctorFinding]]) -> WorkspaceActionItem | None:
    if not any(code in by_code for code in ("approval_missing", "approval_unreadable", "report_approval_missing", "report_approval_not_approved")):
        return None
    return _action(
        root,
        "medium",
        "Record supplied human review decisions",
        "K-ResDev does not infer approval; human decisions must be recorded explicitly.",
        f'python -m k_resdev_skill approval-record --target-type report --target-id monthly-report --decision needs_changes --reviewer "<reviewer>" --approvals-dir "{root / "state" / "approvals"}"',
        by_code,
        ["approval_missing", "approval_unreadable", "report_approval_missing", "report_approval_not_approved"],
    )


def _action(
    root: Path,
    priority: str,
    title: str,
    rationale: str,
    command: str,
    by_code: dict[str, list[WorkspaceDoctorFinding]],
    codes: list[str],
) -> WorkspaceActionItem:
    related = [code for code in codes if code in by_code]
    digest = hashlib.sha256(f"{root}|{title}|{','.join(related)}".encode("utf-8")).hexdigest()[:8].upper()
    return WorkspaceActionItem(
        action_id=f"ACT-{digest}",
        priority=priority,
        title=title,
        rationale=rationale,
        command=command,
        related_findings=related,
    )


def _priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 3)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
