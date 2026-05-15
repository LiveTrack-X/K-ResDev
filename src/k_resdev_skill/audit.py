from __future__ import annotations

from pathlib import Path

from .models import EvidenceItem


def generate_audit_qna(
    evidence_items: list[EvidenceItem],
    output_path: str | Path | None = None,
) -> str:
    """Generate a draft audit Q&A index from evidence metadata only."""

    lines = [
        "# Audit Defense Q&A Draft",
        "",
        "> Draft projection only. Verify against official agency requirements before use.",
        "",
        "| Question | Evidence | Draft Answer | Human Check |",
        "|---|---|---|---|",
    ]
    if not evidence_items:
        lines.append("| What evidence exists? | needs_evidence | No indexed evidence yet. | Intake source files first. |")
    for item in evidence_items:
        lines.append(
            "| What supports this claim? | {evidence_id} | {claim} | Confirm status is accepted and provenance is sufficient. |".format(
                evidence_id=_escape(item.evidence_id),
                claim=_escape(item.claim),
            )
        )
        if item.risk_flags:
            lines.append(
                "| Are there unresolved risks? | {evidence_id} | Risk flags: {flags}. | Resolve or disclose before official use. |".format(
                    evidence_id=_escape(item.evidence_id),
                    flags=_escape(", ".join(item.risk_flags)),
                )
            )
    lines.append("")
    rendered = "\n".join(lines)
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return rendered


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
