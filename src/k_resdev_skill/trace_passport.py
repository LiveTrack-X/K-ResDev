from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .models import (
    CheckpointCreateResult,
    CheckpointResumeAction,
    CheckpointResumePlan,
    TracePassportEntry,
    TracePassportFinding,
    WorkspaceTracePassport,
)

CHECKPOINT_STATUSES = {"draft", "needs_review", "accepted", "superseded"}
DEFAULT_EXCLUDED_STATE_FILES = {"trace-passport.json", "checkpoint-resume-plan.json"}
DEFAULT_EXCLUDED_REPORT_FILES = {"trace-passport.md", "checkpoint-resume-plan.md"}


def create_checkpoint(
    root: str | Path,
    stage: str,
    summary: str,
    artifact_paths: list[str | Path] | None = None,
    status: str = "needs_review",
    resume_hint: str | None = None,
    unresolved_findings: list[str] | None = None,
    pending_human_decisions: list[str] | None = None,
    checkpoint_dir: str | Path | None = None,
    passport_json_path: str | Path | None = None,
) -> CheckpointCreateResult:
    """Create a hash-backed checkpoint entry without copying raw artifact bodies."""

    workspace = Path(root)
    created_at = _utc_now()
    warnings: list[str] = []
    if status not in CHECKPOINT_STATUSES:
        raise ValueError(f"Unsupported checkpoint status: {status}")
    artifacts = _artifact_paths(workspace, artifact_paths, warnings)
    artifact_hashes = {path: _sha256_file(_resolve_path(workspace, path)) for path in artifacts}
    checkpoint_id = _checkpoint_id(created_at, stage, summary, artifact_hashes)
    entry = TracePassportEntry(
        checkpoint_id=checkpoint_id,
        created_at=created_at,
        stage=stage,
        summary=summary,
        artifact_paths=artifacts,
        artifact_hashes=artifact_hashes,
        unresolved_findings=unresolved_findings or [],
        pending_human_decisions=pending_human_decisions or [],
        resume_hint=resume_hint,
        status=status,
    )

    checkpoints = Path(checkpoint_dir) if checkpoint_dir is not None else workspace / "state" / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoints / f"{checkpoint_id}.json"
    checkpoint_path.write_text(entry.model_dump_json(indent=2) + "\n", encoding="utf-8")

    passport_path = Path(passport_json_path) if passport_json_path is not None else workspace / "state" / "trace-passport.json"
    generate_trace_passport(workspace, json_path=passport_path)
    return CheckpointCreateResult(
        root=str(workspace),
        checkpoint_id=checkpoint_id,
        checkpoint_path=str(checkpoint_path),
        passport_json_path=str(passport_path),
        stage=stage,
        artifact_count=len(entry.artifact_paths),
        status=str(entry.status),
        warnings=_unique(warnings),
    )


def load_checkpoint_entries(path: str | Path) -> list[TracePassportEntry]:
    source = Path(path)
    if source.is_dir():
        entries: list[TracePassportEntry] = []
        for checkpoint_path in sorted(source.glob("*.json")):
            entries.extend(load_checkpoint_entries(checkpoint_path))
        return entries
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        return [TracePassportEntry.model_validate(item) for item in payload["entries"]]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [TracePassportEntry.model_validate(item) for item in payload["items"]]
    if isinstance(payload, list):
        return [TracePassportEntry.model_validate(item) for item in payload]
    return [TracePassportEntry.model_validate(payload)]


