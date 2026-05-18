from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    ProfileIntegrityFinding,
    ProfileIntegrityResult,
    ProfileSource,
    ProjectProfile,
    VerifiedProfilePack,
)
from .profile_registry import load_project_profile

PROFILE_SOURCE_STATUSES = {"needs_review", "verified", "rejected", "superseded"}


def default_profile_sources_path(root: str | Path) -> Path:
    return Path(root) / "state" / "profile-sources.json"


def create_profile_source_record(
    profile_id: str,
    title: str,
    source_url: str | None = None,
    source_file: str | Path | None = None,
    retrieved_at: str | None = None,
    source_hash: str | None = None,
    verified_by: str | None = None,
    review_status: str = "needs_review",
    validity_notes: str | None = None,
    risk_flags: list[str] | None = None,
    source_id: str | None = None,
    root: str | Path | None = None,
) -> ProfileSource:
    """Create a profile source record without asserting official validity."""

    risks = list(risk_flags or [])
    normalized_status = _status(review_status)
    file_text = str(source_file) if source_file is not None else None
    resolved_file = _resolve_file(file_text, Path(root) if root is not None else None)
    captured_hash = _normalize_hash(source_hash)
    source_size_bytes: int | None = None

    if resolved_file is not None:
        captured_hash = captured_hash or _sha256_file(resolved_file)
        source_size_bytes = resolved_file.stat().st_size
    elif file_text:
        risks.append("source_file_missing")

    if normalized_status == "verified" and not verified_by:
        risks.append("verified_by_missing")
    if normalized_status == "verified" and not captured_hash:
        risks.append("verified_source_hash_missing")
    if not source_url and not file_text:
        risks.append("source_locator_missing")
    if not retrieved_at:
        risks.append("retrieved_at_missing")

    record = ProfileSource(
        source_id=source_id
        or _source_id(
            profile_id=profile_id,
            title=title,
            source_url=source_url,
            source_file=file_text,
            source_hash=captured_hash,
        ),
        profile_id=profile_id,
        title=title,
        source_url=source_url,
        source_file=file_text,
        retrieved_at=retrieved_at,
        source_hash=captured_hash,
        source_size_bytes=source_size_bytes,
        verified_by=verified_by,
        review_status=normalized_status,
        validity_notes=validity_notes,
        risk_flags=_unique(risks),
    )
    return record


