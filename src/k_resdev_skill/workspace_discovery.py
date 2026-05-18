from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from .models import WorkspaceDiscoveryItem, WorkspaceDiscoveryResult, WorkspaceSetupProposal

STANDARD_DIRS = (
    "inbox",
    "state",
    "evidence",
    "references",
    "reports",
    "reports/analysis",
    "state/approvals",
    "state/bibliography-reviews",
    "state/citation-support",
    "state/checkpoints",
)
STARTER_FILES = (
    "README.k-resdev.md",
    "state/project-state.json",
    "state/project-profile.json",
    "state/profile-sources.json",
)
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
DOCUMENT_SUFFIXES = {".doc", ".docx", ".hwp", ".hwpx", ".md", ".pdf", ".txt"}
DATA_SUFFIXES = {".csv", ".jsonl", ".tsv", ".xls", ".xlsx"}
REFERENCE_SUFFIXES = {".bib", ".ris", ".pdf", ".json", ".md", ".txt"}
KNOWN_SUFFIXES = DOCUMENT_SUFFIXES | DATA_SUFFIXES | REFERENCE_SUFFIXES | {".html", ".json", ".log", ".py"}
MAX_LARGE_FILE_BYTES = 50 * 1024 * 1024


def discover_workspace(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
    max_items: int = 500,
) -> WorkspaceDiscoveryResult:
    """Inspect a local folder and propose K-ResDev setup steps without moving raw files."""

    workspace = Path(root)
    warnings: list[str] = []
    items: list[WorkspaceDiscoveryItem] = []

    if not workspace.exists():
        missing_dirs = list(STANDARD_DIRS)
        proposals = [
            _proposal(
                workspace,
                "high",
                "Initialize a K-ResDev workspace skeleton",
                "The root path does not exist yet; initialization can create only standard K-ResDev folders and starter metadata.",
                f'python -m k_resdev_skill init-workspace --root "{workspace}" --project-id "<project-id>" --title "<project-title>"',
                "initialize",
                creates=[str(workspace / relative) for relative in STANDARD_DIRS],
                roles=["workspace_skeleton"],
            )
        ]
        result = WorkspaceDiscoveryResult(
            root=str(workspace),
            status="needs_setup",
            missing_standard_dirs=missing_dirs,
            missing_starter_files=list(STARTER_FILES),
            proposals=proposals,
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
            warnings=["root_missing"],
        )
        return _write_result(result, output_path, json_path)

    if not workspace.is_dir():
        result = WorkspaceDiscoveryResult(
            root=str(workspace),
            status="blocked",
            proposals=[
                _proposal(
                    workspace,
                    "high",
                    "Choose a directory root",
                    "Workspace discovery requires a directory; this path is a file.",
                    None,
                    "review",
                    review=[str(workspace)],
                    roles=["workspace_root"],
                )
            ],
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
            warnings=["root_not_directory"],
        )
        return _write_result(result, output_path, json_path)

    missing_dirs = [relative for relative in STANDARD_DIRS if not (workspace / relative).is_dir()]
    missing_starter_files = [relative for relative in STARTER_FILES if not (workspace / relative).is_file()]
    standard_dir_count = len(STANDARD_DIRS) - len(missing_dirs)

    for path in _iter_scan_paths(workspace, max_items=max_items, warnings=warnings):
        item = _discovery_item(workspace, path)
        items.append(item)

    role_counts = _count(item.role for item in items)
    loose_candidates = [item for item in items if "outside_standard_workspace_dirs" in item.risk_flags and item.path_type == "file"]
    proposals = _proposals(workspace, missing_dirs, missing_starter_files, items, loose_candidates)
    status = _status(missing_dirs, missing_starter_files, loose_candidates, proposals, warnings)
    result = WorkspaceDiscoveryResult(
        root=str(workspace),
        status=status,
        scanned_count=len(items),
        file_count=sum(1 for item in items if item.path_type == "file"),
        directory_count=sum(1 for item in items if item.path_type == "directory"),
        standard_dir_count=standard_dir_count,
        missing_standard_dirs=missing_dirs,
        missing_starter_files=missing_starter_files,
        loose_candidate_count=len(loose_candidates),
        role_counts=role_counts,
        items=sorted(items, key=lambda item: (item.path_type, item.path)),
        proposals=proposals,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )
    return _write_result(result, output_path, json_path)


