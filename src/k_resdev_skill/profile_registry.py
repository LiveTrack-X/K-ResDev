from __future__ import annotations

import json
from pathlib import Path

from .models import ProjectProfile


def default_agency_templates_root() -> Path:
    cwd_root = Path("templates") / "agencies"
    if cwd_root.exists():
        return cwd_root
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "templates" / "agencies"


def load_project_profile(profile_path: str | Path) -> ProjectProfile:
    payload = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    return ProjectProfile.model_validate(payload)


def list_project_profiles(templates_root: str | Path | None = None) -> list[dict[str, object]]:
    root = Path(templates_root) if templates_root is not None else default_agency_templates_root()
    if not root.exists():
        return []
    profiles: list[dict[str, object]] = []
    for profile_path in sorted(root.glob("*/project-profile.json")):
        profile = load_project_profile(profile_path)
        template_files = sorted(
            path.name for path in profile_path.parent.iterdir() if path.is_file() and path.name != "project-profile.json"
        )
        profiles.append(
            {
                "profile_id": profile.profile_id,
                "agency": profile.agency,
                "program": profile.program,
                "report_cycle": profile.report_cycle,
                "status": profile.status,
                "profile_path": str(profile_path),
                "template_dir": str(profile_path.parent),
                "template_files": template_files,
                "required_outputs": profile.required_outputs,
                "notes": profile.notes,
            }
        )
    return profiles


def generate_profile_registry(
    templates_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> str:
    profiles = list_project_profiles(templates_root)
    lines = [
        "# Agency Profile Registry",
        "",
        "> Registry projection only. Profiles marked `needs_review` are skeletons, not official agency rules.",
        "",
        "| Profile | Agency | Program | Cycle | Status | Templates |",
        "|---|---|---|---|---|---|",
    ]
    if not profiles:
        lines.append("| needs_profile | needs_review | needs_review | needs_review | missing | No profile templates found. |")
    for profile in profiles:
        lines.append(
            "| {profile_id} | {agency} | {program} | {cycle} | {status} | {templates} |".format(
                profile_id=_escape(str(profile["profile_id"])),
                agency=_escape(str(profile["agency"] or "needs_review")),
                program=_escape(str(profile["program"] or "needs_review")),
                cycle=_escape(str(profile["report_cycle"] or "needs_review")),
                status=_escape(str(profile["status"])),
                templates=_escape(", ".join(str(item) for item in profile["template_files"]) or "needs_review"),
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
