from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .approval import load_approval_records
from .bibliography import load_bibliography_index
from .bibliography_integrity import extract_markdown_citation_keys
from .bibliography_review import load_bibliography_review_records
from .budget_ledger import generate_workspace_budget_ledger, load_budget_ledger
from .citation_support import generate_workspace_citation_support_integrity, load_citation_support_records
from .evidence_index import load_evidence_index
from .models import (
    ApprovalRecord,
    BibliographyEntry,
    BibliographyReviewRecord,
    BudgetLedgerItem,
    CitationSupportRecord,
    EvidenceItem,
    ProfileSource,
    ResearchClaim,
    WorkspaceTraceEdge,
    WorkspaceTraceFinding,
    WorkspaceTraceNode,
    WorkspaceTraceResult,
)
from .profile_sources import load_profile_sources
from .research_claims import generate_research_claim_matrix, load_research_claims

OPERATIONAL_MARKDOWN_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "bibliography-integrity.md",
    "budget-ledger.md",
    "budget-checklist.md",
    "citation-support.md",
    "citation-support-summary.md",
    "evidence-bundle-index.md",
    "next-actions.md",
    "profile-integrity.md",
    "profile-source-summary.md",
    "readiness.md",
    "research-claim-matrix.md",
    "research-claims.md",
    "report-integrity.md",
    "source-verification.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
    "workspace-trace.md",
}

EVIDENCE_ID_RE = re.compile(r"\bEVI-[A-Za-z0-9][A-Za-z0-9_.:-]*\b")