def render_workspace_discovery_markdown(result: WorkspaceDiscoveryResult) -> str:
    lines = [
        "# K-ResDev Workspace Discovery",
        "",
        "> Read-only discovery projection. This inspects local paths and proposes additive setup steps; it does not move, rename, delete, or modify raw files.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Scanned paths | {result.scanned_count} |",
        f"| Files | {result.file_count} |",
        f"| Directories | {result.directory_count} |",
        f"| Standard dirs present | {result.standard_dir_count} |",
        f"| Missing standard dirs | {_format_list(result.missing_standard_dirs)} |",
        f"| Missing starter files | {_format_list(result.missing_starter_files)} |",
        f"| Loose candidates | {result.loose_candidate_count} |",
        f"| Setup proposals | {len(result.proposals)} |",
        f"| Warnings | {_format_list(result.warnings)} |",
        "",
        "## Role Counts",
        "",
        "| Role | Count |",
        "|---|---:|",
    ]
    if not result.role_counts:
        lines.append("| - | 0 |")
    for role, count in result.role_counts.items():
        lines.append(f"| {_escape(role)} | {count} |")
    lines.extend(
        [
            "",
            "## Setup Proposals",
            "",
            "| Priority | Proposal | Operation | Destructive | Command | Review Paths |",
            "|---|---|---|---:|---|---|",
        ]
    )
    if not result.proposals:
        lines.append("| ok | No setup proposal generated. | - | false | - | - |")
    for proposal in result.proposals:
        command = f"`{_escape(proposal.command)}`" if proposal.command else "-"
        lines.append(
            "| {priority} | {title} | {operation} | {destructive} | {command} | {review} |".format(
                priority=_escape(proposal.priority),
                title=_escape(proposal.title),
                operation=_escape(proposal.operation_type),
                destructive=str(proposal.destructive).lower(),
                command=command,
                review=_format_list(proposal.review_paths),
            )
        )
    lines.extend(
        [
            "",
            "## Discovered Paths",
            "",
            "| Path | Type | Role | Size | Confidence | Risk Flags |",
            "|---|---|---|---:|---|---|",
        ]
    )
    if not result.items:
        lines.append("| - | - | No paths discovered. | - | - | - |")
    for item in result.items:
        lines.append(
            "| {path} | {kind} | {role} | {size} | {confidence} | {flags} |".format(
                path=f"`{_escape(item.path)}`",
                kind=_escape(item.path_type),
                role=_escape(item.role),
                size=item.size_bytes if item.size_bytes is not None else "-",
                confidence=_escape(item.confidence),
                flags=_format_list(item.risk_flags),
            )
        )
    lines.append("")
    return "\n".join(lines)


def load_workspace_discovery(path: str | Path) -> WorkspaceDiscoveryResult:
    return WorkspaceDiscoveryResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def _iter_scan_paths(workspace: Path, max_items: int, warnings: list[str]) -> list[Path]:
    paths: list[Path] = []
    if max_items <= 0:
        warnings.append("max_items_zero")
        return paths
    stack = [workspace]
    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.as_posix(), reverse=True)
        except OSError as exc:
            warnings.append(f"scan_unreadable:{_display_path(workspace, current)}:{exc.__class__.__name__}")
            continue
        for child in children:
            if len(paths) >= max_items:
                warnings.append("scan_truncated")
                return paths
            if child.is_dir() and child.name in SKIP_DIR_NAMES:
                continue
            paths.append(child)
            if child.is_dir():
                stack.append(child)
    return paths


def _discovery_item(workspace: Path, path: Path) -> WorkspaceDiscoveryItem:
    path_type = "directory" if path.is_dir() else "file"
    relative = _display_path(workspace, path)
    suffix = path.suffix.lower() if path.is_file() else None
    size = _file_size(path) if path.is_file() else None
    role, confidence, notes = _role(workspace, path)
    risk_flags = _risk_flags(workspace, path, role, size)
    return WorkspaceDiscoveryItem(
        path=relative,
        path_type=path_type,
        role=role,
        size_bytes=size,
        suffix=suffix,
        confidence=confidence,
        risk_flags=risk_flags,
        notes=notes,
    )