def load_profile_sources(profile_sources_path: str | Path) -> list[ProfileSource]:
    path = Path(profile_sources_path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("profile source index must be a JSON list or an object with an items list")
    return [ProfileSource.model_validate(item) for item in items]


def write_profile_sources(records: list[ProfileSource], profile_sources_path: str | Path) -> Path:
    path = Path(profile_sources_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_records = sorted(records, key=lambda item: (item.profile_id, item.source_id))
    payload = [record.model_dump(mode="json") for record in sorted_records]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def record_profile_source(
    record: ProfileSource,
    profile_sources_path: str | Path,
) -> ProfileSource:
    records = load_profile_sources(profile_sources_path)
    by_id = {item.source_id: item for item in records}
    by_id[record.source_id] = record
    write_profile_sources(list(by_id.values()), profile_sources_path)
    return record


def summarize_profile_sources(
    root: str | Path,
    profile_id: str | None = None,
    profile_sources_path: str | Path | None = None,
    profile_path: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> VerifiedProfilePack:
    workspace = Path(root)
    profile = _load_profile(profile_path or workspace / "state" / "project-profile.json")
    selected_profile_id = profile_id or (profile.profile_id if profile else "needs_review")
    source_path = Path(profile_sources_path) if profile_sources_path is not None else default_profile_sources_path(workspace)
    warnings: list[str] = []
    try:
        sources = [item for item in load_profile_sources(source_path) if item.profile_id == selected_profile_id]
    except Exception as exc:
        sources = []
        warnings.append(f"profile_sources_unreadable:{exc}")

    pack = _pack_for_profile(
        selected_profile_id,
        sources,
        profile=profile,
        profile_path=Path(profile_path) if profile_path is not None else workspace / "state" / "project-profile.json",
        warnings=warnings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_source_summary_markdown(pack), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(pack.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return pack


def generate_profile_integrity(
    root: str | Path,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfileIntegrityResult:
    """Check project profile source records without certifying official rules."""

    workspace = Path(root)
    profile_path = workspace / "state" / "project-profile.json"
    source_path = default_profile_sources_path(workspace)
    findings: list[ProfileIntegrityFinding] = []
    warnings: list[str] = []
    profile: ProjectProfile | None = None

    if not profile_path.exists():
        findings.append(
            _finding(
                "profile_missing",
                "medium",
                "Project profile is missing.",
                path=profile_path,
                suggested_action="Run init-workspace or add state/project-profile.json.",
            )
        )
    else:
        try:
            profile = load_project_profile(profile_path)
        except Exception as exc:
            findings.append(
                _finding(
                    "profile_unreadable",
                    "medium",
                    f"Project profile could not be read: {exc}",
                    path=profile_path,
                    suggested_action="Fix state/project-profile.json.",
                )
            )

    profile_id = profile.profile_id if profile else None
    sources: list[ProfileSource] = []
    if not source_path.exists():
        findings.append(
            _finding(
                "profile_sources_missing",
                "medium",
                "No profile source index found.",
                path=source_path,
                suggested_action="Record profile source metadata before treating templates as verified.",
            )
        )
    else:
        try:
            all_sources = load_profile_sources(source_path)
            sources = [source for source in all_sources if profile_id is None or source.profile_id == profile_id]
        except Exception as exc:
            warnings.append(f"profile_sources_unreadable:{exc}")
            findings.append(
                _finding(
                    "profile_sources_unreadable",
                    "medium",
                    f"Profile source index could not be read: {exc}",
                    path=source_path,
                    suggested_action="Fix state/profile-sources.json.",
                )
            )

    if profile is not None and profile.status == "verified" and not any(source.review_status == "verified" for source in sources):
        findings.append(
            _finding(
                "profile_verified_without_verified_source",
                "high",
                f"Profile `{profile.profile_id}` is marked verified but has no verified source record.",
                path=profile_path,
                suggested_action="Add a verified profile source record or set the profile back to needs_review.",
            )
        )
    if profile is not None and not sources:
        findings.append(
            _finding(
                "profile_sources_empty",
                "medium",
                f"No profile source records exist for `{profile.profile_id}`.",
                path=source_path,
                suggested_action="Record official source metadata before treating profile templates as verified.",
            )
        )
    if profile is not None and profile.status == "needs_review":
        findings.append(
            _finding(
                "profile_needs_review",
                "medium",
                f"Profile `{profile.profile_id}` remains needs_review.",
                path=profile_path,
                suggested_action="Record official source metadata and supplied human review before official use.",
            )
        )

    for source in sources:
        findings.extend(_source_findings(workspace, source))

    pack = _pack_for_profile(
        profile_id or "needs_review",
        sources,
        profile=profile,
        profile_path=profile_path,
        warnings=warnings,
    )
    findings = _dedupe_findings(findings)
    result = ProfileIntegrityResult(
        root=str(workspace),
        profile_id=profile_id,
        profile_status=profile.status if profile else None,
        status=_status_from_findings(findings),
        source_count=len(sources),
        verified_source_count=sum(1 for source in sources if source.review_status == "verified"),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        findings=findings,
        profile_pack=pack,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=warnings,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_integrity_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_profile_source_summary_markdown(pack: VerifiedProfilePack) -> str:
    lines = [
        "# Profile Source Summary",
        "",
        "> Source summary projection only. This records local evidence for profile review; it does not certify official agency rules or current legal validity.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Profile | {_escape(pack.profile_id)} |",
        f"| Profile status | {_escape(pack.profile_status or '-')} |",
        f"| Summary status | {_escape(pack.status)} |",
        f"| Source count | {pack.source_count} |",
        f"| Verified sources | {pack.verified_source_count} |",
        f"| Needs-review sources | {pack.needs_review_source_count} |",
        f"| Rejected sources | {pack.rejected_source_count} |",
        f"| Missing retrieved_at | {pack.missing_retrieved_at_count} |",
        f"| Missing hash | {pack.missing_hash_count} |",
        f"| Latest retrieved_at | {_escape(pack.latest_retrieved_at or '-')} |",
        f"| Warnings | {_escape(', '.join(pack.warnings) or '-')} |",
        "",
        "## Sources",
        "",
        "| Status | Source ID | Title | URL | File | Retrieved | Hash | Verified By | Risk Flags |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    if not pack.sources:
        lines.append("| missing | - | No profile source records found. | - | - | - | - | - | profile_sources_missing |")
    for source in pack.sources:
        lines.append(
            "| {status} | `{source_id}` | {title} | {url} | {file} | {retrieved} | {hash_value} | {verified_by} | {risks} |".format(
                status=_escape(source.review_status),
                source_id=_escape(source.source_id),
                title=_escape(source.title),
                url=_escape(source.source_url or "-"),
                file=_escape(source.source_file or "-"),
                retrieved=_escape(source.retrieved_at or "-"),
                hash_value=_escape(source.source_hash or "-"),
                verified_by=_escape(source.verified_by or "-"),
                risks=_escape(", ".join(source.risk_flags) or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_profile_integrity_markdown(result: ProfileIntegrityResult) -> str:
    lines = [
        "# Profile Integrity",
        "",
        "> Profile integrity projection only. This checks local profile-source metadata; it does not certify official agency compliance, legal currency, or submission readiness.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Profile | {_escape(result.profile_id or 'missing')} |",
        f"| Profile status | {_escape(result.profile_status or 'missing')} |",
        f"| Integrity status | {_escape(result.status)} |",
        f"| Source count | {result.source_count} |",
        f"| Verified sources | {result.verified_source_count} |",
        f"| Findings | {result.finding_count} |",
        f"| High findings | {result.high_count} |",
        f"| Medium findings | {result.medium_count} |",
        f"| Low findings | {result.low_count} |",
        f"| Warnings | {_escape(', '.join(result.warnings) or '-')} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Message | Source | Path | Suggested Action |",
        "|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | profile_integrity_ready | No profile source findings detected. | - | - | Keep official source records current. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {message} | {source} | {path} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                message=_escape(finding.message),
                source=_escape(finding.source_id or "-"),
                path=_escape(finding.path or "-"),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    if result.profile_pack is not None:
        lines.extend(["", "## Source Pack", ""])
        lines.append(render_profile_source_summary_markdown(result.profile_pack).split("## Sources", 1)[-1].strip())
    lines.append("")
    return "\n".join(lines)


def _source_findings(workspace: Path, source: ProfileSource) -> list[ProfileIntegrityFinding]:
    findings: list[ProfileIntegrityFinding] = []
    if source.review_status not in PROFILE_SOURCE_STATUSES:
        findings.append(
            _finding(
                "profile_source_unknown_status",
                "medium",
                f"Profile source `{source.source_id}` has unknown review_status `{source.review_status}`.",
                source_id=source.source_id,
                suggested_action="Use needs_review, verified, rejected, or superseded.",
            )
        )
    if source.review_status != "verified":
        severity = "high" if source.review_status in {"rejected", "superseded"} else "medium"
        findings.append(
            _finding(
                "profile_source_not_verified",
                severity,
                f"Profile source `{source.source_id}` is `{source.review_status}`.",
                source_id=source.source_id,
                path=source.source_file,
                suggested_action="Keep the profile in needs_review or record supplied human verification.",
            )
        )
    if not source.source_url and not source.source_file:
        findings.append(
            _finding(
                "profile_source_locator_missing",
                "medium",
                f"Profile source `{source.source_id}` has no URL or local source file.",
                source_id=source.source_id,
                suggested_action="Record a source_url or source_file.",
            )
        )
    if not source.retrieved_at:
        findings.append(
            _finding(
                "profile_source_retrieval_missing",
                "medium",
                f"Profile source `{source.source_id}` has no retrieved_at timestamp/date.",
                source_id=source.source_id,
                path=source.source_file,
                suggested_action="Record when the source was retrieved or reviewed.",
            )
        )
    if not source.source_hash:
        findings.append(
            _finding(
                "profile_source_hash_missing",
                "medium" if source.review_status == "verified" else "low",
                f"Profile source `{source.source_id}` has no source hash.",
                source_id=source.source_id,
                path=source.source_file,
                suggested_action="Store a local official source copy or hash-backed review artifact when possible.",
            )
        )
    if source.review_status == "verified" and not source.verified_by:
        findings.append(
            _finding(
                "profile_source_verified_by_missing",
                "medium",
                f"Profile source `{source.source_id}` is verified but has no verified_by value.",
                source_id=source.source_id,
                path=source.source_file,
                suggested_action="Record the supplied human reviewer or owner.",
            )
        )
    if source.source_file:
        path = _resolve_file(source.source_file, workspace)
        if path is None:
            findings.append(
                _finding(
                    "profile_source_file_missing",
                    "high",
                    f"Profile source file `{source.source_file}` is missing.",
                    source_id=source.source_id,
                    path=source.source_file,
                    suggested_action="Restore the local source file or update the profile source record.",
                )
            )
        elif source.source_hash:
            actual = _sha256_file(path)
            if actual != _normalize_hash(source.source_hash):
                findings.append(
                    _finding(
                        "profile_source_hash_mismatch",
                        "high",
                        f"Profile source file `{source.source_file}` changed after recording.",
                        source_id=source.source_id,
                        path=source.source_file,
                        suggested_action="Re-review the source and record a new hash-backed profile source record.",
                    )
                )
    return findings


def _pack_for_profile(
    profile_id: str,
    sources: list[ProfileSource],
    profile: ProjectProfile | None,
    profile_path: Path | None,
    warnings: list[str],
    markdown_path: str | None = None,
    json_path: str | None = None,
) -> VerifiedProfilePack:
    verified = [source for source in sources if source.review_status == "verified"]
    needs_review = [source for source in sources if source.review_status == "needs_review"]
    rejected = [source for source in sources if source.review_status in {"rejected", "superseded"}]
    retrieved_values = sorted(source.retrieved_at for source in sources if source.retrieved_at)
    if rejected:
        status = "blocked"
    elif profile is not None and profile.status == "verified" and verified:
        status = "verified"
    elif verified:
        status = "source_verified_profile_needs_review"
    else:
        status = "needs_review"
    return VerifiedProfilePack(
        profile_id=profile_id,
        profile_path=str(profile_path) if profile_path is not None else None,
        profile_status=profile.status if profile is not None else None,
        status=status,
        source_count=len(sources),
        verified_source_count=len(verified),
        needs_review_source_count=len(needs_review),
        rejected_source_count=len(rejected),
        missing_retrieved_at_count=sum(1 for source in sources if not source.retrieved_at),
        missing_hash_count=sum(1 for source in sources if not source.source_hash),
        latest_retrieved_at=retrieved_values[-1] if retrieved_values else None,
        sources=sorted(sources, key=lambda item: item.source_id),
        warnings=_unique(warnings),
        markdown_path=markdown_path,
        json_path=json_path,
    )


def _load_profile(path: str | Path) -> ProjectProfile | None:
    target = Path(path)
    if not target.exists():
        return None
    return load_project_profile(target)


def _resolve_file(path: str | None, root: Path | None) -> Path | None:
    if not path:
        return None
    target = Path(path)
    candidates = [target]
    if root is not None and not target.is_absolute():
        candidates.append(root / target)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _source_id(profile_id: str, title: str, source_url: str | None, source_file: str | None, source_hash: str | None) -> str:
    digest = hashlib.sha256(
        "|".join([profile_id, title, source_url or "", source_file or "", source_hash or ""]).encode("utf-8")
    ).hexdigest()[:12].upper()
    return f"PSRC-{digest}"


def _status(value: str) -> str:
    text = str(value or "needs_review").strip()
    return text or "needs_review"


def _status_from_findings(findings: list[ProfileIntegrityFinding]) -> str:
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
    source_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> ProfileIntegrityFinding:
    return ProfileIntegrityFinding(
        code=code,
        severity=severity,
        message=message,
        source_id=source_id,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _dedupe_findings(findings: list[ProfileIntegrityFinding]) -> list[ProfileIntegrityFinding]:
    seen: set[tuple[str, str, str | None, str | None]] = set()
    result: list[ProfileIntegrityFinding] = []
    for finding in findings:
        key = (finding.code, finding.message, finding.source_id, finding.path)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.code, item.message))


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _normalize_hash(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    return text if text.lower().startswith("sha256:") else f"sha256:{text}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
