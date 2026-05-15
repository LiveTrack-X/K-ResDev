from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .audit import generate_audit_qna
from .claim_checker import check_unsupported_claims
from .classifier import classify_file
from .data_profiler import profile_data_file
from .evidence_index import load_evidence_index, write_evidence_index
from .io_utils import read_text_file
from .intake import run_intake
from .literature import generate_literature_matrix
from .models import EvidenceItem, PaperRecord, ProjectState
from .plan_mapper import extract_project_state_from_text
from .reporting import write_monthly_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="k-resdev")
    parser.add_argument("--version", action="version", version=f"k-resdev {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify_parser = subparsers.add_parser("classify", help="Classify a file path and optional text.")
    classify_parser.add_argument("path")
    classify_parser.add_argument("--text", default=None)

    profile_parser = subparsers.add_parser("profile", help="Profile a CSV/XLSX data file.")
    profile_parser.add_argument("path")

    intake_parser = subparsers.add_parser("intake", help="Scan inbox and create raw registry/evidence indexes.")
    intake_parser.add_argument("--inbox", default="inbox")
    intake_parser.add_argument("--state-dir", default="state")
    intake_parser.add_argument("--evidence-dir", default="evidence")
    intake_parser.add_argument("--project", default=None)

    index_parser = subparsers.add_parser("index", help="Write state/evidence-index.md and .json.")
    index_parser.add_argument("evidence_json", help="JSON list of EvidenceItem objects.")
    index_parser.add_argument("--state-dir", default="state")

    map_parser = subparsers.add_parser("map-plan", help="Extract a draft project-state JSON from plan text.")
    map_parser.add_argument("plan_text")
    map_parser.add_argument("--project-id", default="PRJ-NEEDS-REVIEW")
    map_parser.add_argument("--output", default=None)

    check_parser = subparsers.add_parser("check-claims", help="Check a report draft against evidence.")
    check_parser.add_argument("report_md")
    check_parser.add_argument("evidence_index_json")

    report_parser = subparsers.add_parser("draft-report", help="Write a monthly report draft and claim review.")
    report_parser.add_argument("evidence_index_json")
    report_parser.add_argument("--project-state", default=None)
    report_parser.add_argument("--reports-dir", default="reports")
    report_parser.add_argument("--period", default=None)
    report_parser.add_argument("--filename", default=None)

    audit_parser = subparsers.add_parser("audit-qna", help="Generate a draft audit Q&A from evidence metadata.")
    audit_parser.add_argument("evidence_index_json")
    audit_parser.add_argument("--output", default="reports/audit-defense-qna.md")

    lit_parser = subparsers.add_parser("lit-matrix", help="Generate a literature matrix.")
    lit_parser.add_argument("papers_json", help="JSON list of paper records.")
    lit_parser.add_argument("--output", default=None)

    args = parser.parse_args(argv)

    if args.command == "classify":
        print(classify_file(args.path, args.text).model_dump_json(indent=2))
        return 0
    if args.command == "profile":
        print(profile_data_file(args.path).model_dump_json(indent=2))
        return 0
    if args.command == "intake":
        result = run_intake(args.inbox, args.state_dir, args.evidence_dir, args.project)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "index":
        payload = json.loads(Path(args.evidence_json).read_text(encoding="utf-8"))
        paths = write_evidence_index([EvidenceItem.model_validate(item) for item in payload], args.state_dir)
        print(paths.model_dump_json(indent=2))
        return 0
    if args.command == "map-plan":
        text = read_text_file(args.plan_text)
        state = extract_project_state_from_text(text, args.project_id)
        rendered = state.model_dump_json(indent=2)
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0
    if args.command == "check-claims":
        report = Path(args.report_md).read_text(encoding="utf-8")
        evidence = load_evidence_index(args.evidence_index_json)
        findings = check_unsupported_claims(report, evidence)
        print(json.dumps([finding.model_dump(mode="json") for finding in findings], ensure_ascii=False, indent=2))
        return 0
    if args.command == "draft-report":
        evidence = load_evidence_index(args.evidence_index_json)
        project_state = None
        if args.project_state:
            project_state = ProjectState.model_validate_json(Path(args.project_state).read_text(encoding="utf-8"))
        paths = write_monthly_report(evidence, args.reports_dir, project_state, args.period, args.filename)
        print(paths.model_dump_json(indent=2))
        return 0
    if args.command == "audit-qna":
        evidence = load_evidence_index(args.evidence_index_json)
        rendered = generate_audit_qna(evidence, args.output)
        print(rendered)
        return 0
    if args.command == "lit-matrix":
        payload = json.loads(Path(args.papers_json).read_text(encoding="utf-8"))
        rendered = generate_literature_matrix(
            [PaperRecord.model_validate(item) for item in payload],
            args.output,
        )
        print(rendered)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")