def _role(workspace: Path, path: Path) -> tuple[str, str, list[str]]:
    relative = _display_path(workspace, path)
    normalized = relative.replace("\\", "/")
    name = path.name.lower()
    suffix = path.suffix.lower()
    notes: list[str] = []
    if path.is_dir():
        if normalized in STANDARD_DIRS:
            return "standard_directory", "high", notes
        if name in {"raw", "docs", "documents", "data", "papers", "literature"}:
            return "legacy_source_directory", "medium", ["candidate_source_folder"]
        return "directory", "medium", notes
    if normalized == "README.k-resdev.md":
        return "workspace_readme", "high", notes
    if normalized == "state/project-state.json":
        return "project_state", "high", notes
    if normalized == "state/project-profile.json":
        return "project_profile", "high", notes
    if normalized == "state/profile-sources.json":
        return "profile_sources", "high", notes
    if normalized == "state/evidence-index.json":
        return "evidence_index", "high", notes
    if normalized == "state/bibliography-index.json":
        return "bibliography_index", "high", notes
    if normalized == "state/literature-corpus.json":
        return "reference_corpus", "high", notes
    if normalized.startswith("state/"):
        return "state_artifact", "medium", notes
    if normalized.startswith("evidence/"):
        return "evidence_artifact", "medium", notes
    if normalized.startswith("reports/analysis/"):
        return "analysis_artifact", "medium", notes
    if normalized.startswith("reports/"):
        if suffix in {".md", ".docx", ".html", ".txt"}:
            return "report_or_projection", "medium", notes
        return "report_artifact", "medium", notes
    if normalized.startswith("references/"):
        return ("reference_source" if suffix in REFERENCE_SUFFIXES else "reference_sidecar"), "medium", notes
    if normalized.startswith("inbox/"):
        return _source_role(name, suffix, default="raw_source")
    return _source_role(name, suffix, default="loose_candidate")


def _source_role(name: str, suffix: str, default: str) -> tuple[str, str, list[str]]:
    if suffix in DATA_SUFFIXES:
        return "data_source", "high", []
    if suffix in {".bib", ".ris"} or "zotero" in name or "library" in name:
        return "reference_source", "high", []
    if any(token in name for token in ("budget", "receipt", "invoice", "expense", "예산", "영수", "정산")):
        return "budget_candidate", "medium", []
    if any(token in name for token in ("plan", "proposal", "agreement", "milestone", "계획", "협약", "마일스톤")):
        return "plan_candidate", "medium", []
    if any(token in name for token in ("paper", "literature", "reference", "논문", "문헌")):
        return "reference_source", "medium", []
    if suffix in DOCUMENT_SUFFIXES:
        return "document_source", "medium", []
    if suffix in KNOWN_SUFFIXES:
        return default, "low", []
    return "unknown_file", "low", []


def _risk_flags(workspace: Path, path: Path, role: str, size: int | None) -> list[str]:
    flags: list[str] = []
    relative = _display_path(workspace, path).replace("\\", "/")
    first = relative.split("/", 1)[0]
    if path.is_file() and first not in {"inbox", "state", "evidence", "references", "reports"} and path.name != "README.k-resdev.md":
        flags.append("outside_standard_workspace_dirs")
    if role in {"loose_candidate", "unknown_file", "document_source", "data_source", "budget_candidate", "plan_candidate"} and "outside_standard_workspace_dirs" in flags:
        flags.append("raw_candidate_needs_manual_placement")
    if path.is_file() and path.suffix.lower() not in KNOWN_SUFFIXES:
        flags.append("unsupported_for_automated_intake")
    if size is not None and size > MAX_LARGE_FILE_BYTES:
        flags.append("large_file_metadata_only")
    return _unique(flags)


