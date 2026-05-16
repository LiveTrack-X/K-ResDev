from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .data_profiler import profile_data_file
from .models import AnalysisRunResult
from .research_assistant import generate_data_insight_report


def run_data_analysis(
    data_file: str | Path,
    output_dir: str | Path = "reports/analysis",
    evidence_ids: list[str] | None = None,
    write_script: bool = True,
) -> AnalysisRunResult:
    """Run deterministic data profiling and insight-candidate generation without altering raw data."""

    source = Path(data_file)
    evidence = evidence_ids or []
    source_hash = _sha256(source)
    analysis_id = _analysis_id(source_hash, str(source))
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(source)

    profile = profile_data_file(source)
    profile_path = target_dir / f"{stem}-profile.json"
    insight_report_path = target_dir / f"{stem}-insights.md"
    script_path = target_dir / f"{stem}-analysis.py" if write_script else None
    manifest_path = target_dir / f"{stem}-analysis-run.json"

    profile_path.write_text(profile.model_dump_json(indent=2) + "\n", encoding="utf-8")
    generate_data_insight_report(profile, evidence, insight_report_path)
    if script_path is not None:
        script_path.write_text(generate_analysis_script(source, target_dir, evidence), encoding="utf-8")

    result = AnalysisRunResult(
        analysis_id=analysis_id,
        source_file=str(source),
        source_hash=source_hash,
        profile_path=str(profile_path),
        insight_report_path=str(insight_report_path),
        script_path=str(script_path) if script_path is not None else None,
        manifest_path=str(manifest_path),
        evidence_ids=evidence,
        warnings=_analysis_warnings(profile),
    )
    manifest = {
        **result.model_dump(mode="json"),
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "profile_summary": {
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "columns": profile.columns,
            "possible_metrics": profile.possible_metrics,
        },
        "safety": {
            "raw_file_modified": False,
            "outputs_are_draft": True,
            "human_review_required": True,
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def generate_analysis_script(
    data_file: str | Path,
    output_dir: str | Path = "reports/analysis",
    evidence_ids: list[str] | None = None,
) -> str:
    """Generate a small reproducible script that reruns the deterministic analysis."""

    evidence = evidence_ids or []
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "from k_resdev_skill.analysis import run_data_analysis",
            "",
            "",
            "if __name__ == \"__main__\":",
            "    result = run_data_analysis(",
            f"        data_file={str(data_file)!r},",
            f"        output_dir={str(output_dir)!r},",
            f"        evidence_ids={evidence!r},",
            "        write_script=False,",
            "    )",
            "    print(result.model_dump_json(indent=2))",
            "",
        ]
    )


def _analysis_warnings(profile) -> list[str]:
    warnings: list[str] = []
    if profile.row_count < 30:
        warnings.append("small_sample")
    for column, missingness in profile.missingness.items():
        if missingness.missing_count:
            warnings.append(f"missing_values:{column}")
    if not profile.possible_metrics:
        warnings.append("no_metric_columns_detected")
    return warnings


def _safe_stem(path: Path) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in path.stem).strip("-") or "data"


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _analysis_id(source_hash: str, source_file: str) -> str:
    digest = hashlib.sha256(f"{source_hash}|{source_file}".encode("utf-8")).hexdigest()
    return f"ANL-{datetime.now(UTC).strftime('%Y')}-{digest[:8].upper()}"
