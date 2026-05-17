from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .audit import generate_audit_qna
from .approval import (
    approval_gate_status,
    create_approval_record,
    generate_approval_summary,
    load_approval_records,
    write_approval_record,
)
from .analysis import generate_analysis_script, run_data_analysis
from .budget import generate_budget_evidence_checklist
from .claim_checker import check_unsupported_claims
from .classifier import classify_file
from .data_profiler import profile_data_file
from .evidence_bundle import generate_evidence_bundle_index
from .evidence_index import load_evidence_index, write_evidence_index
from .experiment_planner import generate_experiment_plan_bundle
from .io_utils import read_text_file
from .intake import run_intake
from .literature import generate_literature_matrix
from .models import EvidenceItem, PaperRecord, ProjectState, ResearchInsight
from .plan_mapper import extract_project_state_from_text
from .profile_registry import generate_profile_registry, list_project_profiles, load_project_profile
from .projection_export import export_projection
from .research_assistant import (
    generate_data_insight_report,
    generate_experiment_comparison_table,
    generate_paper_card_markdown,
    generate_reproducibility_checklist,
    paper_card_from_text,
)
from .reporting import write_monthly_report
from .schema_tools import validate_json_files
from .workspace import initialize_workspace, run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan
from .workspace_review import generate_workspace_review_pack, verify_workspace_review_pack
from .workspace_summary import generate_workspace_summary


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

    paper_parser = subparsers.add_parser("paper-card", help="Create a conservative paper card from text.")
    paper_parser.add_argument("paper_text")
    paper_parser.add_argument("--paper-id", default="PAPER-NEEDS-REVIEW")
    paper_parser.add_argument("--evidence-id", action="append", default=[])
    paper_parser.add_argument("--output", default=None)
    paper_parser.add_argument("--markdown", action="store_true")

    data_insights_parser = subparsers.add_parser("data-insights", help="Generate a data insight candidate report from CSV/XLSX.")
    data_insights_parser.add_argument("data_file")
    data_insights_parser.add_argument("--evidence-id", action="append", default=[])
    data_insights_parser.add_argument("--output", default=None)

    analysis_script_parser = subparsers.add_parser("analysis-script", help="Generate a reproducible analysis script for a CSV/XLSX file.")
    analysis_script_parser.add_argument("data_file")
    analysis_script_parser.add_argument("--output-dir", default="reports/analysis")
    analysis_script_parser.add_argument("--evidence-id", action="append", default=[])
    analysis_script_parser.add_argument("--output", default=None)

    run_analysis_parser = subparsers.add_parser("run-analysis", help="Run deterministic profile/insight analysis and write a manifest.")
    run_analysis_parser.add_argument("data_file")
    run_analysis_parser.add_argument("--output-dir", default="reports/analysis")
    run_analysis_parser.add_argument("--evidence-id", action="append", default=[])
    run_analysis_parser.add_argument("--no-script", action="store_true")

    experiment_parser = subparsers.add_parser("experiment-table", help="Generate an experiment comparison table from evidence index.")
    experiment_parser.add_argument("evidence_index_json")
    experiment_parser.add_argument("--output", default=None)

    repro_parser = subparsers.add_parser("repro-check", help="Generate a reproducibility checklist from evidence index.")
    repro_parser.add_argument("evidence_index_json")
    repro_parser.add_argument("--output", default=None)

    plan_experiment_parser = subparsers.add_parser("plan-experiment", help="Generate validation experiment plans from ResearchInsight JSON.")
    plan_experiment_parser.add_argument("insights_json", help="One ResearchInsight object or a JSON list.")
    plan_experiment_parser.add_argument("--evidence-index", default=None)
    plan_experiment_parser.add_argument("--output", default=None)

    budget_parser = subparsers.add_parser("budget-check", help="Generate a generic budget evidence completeness checklist.")
    budget_parser.add_argument("evidence_index_json")
    budget_parser.add_argument("--output", default=None)

    profiles_parser = subparsers.add_parser("profiles", help="List agency profile templates.")
    profiles_parser.add_argument("--templates-root", default=None)
    profiles_parser.add_argument("--markdown", action="store_true")
    profiles_parser.add_argument("--output", default=None)

    validate_profile_parser = subparsers.add_parser("validate-profile", help="Validate a project profile JSON file.")
    validate_profile_parser.add_argument("profile_json")

    validate_json_parser = subparsers.add_parser("validate-json", help="Validate JSON files against bundled or custom JSON schema.")
    validate_json_parser.add_argument("schema", help="Schema alias such as evidence, research-insight, project-profile, approval, or a schema path.")
    validate_json_parser.add_argument("json_paths", nargs="+")

    approval_record_parser = subparsers.add_parser("approval-record", help="Record a supplied human approval/review decision.")
    approval_record_parser.add_argument("--target-type", required=True, choices=["report", "evidence", "insight", "budget", "profile", "bundle", "other"])
    approval_record_parser.add_argument("--target-id", required=True)
    approval_record_parser.add_argument("--decision", required=True, choices=["approved", "rejected", "needs_changes", "revoked"])
    approval_record_parser.add_argument("--reviewer", required=True)
    approval_record_parser.add_argument("--target-path", default=None)
    approval_record_parser.add_argument("--evidence-id", action="append", default=[])
    approval_record_parser.add_argument("--note", default=None)
    approval_record_parser.add_argument("--risk-flag", action="append", default=[])
    approval_record_parser.add_argument("--reviewed-at", default=None)
    approval_record_parser.add_argument("--approvals-dir", default="state/approvals")
    approval_record_parser.add_argument("--print-only", action="store_true")

    approval_summary_parser = subparsers.add_parser("approval-summary", help="Render a Markdown summary for approval records.")
    approval_summary_parser.add_argument("approval_records")
    approval_summary_parser.add_argument("--output", default=None)

    approval_gate_parser = subparsers.add_parser("approval-gate", help="Check whether the latest supplied decision approves a target.")
    approval_gate_parser.add_argument("approval_records")
    approval_gate_parser.add_argument("--target-type", required=True, choices=["report", "evidence", "insight", "budget", "profile", "bundle", "other"])
    approval_gate_parser.add_argument("--target-id", required=True)

    bundle_parser = subparsers.add_parser("bundle-index", help="Generate an evidence bundle index from evidence and optional approval records.")
    bundle_parser.add_argument("evidence_index_json")
    bundle_parser.add_argument("--approval-records", default=None)
    bundle_parser.add_argument("--output", default=None)

    export_parser = subparsers.add_parser("export-projection", help="Export a Markdown projection to DOCX/HTML/TXT review format.")
    export_parser.add_argument("markdown_path")
    export_parser.add_argument("--output", required=True)
    export_parser.add_argument("--format", choices=["docx", "html", "hwpx-html", "txt"], default=None)
    export_parser.add_argument("--title", default=None)

    init_workspace_parser = subparsers.add_parser("init-workspace", help="Create a standard K-ResDev workspace skeleton.")
    init_workspace_parser.add_argument("--root", default=".")
    init_workspace_parser.add_argument("--project-id", required=True)
    init_workspace_parser.add_argument("--title", required=True)
    init_workspace_parser.add_argument("--profile", default="national-rnd-basic")

    doctor_parser = subparsers.add_parser("doctor", help="Inspect workspace readiness across evidence/report/approval/export/analysis metadata.")
    doctor_parser.add_argument("--root", default=".")
    doctor_parser.add_argument("--output", default=None)
    doctor_parser.add_argument("--json", default=None)

    next_actions_parser = subparsers.add_parser("next-actions", help="Generate a safe next-action plan from workspace doctor findings.")
    next_actions_parser.add_argument("--root", default=".")
    next_actions_parser.add_argument("--output", default=None)
    next_actions_parser.add_argument("--json", default=None)

    workspace_summary_parser = subparsers.add_parser("workspace-summary", help="Generate a one-page operational workspace summary.")
    workspace_summary_parser.add_argument("--root", default=".")
    workspace_summary_parser.add_argument("--output", default=None)
    workspace_summary_parser.add_argument("--json", default=None)
    workspace_summary_parser.add_argument("--max-actions", type=int, default=5)

    review_pack_parser = subparsers.add_parser("workspace-review-pack", help="Generate readiness, next-action, and summary artifacts in one local review pack.")
    review_pack_parser.add_argument("--root", default=".")
    review_pack_parser.add_argument("--reports-dir", default=None)
    review_pack_parser.add_argument("--state-dir", default=None)
    review_pack_parser.add_argument("--max-actions", type=int, default=5)

    verify_review_pack_parser = subparsers.add_parser("verify-review-pack", help="Verify review-pack generated artifacts against saved hashes.")
    verify_review_pack_parser.add_argument("manifest_json")

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
    if args.command == "paper-card":
        text = read_text_file(args.paper_text)
        paper = paper_card_from_text(text, args.paper_id, args.evidence_id)
        if args.markdown:
            rendered = generate_paper_card_markdown(paper, args.output)
            print(rendered)
        else:
            rendered = paper.model_dump_json(indent=2)
            if args.output:
                target = Path(args.output)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(rendered + "\n", encoding="utf-8")
            print(rendered)
        return 0
    if args.command == "data-insights":
        profile = profile_data_file(args.data_file)
        rendered = generate_data_insight_report(profile, args.evidence_id, args.output)
        print(rendered)
        return 0
    if args.command == "analysis-script":
        rendered = generate_analysis_script(args.data_file, args.output_dir, args.evidence_id)
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
        print(rendered)
        return 0
    if args.command == "run-analysis":
        result = run_data_analysis(args.data_file, args.output_dir, args.evidence_id, write_script=not args.no_script)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "experiment-table":
        evidence = load_evidence_index(args.evidence_index_json)
        rendered = generate_experiment_comparison_table(evidence, args.output)
        print(rendered)
        return 0
    if args.command == "repro-check":
        evidence = load_evidence_index(args.evidence_index_json)
        rendered = generate_reproducibility_checklist(evidence, args.output)
        print(rendered)
        return 0
    if args.command == "plan-experiment":
        payload = json.loads(Path(args.insights_json).read_text(encoding="utf-8"))
        if isinstance(payload, list):
            insights = [ResearchInsight.model_validate(item) for item in payload]
        else:
            insights = [ResearchInsight.model_validate(payload)]
        evidence = load_evidence_index(args.evidence_index) if args.evidence_index else []
        rendered = generate_experiment_plan_bundle(insights, evidence, args.output)
        print(rendered)
        return 0
    if args.command == "budget-check":
        evidence = load_evidence_index(args.evidence_index_json)
        rendered = generate_budget_evidence_checklist(evidence, args.output)
        print(rendered)
        return 0
    if args.command == "profiles":
        if args.markdown or args.output:
            rendered = generate_profile_registry(args.templates_root, args.output)
            print(rendered)
        else:
            print(json.dumps(list_project_profiles(args.templates_root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "validate-profile":
        profile = load_project_profile(args.profile_json)
        print(profile.model_dump_json(indent=2))
        return 0
    if args.command == "validate-json":
        result = validate_json_files(args.json_paths, args.schema)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    if args.command == "approval-record":
        record = create_approval_record(
            target_type=args.target_type,
            target_id=args.target_id,
            decision=args.decision,
            reviewer=args.reviewer,
            evidence_ids=args.evidence_id,
            target_path=args.target_path,
            notes=args.note,
            risk_flags=args.risk_flag,
            reviewed_at=args.reviewed_at,
        )
        if not args.print_only:
            write_approval_record(record, args.approvals_dir)
        print(record.model_dump_json(indent=2))
        return 0
    if args.command == "approval-summary":
        records = load_approval_records(args.approval_records)
        rendered = generate_approval_summary(records, args.output)
        print(rendered)
        return 0
    if args.command == "approval-gate":
        records = load_approval_records(args.approval_records)
        print(json.dumps(approval_gate_status(records, args.target_type, args.target_id), ensure_ascii=False, indent=2))
        return 0
    if args.command == "bundle-index":
        evidence = load_evidence_index(args.evidence_index_json)
        approvals = load_approval_records(args.approval_records) if args.approval_records else []
        rendered = generate_evidence_bundle_index(evidence, approvals, args.output)
        print(rendered)
        return 0
    if args.command == "export-projection":
        result = export_projection(args.markdown_path, args.output, args.format, args.title)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "init-workspace":
        result = initialize_workspace(args.root, args.project_id, args.title, args.profile)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "doctor":
        result = run_workspace_doctor(args.root, args.output, args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "next-actions":
        result = generate_workspace_action_plan(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "workspace-summary":
        result = generate_workspace_summary(args.root, output_path=args.output, json_path=args.json, max_actions=args.max_actions)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "workspace-review-pack":
        result = generate_workspace_review_pack(args.root, reports_dir=args.reports_dir, state_dir=args.state_dir, max_actions=args.max_actions)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "verify-review-pack":
        result = verify_workspace_review_pack(args.manifest_json)
        print(result.model_dump_json(indent=2))
        return 0 if result.valid else 1
    raise AssertionError(f"Unhandled command: {args.command}")