def _proposals(
    workspace: Path,
    missing_dirs: list[str],
    missing_starter_files: list[str],
    items: list[WorkspaceDiscoveryItem],
    loose_candidates: list[WorkspaceDiscoveryItem],
) -> list[WorkspaceSetupProposal]:
    proposals: list[WorkspaceSetupProposal] = []
    if missing_dirs or missing_starter_files:
        proposals.append(
            _proposal(
                workspace,
                "high",
                "Initialize a K-ResDev workspace skeleton",
                "Standard folders or starter metadata are missing; initialization only creates missing skeleton files and does not overwrite existing files.",
                f'python -m k_resdev_skill init-workspace --root "{workspace}" --project-id "<project-id>" --title "<project-title>"',
                "initialize",
                creates=[str(workspace / path) for path in missing_dirs + missing_starter_files],
                roles=["workspace_skeleton"],
            )
        )
    if loose_candidates:
        proposals.append(
            _proposal(
                workspace,
                "medium",
                "Review loose source candidates before intake",
                "Potential raw sources were found outside standard K-ResDev folders. Review placement manually; discovery does not move files.",
                None,
                "review",
                review=[item.path for item in loose_candidates[:20]],
                roles=sorted({item.role for item in loose_candidates}),
            )
        )
    inbox_sources = [item for item in items if item.path.startswith("inbox/") and item.path_type == "file"]
    evidence_index_present = any(item.role == "evidence_index" for item in items)
    if inbox_sources and not evidence_index_present:
        proposals.append(
            _proposal(
                workspace,
                "high",
                "Run evidence intake on inbox sources",
                "Inbox contains candidate raw files but no evidence index was detected.",
                f'python -m k_resdev_skill intake --inbox "{workspace / "inbox"}" --state-dir "{workspace / "state"}" --evidence-dir "{workspace / "evidence"}"',
                "generate",
                roles=["raw_source", "evidence_index"],
            )
        )
    reference_sources = [item for item in items if item.path.startswith("references/") and item.role == "reference_source"]
    reference_corpus_present = any(item.role == "reference_corpus" for item in items)
    if reference_sources and not reference_corpus_present:
        proposals.append(
            _proposal(
                workspace,
                "medium",
                "Build the reference corpus review index",
                "Reference files are present but no literature corpus index was detected.",
                f'python -m k_resdev_skill reference-corpus --root "{workspace}" --output "{workspace / "reports" / "reference-corpus-summary.md"}" --json "{workspace / "state" / "literature-corpus.json"}" --rejections "{workspace / "state" / "reference-rejection-log.json"}"',
                "generate",
                roles=["reference_source", "reference_corpus"],
            )
        )
    review_pack_present = any(item.path == "state/workspace-review-pack.json" for item in items)
    if not review_pack_present and not missing_dirs:
        proposals.append(
            _proposal(
                workspace,
                "low",
                "Generate a workspace review pack",
                "A review pack gives one local bundle for readiness, summary, trace, approvals, claims, and setup state.",
                f'python -m k_resdev_skill workspace-review-pack --root "{workspace}"',
                "generate",
                roles=["review_pack"],
            )
        )
    return proposals


def _proposal(
    workspace: Path,
    priority: str,
    title: str,
    rationale: str,
    command: str | None,
    operation_type: str,
    creates: list[str] | None = None,
    review: list[str] | None = None,
    roles: list[str] | None = None,
) -> WorkspaceSetupProposal:
    digest = hashlib.sha256(f"{workspace}|{title}|{command or ''}".encode("utf-8")).hexdigest()[:8].upper()
    return WorkspaceSetupProposal(
        proposal_id=f"WSP-{digest}",
        priority=priority,
        title=title,
        rationale=rationale,
        command=command,
        operation_type=operation_type,
        destructive=False,
        creates_paths=creates or [],
        review_paths=review or [],
        related_roles=roles or [],
    )


def _status(
    missing_dirs: list[str],
    missing_starter_files: list[str],
    loose_candidates: list[WorkspaceDiscoveryItem],
    proposals: list[WorkspaceSetupProposal],
    warnings: list[str],
) -> str:
    if any(warning.startswith("scan_unreadable") for warning in warnings):
        return "needs_review"
    if missing_dirs or missing_starter_files:
        return "needs_setup"
    if loose_candidates:
        return "needs_review"
    if proposals:
        return "ready_with_notes"
    return "ready"


def _write_result(result: WorkspaceDiscoveryResult, output_path: str | Path | None, json_path: str | Path | None) -> WorkspaceDiscoveryResult:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_workspace_discovery_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def _file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def _display_path(workspace: Path, path: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return str(path)


def _count(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _format_list(values: list[str]) -> str:
    if not values:
        return "-"
    return ", ".join(f"`{_escape(value)}`" for value in values[:20])


def _escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()
