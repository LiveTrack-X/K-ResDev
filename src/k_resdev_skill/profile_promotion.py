from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .models import ProfilePromotionRecord, ProfilePromotionSummaryResult, ProfileReviewResult
from .profile_registry import load_project_profile

PROMOTION_DECISIONS = {"verified", "rejected", "needs_changes", "revoked"}


def default_profile_promotions_dir(root: str | Path) -> Path:
    return Path(root) / "state" / "profile-promotions"


def create_profile_promotion_record(
    root: str | Path,
    decision: str,
    reviewer: str,
    profile_review_hash: str,
    profile_review_path: str | Path | None = None,
    reviewed_at: str | None = None,
    notes: str | None = None,
    risk_flags: list[str] | None = None,
) -> ProfilePromotionRecord:
    """Create a supplied human profile-promotion decision record without mutating the profile."""

    workspace = Path(root)
    review_path = Path(profile_review_path) if profile_review_path is not None else workspace / "state" / "profile-review.json"
    normalized_decision = _decision(decision)
    reviewed = reviewed_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer must not be blank")
    if not review_path.exists():
        raise ValueError(f"profile review file not found: {review_path}")

    review = ProfileReviewResult.model_validate_json(review_path.read_text(encoding="utf-8-sig"))
    actual_hash = _sha256_file(review_path)
    expected_hash = _normalize_hash(profile_review_hash)
    if actual_hash != expected_hash:
        raise ValueError("profile_review_hash does not match the current profile review artifact")
    if not review.can_promote or review.status != "ready_for_human_promotion":
        raise ValueError("profile review is not ready for human promotion")
    if not review.profile_id:
        raise ValueError("profile review does not identify a profile_id")

    promotion_id = _promotion_id(review.profile_id, normalized_decision, reviewer.strip(), reviewed, actual_hash)
    return ProfilePromotionRecord(
        promotion_id=promotion_id,
        profile_id=review.profile_id,
        decision=normalized_decision,
        reviewer=reviewer.strip(),
        reviewed_at=reviewed,
        profile_review_path=str(review_path),
        profile_review_hash=f"sha256:{actual_hash}",
        profile_review_status=review.status,
        profile_review_can_promote=review.can_promote,
        notes=notes,
        risk_flags=risk_flags or [],
    )


