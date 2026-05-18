from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from .approval_coverage import generate_workspace_approval_coverage
from .evidence_index import load_evidence_index
from .models import ArtifactAuthorityFinding, ArtifactAuthorityRecord, WorkspaceArtifactAuthorityResult

AUTHORITY_LEVELS = (
    "raw_source",
    "extracted_candidate",
    "evidence_needs_review",
    "accepted_evidence",
    "draft_projection",
    "reviewed_projection",
    "approved_projection",
    "operating_summary",
    "superseded",
    "rejected",
)
OPERATIONAL_MARKDOWN_NAMES = {
    "agency-profiles.md",
    "approval-coverage.md",
    "approval-summary.md",
    "artifact-authority.md",
    "bibliography-integrity.md",
    "bibliography-review-summary.md",
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
    "profile-source-queue.md",
    "profile-source-summary.md",
    "readiness.md",
    "reference-corpus-summary.md",
    "research-claim-matrix.md",
    "research-claims.md",
    "report-integrity.md",
    "source-verification.md",
    "trace-passport.md",
    "workspace-discovery.md",
    "workspace-dashboard.md",
    "workspace-review-pack.md",
    "workspace-summary.md",
    "workspace-trace.md",
}
OPERATIONAL_MARKDOWN_PREFIXES = ("weekly-review-", "workflow-")
EVIDENCE_ID_RE = re.compile(r"\bEVI-[A-Za-z0-9][A-Za-z0-9_.:-]*\b")
HIGH_AUTHORITY_NAME_RE = re.compile(
    "(approved|final|submission|submitted|official|\uCD5C\uC885|\uC81C\uCD9C|\uC2B9\uC778)",
    re.IGNORECASE,
)