def generate_trace_passport(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> WorkspaceTracePassport:
    """Summarize checkpoint entries and mark stale artifact hashes."""

    workspace = Path(root)
    checkpoint_dir = workspace / "state" / "checkpoints"
    warnings: list[str] = []
    findings: list[TracePassportFinding] = []
    if checkpoint_dir.exists():
        try:
            entries = load_checkpoint_entries(checkpoint_dir)
        except Exception as exc:
            entries = []
            findings.append(
                _finding(
                    "trace_passport_checkpoints_unreadable",
                    "high",
                    f"Checkpoint entries could not be read: {exc}",
                    path=checkpoint_dir,
                    suggested_action="Fix invalid checkpoint JSON or move it out of state/checkpoints.",
                )
            )
    else:
        entries = []
        warnings.append("trace_passport_not_configured")

    for entry in entries:
        findings.extend(_entry_findings(workspace, entry))

    findings = _dedupe_findings(findings)
    entries = sorted(entries, key=lambda item: (item.created_at, item.checkpoint_id))
    latest = _latest_checkpoint(entries)
    status = _status_from_findings(findings, entries)
    result = WorkspaceTracePassport(
        workspace_root=str(workspace),
        project_id=_project_id(workspace),
        generated_at=_utc_now(),
        status=status,
        entries=entries,
        latest_checkpoint_id=latest.checkpoint_id if latest else None,
        checkpoint_count=len(entries),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_trace_passport_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def generate_checkpoint_resume_plan(
    root: str | Path,
    checkpoint_id: str | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> CheckpointResumePlan:
    """Generate a compact local resume plan from the latest or selected checkpoint."""

    workspace = Path(root)
    passport = generate_trace_passport(workspace)
    entry = _select_checkpoint(passport.entries, checkpoint_id or passport.latest_checkpoint_id)
    actions: list[CheckpointResumeAction] = []
    warnings: list[str] = []
    if entry is None:
        actions.append(
            _action(
                "high",
                "Create an initial checkpoint",
                "No usable checkpoint was found for this workspace.",
                f'python -m k_resdev_skill checkpoint-create --root "{workspace}" --stage initial --summary "<summary>"',
            )
        )
    else:
        stale_findings = [finding for finding in passport.findings if finding.checkpoint_id == entry.checkpoint_id and finding.code == "checkpoint_artifact_stale"]
        missing_findings = [finding for finding in passport.findings if finding.checkpoint_id == entry.checkpoint_id and finding.code == "checkpoint_artifact_missing"]
        checkpoint_status = str(entry.status)
        if stale_findings or missing_findings:
            actions.append(
                _action(
                    "high",
                    "Refresh stale checkpoint artifacts",
                    "One or more artifacts changed or disappeared after the checkpoint was created.",
                    f'python -m k_resdev_skill workspace-review-pack --root "{workspace}"',
                )
            )
        if checkpoint_status == "superseded":
            actions.append(
                _action(
                    "high",
                    "Select a non-superseded checkpoint",
                    "The selected checkpoint has been marked superseded.",
                    f'python -m k_resdev_skill checkpoint-resume-plan --root "{workspace}"',
                )
            )
        elif checkpoint_status in {"draft", "needs_review"}:
            actions.append(
                _action(
                    "medium",
                    "Review checkpoint status",
                    "The selected checkpoint is not accepted by a human reviewer yet.",
                    None,
                )
            )
        actions.append(
            _action(
                "medium",
                "Run workspace doctor",
                "Recheck current readiness before continuing from the checkpoint.",
                f'python -m k_resdev_skill doctor --root "{workspace}" --output "{workspace / "reports" / "readiness.md"}" --json "{workspace / "state" / "readiness.json"}"',
            )
        )
        actions.append(
            _action(
                "medium",
                "Review workspace summary",
                "Use the one-page operational snapshot to regain context.",
                f'python -m k_resdev_skill workspace-summary --root "{workspace}" --output "{workspace / "reports" / "workspace-summary.md"}" --json "{workspace / "state" / "workspace-summary.json"}"',
            )
        )
        if entry.pending_human_decisions:
            actions.append(
                _action(
                    "medium",
                    "Resolve pending human decisions",
                    "The checkpoint records pending human review or approval decisions.",
                    None,
                )
            )
        if entry.resume_hint:
            warnings.append(f"resume_hint:{entry.resume_hint}")
        plan = CheckpointResumePlan(
            root=str(workspace),
            status="stale" if stale_findings or missing_findings else "needs_review" if checkpoint_status != "accepted" else "ready",
            checkpoint_id=entry.checkpoint_id,
            artifact_count=len(entry.artifact_paths),
            stale_count=len(stale_findings),
            missing_count=len(missing_findings),
            actions=actions,
            warnings=_unique(warnings),
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
        )
    if entry is None:
        plan = CheckpointResumePlan(
            root=str(workspace),
            status="not_configured",
            actions=actions,
            warnings=_unique(warnings + passport.warnings),
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
        )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_checkpoint_resume_plan_markdown(plan), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(plan.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return plan


def render_trace_passport_markdown(result: WorkspaceTracePassport) -> str:
    lines = [
        "# K-ResDev Trace Passport",
        "",
        "> Trace passport projection only. This is a compact resume aid based on artifact paths and hashes; it does not copy raw sources or certify compliance, approval, or scientific truth.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.workspace_root)}` |",
        f"| Project ID | {_escape(result.project_id or '-')} |",
        f"| Status | {_escape(result.status)} |",
        f"| Checkpoints | {result.checkpoint_count} |",
        f"| Latest checkpoint | {_escape(result.latest_checkpoint_id or '-')} |",
        f"| Findings | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        f"| Warnings | {_escape(', '.join(result.warnings) or '-')} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Checkpoint | Path | Message | Suggested Action |",
        "|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | trace_passport_ready | - | - | No trace-passport findings detected. | Continue human review. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {checkpoint} | {path} | {message} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                checkpoint=_escape(finding.checkpoint_id or "-"),
                path=_escape(finding.path or "-"),
                message=_escape(finding.message),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(["", "## Checkpoints", "", "| Checkpoint | Created | Stage | Status | Artifacts | Summary | Resume Hint |", "|---|---|---|---|---:|---|---|"])
    if not result.entries:
        lines.append("| - | - | - | - | 0 | No checkpoints found. | Run checkpoint-create. |")
    for entry in result.entries:
        lines.append(
            "| {checkpoint} | {created} | {stage} | {status} | {count} | {summary} | {hint} |".format(
                checkpoint=_escape(entry.checkpoint_id),
                created=_escape(entry.created_at),
                stage=_escape(entry.stage),
                status=_escape(str(entry.status)),
                count=len(entry.artifact_paths),
                summary=_escape(entry.summary),
                hint=_escape(entry.resume_hint or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_checkpoint_resume_plan_markdown(plan: CheckpointResumePlan) -> str:
    lines = [
        "# K-ResDev Checkpoint Resume Plan",
        "",
        "> Resume plan projection only. Review commands before running; this does not create approvals or certify artifact validity.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(plan.root)}` |",
        f"| Status | {_escape(plan.status)} |",
        f"| Checkpoint | {_escape(plan.checkpoint_id or '-')} |",
        f"| Artifacts | {plan.artifact_count} |",
        f"| Stale artifacts | {plan.stale_count} |",
        f"| Missing artifacts | {plan.missing_count} |",
        f"| Warnings | {_escape(', '.join(plan.warnings) or '-')} |",
        "",
        "## Actions",
        "",
        "| Priority | Action | Rationale | Command |",
        "|---|---|---|---|",
    ]
    if not plan.actions:
        lines.append("| ok | No resume action generated. | Checkpoint appears current. | - |")
    for action in plan.actions:
        command = f"`{_escape(action.command)}`" if action.command else "-"
        lines.append(f"| {_escape(action.priority)} | {_escape(action.title)} | {_escape(action.rationale)} | {command} |")
    lines.append("")
    return "\n".join(lines)


def _entry_findings(workspace: Path, entry: TracePassportEntry) -> list[TracePassportFinding]:
    findings: list[TracePassportFinding] = []
    if str(entry.status) in {"draft", "needs_review"}:
        findings.append(
            _finding(
                "checkpoint_needs_review",
                "medium",
                f"Checkpoint `{entry.checkpoint_id}` is `{entry.status}`.",
                checkpoint_id=entry.checkpoint_id,
                suggested_action="Review or accept the checkpoint before treating it as the preferred resume point.",
            )
        )
    if str(entry.status) == "superseded":
        findings.append(
            _finding(
                "checkpoint_superseded",
                "low",
                f"Checkpoint `{entry.checkpoint_id}` is superseded.",
                checkpoint_id=entry.checkpoint_id,
                suggested_action="Use the latest non-superseded checkpoint for resume planning.",
            )
        )
    for artifact_path, expected_hash in entry.artifact_hashes.items():
        path = _resolve_path(workspace, artifact_path)
        if not path.exists() or not path.is_file():
            findings.append(
                _finding(
                    "checkpoint_artifact_missing",
                    "high",
                    f"Checkpoint artifact `{artifact_path}` is missing.",
                    checkpoint_id=entry.checkpoint_id,
                    path=artifact_path,
                    suggested_action="Regenerate the artifact or create a fresh checkpoint.",
                )
            )
            continue
        actual = _sha256_file(path)
        if actual != _normalize_hash(expected_hash):
            findings.append(
                _finding(
                    "checkpoint_artifact_stale",
                    "high",
                    f"Checkpoint artifact `{artifact_path}` changed after checkpoint creation.",
                    checkpoint_id=entry.checkpoint_id,
                    path=artifact_path,
                    suggested_action="Refresh the review pack and create a new checkpoint.",
                )
            )
    return findings


def _artifact_paths(workspace: Path, artifact_paths: list[str | Path] | None, warnings: list[str]) -> list[str]:
    if artifact_paths:
        candidates = [Path(path) for path in artifact_paths]
    else:
        candidates = _default_artifacts(workspace)
        if not candidates:
            warnings.append("no_checkpoint_artifacts_detected")
    paths: list[str] = []
    for candidate in candidates:
        resolved = candidate if candidate.is_absolute() else workspace / candidate
        if not resolved.exists() or not resolved.is_file():
            warnings.append(f"artifact_missing:{candidate}")
            continue
        display = _display_path(workspace, resolved)
        if display not in paths:
            paths.append(display)
    return sorted(paths)


def _default_artifacts(workspace: Path) -> list[Path]:
    candidates: list[Path] = []
    state = workspace / "state"
    reports = workspace / "reports"
    if state.exists():
        for path in state.rglob("*"):
            if not path.is_file():
                continue
            if "checkpoints" in path.relative_to(state).parts:
                continue
            if path.name in DEFAULT_EXCLUDED_STATE_FILES:
                continue
            candidates.append(path)
    if reports.exists():
        for path in reports.rglob("*"):
            if not path.is_file():
                continue
            if path.name in DEFAULT_EXCLUDED_REPORT_FILES:
                continue
            candidates.append(path)
    return sorted(candidates, key=lambda item: item.as_posix())


def _latest_checkpoint(entries: list[TracePassportEntry]) -> TracePassportEntry | None:
    usable = [entry for entry in entries if str(entry.status) != "superseded"]
    return max(usable, key=lambda item: (item.created_at, item.checkpoint_id), default=None)


def _select_checkpoint(entries: list[TracePassportEntry], checkpoint_id: str | None) -> TracePassportEntry | None:
    if checkpoint_id is None:
        return _latest_checkpoint(entries)
    for entry in entries:
        if entry.checkpoint_id == checkpoint_id:
            return entry
    return None


def _status_from_findings(findings: list[TracePassportFinding], entries: list[TracePassportEntry]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "stale"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    if entries:
        return "ready"
    return "not_configured"


def _project_id(workspace: Path) -> str | None:
    path = workspace / "state" / "project-state.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    value = payload.get("project_id") if isinstance(payload, dict) else None
    return str(value) if value else None


def _checkpoint_id(created_at: str, stage: str, summary: str, artifact_hashes: dict[str, str]) -> str:
    digest = hashlib.sha256(f"{created_at}|{stage}|{summary}|{json.dumps(artifact_hashes, sort_keys=True)}".encode("utf-8")).hexdigest()
    stamp = created_at.replace("-", "").replace(":", "").replace("T", "-")[:15]
    return f"CHK-{stamp}-{digest[:8].upper()}"


def _finding(
    code: str,
    severity: str,
    message: str,
    checkpoint_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> TracePassportFinding:
    return TracePassportFinding(
        code=code,
        severity=severity,
        message=message,
        checkpoint_id=checkpoint_id,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _action(priority: str, title: str, rationale: str, command: str | None) -> CheckpointResumeAction:
    return CheckpointResumeAction(priority=priority, title=title, rationale=rationale, command=command)


def _dedupe_findings(findings: list[TracePassportFinding]) -> list[TracePassportFinding]:
    seen: set[tuple[str, str, str | None, str | None]] = set()
    result: list[TracePassportFinding] = []
    for finding in findings:
        key = (finding.code, finding.message, finding.checkpoint_id, finding.path)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.code, item.message))


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _resolve_path(workspace: Path, path: str | Path) -> Path:
    target = Path(path)
    if target.is_absolute():
        return target
    return workspace / target


def _display_path(workspace: Path, path: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _normalize_hash(value: str) -> str:
    text = str(value).strip()
    return text if text.startswith("sha256:") else f"sha256:{text}"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
