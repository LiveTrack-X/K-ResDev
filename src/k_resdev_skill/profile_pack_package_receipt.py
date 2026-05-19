from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .models import (
    ProfilePackPackageReceiptDecision,
    ProfilePackPackageReceiptFinding,
    ProfilePackPackageReceiptRecord,
    ProfilePackPackageReceiptSummaryResult,
)
from .profile_pack_investigation_package import load_profile_pack_investigation_package


RECEIPT_DECISIONS = {"received", "accepted_for_review", "needs_changes", "rejected"}


def default_profile_pack_package_receipts_dir(root: str | Path) -> Path:
    return Path(root) / "state" / "profile-pack-package-receipts"


def create_profile_pack_package_receipt_record(
    root: str | Path,
    decision: str | ProfilePackPackageReceiptDecision,
    reviewer: str,
    package_hash: str,
    package_path: str | Path | None = None,
    reviewed_at: str | None = None,
    notes: str | None = None,
    risk_flags: list[str] | None = None,
) -> ProfilePackPackageReceiptRecord:
    """Create a supplied reviewer receipt bound to a profile-pack investigation package hash."""

    workspace = Path(root)
    manifest_path = _resolve_workspace_path(workspace, package_path or workspace / "state" / "profile-pack-investigation-package.json")
    if not manifest_path.exists():
        raise ValueError(f"profile pack investigation package not found: {manifest_path}")
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer must not be blank")

    normalized_decision = _decision(decision)
    package = load_profile_pack_investigation_package(manifest_path)
    actual_hash = _sha256_file(manifest_path)
    if _normalize_hash(actual_hash) != _normalize_hash(package_hash):
        raise ValueError("package_hash does not match the current profile pack investigation package")

    reviewed = reviewed_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt_id = _receipt_id(package.package_id, normalized_decision, reviewer.strip(), reviewed, actual_hash)
    return ProfilePackPackageReceiptRecord(
        receipt_id=receipt_id,
        package_id=package.package_id,
        package_manifest_path=str(manifest_path),
        package_manifest_hash=actual_hash,
        decision=normalized_decision,
        reviewer=reviewer.strip(),
        reviewed_at=reviewed,
        notes=notes,
        risk_flags=risk_flags or [],
    )


