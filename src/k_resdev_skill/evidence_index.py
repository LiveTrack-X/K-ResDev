from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import EvidenceIndexPaths, EvidenceItem


def write_evidence_index(
    evidence_items: Iterable[EvidenceItem | dict],
    state_dir: str | Path = "state",
) -> EvidenceIndexPaths:
    """Write Markdown and JSON evidence indexes under a state directory."""

    items = [_to_evidence_item(item) for item in evidence_items]
    items.sort(key=lambda item: item.evidence_id)

    target_dir = Path(state_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = target_dir / "evidence-index.md"
    json_path = target_dir / "evidence-index.json"

    markdown_path.write_text(_render_markdown(items), encoding="utf-8")
    payload = {
        "generated_by": "k-resdev-skill",
        "evidence_count": len(items),
        "items": [item.model_dump(mode="json") for item in items],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return EvidenceIndexPaths(markdown_path=str(markdown_path), json_path=str(json_path))


def load_evidence_index(path: str | Path) -> list[EvidenceItem]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    items = payload.get("items", payload if isinstance(payload, list) else [])
    return [_to_evidence_item(item) for item in items]


def _to_evidence_item(item: EvidenceItem | dict) -> EvidenceItem:
    if isinstance(item, EvidenceItem):
        return item
    return EvidenceItem.model_validate(item)


def _render_markdown(items: list[EvidenceItem]) -> str:
    lines = [
        "# Evidence Index",
        "",
        "| Evidence ID | Type | Status | Linked KPI | Claim | Source | Risk Flags |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in items:
        lines.append(
            "| {evidence_id} | {evidence_type} | {status} | {linked_kpi} | {claim} | {source} | {risk} |".format(
                evidence_id=_escape(item.evidence_id),
                evidence_type=_escape(_enum_value(item.evidence_type)),
                status=_escape(_enum_value(item.status)),
                linked_kpi=_escape(item.linked_kpi or ""),
                claim=_escape(item.claim),
                source=_escape(item.source_file),
                risk=_escape(", ".join(item.risk_flags)),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _enum_value(value: object) -> str:
    return getattr(value, "value", str(value))
