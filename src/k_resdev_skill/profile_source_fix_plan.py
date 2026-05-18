from __future__ import annotations

import hashlib
from pathlib import Path

from .models import ProfileSourceFixPlanAction, ProfileSourceFixPlanResult, ProfileSourceQueueItem
from .profile_source_queue import load_profile_source_queue


def generate_profile_source_fix_plan(
    root: str | Path,
    queue_path: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfileSourceFixPlanResult:
    """Create a local-only remediation plan from profile-source queue items."""

    workspace = Path(root)
    queue_file = _resolve_workspace_path(workspace, queue_path or workspace / "state" / "profile-source-queue.json")
    warnings: list[str] = []

    if not queue_file.exists():
        result = _result(
            workspace,
            queue_file,
            status="missing_queue",
            actions=[
                _bootstrap_action(
                    workspace,
                    issue_code="profile_source_queue_missing",
                    severity="medium",
                    title="Generate profile source queue",
                    rationale="A fix plan needs state/profile-source-queue.json as its input.",
                    command=_command(
                        workspace,
                        "profile-source-queue",
                        "--root",
                        str(workspace),
                        "--output",
                        str(workspace / "reports" / "profile-source-queue.md"),
                        "--json",
                        str(workspace / "state" / "profile-source-queue.json"),
                    ),
                )
            ],
            warnings=["profile_source_queue_missing"],
            output_path=output_path,
            json_path=json_path,
        )
        _write_outputs(result, output_path, json_path)
        return result

    try:
        queue = load_profile_source_queue(queue_file)
    except Exception as exc:
        result = _result(
            workspace,
            queue_file,
            status="unreadable_queue",
            actions=[
                _bootstrap_action(
                    workspace,
                    issue_code="profile_source_queue_unreadable",
                    severity="high",
                    title="Regenerate profile source queue",
                    rationale=f"The existing queue could not be parsed: {exc}",
                    command=_command(
                        workspace,
                        "profile-source-queue",
                        "--root",
                        str(workspace),
                        "--output",
                        str(workspace / "reports" / "profile-source-queue.md"),
                        "--json",
                        str(workspace / "state" / "profile-source-queue.json"),
                    ),
                )
            ],
            warnings=[f"profile_source_queue_unreadable:{exc}"],
            output_path=output_path,
            json_path=json_path,
        )
        _write_outputs(result, output_path, json_path)
        return result

    actions = [_action_for_queue_item(workspace, item) for item in queue.items]
    result = _result(
        workspace,
        queue_file,
        status=_status_from_actions(actions),
        queue_hash=_sha256_file(queue_file),
        queue_status=queue.status,
        queue_item_count=queue.queue_item_count,
        profile_count=queue.profile_count,
        actions=actions,
        warnings=warnings,
        output_path=output_path,
        json_path=json_path,
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_profile_source_fix_plan(path: str | Path) -> ProfileSourceFixPlanResult:
    return ProfileSourceFixPlanResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_source_fix_plan_markdown(result: ProfileSourceFixPlanResult) -> str:
    lines = [
        "# Profile Source Fix Plan",
        "",
        "> Proposal only. This translates local profile-source queue items into reviewable commands and manual steps; it does not fetch official sources, mutate profile packs, or mark sources verified.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Queue path | `{_escape(result.queue_path)}` |",
        f"| Queue hash | {_escape(result.queue_hash or '-')} |",
        f"| Queue status | {_escape(result.queue_status or '-')} |",
        f"| Queue items | {result.queue_item_count} |",
        f"| Profiles | {result.profile_count} |",
        f"| Actions | {result.action_count} |",
        f"| Command actions | {result.command_count} |",
        f"| Manual actions | {result.manual_count} |",
        f"| Human review actions | {result.human_review_count} |",
        f"| Official source check actions | {result.official_source_check_count} |",
        f"| High actions | {result.high_count} |",
        f"| Medium actions | {result.medium_count} |",
        f"| Low actions | {result.low_count} |",
        "",
        "## Profile / Severity Groups",
        "",
        "| Profile | High | Medium | Low |",
        "|---|---:|---:|---:|",
    ]
    groups = _profile_severity_groups(result.actions)
    if not groups:
        lines.append("| - | 0 | 0 | 0 |")
    for profile_id, counts in groups:
        lines.append(
            "| {profile} | {high} | {medium} | {low} |".format(
                profile=_escape(profile_id),
                high=counts.get("high", 0),
                medium=counts.get("medium", 0),
                low=counts.get("low", 0),
            )
        )
    lines.extend(
        [
            "",
            "## Actions",
            "",
            "| Severity | Type | Profile | Source | Issue | Manual Step | Command | Follow-up Commands |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    if not result.actions:
        lines.append("| ok | - | - | - | profile_source_fix_plan_ready | No profile-source remediation actions are currently proposed. | - | Keep source queues current. |")
    for action in result.actions:
        lines.append(
            "| {severity} | {action_type} | {profile} | {source} | {issue} | {manual} | {command} | {followups} |".format(
                severity=_escape(action.severity),
                action_type=_escape(action.action_type),
                profile=_escape(action.profile_id or "-"),
                source=_escape(action.source_id or "-"),
                issue=_escape(action.issue_code),
                manual=_escape(action.manual_step or "-"),
                command=_escape(action.command or "-"),
                followups=_escape("<br>".join(action.followup_commands) or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Manual Review Boundary",
            "",
            "- Actions with `requires_official_source_check=true` require a current official-source review outside this command.",
            "- Suggested commands are local-only and are not executed by this plan.",
            "- Use `needs_review` unless a supplied human review explicitly supports a stronger status.",
            "- Re-run `profile-source-queue`, `profile-source-fix-plan`, `profile-integrity`, and `profile-review` after applying any human-approved metadata changes.",
            "",
        ]
    )
    return "\n".join(lines)


def _action_for_queue_item(workspace: Path, item: ProfileSourceQueueItem) -> ProfileSourceFixPlanAction:
    manual, command, followups, requires_official = _remediation_for_item(workspace, item)
    action_type = "manual_then_command" if manual and command else "manual" if manual else "command"
    return ProfileSourceFixPlanAction(
        action_id=_action_id(item.queue_id, item.issue_code),
        queue_id=item.queue_id,
        scope=item.scope,
        profile_id=item.profile_id,
        source_id=item.source_id,
        issue_code=item.issue_code,
        severity=item.severity,
        action_type=action_type,
        title=_title_for_issue(item.issue_code),
        rationale=item.message,
        manual_step=manual,
        command=command,
        followup_commands=followups,
        source_record_path=item.source_record_path,
        source_file=item.source_file,
        requires_human_review=True,
        requires_official_source_check=requires_official,
    )


def _remediation_for_item(workspace: Path, item: ProfileSourceQueueItem) -> tuple[str | None, str | None, list[str], bool]:
    source_path = item.source_record_path or str(workspace / "state" / "profile-sources.json")
    followups = _followup_commands(workspace, item.profile_id)
    record_command = _command(
        workspace,
        "profile-source-record",
        "--root",
        str(workspace),
        "--profile-id",
        item.profile_id,
        "--title",
        item.source_title or "<official source title>",
        "--source-url",
        item.source_url or "<official source URL>",
        "--retrieved-at",
        "<YYYY-MM-DD>",
        "--review-status",
        "needs_review",
        "--source-id",
        item.source_id or "<source-id>",
    )
    validate_queue = _command(workspace, "validate-json", "profile-source-queue", str(workspace / "state" / "profile-source-queue.json"))
    validate_plan = _command(workspace, "validate-json", "profile-source-fix-plan", str(workspace / "state" / "profile-source-fix-plan.json"))

    if item.issue_code == "profile_source_records_missing":
        return (
            "Find the current official source for this profile pack and record only needs_review metadata until a human verifies it.",
            record_command,
            followups,
            True,
        )
    if item.issue_code == "profile_verified_without_verified_source":
        return (
            "Either add a supplied human-verified source record or move the profile back to needs_review before relying on it.",
            record_command,
            followups + [_command(workspace, "profile-review", "--root", str(workspace), "--output", str(workspace / "reports" / "profile-review.md"), "--json", str(workspace / "state" / "profile-review.json"))],
            True,
        )
    if item.issue_code == "profile_source_unknown_status":
        return (
            f"Edit `{source_path}` so this source uses one of needs_review, verified, rejected, or superseded.",
            validate_queue,
            followups,
            False,
        )
    if item.issue_code == "profile_source_not_verified":
        return (
            "Review the current official source manually; keep this source/profile in needs_review unless a supplied human decision supports promotion.",
            None,
            followups,
            True,
        )
    if item.issue_code == "profile_source_locator_missing":
        return (
            "Add a source_url or source_file locator after checking the current official source location.",
            record_command,
            followups,
            True,
        )
    if item.issue_code == "profile_source_retrieved_at_missing":
        return (
            "Record the date the official source was retrieved or reviewed; do not infer freshness from an old local file.",
            record_command,
            followups,
            True,
        )
    if item.issue_code == "profile_source_hash_missing":
        return (
            "Hash a local official-source copy or source note if available; otherwise keep the record needs_review and explain the gap.",
            record_command,
            followups,
            True,
        )
    if item.issue_code == "profile_source_verified_by_missing":
        return (
            "Record the supplied human reviewer before using this source as verified evidence for profile promotion.",
            record_command,
            followups,
            False,
        )
    if item.issue_code == "profile_source_unresolved_risk_flags":
        return (
            "Resolve, document, or explicitly accept the listed risk flags before profile promotion.",
            _command(workspace, "profile-integrity", "--root", str(workspace), "--output", str(workspace / "reports" / "profile-integrity.md"), "--json", str(workspace / "state" / "profile-integrity.json")),
            followups,
            True,
        )
    if item.issue_code == "profile_source_file_missing":
        return (
            "Restore the referenced local source file or replace the source record after re-checking the official source.",
            record_command,
            followups + [validate_queue],
            True,
        )
    if item.issue_code == "profile_source_hash_mismatch":
        return (
            "Re-review the changed local source file against the current official source before recording a new hash-backed source record.",
            record_command,
            followups + [validate_plan],
            True,
        )
    return (
        "Review this profile-source queue item manually and keep the profile in needs_review until resolved.",
        None,
        followups,
        True,
    )


def _followup_commands(workspace: Path, profile_id: str) -> list[str]:
    return [
        _command(
            workspace,
            "profile-source-summary",
            "--root",
            str(workspace),
            "--profile-id",
            profile_id,
            "--output",
            str(workspace / "reports" / "profile-source-summary.md"),
            "--json",
            str(workspace / "state" / "profile-source-summary.json"),
        ),
        _command(
            workspace,
            "profile-integrity",
            "--root",
            str(workspace),
            "--output",
            str(workspace / "reports" / "profile-integrity.md"),
            "--json",
            str(workspace / "state" / "profile-integrity.json"),
        ),
        _command(
            workspace,
            "profile-source-queue",
            "--root",
            str(workspace),
            "--output",
            str(workspace / "reports" / "profile-source-queue.md"),
            "--json",
            str(workspace / "state" / "profile-source-queue.json"),
        ),
    ]


def _result(
    workspace: Path,
    queue_path: Path,
    status: str,
    actions: list[ProfileSourceFixPlanAction],
    warnings: list[str],
    output_path: str | Path | None,
    json_path: str | Path | None,
    queue_hash: str | None = None,
    queue_status: str | None = None,
    queue_item_count: int = 0,
    profile_count: int = 0,
) -> ProfileSourceFixPlanResult:
    return ProfileSourceFixPlanResult(
        root=str(workspace),
        status=status,
        queue_path=str(queue_path),
        queue_hash=queue_hash,
        queue_status=queue_status,
        queue_item_count=queue_item_count,
        profile_count=profile_count or len({action.profile_id for action in actions if action.profile_id}),
        action_count=len(actions),
        command_count=sum(1 for action in actions if action.command),
        manual_count=sum(1 for action in actions if action.manual_step),
        human_review_count=sum(1 for action in actions if action.requires_human_review),
        official_source_check_count=sum(1 for action in actions if action.requires_official_source_check),
        high_count=sum(1 for action in actions if action.severity == "high"),
        medium_count=sum(1 for action in actions if action.severity == "medium"),
        low_count=sum(1 for action in actions if action.severity == "low"),
        actions=actions,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=sorted(set(warnings)),
    )


def _bootstrap_action(
    workspace: Path,
    issue_code: str,
    severity: str,
    title: str,
    rationale: str,
    command: str,
) -> ProfileSourceFixPlanAction:
    return ProfileSourceFixPlanAction(
        action_id=_action_id("profile-source-queue", issue_code),
        issue_code=issue_code,
        severity=severity,
        action_type="command",
        title=title,
        rationale=rationale,
        command=command,
        followup_commands=[],
        requires_human_review=False,
        requires_official_source_check=False,
    )


def _write_outputs(
    result: ProfileSourceFixPlanResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_source_fix_plan_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _status_from_actions(actions: list[ProfileSourceFixPlanAction]) -> str:
    if any(action.severity == "high" for action in actions):
        return "blocked"
    if any(action.severity == "medium" for action in actions):
        return "needs_review"
    if actions:
        return "ready_with_notes"
    return "ready"


def _profile_severity_groups(actions: list[ProfileSourceFixPlanAction]) -> list[tuple[str, dict[str, int]]]:
    grouped: dict[str, dict[str, int]] = {}
    for action in actions:
        profile_id = action.profile_id or "workspace"
        counts = grouped.setdefault(profile_id, {"high": 0, "medium": 0, "low": 0})
        if action.severity in counts:
            counts[action.severity] += 1
    return sorted(grouped.items())


def _title_for_issue(issue_code: str) -> str:
    titles = {
        "profile_source_records_missing": "Record profile source metadata",
        "profile_verified_without_verified_source": "Resolve verified profile source gap",
        "profile_source_unknown_status": "Normalize profile source status",
        "profile_source_not_verified": "Review non-verified source",
        "profile_source_locator_missing": "Add source locator",
        "profile_source_retrieved_at_missing": "Record retrieval date",
        "profile_source_hash_missing": "Add or document source hash",
        "profile_source_verified_by_missing": "Record reviewer",
        "profile_source_unresolved_risk_flags": "Resolve source risk flags",
        "profile_source_file_missing": "Restore source file",
        "profile_source_hash_mismatch": "Re-review changed source file",
    }
    return titles.get(issue_code, "Review profile source queue item")


def _command(workspace: Path, command: str, *args: str) -> str:
    del workspace
    parts = ["python", "-m", "k_resdev_skill", command, *args]
    return " ".join(_quote(part) for part in parts)


def _quote(value: str) -> str:
    text = str(value)
    if not text:
        return '""'
    if any(char.isspace() for char in text) or any(char in text for char in ['"', "|", "<", ">"]):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def _resolve_workspace_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else workspace / candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _action_id(queue_id: str | None, issue_code: str) -> str:
    digest = hashlib.sha256(f"{queue_id or ''}|{issue_code}".encode("utf-8")).hexdigest()
    return f"PSF-{digest[:12].upper()}"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