def generate_workspace_trace(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceTraceResult:
    """Generate a deterministic local traceability graph for a K-ResDev workspace."""

    workspace = Path(root)
    builder = _TraceBuilder(workspace)
    builder.add_evidence()
    builder.add_budget_ledger()
    builder.add_profile_sources()
    builder.add_bibliography()
    builder.add_reports()
    builder.add_approvals()
    builder.add_bibliography_reviews()
    builder.add_citation_support()
    builder.add_research_claims()
    builder.add_analysis_manifests()
    builder.add_review_pack()

    findings = _dedupe_findings(builder.findings)
    status = _status_from_findings(findings)
    result = WorkspaceTraceResult(
        root=str(workspace),
        status=status,
        node_count=len(builder.nodes),
        edge_count=len(builder.edges),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        nodes=sorted(builder.nodes.values(), key=lambda node: (node.node_type, node.node_id)),
        edges=sorted(builder.edges, key=lambda edge: (edge.source, edge.relation, edge.target)),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=sorted(set(builder.warnings)),
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_workspace_trace_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_workspace_trace_markdown(result: WorkspaceTraceResult) -> str:
    lines = [
        "# K-ResDev Workspace Trace",
        "",
        "> Trace projection only. This local graph links artifacts and review records; it does not certify official compliance, scientific validity, source truth, or approval validity.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Nodes | {result.node_count} |",
        f"| Edges | {result.edge_count} |",
        f"| Findings | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Message | Node | Path | Suggested Action |",
        "|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | trace_ready | No trace findings detected. | - | - | Continue human review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {message} | {node} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                message=_escape(finding.message),
                node=_escape(finding.node_id or "-"),
                path=_escape(finding.path or "-"),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(["", "## Nodes", "", "| Type | Node | Label | Ref | Status | Path |", "|---|---|---|---|---|---|"])
    if not result.nodes:
        lines.append("| - | - | No trace nodes found. | - | - | - |")
    for node in result.nodes:
        lines.append(
            "| {kind} | `{node}` | {label} | {ref} | {status} | {path} |".format(
                kind=_escape(node.node_type),
                node=_escape(node.node_id),
                label=_escape(node.label),
                ref=_escape(node.ref_id or "-"),
                status=_escape(node.status or "-"),
                path=_escape(node.path or "-"),
            )
        )
    lines.extend(["", "## Edges", "", "| Relation | Source | Target |", "|---|---|---|"])
    if not result.edges:
        lines.append("| - | - | - |")
    for edge in result.edges:
        lines.append(f"| {_escape(edge.relation)} | `{_escape(edge.source)}` | `{_escape(edge.target)}` |")
    lines.append("")
    return "\n".join(lines)


class _TraceBuilder:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.nodes: dict[str, WorkspaceTraceNode] = {}
        self.edges: list[WorkspaceTraceEdge] = []
        self.findings: list[WorkspaceTraceFinding] = []
        self.warnings: list[str] = []
        self.evidence_by_id: dict[str, EvidenceItem] = {}
        self.budget_ledger_by_id: dict[str, BudgetLedgerItem] = {}
        self.bibliography_by_id: dict[str, BibliographyEntry] = {}
        self.bibliography_by_key: dict[str, BibliographyEntry] = {}
        self.citation_support_by_id: dict[str, CitationSupportRecord] = {}
        self.profile_sources_by_id: dict[str, ProfileSource] = {}

    def add_evidence(self) -> None:
        path = self.workspace / "state" / "evidence-index.json"
        if not path.exists():
            self.finding(
                "trace_evidence_index_missing",
                "medium",
                "Evidence index is missing; source-to-evidence trace is unavailable.",
                path=path,
                suggested_action="Run intake before relying on workspace trace.",
            )
            return
        try:
            evidence = load_evidence_index(path)
        except Exception as exc:
            self.finding(
                "trace_evidence_index_unreadable",
                "high",
                f"Evidence index could not be read: {exc}",
                path=path,
                suggested_action="Regenerate or repair state/evidence-index.json.",
            )
            return
        for item in evidence:
            self.evidence_by_id[item.evidence_id] = item
            evidence_node = self.node(
                "evidence",
                item.evidence_id,
                item.evidence_id,
                ref_id=item.evidence_id,
                status=str(item.status),
                metadata={
                    "evidence_type": str(item.evidence_type),
                    "claim": item.claim,
                    "risk_flags": item.risk_flags,
                },
            )
            source_node = self.source_node(item.source_file, item.source_hash)
            self.edge(source_node.node_id, evidence_node.node_id, "source_of")
            self._source_hash_findings(source_node, item.source_hash, "evidence")
            if str(item.status) in {"needs_review", "draft"}:
                self.finding(
                    "trace_evidence_unresolved",
                    "medium",
                    f"Evidence `{item.evidence_id}` is not accepted.",
                    node_id=evidence_node.node_id,
                    path=item.source_file,
                    suggested_action="Review evidence status before citing it in approved projections.",
                )
            if str(item.status) in {"rejected", "superseded"}:
                self.finding(
                    "trace_evidence_invalid_status",
                    "high",
                    f"Evidence `{item.evidence_id}` has status `{item.status}`.",
                    node_id=evidence_node.node_id,
                    path=item.source_file,
                    suggested_action="Remove downstream citations or replace the evidence.",
                )

    def add_reports(self) -> None:
        for report in self._reports():
            node = self.node("report", str(report), report.name, path=str(report), sha256=_sha256_file(report))
            text = _read_text(report)
            for evidence_id in sorted(set(EVIDENCE_ID_RE.findall(text))):
                evidence_node_id = _node_id("evidence", evidence_id)
                if evidence_id not in self.evidence_by_id:
                    self.node("evidence", evidence_id, evidence_id, ref_id=evidence_id, status="missing")
                self.edge(node.node_id, evidence_node_id, "cites")
                item = self.evidence_by_id.get(evidence_id)
                if item is None:
                    self.finding(
                        "trace_report_cites_unknown_evidence",
                        "high",
                        f"Report `{report.name}` cites unknown evidence `{evidence_id}`.",
                        node_id=node.node_id,
                        path=report,
                        suggested_action="Add the evidence to the index or remove the citation.",
                    )
                elif str(item.status) in {"draft", "needs_review"}:
                    self.finding(
                        "trace_report_cites_unreviewed_evidence",
                        "medium",
                        f"Report `{report.name}` cites `{evidence_id}` with status `{item.status}`.",
                        node_id=node.node_id,
                        path=report,
                        suggested_action="Review cited evidence before approval or external use.",
                    )
                elif str(item.status) in {"rejected", "superseded"}:
                    self.finding(
                        "trace_report_cites_invalid_evidence",
                        "high",
                        f"Report `{report.name}` cites `{evidence_id}` with status `{item.status}`.",
                        node_id=node.node_id,
                        path=report,
                        suggested_action="Remove the invalid evidence citation.",
                    )
            for citation_key in sorted(extract_markdown_citation_keys(text)):
                bib = self.bibliography_by_key.get(citation_key)
                if bib is None:
                    self.node("bibliography", citation_key, citation_key, ref_id=citation_key, status="missing", metadata={"citation_key": citation_key})
                target = _node_id("bibliography", bib.bibliography_id if bib else citation_key)
                self.edge(node.node_id, target, "cites_paper", {"citation_key": citation_key})

    def add_budget_ledger(self) -> None:
        path = self.workspace / "state" / "budget-ledger.json"
        if not path.exists():
            return
        try:
            items = load_budget_ledger(path)
        except Exception as exc:
            self.finding(
                "trace_budget_ledger_unreadable",
                "high",
                f"Budget ledger could not be read: {exc}",
                path=path,
                suggested_action="Fix state/budget-ledger.json or re-import the budget ledger.",
            )
            return
        for item in items:
            self.budget_ledger_by_id[item.ledger_id] = item
            node = self.node(
                "budget_ledger",
                item.ledger_id,
                item.ledger_id,
                ref_id=item.ledger_id,
                status=item.review_status,
                path=item.source_file,
                metadata={
                    "date": item.date,
                    "vendor": item.vendor,
                    "amount": item.amount,
                    "currency": item.currency,
                    "category": item.category,
                    "proof_type": item.proof_type,
                    "approval_reference": item.approval_reference,
                    "risk_flags": item.risk_flags,
                },
            )
            if item.source_file:
                source_node = self.source_node(item.source_file, item.source_hash)
                self.edge(source_node.node_id, node.node_id, "source_of")
                self._source_hash_findings(source_node, item.source_hash, "budget_ledger")
            for evidence_id in item.evidence_ids:
                self.edge(node.node_id, _node_id("evidence", evidence_id), "references_evidence")
        integrity = generate_workspace_budget_ledger(self.workspace)
        if integrity.status == "not_configured":
            return
        for finding in integrity.findings:
            severity = "high" if finding.severity == "high" else "medium" if finding.severity == "medium" else "low"
            self.finding(
                "trace_budget_ledger_integrity_finding",
                severity,
                finding.message,
                node_id=_node_id("budget_ledger", finding.ledger_id) if finding.ledger_id else None,
                path=finding.path,
                suggested_action=finding.suggested_action or "Review budget ledger integrity before settlement or audit use.",
            )

    def add_profile_sources(self) -> None:
        path = self.workspace / "state" / "profile-sources.json"
        if not path.exists():
            return
        try:
            sources = load_profile_sources(path)
        except Exception as exc:
            self.finding(
                "trace_profile_sources_unreadable",
                "medium",
                f"Profile source index could not be read: {exc}",
                path=path,
                suggested_action="Fix state/profile-sources.json before relying on profile trace impact review.",
            )
            return
        for source in sources:
            self.profile_sources_by_id[source.source_id] = source
            node = self.node(
                "profile_source",
                source.source_id,
                source.title,
                ref_id=source.source_id,
                status=source.review_status,
                path=source.source_file,
                sha256=source.source_hash,
                metadata={
                    "profile_id": source.profile_id,
                    "source_url": source.source_url,
                    "retrieved_at": source.retrieved_at,
                    "verified_by": source.verified_by,
                    "risk_flags": source.risk_flags,
                },
            )
            self.edge(node.node_id, _node_id("profile", source.profile_id), "supports_profile")
            if source.source_file:
                source_node = self.source_node(source.source_file, source.source_hash)
                self.edge(source_node.node_id, node.node_id, "source_of")
                self._source_hash_findings(source_node, source.source_hash, "profile")
            if source.review_status != "verified":
                severity = "high" if source.review_status in {"rejected", "superseded"} else "medium"
                self.finding(
                    "trace_profile_source_not_verified",
                    severity,
                    f"Profile source `{source.source_id}` is `{source.review_status}`.",
                    node_id=node.node_id,
                    path=source.source_file,
                    suggested_action="Keep profile templates in needs_review until official source records are supplied and reviewed.",
                )
            if source.review_status == "verified" and (not source.verified_by or not source.source_hash):
                self.finding(
                    "trace_profile_source_verification_incomplete",
                    "medium",
                    f"Verified profile source `{source.source_id}` is missing reviewer or hash metadata.",
                    node_id=node.node_id,
                    path=source.source_file,
                    suggested_action="Record verified_by and a hash-backed local source/reference artifact.",
                )

    def add_approvals(self) -> None:
        approvals_dir = self.workspace / "state" / "approvals"
        if not approvals_dir.exists():
            return
        try:
            approvals = load_approval_records(approvals_dir)
        except Exception as exc:
            self.finding(
                "trace_approval_records_unreadable",
                "medium",
                f"Approval records could not be read: {exc}",
                path=approvals_dir,
                suggested_action="Fix approval JSON before relying on trace impact review.",
            )
            return
        for record in approvals:
            node = self.node(
                "approval",
                record.approval_id,
                record.approval_id,
                ref_id=record.approval_id,
                status=str(record.decision),
                path=record.target_path,
                metadata={"target_type": str(record.target_type), "target_id": record.target_id, "reviewer": record.reviewer},
            )
            target_node_id = self._approval_target_node(record)
            self.edge(node.node_id, target_node_id, "approves")
            for evidence_id in record.evidence_ids:
                self.edge(node.node_id, _node_id("evidence", evidence_id), "references_evidence")
            self._approval_hash_findings(record, node)

    def add_bibliography(self) -> None:
        path = self.workspace / "state" / "bibliography-index.json"
        if not path.exists():
            return
        try:
            entries = load_bibliography_index(path)
        except Exception as exc:
            self.finding(
                "trace_bibliography_index_unreadable",
                "high",
                f"Bibliography index could not be read: {exc}",
                path=path,
                suggested_action="Regenerate or repair state/bibliography-index.json.",
            )
            return
        for entry in entries:
            self.bibliography_by_id[entry.bibliography_id] = entry
            if entry.citation_key:
                self.bibliography_by_key[entry.citation_key] = entry
            bib_node = self.node(
                "bibliography",
                entry.bibliography_id,
                entry.citation_key or entry.bibliography_id,
                ref_id=entry.bibliography_id,
                status=str(entry.status),
                metadata={"citation_key": entry.citation_key, "title": entry.title, "risk_flags": entry.risk_flags},
            )
            source_node = self.source_node(entry.source_file, entry.source_hash)
            self.edge(source_node.node_id, bib_node.node_id, "source_of")
            self._source_hash_findings(source_node, entry.source_hash, "bibliography")
            if str(entry.status) != "accepted":
                self.finding(
                    "trace_bibliography_unreviewed",
                    "medium",
                    f"Bibliography entry `{entry.bibliography_id}` is not accepted.",
                    node_id=bib_node.node_id,
                    path=entry.source_file,
                    suggested_action="Record a supplied bibliography review decision before external manuscript/report use.",
                )

    def add_bibliography_reviews(self) -> None:
        reviews_dir = self.workspace / "state" / "bibliography-reviews"
        if not reviews_dir.exists():
            return
        try:
            reviews = load_bibliography_review_records(reviews_dir)
        except Exception as exc:
            self.finding(
                "trace_bibliography_reviews_unreadable",
                "medium",
                f"Bibliography review records could not be read: {exc}",
                path=reviews_dir,
                suggested_action="Fix bibliography review JSON before relying on trace impact review.",
            )
            return
        for record in reviews:
            node = self.node(
                "bibliography_review",
                record.review_id,
                record.review_id,
                ref_id=record.review_id,
                status=str(record.decision),
                metadata={"bibliography_id": record.bibliography_id, "reviewer": record.reviewer},
            )
            self.edge(node.node_id, _node_id("bibliography", record.bibliography_id), "reviews")

    def add_citation_support(self) -> None:
        support_dir = self.workspace / "state" / "citation-support"
        if support_dir.exists():
            try:
                records = load_citation_support_records(support_dir)
            except Exception as exc:
                self.finding(
                    "trace_citation_support_unreadable",
                    "medium",
                    f"Citation support records could not be read: {exc}",
                    path=support_dir,
                    suggested_action="Fix citation-support JSON before relying on trace impact review.",
                )
                records = []
            for record in records:
                self.citation_support_by_id[record.support_id] = record
                self._add_citation_support_record(record)
        integrity = generate_workspace_citation_support_integrity(self.workspace)
        if integrity.status == "not_configured":
            return
        for finding in integrity.findings:
            severity = "high" if finding.severity == "high" else "medium"
            self.finding(
                "trace_citation_support_unresolved",
                severity,
                finding.message,
                node_id=_node_id("citation_support", finding.support_id) if finding.support_id else None,
                path=finding.path,
                suggested_action=finding.suggested_action or "Review citation support before external manuscript/report use.",
            )
        for warning in integrity.warnings:
            self.finding(
                "trace_citation_support_warning",
                "medium",
                warning,
                path=support_dir,
                suggested_action="Review citation-support integrity output.",
            )

    def add_research_claims(self) -> None:
        claim_path = self.workspace / "state" / "research-claims.json"
        if not claim_path.exists():
            return
        try:
            claims = load_research_claims(claim_path)
        except Exception as exc:
            self.finding(
                "trace_research_claims_unreadable",
                "high",
                f"Research claims could not be read: {exc}",
                path=claim_path,
                suggested_action="Fix state/research-claims.json or re-import supplied research claims.",
            )
            return
        for claim in claims:
            self._add_research_claim(claim, claim_path)
        matrix = generate_research_claim_matrix(self.workspace)
        if matrix.status == "not_configured":
            return
        for finding in matrix.findings:
            severity = "high" if finding.severity == "high" else "medium" if finding.severity == "medium" else "low"
            self.finding(
                "trace_research_claim_matrix_finding",
                severity,
                finding.message,
                node_id=_node_id("research_claim", finding.claim_id) if finding.claim_id else None,
                path=finding.path,
                suggested_action=finding.suggested_action or "Review research-claim matrix before external manuscript/report use.",
            )
        for warning in matrix.warnings:
            self.finding(
                "trace_research_claim_warning",
                "medium",
                warning,
                path=claim_path,
                suggested_action="Review research-claim matrix output.",
            )

    def add_analysis_manifests(self) -> None:
        analysis_dir = self.workspace / "reports" / "analysis"
        if not analysis_dir.exists():
            return
        for manifest in sorted(analysis_dir.glob("*-analysis-run.json")):
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                self.finding(
                    "trace_analysis_manifest_unreadable",
                    "medium",
                    f"Analysis manifest `{manifest.name}` could not be read: {exc}",
                    path=manifest,
                    suggested_action="Regenerate the analysis manifest.",
                )
                continue
            analysis_id = _text(payload.get("analysis_id")) or manifest.stem
            node = self.node(
                "analysis_manifest",
                analysis_id,
                analysis_id,
                ref_id=analysis_id,
                status=_text(payload.get("status")),
                path=str(manifest),
                sha256=_sha256_file(manifest),
                metadata={"profile_path": payload.get("profile_path"), "insight_report_path": payload.get("insight_report_path")},
            )
            source_file = _text(payload.get("source_file"))
            source_hash = _text(payload.get("source_hash"))
            if source_file:
                source_node = self.source_node(source_file, source_hash)
                self.edge(source_node.node_id, node.node_id, "derived_from")
                self._source_hash_findings(source_node, source_hash, "analysis")
            for evidence_id in payload.get("evidence_ids") or []:
                self.edge(node.node_id, _node_id("evidence", str(evidence_id)), "uses_evidence")

    def add_review_pack(self) -> None:
        pack_path = self.workspace / "state" / "workspace-review-pack.json"
        if not pack_path.exists():
            return
        try:
            payload = json.loads(pack_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            self.finding(
                "trace_review_pack_unreadable",
                "medium",
                f"Review pack manifest could not be read: {exc}",
                path=pack_path,
                suggested_action="Regenerate workspace-review-pack.",
            )
            return
        pack_node = self.node("review_pack", str(pack_path), pack_path.name, path=str(pack_path), sha256=_sha256_file(pack_path))
        for artifact in payload.get("artifacts") or []:
            artifact_path = _text(artifact.get("path")) if isinstance(artifact, dict) else None
            if not artifact_path:
                continue
            artifact_node = self.node(
                "generated_artifact",
                artifact_path,
                Path(artifact_path).name,
                path=artifact_path,
                sha256=_text(artifact.get("sha256")) if isinstance(artifact, dict) else None,
            )
            self.edge(pack_node.node_id, artifact_node.node_id, "generated_artifact")
            target = Path(artifact_path)
            if not target.exists():
                self.finding(
                    "trace_review_pack_artifact_missing",
                    "medium",
                    f"Review-pack artifact `{artifact_path}` is missing.",
                    node_id=artifact_node.node_id,
                    path=artifact_path,
                    suggested_action="Regenerate or verify the workspace review pack.",
                )

    def _add_citation_support_record(self, record: CitationSupportRecord) -> None:
        node = self.node(
            "citation_support",
            record.support_id,
            record.support_id,
            ref_id=record.support_id,
            status=str(record.decision),
            metadata={"bibliography_id": record.bibliography_id, "citation_key": record.citation_key, "claim": record.claim},
        )
        self.edge(node.node_id, _node_id("bibliography", record.bibliography_id), "supports_claim")
        for evidence_id in record.evidence_ids:
            self.edge(node.node_id, _node_id("evidence", evidence_id), "references_evidence")
        if str(record.decision) == "needs_review":
            self.finding(
                "trace_citation_support_needs_review",
                "medium",
                f"Citation support `{record.support_id}` is needs_review.",
                node_id=node.node_id,
                suggested_action="Resolve the paper-claim support decision before external manuscript/report use.",
            )
        if str(record.decision) in {"does_not_support", "superseded"}:
            self.finding(
                "trace_citation_support_negative",
                "high",
                f"Citation support `{record.support_id}` has decision `{record.decision}`.",
                node_id=node.node_id,
                suggested_action="Remove or revise downstream claims that depend on this citation support.",
            )

    def _add_research_claim(self, claim: ResearchClaim, claim_path: Path) -> None:
        node = self.node(
            "research_claim",
            claim.claim_id,
            claim.claim_id,
            ref_id=claim.claim_id,
            status=str(claim.status),
            path=str(claim_path),
            metadata={
                "claim": claim.claim,
                "claim_type": claim.claim_type,
                "confidence": str(claim.confidence),
                "risk_flags": claim.risk_flags,
                "next_checks": claim.next_checks,
            },
        )
        for evidence_id in claim.evidence_ids:
            self.edge(node.node_id, _node_id("evidence", evidence_id), "references_evidence")
        for bibliography_id in claim.bibliography_ids:
            self.edge(node.node_id, _node_id("bibliography", bibliography_id), "cites_paper")
        for citation_key in claim.citation_keys:
            bib = self.bibliography_by_key.get(citation_key)
            if bib is None:
                self.node("bibliography", citation_key, citation_key, ref_id=citation_key, status="missing", metadata={"citation_key": citation_key})
                target = _node_id("bibliography", citation_key)
            else:
                target = _node_id("bibliography", bib.bibliography_id)
            self.edge(node.node_id, target, "cites_paper", {"citation_key": citation_key})
        for support_id in claim.support_ids:
            self.edge(node.node_id, _node_id("citation_support", support_id), "uses_citation_support")
        for insight_id in claim.insight_ids:
            self.edge(node.node_id, _node_id("research_insight", insight_id), "relates_insight")
        if str(claim.status) in {"hypothesis", "candidate", "needs_review"}:
            self.finding(
                "trace_research_claim_unresolved",
                "medium",
                f"Research claim `{claim.claim_id}` is `{claim.status}`.",
                node_id=node.node_id,
                path=claim_path,
                suggested_action="Keep unresolved research claims marked as hypothesis/candidate or record supplied human acceptance.",
            )
        if str(claim.status) in {"rejected", "superseded"}:
            self.finding(
                "trace_research_claim_invalid_status",
                "high",
                f"Research claim `{claim.claim_id}` has status `{claim.status}`.",
                node_id=node.node_id,
                path=claim_path,
                suggested_action="Remove downstream use of rejected or superseded research claims.",
            )

    def _approval_target_node(self, record: ApprovalRecord) -> str:
        if record.target_path:
            path = self._resolve_path(record.target_path)
            node = self.node("artifact", str(path), Path(record.target_path).name, path=str(path), sha256=_sha256_file(path) if path.exists() else None)
            return node.node_id
        return _node_id(str(record.target_type), record.target_id)

    def _approval_hash_findings(self, record: ApprovalRecord, node: WorkspaceTraceNode) -> None:
        if not record.target_path:
            self.finding(
                "trace_approval_target_path_missing",
                "medium",
                f"Approval `{record.approval_id}` has no target_path.",
                node_id=node.node_id,
                suggested_action="Record approvals with target_path so artifact drift can be checked.",
            )
            return
        path = self._resolve_path(record.target_path)
        if not path.exists():
            self.finding(
                "trace_approval_target_missing",
                "high",
                f"Approval target `{record.target_path}` is missing.",
                node_id=node.node_id,
                path=record.target_path,
                suggested_action="Restore the approved artifact or record a new human decision for the replacement.",
            )
            return
        if not record.target_hash:
            self.finding(
                "trace_approval_target_hash_unverified",
                "medium",
                f"Approval `{record.approval_id}` has no target hash.",
                node_id=node.node_id,
                path=record.target_path,
                suggested_action="Record approval decisions with target_path so hashes are captured.",
            )
            return
        actual = _sha256_file(path)
        if actual != _normalize_hash(record.target_hash):
            self.finding(
                "trace_approval_target_hash_mismatch",
                "high",
                f"Approval target `{record.target_path}` changed after approval.",
                node_id=node.node_id,
                path=record.target_path,
                suggested_action="Re-review changed artifacts and record a new supplied human approval decision.",
            )

    def _source_hash_findings(self, source_node: WorkspaceTraceNode, expected_hash: str | None, kind: str) -> None:
        source_path = self._resolve_path(source_node.path or "")
        if not expected_hash:
            self.finding(
                f"trace_{kind}_source_hash_unverified",
                "low",
                f"{kind.title()} source `{source_node.path}` has no saved source hash.",
                node_id=source_node.node_id,
                path=source_node.path,
                suggested_action="Prefer source-hash-bound records for audit-sensitive use.",
            )
            return
        if not source_path.exists():
            self.finding(
                f"trace_{kind}_source_missing",
                "high",
                f"{kind.title()} source `{source_node.path}` is missing.",
                node_id=source_node.node_id,
                path=source_node.path,
                suggested_action="Restore the source file or regenerate affected records.",
            )
            return
        actual = _sha256_file(source_path)
        if actual != _normalize_hash(expected_hash):
            self.finding(
                f"trace_{kind}_source_hash_mismatch",
                "high",
                f"{kind.title()} source `{source_node.path}` changed after indexing/import.",
                node_id=source_node.node_id,
                path=source_node.path,
                suggested_action="Rerun intake/import and review downstream artifacts before relying on them.",
            )

    def source_node(self, source_file: str, source_hash: str | None = None) -> WorkspaceTraceNode:
        path = str(source_file)
        resolved = self._resolve_path(path)
        node_hash = _sha256_file(resolved) if resolved.exists() and resolved.is_file() else _normalize_hash(source_hash) if source_hash else None
        return self.node("source", path, Path(path).name or path, path=path, sha256=node_hash)

    def node(
        self,
        node_type: str,
        key: str,
        label: str,
        path: str | None = None,
        ref_id: str | None = None,
        status: str | None = None,
        sha256: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkspaceTraceNode:
        node_id = _node_id(node_type, key)
        existing = self.nodes.get(node_id)
        if existing is not None:
            merged_metadata = {**existing.metadata, **(metadata or {})}
            updated = existing.model_copy(
                update={
                    "path": existing.path or path,
                    "ref_id": existing.ref_id or ref_id,
                    "status": existing.status or status,
                    "sha256": existing.sha256 or _normalize_hash(sha256) if sha256 else existing.sha256,
                    "metadata": merged_metadata,
                }
            )
            self.nodes[node_id] = updated
            return updated
        node = WorkspaceTraceNode(
            node_id=node_id,
            node_type=node_type,
            label=label,
            path=path,
            ref_id=ref_id,
            status=status,
            sha256=_normalize_hash(sha256) if sha256 else None,
            metadata=metadata or {},
        )
        self.nodes[node_id] = node
        return node

    def edge(self, source: str, target: str, relation: str, metadata: dict[str, Any] | None = None) -> None:
        edge = WorkspaceTraceEdge(source=source, target=target, relation=relation, metadata=metadata or {})
        if edge not in self.edges:
            self.edges.append(edge)

    def finding(
        self,
        code: str,
        severity: str,
        message: str,
        node_id: str | None = None,
        path: str | Path | None = None,
        suggested_action: str | None = None,
    ) -> None:
        self.findings.append(
            WorkspaceTraceFinding(
                code=code,
                severity=severity,
                message=message,
                node_id=node_id,
                path=str(path) if path is not None else None,
                suggested_action=suggested_action,
            )
        )

    def _reports(self) -> list[Path]:
        reports = self.workspace / "reports"
        if not reports.exists():
            return []
        return sorted(path for path in reports.glob("*.md") if path.name not in OPERATIONAL_MARKDOWN_NAMES)

    def _resolve_path(self, path: str) -> Path:
        target = Path(path)
        if target.is_absolute():
            return target
        return self.workspace / target


def _node_id(node_type: str, key: str) -> str:
    digest = hashlib.sha256(f"{node_type}|{key}".encode("utf-8")).hexdigest()[:12].upper()
    safe = re.sub(r"[^A-Za-z0-9]+", "-", key).strip("-").upper()[:40] or "NODE"
    return f"{node_type}:{safe}:{digest}"


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _normalize_hash(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value)
    return text if text.startswith("sha256:") else f"sha256:{text}"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _status_from_findings(findings: list[WorkspaceTraceFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "impacted"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    return "ready"


def _dedupe_findings(findings: list[WorkspaceTraceFinding]) -> list[WorkspaceTraceFinding]:
    seen: set[tuple[str, str, str | None, str | None]] = set()
    result: list[WorkspaceTraceFinding] = []
    for finding in findings:
        key = (finding.code, finding.message, finding.node_id, finding.path)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.code, item.message))


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