def write_profile_pack_package_receipt_record(
    record: ProfilePackPackageReceiptRecord,
    receipts_dir: str | Path,
) -> Path:
    target_dir = Path(receipts_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{record.receipt_id}.json"
    target.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


def load_profile_pack_package_receipt_records(path: str | Path) -> list[ProfilePackPackageReceiptRecord]:
    source = Path(path)
    if not source.exists():
        return []
    if source.is_dir():
        records: list[ProfilePackPackageReceiptRecord] = []
        for record_path in sorted(source.glob("*.json")):
            records.extend(load_profile_pack_package_receipt_records(record_path))
        return records
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [ProfilePackPackageReceiptRecord.model_validate(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [ProfilePackPackageReceiptRecord.model_validate(item) for item in payload["records"]]
    return [ProfilePackPackageReceiptRecord.model_validate(payload)]


def summarize_profile_pack_package_receipts(
    root: str | Path,
    package_path: str | Path | None = None,
    receipts_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfilePackPackageReceiptSummaryResult:
    """Compare supplied reviewer receipts against the current package manifest."""

    workspace = Path(root)
    manifest_path = _resolve_workspace_path(workspace, package_path or workspace / "state" / "profile-pack-investigation-package.json")
    source_dir = _resolve_workspace_path(workspace, receipts_dir) if receipts_dir is not None else default_profile_pack_package_receipts_dir(workspace)
    warnings: list[str] = []
    findings: list[ProfilePackPackageReceiptFinding] = []
    records: list[ProfilePackPackageReceiptRecord] = []
    package_hash: str | None = None
    package_id: str | None = None
    package_status: str | None = None

    if not manifest_path.exists():
        result = _summary_result(
            workspace,
            manifest_path,
            "not_configured",
            package_hash,
            package_id,
            package_status,
            records,
            findings,
            warnings,
            output_path,
            json_path,
        )
        _write_outputs(result, output_path, json_path)
        return result

    try:
        package = load_profile_pack_investigation_package(manifest_path)
        package_hash = _sha256_file(manifest_path)
        package_id = package.package_id
        package_status = package.status
    except Exception as exc:
        findings.append(
            _finding(
                "profile_pack_package_unreadable",
                "high",
                f"Profile pack investigation package could not be read: {exc}",
                path=manifest_path,
                suggested_action="Regenerate profile-pack-investigation-package before recording reviewer receipts.",
            )
        )
        result = _summary_result(workspace, manifest_path, "blocked", package_hash, package_id, package_status, records, findings, warnings, output_path, json_path)
        _write_outputs(result, output_path, json_path)
        return result

    try:
        records = load_profile_pack_package_receipt_records(source_dir)
    except Exception as exc:
        warnings.append(f"profile_pack_package_receipts_unreadable:{exc}")
        findings.append(
            _finding(
                "profile_pack_package_receipts_unreadable",
                "medium",
                f"Profile pack package receipt records could not be read: {exc}",
                path=source_dir,
                suggested_action="Fix state/profile-pack-package-receipts before relying on package handoff state.",
            )
        )
        records = []

    if not records:
        findings.append(
            _finding(
                "profile_pack_package_receipt_missing",
                "medium",
                "Profile pack investigation package has no supplied reviewer receipt record.",
                package_id=package_id,
                path=source_dir,
                suggested_action="Run profile-pack-package-receipt-record after transferring the generated metadata package for review.",
            )
        )

    for record in records:
        if package_hash is not None and _normalize_hash(record.package_manifest_hash) != _normalize_hash(package_hash):
            findings.append(
                _finding(
                    "profile_pack_package_receipt_stale_hash",
                    "high",
                    f"Receipt `{record.receipt_id}` is bound to a stale package manifest hash.",
                    receipt_id=record.receipt_id,
                    package_id=record.package_id,
                    path=record.package_manifest_path,
                    suggested_action="Regenerate the package and record a fresh supplied reviewer receipt if the handoff still applies.",
                )
            )
        if record.package_id != package_id:
            findings.append(
                _finding(
                    "profile_pack_package_receipt_package_id_mismatch",
                    "high",
                    f"Receipt `{record.receipt_id}` references package `{record.package_id}`, not current package `{package_id}`.",
                    receipt_id=record.receipt_id,
                    package_id=record.package_id,
                    path=record.package_manifest_path,
                    suggested_action="Check whether the receipt belongs to an older package or regenerate the package receipt.",
                )
            )

    latest = _latest_record(records, package_id)
    if latest is not None:
        if latest.decision == "needs_changes":
            findings.append(
                _finding(
                    "profile_pack_package_receipt_needs_changes",
                    "medium",
                    f"Latest reviewer receipt `{latest.receipt_id}` says the package needs changes.",
                    receipt_id=latest.receipt_id,
                    package_id=latest.package_id,
                    path=latest.package_manifest_path,
                    suggested_action="Address the requested package changes before using the handoff as reviewed.",
                )
            )
        elif latest.decision == "rejected":
            findings.append(
                _finding(
                    "profile_pack_package_receipt_rejected",
                    "high",
                    f"Latest reviewer receipt `{latest.receipt_id}` rejected the package.",
                    receipt_id=latest.receipt_id,
                    package_id=latest.package_id,
                    path=latest.package_manifest_path,
                    suggested_action="Do not rely on the package handoff until a new package is prepared and reviewed.",
                )
            )

    result = _summary_result(
        workspace,
        manifest_path,
        _status_from_findings(findings),
        package_hash,
        package_id,
        package_status,
        records,
        findings,
        warnings,
        output_path,
        json_path,
    )
    _write_outputs(result, output_path, json_path)
    return result


def load_profile_pack_package_receipt_summary(path: str | Path) -> ProfilePackPackageReceiptSummaryResult:
    return ProfilePackPackageReceiptSummaryResult.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))


def render_profile_pack_package_receipt_summary_markdown(result: ProfilePackPackageReceiptSummaryResult) -> str:
    lines = [
        "# Profile Pack Package Receipt Summary",
        "",
        "> Supplied reviewer receipt log only. This records package transfer/review metadata; it does not promote profiles, resolve official-source checks, create approvals, or certify agency compliance.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Status | {_escape(result.status)} |",
        f"| Package path | `{_escape(result.package_path)}` |",
        f"| Package hash | {_escape(result.package_hash or '-')} |",
        f"| Package ID | {_escape(result.package_id or '-')} |",
        f"| Package status | {_escape(result.package_status or '-')} |",
        f"| Records | {result.record_count} |",
        f"| Received | {result.received_count} |",
        f"| Accepted for review | {result.accepted_for_review_count} |",
        f"| Needs changes | {result.needs_changes_count} |",
        f"| Rejected | {result.rejected_count} |",
        f"| Unresolved | {result.unresolved_count} |",
        f"| Stale records | {result.stale_record_count} |",
        f"| Missing package ID records | {result.missing_package_id_count} |",
        "",
        "## Findings",
        "",
        "| Severity | Code | Receipt | Package | Message | Suggested Action |",
        "|---|---|---|---|---|---|",
    ]
    if not result.findings:
        lines.append("| ok | profile_pack_package_receipts_ready | - | - | No package receipt findings detected. | Keep receipts current with package hashes. |")
    for finding in result.findings:
        lines.append(
            "| {severity} | {code} | {receipt} | {package} | {message} | {action} |".format(
                severity=_escape(finding.severity),
                code=_escape(finding.code),
                receipt=_escape(finding.receipt_id or "-"),
                package=_escape(finding.package_id or "-"),
                message=_escape(finding.message),
                action=_escape(finding.suggested_action or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Records",
            "",
            "| Decision | Receipt | Package | Reviewer | Reviewed At | Manifest Hash | Risk Flags | Notes |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    if not result.records:
        lines.append("| missing | - | - | - | - | - | profile_pack_package_receipt_missing | Record supplied reviewer receipt decisions. |")
    for record in sorted(result.records, key=lambda item: (item.package_id, item.reviewed_at, item.receipt_id)):
        lines.append(
            "| {decision} | `{receipt}` | `{package}` | {reviewer} | {reviewed} | `{manifest_hash}` | {risks} | {notes} |".format(
                decision=_escape(str(record.decision)),
                receipt=_escape(record.receipt_id),
                package=_escape(record.package_id),
                reviewer=_escape(record.reviewer),
                reviewed=_escape(record.reviewed_at),
                manifest_hash=_escape(record.package_manifest_hash),
                risks=_escape(", ".join(record.risk_flags) or "-"),
                notes=_escape(record.notes or "-"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Receipts document supplied human transfer/review metadata only.",
            "- Receipt decisions do not update profile status, source-review status, approval status, or compliance state.",
            "- `needs_changes` and `rejected` stay visible until a new package and receipt supersede them.",
            "",
        ]
    )
    return "\n".join(lines)


def _summary_result(
    workspace: Path,
    package_path: Path,
    status: str,
    package_hash: str | None,
    package_id: str | None,
    package_status: str | None,
    records: list[ProfilePackPackageReceiptRecord],
    findings: list[ProfilePackPackageReceiptFinding],
    warnings: list[str],
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> ProfilePackPackageReceiptSummaryResult:
    decision_counts = _decision_counts(records)
    findings = _dedupe_findings(findings)
    unresolved_count = sum(1 for finding in findings if finding.code in {"profile_pack_package_receipt_missing", "profile_pack_package_receipt_needs_changes", "profile_pack_package_receipt_rejected"})
    return ProfilePackPackageReceiptSummaryResult(
        root=str(workspace),
        status=status,
        package_path=str(package_path),
        package_hash=package_hash,
        package_id=package_id,
        package_status=package_status,
        record_count=len(records),
        received_count=decision_counts.get("received", 0),
        accepted_for_review_count=decision_counts.get("accepted_for_review", 0),
        needs_changes_count=decision_counts.get("needs_changes", 0),
        rejected_count=decision_counts.get("rejected", 0),
        unresolved_count=unresolved_count,
        stale_record_count=sum(1 for finding in findings if finding.code == "profile_pack_package_receipt_stale_hash"),
        missing_package_id_count=sum(1 for finding in findings if finding.code == "profile_pack_package_receipt_package_id_mismatch"),
        finding_count=len(findings),
        high_count=sum(1 for finding in findings if finding.severity == "high"),
        medium_count=sum(1 for finding in findings if finding.severity == "medium"),
        low_count=sum(1 for finding in findings if finding.severity == "low"),
        records=sorted(records, key=lambda item: (item.package_id, item.reviewed_at, item.receipt_id)),
        findings=findings,
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=_unique(warnings),
    )


def _write_outputs(
    result: ProfilePackPackageReceiptSummaryResult,
    output_path: str | Path | None,
    json_path: str | Path | None,
) -> None:
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_pack_package_receipt_summary_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _latest_record(records: list[ProfilePackPackageReceiptRecord], package_id: str | None) -> ProfilePackPackageReceiptRecord | None:
    candidates = [record for record in records if package_id is None or record.package_id == package_id]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item.reviewed_at, item.receipt_id))[-1]


def _decision(value: str | ProfilePackPackageReceiptDecision) -> str:
    decision = str(getattr(value, "value", value)).strip()
    if decision not in RECEIPT_DECISIONS:
        raise ValueError(f"Unsupported package receipt decision: {decision}")
    return decision


def _decision_counts(records: list[ProfilePackPackageReceiptRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        key = str(record.decision)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _finding(
    code: str,
    severity: str,
    message: str,
    receipt_id: str | None = None,
    package_id: str | None = None,
    path: str | Path | None = None,
    suggested_action: str | None = None,
) -> ProfilePackPackageReceiptFinding:
    return ProfilePackPackageReceiptFinding(
        code=code,
        severity=severity,
        message=message,
        receipt_id=receipt_id,
        package_id=package_id,
        path=str(path) if path is not None else None,
        suggested_action=suggested_action,
    )


def _status_from_findings(findings: list[ProfilePackPackageReceiptFinding]) -> str:
    if any(finding.severity == "high" for finding in findings):
        return "blocked"
    if any(finding.severity == "medium" for finding in findings):
        return "needs_review"
    if findings:
        return "ready_with_notes"
    return "ready"


def _dedupe_findings(findings: list[ProfilePackPackageReceiptFinding]) -> list[ProfilePackPackageReceiptFinding]:
    seen: set[tuple[str, str, str | None, str | None]] = set()
    result: list[ProfilePackPackageReceiptFinding] = []
    for finding in findings:
        key = (finding.code, finding.message, finding.receipt_id, finding.path)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return sorted(result, key=lambda item: (_severity_rank(item.severity), item.code, item.message))


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _resolve_workspace_path(workspace: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else workspace / candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _normalize_hash(value: str) -> str:
    return value.replace("sha256:", "").strip().lower()


def _receipt_id(package_id: str, decision: str, reviewer: str, reviewed_at: str, package_hash: str) -> str:
    digest = hashlib.sha256(f"{package_id}|{decision}|{reviewer}|{reviewed_at}|{package_hash}".encode("utf-8")).hexdigest()[:12].upper()
    return f"PPIR-{digest}"


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