def write_profile_promotion_record(
    record: ProfilePromotionRecord,
    promotions_dir: str | Path,
) -> Path:
    target_dir = Path(promotions_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{record.promotion_id}.json"
    target.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return target


def load_profile_promotion_records(path: str | Path) -> list[ProfilePromotionRecord]:
    source = Path(path)
    if not source.exists():
        return []
    if source.is_dir():
        records: list[ProfilePromotionRecord] = []
        for record_path in sorted(source.glob("*.json")):
            records.extend(load_profile_promotion_records(record_path))
        return records
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [ProfilePromotionRecord.model_validate(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [ProfilePromotionRecord.model_validate(item) for item in payload["items"]]
    return [ProfilePromotionRecord.model_validate(payload)]


def latest_profile_promotion(records: list[ProfilePromotionRecord], profile_id: str | None = None) -> ProfilePromotionRecord | None:
    selected = [record for record in records if profile_id is None or record.profile_id == profile_id]
    return max(selected, key=lambda item: item.reviewed_at, default=None)


def summarize_profile_promotions(
    root: str | Path,
    promotions_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> ProfilePromotionSummaryResult:
    workspace = Path(root)
    profile_id = _profile_id(workspace)
    review_path = workspace / "state" / "profile-review.json"
    current_review_hash = f"sha256:{_sha256_file(review_path)}" if review_path.exists() else None
    source_dir = Path(promotions_dir) if promotions_dir is not None else default_profile_promotions_dir(workspace)
    warnings: list[str] = []
    try:
        records = [record for record in load_profile_promotion_records(source_dir) if profile_id is None or record.profile_id == profile_id]
    except Exception as exc:
        records = []
        warnings.append(f"profile_promotions_unreadable:{exc}")
    latest = latest_profile_promotion(records, profile_id)
    mismatch_count = sum(1 for record in records if current_review_hash is not None and _normalize_hash(record.profile_review_hash) != _normalize_hash(current_review_hash))
    latest_hash_matches = (
        latest is not None
        and current_review_hash is not None
        and _normalize_hash(latest.profile_review_hash) == _normalize_hash(current_review_hash)
    )
    result = ProfilePromotionSummaryResult(
        root=str(workspace),
        status=_summary_status(latest, latest_hash_matches),
        profile_id=profile_id,
        record_count=len(records),
        verified_count=sum(1 for record in records if record.decision == "verified"),
        latest_promotion_id=latest.promotion_id if latest else None,
        latest_decision=latest.decision if latest else None,
        latest_reviewer=latest.reviewer if latest else None,
        latest_reviewed_at=latest.reviewed_at if latest else None,
        current_profile_review_hash=current_review_hash,
        hash_mismatch_count=mismatch_count,
        records=sorted(records, key=lambda item: (item.profile_id, item.reviewed_at, item.promotion_id)),
        markdown_path=str(output_path) if output_path else None,
        json_path=str(json_path) if json_path else None,
        warnings=warnings,
    )
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_profile_promotion_summary_markdown(result), encoding="utf-8")
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return result


def render_profile_promotion_summary_markdown(result: ProfilePromotionSummaryResult) -> str:
    lines = [
        "# Profile Promotion Summary",
        "",
        "> Human decision log only. This records supplied profile-promotion decisions; it does not certify agency compliance or mutate project profiles.",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Root | `{_escape(result.root)}` |",
        f"| Profile | {_escape(result.profile_id or 'missing')} |",
        f"| Status | {_escape(result.status)} |",
        f"| Records | {result.record_count} |",
        f"| Verified decisions | {result.verified_count} |",
        f"| Latest decision | {_escape(result.latest_decision or '-')} |",
        f"| Latest reviewer | {_escape(result.latest_reviewer or '-')} |",
        f"| Latest reviewed at | {_escape(result.latest_reviewed_at or '-')} |",
        f"| Review hash mismatches | {result.hash_mismatch_count} |",
        f"| Current profile-review hash | {_escape(result.current_profile_review_hash or '-')} |",
        "",
        "## Records",
        "",
        "| Decision | Promotion ID | Profile | Reviewer | Reviewed At | Review Hash | Risk Flags | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    if not result.records:
        lines.append("| missing | - | - | - | - | - | profile_promotion_missing | Record supplied human promotion decision after profile-review passes. |")
    for record in result.records:
        lines.append(
            "| {decision} | `{promotion_id}` | {profile} | {reviewer} | {reviewed_at} | `{review_hash}` | {risks} | {notes} |".format(
                decision=_escape(record.decision),
                promotion_id=_escape(record.promotion_id),
                profile=_escape(record.profile_id),
                reviewer=_escape(record.reviewer),
                reviewed_at=_escape(record.reviewed_at),
                review_hash=_escape(record.profile_review_hash),
                risks=_escape(", ".join(record.risk_flags) or "-"),
                notes=_escape(record.notes or "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _decision(value: str) -> str:
    decision = value.strip()
    if decision not in PROMOTION_DECISIONS:
        raise ValueError(f"unknown profile promotion decision: {value}")
    return decision


def _profile_id(workspace: Path) -> str | None:
    path = workspace / "state" / "project-profile.json"
    if not path.exists():
        return None
    try:
        return load_project_profile(path).profile_id
    except Exception:
        return None


def _summary_status(latest: ProfilePromotionRecord | None, latest_hash_matches: bool) -> str:
    if latest is None:
        return "not_recorded"
    if not latest_hash_matches:
        return "stale_review_hash"
    if latest.decision == "verified":
        return "verified_recorded"
    if latest.decision in {"rejected", "revoked"}:
        return "blocked"
    return "needs_review"


def _promotion_id(profile_id: str, decision: str, reviewer: str, reviewed_at: str, review_hash: str) -> str:
    digest = hashlib.sha256(f"{profile_id}|{decision}|{reviewer}|{reviewed_at}|{review_hash}".encode("utf-8")).hexdigest()
    year = reviewed_at[:4] if reviewed_at[:4].isdigit() else datetime.now(UTC).strftime("%Y")
    return f"PPR-{year}-{digest[:8].upper()}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_hash(value: str) -> str:
    normalized = value.lower()
    if normalized.startswith("sha256:"):
        normalized = normalized.split(":", 1)[1]
    return normalized


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
