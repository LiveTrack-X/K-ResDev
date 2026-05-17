from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .evidence_index import load_evidence_index
from .models import EvidenceItem, EvidenceSourceVerificationItem, EvidenceSourceVerificationResult

_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")


def verify_evidence_sources(
    evidence_index_json: str | Path,
    root: str | Path | None = None,
    inbox: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> EvidenceSourceVerificationResult:
    """Verify indexed evidence source files against saved source hashes."""

    index_path = Path(evidence_index_json)
    root_path = Path(root) if root is not None else None
    inbox_path = Path(inbox) if inbox is not None else None
    try:
        evidence = load_evidence_index(index_path)
    except Exception as exc:
        result = EvidenceSourceVerificationResult(
            evidence_index_path=str(index_path),
            root=str(root_path) if root_path is not None else None,
            inbox=str(inbox_path) if inbox_path is not None else None,
            valid=False,
            markdown_path=str(output_path) if output_path else None,
            json_path=str(json_path) if json_path else None,
            warnings=[f"evidence_index_unreadable:{exc}"],
        )
        _write_result(result, output_path, json_path)
        return result

    items = [_verify_source_group(source_file, source_items, root_path, inbox_path) for source_file, source_items in _group_by_source(evidence).items()]

    result = EvidenceSourceVerificationResult(
        evidence_index_path=str(index_path),
        root=str(root_path) if root_path is not None else None,
        inbox=str(inbox_path) if inbox_path is not None else None,
        valid=bool(items) and all(item.status == "ok" for item in items),
        source_count=len(items),
        ok_count=sum(1 for item in items if item.status == "ok"),
        missing_count=sum(1 for item in items if item.status == "missing"),
        mismatch_count=sum(1 for item in items if item.status == "mismatch"),
        no_hash_count=sum(1 for item in items if item.status == "no_expected_hash"),
        conflict_count=sum(1 for item in items if item.status == "conflicting_expected_hashes"),
        items=items,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
    )
    _write_result(result, output_path, json_path)
    return result


def _write_result(
    result: EvidenceSourceVerificationResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_evidence_source_verification_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def render_evidence_source_verification_markdown(result: EvidenceSourceVerificationResult) -> str:
    lines = [
        "# Evidence Source Verification",
        "",
        "> Local source-hash verification only. This checks whether indexed source files are present and unchanged; it does not validate official compliance or scientific truth.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Evidence index | `{_escape(result.evidence_index_path)}` |",
        f"| Root | `{_escape(result.root or '-')}` |",
        f"| Inbox | `{_escape(result.inbox or '-')}` |",
        f"| Valid | {result.valid} |",
        f"| Source count | {result.source_count} |",
        f"| OK | {result.ok_count} |",
        f"| Missing | {result.missing_count} |",
        f"| Mismatch | {result.mismatch_count} |",
        f"| No expected hash | {result.no_hash_count} |",
        f"| Conflicting hashes | {result.conflict_count} |",
        f"| Warnings | {_escape(', '.join(result.warnings) or '-')} |",
        "",
        "## Sources",
        "",
        "| Status | Source | Resolved Path | Evidence IDs | Expected Hash | Actual Hash | Warnings |",
        "|---|---|---|---|---|---|---|",
    ]
    if not result.items:
        warnings = ", ".join(result.warnings) or "evidence_index_empty"
        lines.append(f"| no_sources | - | - | - | - | - | {_escape(warnings)} |")
    for item in result.items:
        lines.append(
            "| {status} | {source} | {path} | {evidence} | {expected} | {actual} | {warnings} |".format(
                status=_escape(item.status),
                source=_escape(item.source_file),
                path=_escape(item.resolved_path or "-"),
                evidence=_escape(", ".join(item.evidence_ids) or "-"),
                expected=_escape(", ".join(item.expected_hashes) or "-"),
                actual=_escape(item.actual_hash or "-"),
                warnings=_escape(", ".join(item.warnings) or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _group_by_source(evidence: list[EvidenceItem]) -> dict[str, list[EvidenceItem]]:
    groups: dict[str, list[EvidenceItem]] = {}
    for item in evidence:
        groups.setdefault(item.source_file, []).append(item)
    return dict(sorted(groups.items()))


def _verify_source_group(
    source_file: str,
    evidence: list[EvidenceItem],
    root: Path | None,
    inbox: Path | None,
) -> EvidenceSourceVerificationItem:
    evidence_ids = sorted(item.evidence_id for item in evidence)
    expected_hashes: list[str] = []
    warnings: list[str] = []
    for item in evidence:
        normalized = _normalize_sha256(item.source_hash)
        if normalized is None:
            warnings.append(f"unverifiable_hash:{item.evidence_id}")
            continue
        if normalized not in expected_hashes:
            expected_hashes.append(normalized)

    resolved = _resolve_source(source_file, root, inbox)
    if resolved is None:
        return EvidenceSourceVerificationItem(
            source_file=source_file,
            evidence_ids=evidence_ids,
            expected_hashes=expected_hashes,
            status="missing",
            warnings=warnings,
        )

    actual = _sha256_file(resolved)
    byte_count = resolved.stat().st_size
    if not expected_hashes:
        status = "no_expected_hash"
    elif len(expected_hashes) > 1:
        status = "conflicting_expected_hashes"
    elif actual == expected_hashes[0]:
        status = "ok"
    else:
        status = "mismatch"

    return EvidenceSourceVerificationItem(
        source_file=source_file,
        resolved_path=str(resolved),
        evidence_ids=evidence_ids,
        expected_hashes=expected_hashes,
        actual_hash=actual,
        byte_count=byte_count,
        status=status,
        warnings=warnings,
    )


def _resolve_source(source_file: str, root: Path | None, inbox: Path | None) -> Path | None:
    source = Path(source_file)
    candidates: list[Path] = []
    if source.is_absolute():
        candidates.append(source)
    else:
        candidates.append(source)
        if root is not None:
            candidates.append(root / source)
            candidates.append(root / "inbox" / source)
        if inbox is not None:
            candidates.append(inbox / source)
            if root is not None and not inbox.is_absolute():
                candidates.append(root / inbox / source)

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _normalize_sha256(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip()
    if not _SHA256_RE.match(stripped):
        return None
    digest = stripped.split(":", 1)[1] if stripped.lower().startswith("sha256:") else stripped
    return f"sha256:{digest.lower()}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
