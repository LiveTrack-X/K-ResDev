from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .approval import load_approval_records
from .budget_ledger import generate_workspace_budget_ledger, load_budget_ledger
from .evidence_index import load_evidence_index
from .models import (
    AdminCalendarResult,
    AdminChangeLedgerResult,
    AdminChangeRecord,
    AdminFinding,
    AdminObligation,
    AdminObligationGraphResult,
    AdminObligationProfilePack,
    AdminObligationProfilePackReviewResult,
    AdminSubmission,
    BudgetLedgerFinding,
    EvidenceItem,
    ProjectDeadline,
    ProjectGoalsFile,
    ProjectProfile,
    SettlementBinderItem,
    SettlementEvidenceRequirement,
    WorkspaceSettlementBinderResult,
)
from .profile_registry import default_agency_templates_root, load_project_profile
from .profile_sources import load_profile_sources


ADMIN_OBLIGATIONS_PATH = "state/admin-obligations.json"
ADMIN_SUBMISSIONS_PATH = "state/admin-submissions.json"
ADMIN_CHANGE_LEDGER_PATH = "state/admin-change-ledger.json"


def initialize_admin_obligations(
    root: str | Path,
    profile_id: str = "national-rnd-basic",
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    templates_root: str | Path | None = None,
    reviewed_seed: bool = False,
    gate_path: str | Path | None = None,
) -> AdminObligationGraphResult:
    """Create a local admin-obligation starter without encoding official agency rules."""

    workspace = Path(root)
    state = workspace / "state"
    state.mkdir(parents=True, exist_ok=True)
    obligations_path = state / "admin-obligations.json"
    if not obligations_path.exists():
        seed_pack, seed_path, seed_warnings = _admin_obligation_seed_pack(profile_id, templates_root)
        seed_metadata: dict[str, Any] = {}
        if reviewed_seed:
            seed_pack, seed_metadata, reviewed_seed_warnings = _reviewed_seed_pack(workspace, profile_id, seed_pack, seed_path, templates_root, gate_path)
            seed_warnings = _unique(seed_warnings + reviewed_seed_warnings)
        obligations_path.write_text(
            json.dumps(
                {
                    "generated_by": "k-resdev-skill",
                    "profile_id": profile_id,
                    "status": seed_pack.status,
                    "profile_status": seed_pack.profile_status,
                    "source_pack_path": str(seed_path) if seed_path is not None else None,
                    "source_record_ids": seed_pack.source_record_ids,
                    "notes": seed_pack.notes or "Local admin obligation starter. Verify current agency/program rules before official use.",
                    "warnings": _unique(seed_pack.warnings + seed_warnings),
                    **seed_metadata,
                    "obligations": [item.model_dump(mode="json") for item in seed_pack.obligations],
                    "settlement_requirements": [item.model_dump(mode="json") for item in seed_pack.settlement_requirements],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    submissions_path = state / "admin-submissions.json"
    if not submissions_path.exists():
        submissions_path.write_text(
            json.dumps(
                {
                    "generated_by": "k-resdev-skill",
                    "status": seed_pack.status if "seed_pack" in locals() else "needs_review",
                    **(seed_metadata if "seed_metadata" in locals() else {}),
                    "submissions": [item.model_dump(mode="json") for item in seed_pack.submissions] if "seed_pack" in locals() else [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return review_admin_obligations(workspace, output_path=output_path, json_path=json_path)


def load_admin_obligation_profile_pack(
    profile_id: str,
    templates_root: str | Path | None = None,
) -> AdminObligationProfilePack:
    """Load a bundled/admin profile obligation pack and keep unverified content in needs_review."""

    pack_path = _admin_obligation_profile_pack_path(profile_id, templates_root)
    if not pack_path.exists():
        raise FileNotFoundError(f"admin obligation profile pack not found: {pack_path}")
    profile = _load_template_profile(pack_path.parent)
    sources = _load_template_sources(pack_path.parent)
    warnings: list[str] = []
    pack = _load_admin_obligation_profile_pack_payload(pack_path, profile_id, profile.status if profile else None, sources, warnings)
    if warnings:
        pack = pack.model_copy(update={"warnings": _unique(pack.warnings + warnings)})
    return pack


def review_admin_obligation_profile_pack(
    profile_id: str,
    templates_root: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> AdminObligationProfilePackReviewResult:
    """Review a profile-driven admin obligation seed pack before local workspace initialization."""

    root = Path(templates_root) if templates_root is not None else default_agency_templates_root()
    profile_dir = root / profile_id
    pack_path = profile_dir / "admin-obligations.json"
    profile = _load_template_profile(profile_dir)
    sources = _load_template_sources(profile_dir)
    warnings: list[str] = []
    findings: list[AdminFinding] = []
    pack: AdminObligationProfilePack | None = None

    if profile is None:
        findings.append(
            _admin_finding(
                "admin_profile_pack_project_profile_missing",
                "medium",
                f"Profile `{profile_id}` has no project-profile.json template.",
                path=profile_dir / "project-profile.json",
                suggested_action="Add a project-profile.json template before using profile-driven admin obligations.",
            )
        )
    elif profile.status != "verified":
        findings.append(
            _admin_finding(
                "admin_profile_pack_profile_needs_review",
                "medium",
                f"Profile `{profile_id}` is `{profile.status}`.",
                path=profile_dir / "project-profile.json",
                suggested_action="Keep seeded admin obligations as needs_review until the profile is promoted after human verification.",
            )
        )

    if not pack_path.exists():
        findings.append(
            _admin_finding(
                "admin_profile_pack_missing",
                "medium",
                f"Profile `{profile_id}` has no admin-obligations.json pack.",
                path=pack_path,
                suggested_action="Add a needs-review admin-obligations.json pack or fall back to the generic local starter.",
            )
        )
    else:
        try:
            pack = _load_admin_obligation_profile_pack_payload(pack_path, profile_id, profile.status if profile else None, sources, warnings)
        except Exception as exc:
            warnings.append(f"admin_profile_pack_unreadable:{profile_id}:{exc}")
            findings.append(
                _admin_finding(
                    "admin_profile_pack_unreadable",
                    "high",
                    f"Profile `{profile_id}` admin-obligations.json could not be read: {exc}",
                    path=pack_path,
                    suggested_action="Fix the profile pack JSON before using it for workspace initialization.",
                )
            )
        else:
            findings.extend(_admin_profile_pack_findings(profile_id, pack, pack_path, profile.status if profile else None, sources))

    findings = _dedupe_admin_findings(findings)
    status = "not_configured" if not pack_path.exists() else _status_from_admin_findings(findings)
    result = AdminObligationProfilePackReviewResult(
        root=str(root),
        status=status,
        profile_id=profile_id,
        profile_status=profile.status if profile else None,
        pack_path=str(pack_path) if pack_path.exists() else None,
        source_record_count=len(sources),
        verified_source_count=sum(1 for source in sources if source.review_status == "verified"),
        needs_review_source_count=sum(1 for source in sources if source.review_status != "verified"),
        obligation_count=len(pack.obligations) if pack else 0,
        submission_count=len(pack.submissions) if pack else 0,
        settlement_requirement_count=len(pack.settlement_requirements) if pack else 0,
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        pack=pack,
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings + (pack.warnings if pack else [])),
    )
    _write_admin_profile_pack_review_outputs(result, output_path, json_path)
    return result


def review_admin_obligations(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> AdminObligationGraphResult:
    """Review local admin obligations, submissions, settlement requirements, and approval/evidence links."""

    workspace = Path(root)
    profile = _load_profile(workspace)
    evidence = _load_evidence(workspace)
    approvals = _load_approvals(workspace)
    obligations_path = workspace / ADMIN_OBLIGATIONS_PATH
    submissions_path = workspace / ADMIN_SUBMISSIONS_PATH
    warnings: list[str] = []
    findings: list[AdminFinding] = []
    metadata = _admin_obligation_metadata(obligations_path, warnings)
    obligations = _load_obligations(obligations_path, warnings)
    submissions = _load_submissions(submissions_path, warnings)
    settlement_requirements = _combined_settlement_requirements(workspace, obligations_path, warnings)

    if not obligations_path.exists():
        findings.append(
            _admin_finding(
                "admin_obligations_missing",
                "medium",
                "No local admin obligation graph was found.",
                path=obligations_path,
                suggested_action="Run admin-obligations-init to create a needs-review local obligation starter.",
            )
        )
    if profile is None:
        findings.append(
            _admin_finding(
                "admin_profile_missing",
                "medium",
                "No project profile found for admin obligation review.",
                path=workspace / "state" / "project-profile.json",
                suggested_action="Run init-workspace or add state/project-profile.json before admin review.",
            )
        )
    elif profile.status == "needs_review":
        findings.append(
            _admin_finding(
                "admin_profile_needs_review",
                "medium",
                f"Project profile `{profile.profile_id}` is still needs_review.",
                path=workspace / "state" / "project-profile.json",
                suggested_action="Keep admin obligations as local candidates until current agency/program sources are reviewed.",
            )
        )

    findings.extend(_reviewed_seed_metadata_findings(workspace, obligations_path, metadata))

    evidence_by_type = _evidence_by_type(evidence)
    submissions_by_obligation: dict[str, list[AdminSubmission]] = {}
    for submission in submissions:
        submissions_by_obligation.setdefault(submission.obligation_id, []).append(submission)
        findings.extend(_submission_findings(workspace, submission, evidence, approvals))

    for obligation in obligations:
        if obligation.status == "needs_review":
            findings.append(
                _admin_finding(
                    "admin_obligation_needs_review",
                    "medium",
                    f"Admin obligation `{obligation.obligation_id}` is a needs_review candidate.",
                    obligation_id=obligation.obligation_id,
                    path=obligations_path,
                    suggested_action="Verify current agency/program requirements before treating this obligation as official.",
                )
            )
        for evidence_type in obligation.required_evidence_types:
            if not evidence_by_type.get(evidence_type):
                findings.append(
                    _admin_finding(
                        "admin_obligation_missing_evidence_type",
                        "medium",
                        f"Admin obligation `{obligation.obligation_id}` has no linked `{evidence_type}` evidence candidate.",
                        obligation_id=obligation.obligation_id,
                        path=workspace / "state" / "evidence-index.json",
                        suggested_action="Run intake or add evidence records before relying on this admin obligation.",
                    )
                )
        if obligation.required_approval and not submissions_by_obligation.get(obligation.obligation_id):
            findings.append(
                _admin_finding(
                    "admin_obligation_submission_missing",
                    "low",
                    f"Admin obligation `{obligation.obligation_id}` has no local submission candidate.",
                    obligation_id=obligation.obligation_id,
                    path=submissions_path,
                    suggested_action="Add a supplied submission record when a draft, uploaded file, or review artifact exists.",
                )
            )
        if obligation.risk_flags:
            findings.append(
                _admin_finding(
                    "admin_obligation_risk_flags",
                    "medium",
                    f"Admin obligation `{obligation.obligation_id}` has risk flags: {', '.join(obligation.risk_flags)}.",
                    obligation_id=obligation.obligation_id,
                    path=obligations_path,
                    suggested_action="Resolve or disclose admin obligation risk flags before external use.",
                )
            )

    result = AdminObligationGraphResult(
        root=str(workspace),
        status=_status_from_admin_findings(findings),
        profile_id=profile.profile_id if profile else None,
        profile_status=profile.status if profile else None,
        seed_mode=_metadata_str(metadata, "seed_mode"),
        source_pack_path=_metadata_str(metadata, "source_pack_path"),
        source_pack_hash=_metadata_str(metadata, "source_pack_hash"),
        reviewed_seed_gate_status=_metadata_str(metadata, "reviewed_seed_gate_status"),
        reviewed_seed_gate_path=_metadata_str(metadata, "reviewed_seed_gate_path"),
        reviewed_seed_gate_hash=_metadata_str(metadata, "reviewed_seed_gate_hash"),
        reviewed_seed_profile_review_hash=_metadata_str(metadata, "reviewed_seed_profile_review_hash"),
        reviewed_seed_profile_promotion_id=_metadata_str(metadata, "reviewed_seed_profile_promotion_id"),
        reviewed_seed_admin_profile_pack_hash=_metadata_str(metadata, "reviewed_seed_admin_profile_pack_hash"),
        reviewed_seed_review_ids=_metadata_str_list(metadata, "reviewed_seed_review_ids"),
        obligation_count=len(obligations),
        submission_count=len(submissions),
        settlement_requirement_count=len(settlement_requirements),
        finding_count=len(_dedupe_admin_findings(findings)),
        high_count=sum(1 for finding in _dedupe_admin_findings(findings) if finding.severity == "high"),
        medium_count=sum(1 for finding in _dedupe_admin_findings(findings) if finding.severity == "medium"),
        low_count=sum(1 for finding in _dedupe_admin_findings(findings) if finding.severity == "low"),
        obligations=sorted(obligations, key=lambda item: item.obligation_id),
        submissions=sorted(submissions, key=lambda item: item.submission_id),
        settlement_requirements=settlement_requirements,
        findings=_dedupe_admin_findings(findings),
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )
    _write_admin_obligation_outputs(result, output_path, json_path)
    return result


def generate_settlement_binder(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceSettlementBinderResult:
    """Bind budget ledger rows to evidence, proof, approval, and source-hash review state."""

    workspace = Path(root)
    ledger_path = workspace / "state" / "budget-ledger.json"
    integrity = generate_workspace_budget_ledger(workspace)
    warnings: list[str] = list(integrity.warnings)
    if integrity.status == "not_configured":
        result = WorkspaceSettlementBinderResult(
            root=str(workspace),
            status="not_configured",
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
            warnings=warnings,
        )
        _write_settlement_binder_outputs(result, output_path, json_path)
        return result

    try:
        ledger_items = load_budget_ledger(ledger_path)
    except Exception:
        ledger_items = []

    binder_findings = list(integrity.findings)
    for item in ledger_items:
        binder_findings.extend(_settlement_source_findings(workspace, item, ledger_path))

    findings_by_ledger: dict[str, list[BudgetLedgerFinding]] = {}
    for finding in binder_findings:
        if finding.ledger_id:
            findings_by_ledger.setdefault(finding.ledger_id, []).append(finding)
    items = [
        SettlementBinderItem(
            ledger_id=item.ledger_id,
            date=item.date,
            vendor=item.vendor,
            amount=item.amount,
            currency=item.currency,
            category=item.category,
            proof_type=item.proof_type,
            approval_reference=item.approval_reference,
            evidence_ids=item.evidence_ids,
            evidence_count=len(item.evidence_ids),
            source_file=item.source_file,
            source_hash=item.source_hash,
            review_status=item.review_status,
            finding_codes=sorted({finding.code for finding in findings_by_ledger.get(item.ledger_id, [])}),
            risk_flags=item.risk_flags,
        )
        for item in ledger_items
    ]
    result = WorkspaceSettlementBinderResult(
        root=str(workspace),
        status=_status_from_budget_findings(binder_findings),
        item_count=len(items),
        linked_evidence_count=integrity.linked_evidence_count,
        finding_count=len(_dedupe_budget_findings(binder_findings)),
        high_count=sum(1 for finding in _dedupe_budget_findings(binder_findings) if finding.severity == "high"),
        medium_count=sum(1 for finding in _dedupe_budget_findings(binder_findings) if finding.severity == "medium"),
        low_count=sum(1 for finding in _dedupe_budget_findings(binder_findings) if finding.severity == "low"),
        items=sorted(items, key=lambda item: item.ledger_id),
        findings=_dedupe_budget_findings(binder_findings),
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=warnings,
    )
    _write_settlement_binder_outputs(result, output_path, json_path)
    return result


def review_admin_change_ledger(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> AdminChangeLedgerResult:
    """Review supplied agreement/change/approval ledger records without mutating project state."""

    workspace = Path(root)
    path = workspace / ADMIN_CHANGE_LEDGER_PATH
    warnings: list[str] = []
    findings: list[AdminFinding] = []
    changes = _load_changes(path, warnings)

    if not path.exists():
        result = _change_result(workspace, "not_configured", [], [], warnings, output_path, json_path)
        _write_change_outputs(result, output_path, json_path)
        return result

    for change in changes:
        findings.extend(_change_findings(workspace, change, path))
        if change.decision not in {"approved", "rejected", "needs_review", "deferred", "superseded"}:
            findings.append(
                _admin_finding(
                    "admin_change_unknown_decision",
                    "medium",
                    f"Change `{change.change_id}` has unknown decision `{change.decision}`.",
                    change_id=change.change_id,
                    path=path,
                    suggested_action="Use approved, rejected, needs_review, deferred, or superseded.",
                )
            )
        if _change_referenced_in_reports(workspace, change.change_id) and change.decision != "approved":
            findings.append(
                _admin_finding(
                    "admin_change_unapproved_referenced",
                    "high",
                    f"Unapproved change `{change.change_id}` appears to be referenced by a report draft.",
                    change_id=change.change_id,
                    path=workspace / "reports",
                    suggested_action="Do not use changed KPI/budget/period values in reports until the supplied change record is approved.",
                )
            )

    result = _change_result(workspace, _status_from_admin_findings(findings), changes, findings, warnings, output_path, json_path)
    _write_change_outputs(result, output_path, json_path)
    return result


def review_admin_calendar(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    today: date | None = None,
) -> AdminCalendarResult:
    """Review admin obligation due dates and project-goals deadline links."""

    workspace = Path(root)
    current_date = today or date.today()
    warnings: list[str] = []
    obligations = _load_obligations(workspace / ADMIN_OBLIGATIONS_PATH, warnings)
    goals = _load_goals(workspace)
    deadline_ids = {deadline.deadline_id for deadline in goals.deadlines}
    deadlines_by_id = {deadline.deadline_id: deadline for deadline in goals.deadlines}
    findings: list[AdminFinding] = []
    linked_count = 0
    due_soon_count = 0
    overdue_count = 0

    if not obligations:
        findings.append(
            _admin_finding(
                "admin_calendar_obligations_missing",
                "medium",
                "No admin obligations were found for calendar review.",
                path=workspace / ADMIN_OBLIGATIONS_PATH,
                suggested_action="Run admin-obligations-init before reviewing admin deadline links.",
            )
        )

    for obligation in obligations:
        if obligation.linked_deadline_id:
            if obligation.linked_deadline_id in deadline_ids:
                linked_count += 1
            else:
                findings.append(
                    _admin_finding(
                        "admin_calendar_deadline_missing",
                        "medium",
                        f"Admin obligation `{obligation.obligation_id}` links missing deadline `{obligation.linked_deadline_id}`.",
                        obligation_id=obligation.obligation_id,
                        path=workspace / "state" / "project-goals.json",
                        suggested_action="Add the linked ProjectDeadline or remove the stale deadline link.",
                    )
                )
        else:
            findings.append(
                _admin_finding(
                    "admin_calendar_deadline_link_missing",
                    "low",
                    f"Admin obligation `{obligation.obligation_id}` is not linked to a project deadline.",
                    obligation_id=obligation.obligation_id,
                    path=workspace / ADMIN_OBLIGATIONS_PATH,
                    suggested_action="Link local reporting, settlement, or performance obligations to project-goals deadlines after human review.",
                )
            )
        due_date = obligation.due_date
        if due_date is None and obligation.linked_deadline_id in deadlines_by_id:
            due_date = deadlines_by_id[obligation.linked_deadline_id].due_date
        if due_date:
            if due_date < current_date:
                overdue_count += 1
                findings.append(
                    _admin_finding(
                        "admin_calendar_overdue",
                        "high",
                        f"Admin obligation `{obligation.obligation_id}` is overdue: {due_date.isoformat()}.",
                        obligation_id=obligation.obligation_id,
                        path=workspace / ADMIN_OBLIGATIONS_PATH,
                        suggested_action="Review submission/approval evidence and update the local obligation status.",
                    )
                )
            elif due_date <= current_date + timedelta(days=14):
                due_soon_count += 1
                findings.append(
                    _admin_finding(
                        "admin_calendar_due_soon",
                        "medium",
                        f"Admin obligation `{obligation.obligation_id}` is due soon: {due_date.isoformat()}.",
                        obligation_id=obligation.obligation_id,
                        path=workspace / ADMIN_OBLIGATIONS_PATH,
                        suggested_action="Prepare local evidence, draft, and approval records before the due date.",
                    )
                )

    findings = _dedupe_admin_findings(findings)
    result = AdminCalendarResult(
        root=str(workspace),
        status=_status_from_admin_findings(findings),
        obligation_count=len(obligations),
        linked_deadline_count=linked_count,
        due_soon_count=due_soon_count,
        overdue_count=overdue_count,
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        obligations=sorted(obligations, key=lambda item: item.obligation_id),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )
    _write_calendar_outputs(result, output_path, json_path)
    return result


def render_admin_obligations_markdown(result: AdminObligationGraphResult) -> str:
    lines = [
        "# Admin Obligation Graph",
        "",
        "> Local operating projection only. This graph helps track Korean R&D admin evidence, submissions, approvals, and settlement candidates; it does not hardcode or certify official IRIS/NTIS/RCMS/Ezbaro rules.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Profile | {_escape(result.profile_id or '-')} |",
        f"| Profile status | {_escape(result.profile_status or '-')} |",
        f"| Seed mode | {_escape(result.seed_mode or '-')} |",
        f"| Source pack hash | `{_escape(result.source_pack_hash or '-')}` |",
        f"| Reviewed-seed gate | {_escape(result.reviewed_seed_gate_status or '-')} |",
        f"| Reviewed-seed gate hash | `{_escape(result.reviewed_seed_gate_hash or '-')}` |",
        f"| Reviewed-seed profile review hash | `{_escape(result.reviewed_seed_profile_review_hash or '-')}` |",
        f"| Reviewed-seed promotion ID | {_escape(result.reviewed_seed_profile_promotion_id or '-')} |",
        f"| Reviewed-seed admin pack hash | `{_escape(result.reviewed_seed_admin_profile_pack_hash or '-')}` |",
        f"| Reviewed-seed review receipts | {_escape(', '.join(result.reviewed_seed_review_ids) or '-')} |",
        f"| Obligations | {result.obligation_count} |",
        f"| Submissions | {result.submission_count} |",
        f"| Settlement requirements | {result.settlement_requirement_count} |",
        f"| Findings | {result.finding_count} |",
        f"| High | {result.high_count} |",
        f"| Medium | {result.medium_count} |",
        f"| Low | {result.low_count} |",
        "",
        "## Obligations",
        "",
        "| ID | Type | Source | Status | Due Date | Approval | Evidence Types | Deadline | Title |",
        "|---|---|---|---|---|---:|---|---|---|",
    ]
    if not result.obligations:
        lines.append("| - | - | - | missing | - | - | - | - | Run admin-obligations-init. |")
    for item in result.obligations:
        lines.append(
            "| {id} | {kind} | {source} | {status} | {due} | {approval} | {evidence} | {deadline} | {title} |".format(
                id=_escape(item.obligation_id),
                kind=_escape(item.obligation_type),
                source=_escape(item.source_system),
                status=_escape(item.status),
                due=_escape(item.due_date.isoformat() if item.due_date else "-"),
                approval="yes" if item.required_approval else "no",
                evidence=_escape(", ".join(item.required_evidence_types) or "-"),
                deadline=_escape(item.linked_deadline_id or "-"),
                title=_escape(item.title),
            )
        )
    lines.extend(["", "## Submissions", "", "| ID | Obligation | Status | Artifact | Approval | Evidence IDs |", "|---|---|---|---|---|---|"])
    if not result.submissions:
        lines.append("| - | - | missing | - | - | - |")
    for item in result.submissions:
        lines.append(
            "| {id} | {obligation} | {status} | `{artifact}` | {approval} | {evidence} |".format(
                id=_escape(item.submission_id),
                obligation=_escape(item.obligation_id),
                status=_escape(item.status),
                artifact=_escape(item.artifact_path or "-"),
                approval=_escape(item.approval_id or "-"),
                evidence=_escape(", ".join(item.evidence_ids) or "-"),
            )
        )
    lines.extend(["", "## Findings", "", "| Severity | Code | Ref | Message | Suggested Action |", "|---|---|---|---|---|"])
    if not result.findings:
        lines.append("| ok | admin_obligations_ready | - | No admin obligation findings detected. | Keep official-source review current. |")
    for finding in result.findings:
        ref = finding.obligation_id or finding.submission_id or finding.ledger_id or finding.change_id or "-"
        lines.append(f"| {_escape(finding.severity)} | {_escape(finding.code)} | {_escape(ref)} | {_escape(finding.message)} | {_escape(finding.suggested_action or '-')} |")
    lines.append("")
    return "\n".join(lines)


def render_settlement_binder_markdown(result: WorkspaceSettlementBinderResult) -> str:
    lines = [
        "# Settlement Evidence Binder",
        "",
        "> Settlement binder projection only. This binds local budget ledger rows to proof, approval, evidence, and source-hash review state; it does not decide cost eligibility or agency compliance.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Items | {result.item_count} |",
        f"| Linked evidence | {result.linked_evidence_count} |",
        f"| Findings | {result.finding_count} |",
        "",
        "## Binder Rows",
        "",
        "| Ledger | Date | Vendor | Amount | Category | Proof | Approval | Evidence | Status | Findings |",
        "|---|---|---|---:|---|---|---|---|---|---|",
    ]
    if not result.items:
        lines.append("| - | - | - | - | - | - | - | - | not_configured | - |")
    for item in result.items:
        lines.append(
            "| {ledger} | {date} | {vendor} | {amount} | {category} | {proof} | {approval} | {evidence} | {status} | {findings} |".format(
                ledger=_escape(item.ledger_id),
                date=_escape(item.date or "-"),
                vendor=_escape(item.vendor or "-"),
                amount=_format_amount(item.amount),
                category=_escape(item.category or "-"),
                proof=_escape(item.proof_type or "-"),
                approval=_escape(item.approval_reference or "-"),
                evidence=_escape(", ".join(item.evidence_ids) or "-"),
                status=_escape(item.review_status),
                findings=_escape(", ".join(item.finding_codes) or "-"),
            )
        )
    lines.extend(["", "## Findings", "", "| Severity | Code | Ledger | Message | Suggested Action |", "|---|---|---|---|---|"])
    if not result.findings:
        lines.append("| ok | settlement_binder_ready | - | No settlement binder findings detected. | Continue human settlement review. |")
    for finding in result.findings:
        lines.append(f"| {_escape(finding.severity)} | {_escape(finding.code)} | {_escape(finding.ledger_id or '-')} | {_escape(finding.message)} | {_escape(finding.suggested_action or '-')} |")
    lines.append("")
    return "\n".join(lines)


def render_admin_change_ledger_markdown(result: AdminChangeLedgerResult) -> str:
    lines = [
        "# Admin Change Ledger",
        "",
        "> Supplied change/approval ledger only. This tracks local agreement, KPI, budget, period, and submission changes; it does not approve changes or mutate project state.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Changes | {result.change_count} |",
        f"| Approved | {result.approved_count} |",
        f"| Pending | {result.pending_count} |",
        f"| Rejected | {result.rejected_count} |",
        f"| Findings | {result.finding_count} |",
        "",
        "## Changes",
        "",
        "| Change | Type | Target | Decision | Reviewer | Approval | Status | Risk Flags |",
        "|---|---|---|---|---|---|---|---|",
    ]
    if not result.changes:
        lines.append("| - | - | - | not_configured | - | - | - | - |")
    for change in result.changes:
        lines.append(
            "| {change} | {kind} | {target} | {decision} | {reviewer} | {approval} | {status} | {risks} |".format(
                change=_escape(change.change_id),
                kind=_escape(change.change_type),
                target=_escape(change.target_id),
                decision=_escape(change.decision),
                reviewer=_escape(change.reviewer or "-"),
                approval=_escape(change.approval_id or "-"),
                status=_escape(change.status),
                risks=_escape(", ".join(change.risk_flags) or "-"),
            )
        )
    lines.extend(["", "## Findings", "", "| Severity | Code | Change | Message | Suggested Action |", "|---|---|---|---|---|"])
    if not result.findings:
        lines.append("| ok | admin_change_ledger_ready | - | No admin change ledger findings detected. | Keep change records hash-bound and human-reviewed. |")
    for finding in result.findings:
        lines.append(f"| {_escape(finding.severity)} | {_escape(finding.code)} | {_escape(finding.change_id or '-')} | {_escape(finding.message)} | {_escape(finding.suggested_action or '-')} |")
    lines.append("")
    return "\n".join(lines)


def render_admin_calendar_markdown(result: AdminCalendarResult) -> str:
    lines = [
        "# Admin Calendar Review",
        "",
        "> Local deadline projection only. This links admin obligations to project-goals deadlines; it does not encode official submission schedules.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Obligations | {result.obligation_count} |",
        f"| Linked deadlines | {result.linked_deadline_count} |",
        f"| Due soon | {result.due_soon_count} |",
        f"| Overdue | {result.overdue_count} |",
        f"| Findings | {result.finding_count} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Obligation | Message | Suggested Action |",
        "|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | admin_calendar_ready | - | No admin calendar findings detected. | Keep local deadlines current. |")
    for finding in result.findings:
        lines.append(f"| {_escape(finding.severity)} | {_escape(finding.code)} | {_escape(finding.obligation_id or '-')} | {_escape(finding.message)} | {_escape(finding.suggested_action or '-')} |")
    lines.append("")
    return "\n".join(lines)


def render_admin_obligation_profile_pack_review_markdown(result: AdminObligationProfilePackReviewResult) -> str:
    lines = [
        "# Admin Obligation Profile Pack Review",
        "",
        "> Profile pack review projection only. Seeded obligations remain local candidates until current official sources and human verification support promotion.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Templates root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Profile | {_escape(result.profile_id)} |",
        f"| Profile status | {_escape(result.profile_status or '-')} |",
        f"| Pack path | `{_escape(result.pack_path or '-')}` |",
        f"| Sources | {result.source_record_count} |",
        f"| Verified sources | {result.verified_source_count} |",
        f"| Needs-review sources | {result.needs_review_source_count} |",
        f"| Obligations | {result.obligation_count} |",
        f"| Submissions | {result.submission_count} |",
        f"| Settlement requirements | {result.settlement_requirement_count} |",
        f"| Findings | {result.finding_count} |",
        "",
        "## Obligations",
        "",
        "| ID | Type | Source | Status | Evidence Types | Risk Flags | Title |",
        "|---|---|---|---|---|---|---|",
    ]
    obligations = result.pack.obligations if result.pack else []
    if not obligations:
        lines.append("| - | - | - | missing | - | - | Add an admin-obligations.json profile pack. |")
    for item in obligations:
        lines.append(
            "| {id} | {kind} | {source} | {status} | {evidence} | {risks} | {title} |".format(
                id=_escape(item.obligation_id),
                kind=_escape(item.obligation_type),
                source=_escape(item.source_system),
                status=_escape(item.status),
                evidence=_escape(", ".join(item.required_evidence_types) or "-"),
                risks=_escape(", ".join(item.risk_flags) or "-"),
                title=_escape(item.title),
            )
        )
    lines.extend(["", "## Findings", "", "| Severity | Code | Ref | Message | Suggested Action |", "|---|---|---|---|---|"])
    if not result.findings:
        lines.append("| ok | admin_profile_pack_ready | - | No profile pack findings detected. | Keep source verification current before promotion. |")
    for finding in result.findings:
        ref = finding.obligation_id or finding.submission_id or finding.ledger_id or finding.change_id or "-"
        lines.append(f"| {_escape(finding.severity)} | {_escape(finding.code)} | {_escape(ref)} | {_escape(finding.message)} | {_escape(finding.suggested_action or '-')} |")
    lines.append("")
    return "\n".join(lines)


def _admin_obligation_seed_pack(
    profile_id: str,
    templates_root: str | Path | None,
) -> tuple[AdminObligationProfilePack, Path | None, list[str]]:
    warnings: list[str] = []
    pack_path = _admin_obligation_profile_pack_path(profile_id, templates_root)
    if pack_path.exists():
        profile = _load_template_profile(pack_path.parent)
        sources = _load_template_sources(pack_path.parent)
        try:
            pack = _load_admin_obligation_profile_pack_payload(pack_path, profile_id, profile.status if profile else None, sources, warnings)
            return pack, pack_path, warnings
        except Exception as exc:
            warnings.append(f"admin_profile_pack_unreadable:{profile_id}:{exc}")
    return (
        AdminObligationProfilePack(
            profile_id=profile_id,
            status="needs_review",
            profile_status="needs_review",
            obligations=_starter_obligations(profile_id),
            notes="Generic local admin obligation starter. Verify current agency/program rules before official use.",
            warnings=warnings,
        ),
        None,
        warnings,
    )


def _reviewed_seed_pack(
    workspace: Path,
    profile_id: str,
    seed_pack: AdminObligationProfilePack,
    seed_path: Path | None,
    templates_root: str | Path | None,
    gate_path: str | Path | None,
) -> tuple[AdminObligationProfilePack, dict[str, Any], list[str]]:
    if seed_path is None:
        raise ValueError("reviewed_seed requires a configured admin obligation profile pack")

    from .admin_profile_pack_gate import generate_admin_profile_pack_promotion_gate, load_admin_profile_pack_promotion_gate
    from .admin_profile_pack_reviews import summarize_admin_profile_pack_reviews

    if gate_path is not None:
        requested_gate_path = Path(gate_path)
        gate_json_path = requested_gate_path if requested_gate_path.is_absolute() else workspace / requested_gate_path
    else:
        gate_json_path = workspace / "state" / "admin-profile-pack-gate.json"
    if gate_path is None:
        gate = generate_admin_profile_pack_promotion_gate(
            workspace,
            profile_id=profile_id,
            output_path=workspace / "reports" / "admin-profile-pack-gate.md",
            json_path=gate_json_path,
            templates_root=templates_root,
        )
    else:
        if not gate_json_path.exists():
            raise ValueError(f"reviewed seed gate artifact not found: {gate_json_path}")
        gate = load_admin_profile_pack_promotion_gate(gate_json_path)
        current_gate = generate_admin_profile_pack_promotion_gate(workspace, profile_id=profile_id, templates_root=templates_root)
        if _gate_signature(gate) != _gate_signature(current_gate):
            raise ValueError("reviewed seed gate artifact is stale against current profile/admin pack review state")

    if not gate.can_use_reviewed_seed:
        raise ValueError(f"admin profile-pack gate is not reviewed-seed eligible: {gate.status}")

    review_summary = summarize_admin_profile_pack_reviews(workspace, profile_id, templates_root=templates_root)
    current_review_ids = [
        record.review_id
        for record in review_summary.records
        if review_summary.profile_pack_hash is not None
        and _normalize_hash(record.profile_pack_hash) == _normalize_hash(review_summary.profile_pack_hash)
        and record.decision in {"accepted", "accepted_risk"}
    ]
    pack_hash = _sha256_file(seed_path)
    reviewed_pack = seed_pack.model_copy(
        update={
            "status": "reviewed_seed_candidate",
            "notes": (seed_pack.notes or "Admin obligation profile pack copied as a reviewed local seed candidate.")
            + " Reviewed-seed mode remains local and does not certify official agency compliance.",
            "obligations": [_reviewed_seed_obligation(item) for item in seed_pack.obligations],
            "submissions": [_reviewed_seed_submission(item) for item in seed_pack.submissions],
            "settlement_requirements": [_reviewed_seed_settlement_requirement(item) for item in seed_pack.settlement_requirements],
            "warnings": _unique(seed_pack.warnings + ["reviewed_seed_candidate", "official_submission_requires_human_approval"]),
        }
    )
    metadata = {
        "seed_mode": "reviewed_seed",
        "reviewed_seed_gate_status": gate.status,
        "reviewed_seed_gate_path": str(gate_json_path),
        "reviewed_seed_gate_hash": _sha256_file(gate_json_path),
        "reviewed_seed_profile_review_hash": gate.profile_review_hash,
        "reviewed_seed_profile_promotion_id": gate.latest_profile_promotion_id,
        "reviewed_seed_admin_profile_pack_hash": pack_hash,
        "reviewed_seed_review_ids": sorted(set(current_review_ids)),
        "source_pack_hash": pack_hash,
    }
    return reviewed_pack, metadata, ["reviewed_seed_mode_enabled"]


def _admin_obligation_profile_pack_path(profile_id: str, templates_root: str | Path | None) -> Path:
    root = Path(templates_root) if templates_root is not None else default_agency_templates_root()
    return root / profile_id / "admin-obligations.json"


def _load_admin_obligation_profile_pack_payload(
    pack_path: Path,
    profile_id: str,
    profile_status: str | None,
    sources,
    warnings: list[str],
) -> AdminObligationProfilePack:
    payload = json.loads(pack_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("admin obligation profile pack must be a JSON object")
    payload.setdefault("profile_id", profile_id)
    payload.setdefault("status", "needs_review")
    payload.setdefault("profile_status", profile_status)
    pack = AdminObligationProfilePack.model_validate(payload)
    if pack.profile_id != profile_id:
        warnings.append(f"admin_profile_pack_profile_mismatch:{pack.profile_id}!={profile_id}")
    return _guarded_admin_profile_pack(pack, profile_id, profile_status, sources)


def _guarded_admin_profile_pack(
    pack: AdminObligationProfilePack,
    requested_profile_id: str,
    profile_status: str | None,
    sources,
) -> AdminObligationProfilePack:
    source_ids = {source.source_id for source in sources}
    referenced_sources = [source for source in sources if not pack.source_record_ids or source.source_id in set(pack.source_record_ids)]
    verified = bool(referenced_sources) and all(source.review_status == "verified" and source.verified_by for source in referenced_sources)
    trusted = pack.status == "verified" and profile_status == "verified" and verified
    status = "verified" if trusted else "needs_review"
    guard_risks = [] if trusted else ["official_source_needs_review"]
    obligations = [
        item.model_copy(
            update={
                "profile_id": requested_profile_id,
                "status": item.status if trusted else "needs_review",
                "risk_flags": _unique(item.risk_flags + guard_risks),
            }
        )
        for item in pack.obligations
    ]
    submissions = [
        item.model_copy(update={"status": item.status if trusted else "needs_review", "risk_flags": _unique(item.risk_flags + guard_risks)})
        for item in pack.submissions
    ]
    settlement_requirements = [
        item.model_copy(update={"status": item.status if trusted else "needs_review", "risk_flags": _unique(item.risk_flags + guard_risks)})
        for item in pack.settlement_requirements
    ]
    warnings = list(pack.warnings)
    for source_id in pack.source_record_ids:
        if source_id not in source_ids:
            warnings.append(f"admin_profile_pack_source_missing:{source_id}")
    return pack.model_copy(
        update={
            "profile_id": requested_profile_id,
            "status": status,
            "profile_status": profile_status,
            "obligations": obligations,
            "submissions": submissions,
            "settlement_requirements": settlement_requirements,
            "warnings": _unique(warnings),
        }
    )


def _reviewed_seed_obligation(item: AdminObligation) -> AdminObligation:
    return item.model_copy(update={"status": "accepted_risk", "risk_flags": _reviewed_seed_risk_flags(item.risk_flags)})


def _reviewed_seed_submission(item: AdminSubmission) -> AdminSubmission:
    return item.model_copy(update={"status": "accepted_risk", "risk_flags": _reviewed_seed_risk_flags(item.risk_flags)})


def _reviewed_seed_settlement_requirement(item: SettlementEvidenceRequirement) -> SettlementEvidenceRequirement:
    return item.model_copy(update={"status": "accepted_risk", "risk_flags": _reviewed_seed_risk_flags(item.risk_flags)})


def _reviewed_seed_risk_flags(flags: list[str]) -> list[str]:
    retained = [flag for flag in flags if flag != "official_source_needs_review"]
    return _unique(retained + ["reviewed_seed_candidate", "official_submission_requires_human_approval"])


def _admin_profile_pack_findings(
    profile_id: str,
    pack: AdminObligationProfilePack,
    pack_path: Path,
    profile_status: str | None,
    sources,
) -> list[AdminFinding]:
    findings: list[AdminFinding] = []
    sources_by_id = {source.source_id: source for source in sources}
    if pack.profile_id != profile_id:
        findings.append(
            _admin_finding(
                "admin_profile_pack_profile_mismatch",
                "high",
                f"Admin obligation pack profile_id `{pack.profile_id}` does not match requested `{profile_id}`.",
                path=pack_path,
                suggested_action="Fix the profile_id before using the pack for workspace initialization.",
            )
        )
    if pack.status != "verified":
        findings.append(
            _admin_finding(
                "admin_profile_pack_needs_review",
                "medium",
                f"Admin obligation pack `{profile_id}` is `{pack.status}`.",
                path=pack_path,
                suggested_action="Keep seeded obligations as local candidates until official-source review and human promotion are complete.",
            )
        )
    if not pack.obligations:
        findings.append(
            _admin_finding(
                "admin_profile_pack_obligations_missing",
                "medium",
                f"Admin obligation pack `{profile_id}` contains no obligations.",
                path=pack_path,
                suggested_action="Add explicit needs-review obligation rows or use the generic starter.",
            )
        )
    if not pack.source_record_ids:
        findings.append(
            _admin_finding(
                "admin_profile_pack_source_records_missing",
                "medium",
                f"Admin obligation pack `{profile_id}` has no source_record_ids.",
                path=pack_path,
                suggested_action="Bind the pack to profile source records before treating it as source-backed.",
            )
        )
    for source_id in pack.source_record_ids:
        source = sources_by_id.get(source_id)
        if source is None:
            findings.append(
                _admin_finding(
                    "admin_profile_pack_source_record_missing",
                    "high",
                    f"Admin obligation pack references missing source record `{source_id}`.",
                    path=pack_path,
                    suggested_action="Add the source record or remove the stale source_record_id.",
                )
            )
        elif source.review_status != "verified":
            findings.append(
                _admin_finding(
                    "admin_profile_pack_source_needs_review",
                    "medium",
                    f"Profile source `{source_id}` is `{source.review_status}`.",
                    path=pack_path.parent / "profile-sources.json",
                    suggested_action="Keep profile-driven admin obligations as needs_review until this source is human-verified.",
                )
            )
    if profile_status != "verified":
        for obligation in pack.obligations:
            if obligation.status != "needs_review":
                findings.append(
                    _admin_finding(
                        "admin_profile_pack_obligation_not_guarded",
                        "high",
                        f"Admin obligation `{obligation.obligation_id}` is not guarded as needs_review while the profile is unverified.",
                        obligation_id=obligation.obligation_id,
                        path=pack_path,
                        suggested_action="Do not seed non-review obligations from an unverified profile pack.",
                    )
                )
    for obligation in pack.obligations:
        if not obligation.required_evidence_types:
            findings.append(
                _admin_finding(
                    "admin_profile_pack_obligation_evidence_types_missing",
                    "low",
                    f"Admin obligation `{obligation.obligation_id}` has no required_evidence_types.",
                    obligation_id=obligation.obligation_id,
                    path=pack_path,
                    suggested_action="Add evidence type hints so review and binder workflows can connect the obligation.",
                )
            )
        if "official_source_needs_review" not in obligation.risk_flags and profile_status != "verified":
            findings.append(
                _admin_finding(
                    "admin_profile_pack_official_source_guard_missing",
                    "high",
                    f"Admin obligation `{obligation.obligation_id}` lacks official_source_needs_review guard.",
                    obligation_id=obligation.obligation_id,
                    path=pack_path,
                    suggested_action="Retain official_source_needs_review until the profile pack is promoted.",
                )
            )
    return findings


def _load_template_profile(profile_dir: Path) -> ProjectProfile | None:
    path = profile_dir / "project-profile.json"
    if not path.exists():
        return None
    try:
        return load_project_profile(path)
    except Exception:
        return None


def _load_template_sources(profile_dir: Path):
    try:
        return load_profile_sources(profile_dir / "profile-sources.json")
    except Exception:
        return []


def _starter_obligations(profile_id: str) -> list[AdminObligation]:
    return [
        AdminObligation(
            obligation_id="ADM-AGREEMENT-001",
            title="Agreement and change request evidence candidate",
            obligation_type="agreement_change",
            profile_id=profile_id,
            source_system="IRIS",
            required_evidence_types=["change_request"],
            notes="IRIS agreement/change workflows vary by program; verify current manual and agency guidance.",
            risk_flags=["official_source_needs_review"],
        ),
        AdminObligation(
            obligation_id="ADM-BUDGET-001",
            title="Research expense ledger and proof evidence candidate",
            obligation_type="budget_evidence",
            profile_id=profile_id,
            source_system="GAIA/RCMS/Ezbaro",
            required_evidence_types=["budget_evidence"],
            notes="Use as a local binder for proof, approval, and evidence IDs; do not infer cost eligibility.",
            risk_flags=["official_source_needs_review"],
        ),
        AdminObligation(
            obligation_id="ADM-SETTLEMENT-001",
            title="Settlement readiness candidate",
            obligation_type="settlement",
            profile_id=profile_id,
            source_system="IRIS/GAIA",
            required_evidence_types=["budget_evidence"],
            notes="Settlement requirements differ by program and system. Keep this as needs_review.",
            risk_flags=["official_source_needs_review"],
        ),
        AdminObligation(
            obligation_id="ADM-REPORT-001",
            title="Periodic report submission candidate",
            obligation_type="reporting",
            profile_id=profile_id,
            source_system="IRIS",
            required_evidence_types=["plan_goal", "kpi", "milestone", "outcome"],
            notes="Link monthly/interim/annual/final report drafts after human schedule review.",
            risk_flags=["official_source_needs_review"],
        ),
        AdminObligation(
            obligation_id="ADM-PERFORMANCE-001",
            title="Performance registration candidate",
            obligation_type="performance_registration",
            profile_id=profile_id,
            source_system="NTIS/IRIS",
            required_evidence_types=["outcome"],
            notes="Performance fields should be profile-driven and verified before use.",
            risk_flags=["official_source_needs_review"],
        ),
        AdminObligation(
            obligation_id="ADM-EQUIPMENT-001",
            title="Research facilities and equipment admin candidate",
            obligation_type="equipment",
            profile_id=profile_id,
            source_system="IRIS",
            required_evidence_types=["budget_evidence"],
            notes="Equipment workflows and thresholds are not encoded; verify current official guidance.",
            risk_flags=["official_source_needs_review"],
        ),
    ]


def _load_obligations(path: Path, warnings: list[str]) -> list[AdminObligation]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = payload.get("obligations", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("admin obligations must be a list or object with obligations list")
        return [AdminObligation.model_validate(row) for row in rows]
    except Exception as exc:
        warnings.append(f"admin_obligations_unreadable:{exc}")
        return []


def _admin_obligation_metadata(path: Path, warnings: list[str]) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            return {}
        keys = {
            "seed_mode",
            "source_pack_path",
            "source_pack_hash",
            "reviewed_seed_gate_status",
            "reviewed_seed_gate_path",
            "reviewed_seed_gate_hash",
            "reviewed_seed_profile_review_hash",
            "reviewed_seed_profile_promotion_id",
            "reviewed_seed_admin_profile_pack_hash",
            "reviewed_seed_review_ids",
        }
        return {key: payload.get(key) for key in keys if key in payload}
    except Exception as exc:
        warnings.append(f"admin_obligation_metadata_unreadable:{exc}")
        return {}


def _reviewed_seed_metadata_findings(workspace: Path, obligations_path: Path, metadata: dict[str, Any]) -> list[AdminFinding]:
    if metadata.get("seed_mode") != "reviewed_seed":
        return []
    findings: list[AdminFinding] = []
    gate_path = _metadata_path(metadata, "reviewed_seed_gate_path", workspace)
    gate_hash = _metadata_str(metadata, "reviewed_seed_gate_hash")
    if gate_path is None or not gate_hash:
        findings.append(
            _admin_finding(
                "admin_reviewed_seed_gate_metadata_missing",
                "medium",
                "Reviewed-seed admin obligations are missing gate path or hash metadata.",
                path=obligations_path,
                suggested_action="Regenerate admin obligations with reviewed-seed mode after the promotion gate passes.",
            )
        )
    elif not gate_path.exists():
        findings.append(
            _admin_finding(
                "admin_reviewed_seed_gate_missing",
                "medium",
                f"Reviewed-seed gate artifact is missing: {gate_path}.",
                path=gate_path,
                suggested_action="Restore the gate artifact or regenerate reviewed-seed admin obligations.",
            )
        )
    elif _normalize_hash(_sha256_file(gate_path)) != _normalize_hash(gate_hash):
        findings.append(
            _admin_finding(
                "admin_reviewed_seed_gate_hash_mismatch",
                "high",
                "Reviewed-seed gate artifact hash no longer matches the recorded seed metadata.",
                path=gate_path,
                suggested_action="Re-run admin-profile-pack-gate and regenerate reviewed-seed admin obligations.",
            )
        )

    profile_review_hash = _metadata_str(metadata, "reviewed_seed_profile_review_hash")
    profile_review_path = workspace / "state" / "profile-review.json"
    if profile_review_hash and profile_review_path.exists() and _normalize_hash(_sha256_file(profile_review_path)) != _normalize_hash(profile_review_hash):
        findings.append(
            _admin_finding(
                "admin_reviewed_seed_profile_review_hash_mismatch",
                "high",
                "Current profile-review.json hash differs from the reviewed-seed metadata.",
                path=profile_review_path,
                suggested_action="Re-run profile review, profile promotion, admin-profile-pack-gate, and reviewed-seed initialization.",
            )
        )

    pack_path = _metadata_path(metadata, "source_pack_path", workspace)
    pack_hash = _metadata_str(metadata, "reviewed_seed_admin_profile_pack_hash") or _metadata_str(metadata, "source_pack_hash")
    if pack_hash and pack_path is not None and pack_path.exists() and _normalize_hash(_sha256_file(pack_path)) != _normalize_hash(pack_hash):
        findings.append(
            _admin_finding(
                "admin_reviewed_seed_profile_pack_hash_mismatch",
                "high",
                "Current admin profile-pack hash differs from the reviewed-seed metadata.",
                path=pack_path,
                suggested_action="Review the changed admin profile pack and regenerate reviewed-seed admin obligations if still appropriate.",
            )
        )
    if not _metadata_str_list(metadata, "reviewed_seed_review_ids"):
        findings.append(
            _admin_finding(
                "admin_reviewed_seed_review_receipts_missing",
                "medium",
                "Reviewed-seed metadata has no admin profile-pack review receipt IDs.",
                path=obligations_path,
                suggested_action="Record hash-bound admin profile-pack review receipts before relying on reviewed-seed obligations.",
            )
        )
    return findings


def _load_submissions(path: Path, warnings: list[str]) -> list[AdminSubmission]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = payload.get("submissions", payload.get("items", payload)) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("admin submissions must be a list or object with submissions list")
        return [AdminSubmission.model_validate(row) for row in rows]
    except Exception as exc:
        warnings.append(f"admin_submissions_unreadable:{exc}")
        return []


def _load_changes(path: Path, warnings: list[str]) -> list[AdminChangeRecord]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = payload.get("changes", payload.get("items", payload)) if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("admin change ledger must be a list or object with changes list")
        return [AdminChangeRecord.model_validate(row) for row in rows]
    except Exception as exc:
        warnings.append(f"admin_change_ledger_unreadable:{exc}")
        return []


def _combined_settlement_requirements(
    workspace: Path,
    obligations_path: Path,
    warnings: list[str],
) -> list[SettlementEvidenceRequirement]:
    requirements = _profile_settlement_requirements(obligations_path, warnings) + _settlement_requirements(workspace)
    by_id: dict[str, SettlementEvidenceRequirement] = {}
    for item in requirements:
        by_id.setdefault(item.requirement_id, item)
    return sorted(by_id.values(), key=lambda item: item.requirement_id)


def _profile_settlement_requirements(path: Path, warnings: list[str]) -> list[SettlementEvidenceRequirement]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = payload.get("settlement_requirements", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            raise ValueError("settlement_requirements must be a list")
        return [SettlementEvidenceRequirement.model_validate(row) for row in rows]
    except Exception as exc:
        warnings.append(f"admin_profile_settlement_requirements_unreadable:{exc}")
        return []


def _settlement_requirements(workspace: Path) -> list[SettlementEvidenceRequirement]:
    path = workspace / "state" / "budget-ledger.json"
    if not path.exists():
        return []
    try:
        items = load_budget_ledger(path)
    except Exception:
        return []
    return [
        SettlementEvidenceRequirement(
            requirement_id=f"SET-{item.ledger_id}",
            ledger_id=item.ledger_id,
            category=item.category,
            proof_type_required=True,
            approval_required=True,
            evidence_required=True,
            status="needs_review" if item.review_status != "accepted" else "accepted",
            risk_flags=item.risk_flags,
        )
        for item in sorted(items, key=lambda item: item.ledger_id)
    ]


def _settlement_source_findings(workspace: Path, item, ledger_path: Path) -> list[BudgetLedgerFinding]:
    findings: list[BudgetLedgerFinding] = []
    if not item.source_file or not item.source_hash:
        return findings
    source = Path(item.source_file)
    if not source.is_absolute():
        source = workspace / source
    if not source.exists():
        findings.append(
            BudgetLedgerFinding(
                code="settlement_binder_source_missing",
                severity="medium",
                message=f"Settlement binder item `{item.ledger_id}` source file is missing.",
                ledger_id=item.ledger_id,
                path=str(source),
                suggested_action="Restore the source ledger/proof artifact or update the ledger source reference.",
            )
        )
        return findings
    if _normalize_hash(_sha256_file(source)) != _normalize_hash(item.source_hash):
        findings.append(
            BudgetLedgerFinding(
                code="budget_ledger_source_hash_mismatch",
                severity="high",
                message=f"Settlement binder item `{item.ledger_id}` source hash no longer matches the referenced source file.",
                ledger_id=item.ledger_id,
                path=str(ledger_path),
                suggested_action="Re-import or re-review the budget ledger after source file changes.",
            )
        )
    return findings


def _load_profile(workspace: Path) -> ProjectProfile | None:
    path = workspace / "state" / "project-profile.json"
    if not path.exists():
        return None
    try:
        return load_project_profile(path)
    except Exception:
        return None


def _load_evidence(workspace: Path) -> list[EvidenceItem]:
    path = workspace / "state" / "evidence-index.json"
    if not path.exists():
        return []
    try:
        return load_evidence_index(path)
    except Exception:
        return []


def _load_approvals(workspace: Path):
    path = workspace / "state" / "approvals"
    if not path.exists():
        return []
    try:
        return load_approval_records(path)
    except Exception:
        return []


def _load_goals(workspace: Path) -> ProjectGoalsFile:
    path = workspace / "state" / "project-goals.json"
    if not path.exists():
        return ProjectGoalsFile()
    try:
        return ProjectGoalsFile.model_validate_json(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return ProjectGoalsFile(warnings=["project_goals_unreadable"])


def _evidence_by_type(evidence: list[EvidenceItem]) -> dict[str, list[EvidenceItem]]:
    result: dict[str, list[EvidenceItem]] = {}
    for item in evidence:
        result.setdefault(str(item.evidence_type), []).append(item)
    return result


def _submission_findings(workspace: Path, submission: AdminSubmission, evidence: list[EvidenceItem], approvals) -> list[AdminFinding]:
    findings: list[AdminFinding] = []
    evidence_ids = {item.evidence_id for item in evidence}
    approval_ids = {item.approval_id for item in approvals}
    if submission.artifact_path:
        artifact = Path(submission.artifact_path)
        if not artifact.is_absolute():
            artifact = workspace / artifact
        if not artifact.exists():
            findings.append(
                _admin_finding(
                    "admin_submission_artifact_missing",
                    "medium",
                    f"Admin submission `{submission.submission_id}` points to a missing artifact.",
                    submission_id=submission.submission_id,
                    path=artifact,
                    suggested_action="Restore the local artifact or update the submission record.",
                )
            )
    if submission.approval_id and submission.approval_id not in approval_ids:
        findings.append(
            _admin_finding(
                "admin_submission_approval_missing",
                "medium",
                f"Admin submission `{submission.submission_id}` references unknown approval `{submission.approval_id}`.",
                submission_id=submission.submission_id,
                path=workspace / "state" / "approvals",
                suggested_action="Record the supplied human approval or remove the stale approval ID.",
            )
        )
    if not submission.approval_id:
        findings.append(
            _admin_finding(
                "admin_submission_approval_unlinked",
                "medium",
                f"Admin submission `{submission.submission_id}` has no approval ID.",
                submission_id=submission.submission_id,
                path=workspace / ADMIN_SUBMISSIONS_PATH,
                suggested_action="Link a supplied human approval record before treating the submission as ready.",
            )
        )
    for evidence_id in submission.evidence_ids:
        if evidence_id not in evidence_ids:
            findings.append(
                _admin_finding(
                    "admin_submission_evidence_missing",
                    "high",
                    f"Admin submission `{submission.submission_id}` references unknown evidence `{evidence_id}`.",
                    submission_id=submission.submission_id,
                    path=workspace / "state" / "evidence-index.json",
                    suggested_action="Add the evidence record or remove the stale evidence ID.",
                )
            )
    if submission.status != "accepted":
        findings.append(
            _admin_finding(
                "admin_submission_not_accepted",
                "medium" if submission.status == "needs_review" else "high",
                f"Admin submission `{submission.submission_id}` is `{submission.status}`.",
                submission_id=submission.submission_id,
                path=workspace / ADMIN_SUBMISSIONS_PATH,
                suggested_action="Resolve the submission review state before official use.",
            )
        )
    return findings


def _change_findings(workspace: Path, change: AdminChangeRecord, ledger_path: Path) -> list[AdminFinding]:
    findings: list[AdminFinding] = []
    if change.decision == "approved":
        for field, value in {"reviewer": change.reviewer, "approved_at": change.approved_at, "approval_id": change.approval_id}.items():
            if not value:
                findings.append(
                    _admin_finding(
                        f"admin_change_approved_missing_{field}",
                        "medium",
                        f"Approved change `{change.change_id}` is missing {field}.",
                        change_id=change.change_id,
                        path=ledger_path,
                        suggested_action="Keep approved change records reviewer-, timestamp-, and approval-bound.",
                    )
                )
    elif change.decision in {"needs_review", "deferred"}:
        findings.append(
            _admin_finding(
                "admin_change_unresolved",
                "medium",
                f"Change `{change.change_id}` is not approved: {change.decision}.",
                change_id=change.change_id,
                path=ledger_path,
                suggested_action="Keep affected reports, budgets, and KPI values as draft until the change is approved.",
            )
        )
    elif change.decision == "rejected":
        findings.append(
            _admin_finding(
                "admin_change_rejected",
                "high",
                f"Change `{change.change_id}` was rejected.",
                change_id=change.change_id,
                path=ledger_path,
                suggested_action="Do not use rejected change values in reports, settlement, or performance registrations.",
            )
        )
    if change.target_path and change.target_hash:
        target = Path(change.target_path)
        if not target.is_absolute():
            target = workspace / target
        if not target.exists():
            findings.append(
                _admin_finding(
                    "admin_change_target_missing",
                    "medium",
                    f"Change `{change.change_id}` target path is missing.",
                    change_id=change.change_id,
                    path=target,
                    suggested_action="Restore the target artifact or update the change record.",
                )
            )
        elif _normalize_hash(_sha256_file(target)) != _normalize_hash(change.target_hash):
            findings.append(
                _admin_finding(
                    "admin_change_target_hash_mismatch",
                    "high",
                    f"Change `{change.change_id}` target artifact changed after the saved hash.",
                    change_id=change.change_id,
                    path=target,
                    suggested_action="Re-review the changed artifact and record a fresh supplied change decision.",
                )
            )
    return findings


def _change_referenced_in_reports(workspace: Path, change_id: str) -> bool:
    reports = workspace / "reports"
    if not reports.exists():
        return False
    for path in reports.glob("*.md"):
        try:
            if change_id in path.read_text(encoding="utf-8", errors="replace"):
                return True
        except Exception:
            continue
    return False


def _change_result(
    workspace: Path,
    status: str,
    changes: list[AdminChangeRecord],
    findings: list[AdminFinding],
    warnings: list[str],
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> AdminChangeLedgerResult:
    findings = _dedupe_admin_findings(findings)
    return AdminChangeLedgerResult(
        root=str(workspace),
        status=status,
        change_count=len(changes),
        approved_count=sum(1 for change in changes if change.decision == "approved"),
        pending_count=sum(1 for change in changes if change.decision in {"needs_review", "deferred"}),
        rejected_count=sum(1 for change in changes if change.decision == "rejected"),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        changes=sorted(changes, key=lambda item: item.change_id),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )


def _write_admin_obligation_outputs(result: AdminObligationGraphResult, output_path: str | Path | None, json_path: str | Path | None) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_admin_obligations_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _write_settlement_binder_outputs(result: WorkspaceSettlementBinderResult, output_path: str | Path | None, json_path: str | Path | None) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_settlement_binder_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _write_change_outputs(result: AdminChangeLedgerResult, output_path: str | Path | None, json_path: str | Path | None) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_admin_change_ledger_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _write_calendar_outputs(result: AdminCalendarResult, output_path: str | Path | None, json_path: str | Path | None) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_admin_calendar_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _write_admin_profile_pack_review_outputs(
    result: AdminObligationProfilePackReviewResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_admin_obligation_profile_pack_review_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _admin_finding(
    code: str,
    severity: str,
    message: str,
    obligation_id: str | None = None,
    submission_id: str | None = None,
    ledger_id: str | None = None,
    change_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> AdminFinding:
    return AdminFinding(
        code=code,
        severity=severity,
        message=message,
        obligation_id=obligation_id,
        submission_id=submission_id,
        ledger_id=ledger_id,
        change_id=change_id,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _dedupe_admin_findings(findings: list[AdminFinding]) -> list[AdminFinding]:
    seen: set[tuple[str, str, str | None, str | None, str | None, str | None, str | None]] = set()
    result: list[AdminFinding] = []
    for finding in findings:
        key = (finding.code, finding.message, finding.obligation_id, finding.submission_id, finding.ledger_id, finding.change_id, finding.path)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.code, item.message))


def _dedupe_budget_findings(findings: list[BudgetLedgerFinding]) -> list[BudgetLedgerFinding]:
    seen: set[tuple[str, str, str | None, str | None]] = set()
    result: list[BudgetLedgerFinding] = []
    for finding in findings:
        key = (finding.code, finding.message, finding.ledger_id, finding.path)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.code, item.message))


def _status_from_admin_findings(findings: list[AdminFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    return "ready"


def _status_from_budget_findings(findings: list[BudgetLedgerFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    return "ready"


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _format_amount(value: float | None) -> str:
    if value is None:
        return "-"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _normalize_hash(value: str) -> str:
    return value.replace("sha256:", "").strip().lower()


def _metadata_str(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) and value.strip() else None


def _metadata_str_list(metadata: dict[str, Any], key: str) -> list[str]:
    value = metadata.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _metadata_path(metadata: dict[str, Any], key: str, workspace: Path) -> Path | None:
    value = _metadata_str(metadata, key)
    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else workspace / path


def _gate_signature(gate) -> tuple[Any, ...]:
    return (
        gate.status,
        gate.can_use_reviewed_seed,
        gate.profile_id,
        gate.profile_review_hash,
        gate.latest_profile_promotion_id,
        gate.admin_profile_pack_status,
        gate.admin_profile_pack_path,
        gate.admin_profile_pack_review_status,
        gate.admin_profile_pack_review_target_count,
        gate.admin_profile_pack_reviewed_target_count,
        gate.high_count,
        gate.medium_count,
    )


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