def generate_artifact_authority(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceArtifactAuthorityResult:
    """Classify local artifact authority levels without creating approvals."""

    workspace = Path(root)
    warnings: list[str] = []
    records: list[ArtifactAuthorityRecord] = []
    findings: list[ArtifactAuthorityFinding] = []

    evidence_by_id = {}
    evidence_path = workspace / "state" / "evidence-index.json"
    if evidence_path.exists():
        try:
            for item in load_evidence_index(evidence_path):
                evidence_by_id[item.evidence_id] = item
                record = ArtifactAuthorityRecord(
                    artifact_id=_artifact_id("evidence", item.evidence_id),
                    path=item.source_file,
                    artifact_type="evidence_item",
                    authority_level=authority_for_evidence_status(str(item.status)),
                    status=str(item.status),
                    ref_id=item.evidence_id,
                    source_hash=item.source_hash,
                    risk_flags=list(item.risk_flags),
                    metadata={"evidence_type": str(item.evidence_type), "claim": item.claim},
                )
                records.append(record)
                if record.authority_level in {"evidence_needs_review", "extracted_candidate"}:
                    findings.append(
                        _finding(
                            "authority_evidence_unreviewed",
                            "medium",
                            f"Evidence `{item.evidence_id}` is `{item.status}` and remains below accepted_evidence authority.",
                            path=item.source_file,
                            artifact_id=record.artifact_id,
                            authority_level=record.authority_level,
                            suggested_action="Review evidence before citing it in external reports or approved projections.",
                        )
                    )
                if record.authority_level in {"rejected", "superseded"}:
                    findings.append(
                        _finding(
                            "authority_evidence_invalid",
                            "high",
                            f"Evidence `{item.evidence_id}` has invalid downstream authority `{record.authority_level}`.",
                            path=item.source_file,
                            artifact_id=record.artifact_id,
                            authority_level=record.authority_level,
                            suggested_action="Remove downstream citations or replace the evidence.",
                        )
                    )
        except Exception as exc:
            warnings.append(f"evidence_index_unreadable:{exc}")

    for source_path in _raw_source_paths(workspace):
        records.append(
            ArtifactAuthorityRecord(
                artifact_id=_artifact_id("raw_source", _display_path(workspace, source_path)),
                path=_display_path(workspace, source_path),
                artifact_type="raw_source",
                authority_level="raw_source",
                source_hash=_sha256_file(source_path),
            )
        )

    coverage = generate_workspace_approval_coverage(workspace)
    report_paths = {Path(item.path) for item in coverage.items}
    for item in coverage.items:
        level = _authority_for_approval_item(item.approved, item.decision, item.hash_status)
        record = ArtifactAuthorityRecord(
            artifact_id=_artifact_id(item.artifact_type, item.path),
            path=item.path,
            artifact_type=item.artifact_type,
            authority_level=level,
            status=item.decision,
            target_id=item.target_id,
            approval_id=item.approval_id,
            source_hash=item.actual_target_hash,
            risk_flags=list(item.warnings),
            metadata={"hash_status": item.hash_status, "target_id_candidates": item.target_id_candidates},
        )
        records.append(record)
        findings.extend(_projection_findings(workspace, record, evidence_by_id))

    for path in _operating_artifact_paths(workspace):
        if path in report_paths:
            continue
        records.append(
            ArtifactAuthorityRecord(
                artifact_id=_artifact_id("operating_summary", _display_path(workspace, path)),
                path=str(path),
                artifact_type="operating_summary",
                authority_level="operating_summary",
                source_hash=_sha256_file(path),
                metadata={"submission_artifact": False},
            )
        )

    records = sorted(_dedupe_records(records), key=lambda item: (item.authority_level, item.artifact_type, item.path or item.ref_id or item.artifact_id))
    findings = sorted(_dedupe_findings(findings), key=lambda item: (_severity_rank(item.severity), item.code, item.path or "", item.artifact_id or ""))
    level_counts = _count(record.authority_level for record in records)
    high_count = sum(1 for finding in findings if finding.severity == "high")
    medium_count = sum(1 for finding in findings if finding.severity == "medium")
    low_count = sum(1 for finding in findings if finding.severity == "low")
    status = "blocked" if high_count else "needs_review" if medium_count else "ready_with_notes" if low_count or warnings else "ready" if records else "not_configured"
    result = WorkspaceArtifactAuthorityResult(
        root=str(workspace),
        status=status,
        artifact_count=len(records),
        finding_count=len(findings),
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        authority_level_counts=level_counts,
        records=records,
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_artifact_authority_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_artifact_authority_markdown(result: WorkspaceArtifactAuthorityResult) -> str:
    lines = [
        "# K-ResDev Artifact Authority",
        "",
        "> Authority projection only. These labels describe local workflow authority; they do not certify official agency compliance, legal status, or scientific truth.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Artifacts | {result.artifact_count} |",
        f"| Findings | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        f"| Authority counts | {_format_counts(result.authority_level_counts)} |",
        f"| Warnings | {_format_list(result.warnings)} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Authority | Artifact | Path | Message | Suggested Action |",
        "|---|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | authority_ready | - | - | - | No authority findings detected. | Continue human review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {level} | {artifact} | {path} | {message} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                level=_escape(finding.authority_level or "-"),
                artifact=_escape(finding.artifact_id or "-"),
                path=_escape(finding.path or "-"),
                message=_escape(finding.message),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Records",
            "",
            "| Authority | Type | Status | Ref | Target | Approval | Path | Risk Flags |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    if not result.records:
        lines.append("| - | - | - | - | - | - | No authority records detected. | - |")
    for record in result.records:
        lines.append(
            "| {level} | {kind} | {status} | {ref} | {target} | {approval} | {path} | {flags} |".format(
                level=_escape(record.authority_level),
                kind=_escape(record.artifact_type),
                status=_escape(record.status or "-"),
                ref=_escape(record.ref_id or "-"),
                target=_escape(record.target_id or "-"),
                approval=_escape(record.approval_id or "-"),
                path=_escape(record.path or "-"),
                flags=_format_list(record.risk_flags),
            )
        )
    lines.append("")
    return "\n".join(lines)


def load_artifact_authority(path: str | Path) -> WorkspaceArtifactAuthorityResult:
    return WorkspaceArtifactAuthorityResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def authority_for_evidence_status(status: str | None) -> str:
    value = str(status or "").strip()
    if value == "accepted":
        return "accepted_evidence"
    if value in {"rejected"}:
        return "rejected"
    if value in {"superseded"}:
        return "superseded"
    if value in {"draft"}:
        return "extracted_candidate"
    return "evidence_needs_review"


def authority_for_trace_node(node_type: str, status: str | None = None, path: str | None = None, metadata: dict | None = None) -> str:
    metadata = metadata or {}
    if isinstance(metadata.get("artifact_authority_level"), str):
        return metadata["artifact_authority_level"]
    if node_type == "source":
        return "raw_source"
    if node_type == "evidence":
        return authority_for_evidence_status(status)
    if node_type in {"report"}:
        return "draft_projection"
    if node_type in {
        "generated_artifact",
        "review_pack",
        "checkpoint",
        "analysis_manifest",
        "project_goals",
        "project_objective",
        "project_deadline",
        "weekly_review",
        "workspace_dashboard",
        "workflow_plan",
    }:
        return "operating_summary"
    if node_type in {"reference", "bibliography", "research_claim"}:
        if str(status) in {"accepted", "supports", "verified"}:
            return "accepted_evidence"
        if str(status) in {"rejected", "does_not_support"}:
            return "rejected"
        if str(status) == "superseded":
            return "superseded"
        return "extracted_candidate"
    if node_type in {"approval", "bibliography_review", "citation_support"}:
        if str(status) == "approved" or str(status) in {"accepted", "supports"}:
            return "reviewed_projection"
        if str(status) in {"rejected", "does_not_support"}:
            return "rejected"
        if str(status) == "superseded":
            return "superseded"
        return "evidence_needs_review"
    if path and Path(path).suffix.lower() in {".docx", ".html", ".txt", ".md"}:
        return "draft_projection"
    return "extracted_candidate"


def _projection_findings(workspace: Path, record: ArtifactAuthorityRecord, evidence_by_id: dict) -> list[ArtifactAuthorityFinding]:
    findings: list[ArtifactAuthorityFinding] = []
    if record.authority_level != "approved_projection":
        severity = "high" if record.path and HIGH_AUTHORITY_NAME_RE.search(Path(record.path).name) else "medium"
        code = "authority_projection_named_final_without_approval" if severity == "high" else "authority_projection_not_approved"
        findings.append(
            _finding(
                code,
                severity,
                f"Projection `{record.path}` is `{record.authority_level}` and has no current approved authority.",
                path=record.path,
                artifact_id=record.artifact_id,
                authority_level=record.authority_level,
                suggested_action="Record a supplied human approval with target_path before treating this artifact as approved.",
            )
        )
    if not record.path or not str(record.path).lower().endswith(".md"):
        return findings
    path = Path(record.path)
    if not path.is_absolute():
        path = workspace / path
    if not path.exists():
        return findings
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings
    for evidence_id in sorted(set(EVIDENCE_ID_RE.findall(text))):
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            findings.append(
                _finding(
                    "authority_projection_cites_unknown_evidence",
                    "high",
                    f"Projection cites unknown evidence `{evidence_id}`.",
                    path=record.path,
                    artifact_id=record.artifact_id,
                    authority_level=record.authority_level,
                    suggested_action="Add the evidence to the index or remove the citation.",
                )
            )
            continue
        level = authority_for_evidence_status(str(evidence.status))
        if level in {"evidence_needs_review", "extracted_candidate"}:
            findings.append(
                _finding(
                    "authority_projection_cites_low_authority_evidence",
                    "medium",
                    f"Projection cites `{evidence_id}` with authority `{level}`.",
                    path=record.path,
                    artifact_id=record.artifact_id,
                    authority_level=record.authority_level,
                    suggested_action="Review cited evidence before external use or approval.",
                )
            )
        if level in {"rejected", "superseded"}:
            findings.append(
                _finding(
                    "authority_projection_cites_invalid_evidence",
                    "high",
                    f"Projection cites `{evidence_id}` with authority `{level}`.",
                    path=record.path,
                    artifact_id=record.artifact_id,
                    authority_level=record.authority_level,
                    suggested_action="Remove rejected or superseded evidence citations.",
                )
            )
    return findings


def _authority_for_approval_item(approved: bool, decision: str, hash_status: str) -> str:
    if approved and hash_status == "ok":
        return "approved_projection"
    if decision not in {"missing", ""}:
        return "reviewed_projection"
    return "draft_projection"


def _raw_source_paths(workspace: Path) -> list[Path]:
    paths: list[Path] = []
    for folder in (workspace / "inbox", workspace / "references"):
        if not folder.exists():
            continue
        paths.extend(path for path in folder.rglob("*") if path.is_file())
    return sorted(paths, key=lambda item: item.as_posix())


def _operating_artifact_paths(workspace: Path) -> list[Path]:
    paths: list[Path] = []
    reports = workspace / "reports"
    if reports.exists():
        paths.extend(path for path in reports.glob("*.md") if _is_operational_markdown(path))
    state = workspace / "state"
    if state.exists():
        for name in (
            "readiness.json",
            "next-actions.json",
            "workspace-summary.json",
            "workspace-dashboard.json",
            "workspace-review-pack.json",
            "workspace-discovery.json",
            "workspace-trace.json",
            "artifact-authority.json",
            "goals-review.json",
        ):
            target = state / name
            if target.exists():
                paths.append(target)
        paths.extend(state.glob("weekly-review-*.json"))
        paths.extend(state.glob("workflow-*.json"))
    return sorted(paths, key=lambda item: item.as_posix())


def _is_operational_markdown(path: str | Path) -> bool:
    name = Path(path).name
    return name in OPERATIONAL_MARKDOWN_NAMES or any(name.startswith(prefix) for prefix in OPERATIONAL_MARKDOWN_PREFIXES)


def _finding(
    code: str,
    severity: str,
    message: str,
    path: str | Path | None = None,
    artifact_id: str | None = None,
    authority_level: str | None = None,
    suggested_action: str | None = None,
) -> ArtifactAuthorityFinding:
    return ArtifactAuthorityFinding(
        code=code,
        severity=severity,
        message=message,
        path=str(path) if path is not None else None,
        artifact_id=artifact_id,
        authority_level=authority_level,
        suggested_action=suggested_action,
    )


def _artifact_id(kind: str, key: str) -> str:
    digest = hashlib.sha256(f"{kind}|{key}".encode("utf-8")).hexdigest()[:10].upper()
    return f"AUTH-{digest}"


def _display_path(workspace: Path, path: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _count(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _dedupe_records(records: Iterable[ArtifactAuthorityRecord]) -> list[ArtifactAuthorityRecord]:
    seen: set[tuple[str, str | None, str | None]] = set()
    result: list[ArtifactAuthorityRecord] = []
    for record in records:
        key = (record.artifact_type, record.path, record.ref_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def _dedupe_findings(findings: Iterable[ArtifactAuthorityFinding]) -> list[ArtifactAuthorityFinding]:
    seen: set[tuple[str, str | None, str]] = set()
    result: list[ArtifactAuthorityFinding] = []
    for finding in findings:
        key = (finding.code, finding.path, finding.message)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"{key}: {value}" for key, value in counts.items())


def _format_list(values: list[str]) -> str:
    if not values:
        return "-"
    return ", ".join(f"`{_escape(value)}`" for value in values[:20])


def _escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()
