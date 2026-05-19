from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from . import __version__
from .artifact_authority import generate_artifact_authority
from .audit import generate_audit_qna
from .approval import (
    approval_gate_status,
    create_approval_record,
    generate_approval_summary,
    load_approval_records,
    write_approval_record,
)
from .approval_coverage import generate_workspace_approval_coverage
from .analysis import generate_analysis_script, run_data_analysis
from .bibliography import import_bibliography, load_bibliography_index, paper_records_from_bibliography
from .bibliography_integrity import generate_workspace_bibliography_integrity
from .bibliography_review import (
    bibliography_review_status,
    create_bibliography_review_record,
    generate_bibliography_review_summary,
    load_bibliography_review_records,
    write_bibliography_review_record,
)
from .budget import generate_budget_evidence_checklist
from .budget_ledger import generate_workspace_budget_ledger, import_budget_ledger
from .claim_checker import check_unsupported_claims
from .citation_support import (
    citation_support_status,
    create_citation_support_record,
    generate_citation_support_summary,
    generate_workspace_citation_support_integrity,
    load_citation_support_records,
    write_citation_support_record,
)
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
from .profile_promotion import (
    create_profile_promotion_record,
    default_profile_promotions_dir,
    summarize_profile_promotions,
    write_profile_promotion_record,
)
from .profile_promotion_apply import apply_profile_promotion_plan, generate_profile_promotion_apply_plan
from .profile_promotion_revoke import generate_profile_promotion_revoke_plan, revoke_profile_promotion_plan
from .profile_lifecycle import generate_profile_lifecycle_ledger
from .profile_pack_drilldown import generate_profile_pack_readiness_drilldown
from .profile_pack_readiness import generate_profile_pack_readiness
from .profile_sources import (
    create_profile_source_record,
    default_profile_sources_path,
    generate_profile_integrity,
    record_profile_source,
    summarize_profile_sources,
    utc_now_iso,
)
from .profile_registry import generate_profile_registry, list_project_profiles, load_project_profile
from .profile_review import generate_profile_review
from .profile_source_fix_plan import generate_profile_source_fix_plan
from .profile_source_fix_review import (
    create_profile_source_fix_review_record,
    default_profile_source_fix_reviews_dir,
    summarize_profile_source_fix_reviews,
    write_profile_source_fix_review_record,
)
from .profile_source_queue import generate_profile_source_queue
from .project_goals import generate_goals_review, initialize_project_goals
from .projection_export import export_projection
from .reference_corpus import build_reference_corpus
from .report_integrity import generate_workspace_report_integrity
from .research_claims import generate_research_claim_matrix, import_research_claims, load_research_claims, render_research_claims_markdown
from .research_assistant import (
    generate_data_insight_report,
    generate_experiment_comparison_table,
    generate_paper_card_markdown,
    generate_reproducibility_checklist,
    paper_card_from_text,
)
from .reporting import write_monthly_report
from .schema_tools import validate_json_files
from .source_verification import verify_evidence_sources
from .trace_passport import create_checkpoint, generate_checkpoint_resume_plan, generate_trace_passport
from .workspace import initialize_workspace, run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan
from .workspace_discovery import discover_workspace
from .workspace_review import generate_workspace_review_pack, verify_workspace_review_pack
from .workspace_summary import generate_workspace_summary
from .workspace_trace import generate_workspace_trace
from .weekly_review import generate_weekly_review, generate_workspace_dashboard
from .workflow_router import WORKFLOW_NAMES, generate_workflow_plan


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

    bib_import_parser = subparsers.add_parser("bib-import", help="Import BibTeX/RIS/CSL JSON bibliography metadata.")
    bib_import_parser.add_argument("bibliography_file")
    bib_import_parser.add_argument("--state-dir", default="state")
    bib_import_parser.add_argument("--literature-matrix", default=None)

    bib_lit_parser = subparsers.add_parser("bib-lit-matrix", help="Generate a literature matrix from a bibliography index.")
    bib_lit_parser.add_argument("bibliography_index_json")
    bib_lit_parser.add_argument("--output", default=None)

    bib_integrity_parser = subparsers.add_parser("bib-integrity", help="Check bibliography metadata and Markdown citation keys.")
    bib_integrity_parser.add_argument("--root", default=".")
    bib_integrity_parser.add_argument("--output", default=None)
    bib_integrity_parser.add_argument("--json", default=None)

    reference_corpus_parser = subparsers.add_parser("reference-corpus", help="Scan local reference files into a reviewable corpus and rejection log.")
    reference_corpus_parser.add_argument("--root", default=".")
    reference_corpus_parser.add_argument("--references", default=None)
    reference_corpus_parser.add_argument("--output", default=None)
    reference_corpus_parser.add_argument("--json", default=None)
    reference_corpus_parser.add_argument("--rejections", default=None)

    bib_review_record_parser = subparsers.add_parser("bib-review-record", help="Record a supplied human bibliography metadata review decision.")
    bib_review_record_parser.add_argument("--bibliography-id", required=True)
    bib_review_record_parser.add_argument("--decision", required=True, choices=["accepted", "rejected", "needs_review", "superseded"])
    bib_review_record_parser.add_argument("--reviewer", required=True)
    bib_review_record_parser.add_argument("--citation-key", default=None)
    bib_review_record_parser.add_argument("--paper-id", default=None)
    bib_review_record_parser.add_argument("--note", default=None)
    bib_review_record_parser.add_argument("--risk-flag", action="append", default=[])
    bib_review_record_parser.add_argument("--reviewed-at", default=None)
    bib_review_record_parser.add_argument("--reviews-dir", default="state/bibliography-reviews")
    bib_review_record_parser.add_argument("--print-only", action="store_true")

    bib_review_summary_parser = subparsers.add_parser("bib-review-summary", help="Render a Markdown summary for bibliography review records.")
    bib_review_summary_parser.add_argument("review_records")
    bib_review_summary_parser.add_argument("--output", default=None)

    bib_review_status_parser = subparsers.add_parser("bib-review-status", help="Check latest supplied bibliography metadata review decision.")
    bib_review_status_parser.add_argument("review_records")
    bib_review_status_parser.add_argument("--bibliography-id", required=True)

    citation_support_record_parser = subparsers.add_parser(
        "citation-support-record",
        help="Record a supplied human paper-claim citation support decision.",
    )
    citation_support_record_parser.add_argument("--bibliography-id", required=True)
    citation_support_record_parser.add_argument("--claim", required=True)
    citation_support_record_parser.add_argument(
        "--decision",
        required=True,
        choices=["supports", "partially_supports", "does_not_support", "needs_review", "superseded"],
    )
    citation_support_record_parser.add_argument("--reviewer", required=True)
    citation_support_record_parser.add_argument("--citation-key", default=None)
    citation_support_record_parser.add_argument("--paper-id", default=None)
    citation_support_record_parser.add_argument("--locator", default=None)
    citation_support_record_parser.add_argument("--quote", default=None)
    citation_support_record_parser.add_argument("--evidence-id", action="append", default=[])
    citation_support_record_parser.add_argument("--note", default=None)
    citation_support_record_parser.add_argument("--risk-flag", action="append", default=[])
    citation_support_record_parser.add_argument("--reviewed-at", default=None)
    citation_support_record_parser.add_argument("--support-dir", default="state/citation-support")
    citation_support_record_parser.add_argument("--print-only", action="store_true")

    citation_support_summary_parser = subparsers.add_parser(
        "citation-support-summary",
        help="Render a Markdown summary for paper-claim citation support records.",
    )
    citation_support_summary_parser.add_argument("support_records")
    citation_support_summary_parser.add_argument("--output", default=None)

    citation_support_status_parser = subparsers.add_parser(
        "citation-support-status",
        help="Check latest supplied citation support decision for a bibliography entry and optional claim.",
    )
    citation_support_status_parser.add_argument("support_records")
    citation_support_status_parser.add_argument("--bibliography-id", required=True)
    citation_support_status_parser.add_argument("--claim", default=None)

    citation_support_integrity_parser = subparsers.add_parser(
        "citation-support-integrity",
        help="Check Markdown citations against supplied paper-claim support records.",
    )
    citation_support_integrity_parser.add_argument("--root", default=".")
    citation_support_integrity_parser.add_argument("--output", default=None)
    citation_support_integrity_parser.add_argument("--json", default=None)

    research_claim_import_parser = subparsers.add_parser("research-claim-import", help="Import supplied research claims into state/research-claims.json.")
    research_claim_import_parser.add_argument("claim_file")
    research_claim_import_parser.add_argument("--state-dir", default="state")
    research_claim_import_parser.add_argument("--markdown", default=None)

    research_claim_summary_parser = subparsers.add_parser("research-claim-summary", help="Render a Markdown summary for research claim records.")
    research_claim_summary_parser.add_argument("claims_json")
    research_claim_summary_parser.add_argument("--output", default=None)

    research_claim_matrix_parser = subparsers.add_parser("research-claim-matrix", help="Check research claims against evidence, bibliography, and citation support.")
    research_claim_matrix_parser.add_argument("--root", default=".")
    research_claim_matrix_parser.add_argument("--output", default=None)
    research_claim_matrix_parser.add_argument("--json", default=None)

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

    budget_ledger_import_parser = subparsers.add_parser("budget-ledger-import", help="Import a CSV/JSON budget evidence ledger.")
    budget_ledger_import_parser.add_argument("ledger_file")
    budget_ledger_import_parser.add_argument("--state-dir", default="state")
    budget_ledger_import_parser.add_argument("--markdown", default=None)

    budget_ledger_parser = subparsers.add_parser("budget-ledger-integrity", help="Check budget ledger metadata and evidence links.")
    budget_ledger_parser.add_argument("--root", default=".")
    budget_ledger_parser.add_argument("--output", default=None)
    budget_ledger_parser.add_argument("--json", default=None)

    profiles_parser = subparsers.add_parser("profiles", help="List agency profile templates.")
    profiles_parser.add_argument("--templates-root", default=None)
    profiles_parser.add_argument("--markdown", action="store_true")
    profiles_parser.add_argument("--output", default=None)

    validate_profile_parser = subparsers.add_parser("validate-profile", help="Validate a project profile JSON file.")
    validate_profile_parser.add_argument("profile_json")

    profile_source_record_parser = subparsers.add_parser("profile-source-record", help="Record a supplied profile official-source review record.")
    profile_source_record_parser.add_argument("--profile-id", required=True)
    profile_source_record_parser.add_argument("--title", required=True)
    profile_source_record_parser.add_argument("--source-url", default=None)
    profile_source_record_parser.add_argument("--source-file", default=None)
    profile_source_record_parser.add_argument("--retrieved-at", default=None)
    profile_source_record_parser.add_argument("--source-hash", default=None)
    profile_source_record_parser.add_argument("--verified-by", default=None)
    profile_source_record_parser.add_argument("--review-status", default="needs_review", choices=["needs_review", "verified", "rejected", "superseded"])
    profile_source_record_parser.add_argument("--validity-note", default=None)
    profile_source_record_parser.add_argument("--risk-flag", action="append", default=[])
    profile_source_record_parser.add_argument("--root", default=".")
    profile_source_record_parser.add_argument("--profile-sources", default=None)
    profile_source_record_parser.add_argument("--source-id", default=None)
    profile_source_record_parser.add_argument("--now", action="store_true", help="Use the current UTC time as retrieved_at when omitted.")
    profile_source_record_parser.add_argument("--print-only", action="store_true")

    profile_source_summary_parser = subparsers.add_parser("profile-source-summary", help="Summarize profile source records for one profile.")
    profile_source_summary_parser.add_argument("--root", default=".")
    profile_source_summary_parser.add_argument("--profile-id", default=None)
    profile_source_summary_parser.add_argument("--profile-sources", default=None)
    profile_source_summary_parser.add_argument("--profile-path", default=None)
    profile_source_summary_parser.add_argument("--output", default=None)
    profile_source_summary_parser.add_argument("--json", default=None)

    profile_source_queue_parser = subparsers.add_parser("profile-source-queue", help="Scan profile source packs into a review queue.")
    profile_source_queue_parser.add_argument("--root", default=".")
    profile_source_queue_parser.add_argument("--templates-root", default=None)
    profile_source_queue_parser.add_argument("--output", default=None)
    profile_source_queue_parser.add_argument("--json", default=None)

    profile_source_fix_plan_parser = subparsers.add_parser("profile-source-fix-plan", help="Plan local remediation commands for profile source queue items.")
    profile_source_fix_plan_parser.add_argument("--root", default=".")
    profile_source_fix_plan_parser.add_argument("--queue", default=None)
    profile_source_fix_plan_parser.add_argument("--output", default=None)
    profile_source_fix_plan_parser.add_argument("--json", default=None)

    profile_source_fix_record_parser = subparsers.add_parser("profile-source-fix-record", help="Record a supplied human review decision for one profile-source fix-plan action.")
    profile_source_fix_record_parser.add_argument("--root", default=".")
    profile_source_fix_record_parser.add_argument("--action-id", required=True)
    profile_source_fix_record_parser.add_argument("--decision", required=True, choices=["resolved", "accepted_risk", "deferred", "rejected"])
    profile_source_fix_record_parser.add_argument("--reviewer", required=True)
    profile_source_fix_record_parser.add_argument("--fix-plan", default=None)
    profile_source_fix_record_parser.add_argument("--fix-plan-hash", required=True)
    profile_source_fix_record_parser.add_argument("--reviewed-at", default=None)
    profile_source_fix_record_parser.add_argument("--note", default=None)
    profile_source_fix_record_parser.add_argument("--risk-flag", action="append", default=[])
    profile_source_fix_record_parser.add_argument("--reviews-dir", default=None)
    profile_source_fix_record_parser.add_argument("--print-only", action="store_true")

    profile_source_fix_summary_parser = subparsers.add_parser("profile-source-fix-summary", help="Summarize supplied profile-source fix action review records.")
    profile_source_fix_summary_parser.add_argument("--root", default=".")
    profile_source_fix_summary_parser.add_argument("--fix-plan", default=None)
    profile_source_fix_summary_parser.add_argument("--reviews-dir", default=None)
    profile_source_fix_summary_parser.add_argument("--output", default=None)
    profile_source_fix_summary_parser.add_argument("--json", default=None)

    profile_integrity_parser = subparsers.add_parser("profile-integrity", help="Check project profile source records and review status.")
    profile_integrity_parser.add_argument("--root", default=".")
    profile_integrity_parser.add_argument("--output", default=None)
    profile_integrity_parser.add_argument("--json", default=None)

    profile_review_parser = subparsers.add_parser("profile-review", help="Review whether a profile has enough source and human-review metadata for promotion.")
    profile_review_parser.add_argument("--root", default=".")
    profile_review_parser.add_argument("--output", default=None)
    profile_review_parser.add_argument("--json", default=None)

    profile_promotion_record_parser = subparsers.add_parser("profile-promotion-record", help="Record a supplied human profile-promotion decision after profile-review passes.")
    profile_promotion_record_parser.add_argument("--root", default=".")
    profile_promotion_record_parser.add_argument("--decision", required=True, choices=["verified", "rejected", "needs_changes", "revoked"])
    profile_promotion_record_parser.add_argument("--reviewer", required=True)
    profile_promotion_record_parser.add_argument("--profile-review", default=None)
    profile_promotion_record_parser.add_argument("--profile-review-hash", required=True)
    profile_promotion_record_parser.add_argument("--reviewed-at", default=None)
    profile_promotion_record_parser.add_argument("--note", default=None)
    profile_promotion_record_parser.add_argument("--risk-flag", action="append", default=[])
    profile_promotion_record_parser.add_argument("--promotions-dir", default=None)
    profile_promotion_record_parser.add_argument("--print-only", action="store_true")

    profile_promotion_summary_parser = subparsers.add_parser("profile-promotion-summary", help="Summarize supplied profile-promotion decision records.")
    profile_promotion_summary_parser.add_argument("--root", default=".")
    profile_promotion_summary_parser.add_argument("--promotions-dir", default=None)
    profile_promotion_summary_parser.add_argument("--output", default=None)
    profile_promotion_summary_parser.add_argument("--json", default=None)

    profile_promotion_apply_parser = subparsers.add_parser("profile-promotion-apply-plan", help="Generate a non-destructive profile promotion apply plan.")
    profile_promotion_apply_parser.add_argument("--root", default=".")
    profile_promotion_apply_parser.add_argument("--output", default=None)
    profile_promotion_apply_parser.add_argument("--json", default=None)

    profile_promotion_apply_run_parser = subparsers.add_parser("profile-promotion-apply", help="Apply a hash-matched profile promotion apply plan with a backup.")
    profile_promotion_apply_run_parser.add_argument("--root", default=".")
    profile_promotion_apply_run_parser.add_argument("--apply-plan", required=True)
    profile_promotion_apply_run_parser.add_argument("--apply-plan-hash", required=True)
    profile_promotion_apply_run_parser.add_argument("--backup-dir", default=None)
    profile_promotion_apply_run_parser.add_argument("--applied-at", default=None)
    profile_promotion_apply_run_parser.add_argument("--output", default=None)
    profile_promotion_apply_run_parser.add_argument("--json", default=None)

    profile_promotion_revoke_parser = subparsers.add_parser("profile-promotion-revoke-plan", help="Generate a non-destructive profile promotion revocation plan.")
    profile_promotion_revoke_parser.add_argument("--root", default=".")
    profile_promotion_revoke_parser.add_argument("--reviewer", required=True)
    profile_promotion_revoke_parser.add_argument("--reason", required=True)
    profile_promotion_revoke_parser.add_argument("--apply-result", default=None)
    profile_promotion_revoke_parser.add_argument("--requested-at", default=None)
    profile_promotion_revoke_parser.add_argument("--output", default=None)
    profile_promotion_revoke_parser.add_argument("--json", default=None)

    profile_promotion_revoke_run_parser = subparsers.add_parser("profile-promotion-revoke", help="Apply a hash-matched profile promotion revocation plan with a backup.")
    profile_promotion_revoke_run_parser.add_argument("--root", default=".")
    profile_promotion_revoke_run_parser.add_argument("--revoke-plan", required=True)
    profile_promotion_revoke_run_parser.add_argument("--revoke-plan-hash", required=True)
    profile_promotion_revoke_run_parser.add_argument("--backup-dir", default=None)
    profile_promotion_revoke_run_parser.add_argument("--revoked-at", default=None)
    profile_promotion_revoke_run_parser.add_argument("--output", default=None)
    profile_promotion_revoke_run_parser.add_argument("--json", default=None)

    profile_lifecycle_parser = subparsers.add_parser("profile-lifecycle-ledger", help="Render a chronological profile lifecycle ledger.")
    profile_lifecycle_parser.add_argument("--root", default=".")
    profile_lifecycle_parser.add_argument("--output", default=None)
    profile_lifecycle_parser.add_argument("--json", default=None)

    profile_pack_readiness_parser = subparsers.add_parser("profile-pack-readiness", help="Summarize profile-source and promotion readiness across profile packs.")
    profile_pack_readiness_parser.add_argument("--root", default=".")
    profile_pack_readiness_parser.add_argument("--output", default=None)
    profile_pack_readiness_parser.add_argument("--json", default=None)

    profile_pack_drilldown_parser = subparsers.add_parser("profile-pack-readiness-drilldown", help="Link profile-pack readiness findings to upstream local artifacts.")
    profile_pack_drilldown_parser.add_argument("--root", default=".")
    profile_pack_drilldown_parser.add_argument("--readiness", default=None)
    profile_pack_drilldown_parser.add_argument("--output", default=None)
    profile_pack_drilldown_parser.add_argument("--json", default=None)

    validate_json_parser = subparsers.add_parser("validate-json", help="Validate JSON files against bundled or custom JSON schema.")
    validate_json_parser.add_argument(
        "schema",
        help="Schema alias such as evidence, research-insight, project-profile, profile-source, profile-source-fix-plan, profile-source-fix-review, profile-pack-readiness, profile-pack-readiness-drilldown, budget-ledger, approval, or a schema path.",
    )
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

    discovery_parser = subparsers.add_parser("discover-workspace", help="Read-only workspace layout discovery and additive setup planning.")
    discovery_parser.add_argument("--root", default=".")
    discovery_parser.add_argument("--output", default=None)
    discovery_parser.add_argument("--json", default=None)
    discovery_parser.add_argument("--max-items", type=int, default=500)

    authority_parser = subparsers.add_parser("artifact-authority", help="Classify local artifact authority levels and detect projection authority risks.")
    authority_parser.add_argument("--root", default=".")
    authority_parser.add_argument("--output", default=None)
    authority_parser.add_argument("--json", default=None)

    goals_init_parser = subparsers.add_parser("goals-init", help="Create a local project goals/deadlines operating file.")
    goals_init_parser.add_argument("--root", default=".")
    goals_init_parser.add_argument("--output", default=None)
    goals_init_parser.add_argument("--force", action="store_true")

    goals_review_parser = subparsers.add_parser("goals-review", help="Review local objectives, deadlines, evidence, reports, and approvals.")
    goals_review_parser.add_argument("--root", default=".")
    goals_review_parser.add_argument("--output", default=None)
    goals_review_parser.add_argument("--json", default=None)

    deadline_check_parser = subparsers.add_parser("deadline-check", help="Check local deadline readiness from state/project-goals.json.")
    deadline_check_parser.add_argument("--root", default=".")
    deadline_check_parser.add_argument("--output", default=None)
    deadline_check_parser.add_argument("--json", default=None)

    next_actions_parser = subparsers.add_parser("next-actions", help="Generate a safe next-action plan from workspace doctor findings.")
    next_actions_parser.add_argument("--root", default=".")
    next_actions_parser.add_argument("--output", default=None)
    next_actions_parser.add_argument("--json", default=None)

    approval_coverage_parser = subparsers.add_parser("approval-coverage", help="Check report artifacts against supplied human approval records.")
    approval_coverage_parser.add_argument("--root", default=".")
    approval_coverage_parser.add_argument("--output", default=None)
    approval_coverage_parser.add_argument("--json", default=None)

    report_integrity_parser = subparsers.add_parser("report-integrity", help="Check report drafts against indexed evidence claims.")
    report_integrity_parser.add_argument("--root", default=".")
    report_integrity_parser.add_argument("--output", default=None)
    report_integrity_parser.add_argument("--json", default=None)

    workspace_summary_parser = subparsers.add_parser("workspace-summary", help="Generate a one-page operational workspace summary.")
    workspace_summary_parser.add_argument("--root", default=".")
    workspace_summary_parser.add_argument("--output", default=None)
    workspace_summary_parser.add_argument("--json", default=None)
    workspace_summary_parser.add_argument("--max-actions", type=int, default=5)

    weekly_review_parser = subparsers.add_parser("weekly-review", help="Generate a dated local weekly operating review.")
    weekly_review_parser.add_argument("--root", default=".")
    weekly_review_parser.add_argument("--date", default=None)
    weekly_review_parser.add_argument("--output", default=None)
    weekly_review_parser.add_argument("--json", default=None)
    weekly_review_parser.add_argument("--max-actions", type=int, default=5)

    workspace_dashboard_parser = subparsers.add_parser("workspace-dashboard", help="Generate a compact local workspace dashboard.")
    workspace_dashboard_parser.add_argument("--root", default=".")
    workspace_dashboard_parser.add_argument("--output", default=None)
    workspace_dashboard_parser.add_argument("--json", default=None)

    workflow_parser = subparsers.add_parser("workflow", help="Plan or run a thin local K-ResDev workflow.")
    workflow_parser.add_argument("workflow", choices=WORKFLOW_NAMES)
    workflow_parser.add_argument("--root", default=".")
    workflow_parser.add_argument("--output", default=None)
    workflow_parser.add_argument("--json", default=None)
    workflow_parser.add_argument("--date", default=None)
    workflow_parser.add_argument("--max-actions", type=int, default=5)
    workflow_parser.add_argument("--run", action="store_true")

    workspace_trace_parser = subparsers.add_parser("workspace-trace", help="Generate a local workspace traceability graph and impact report.")
    workspace_trace_parser.add_argument("--root", default=".")
    workspace_trace_parser.add_argument("--output", default=None)
    workspace_trace_parser.add_argument("--json", default=None)

    checkpoint_create_parser = subparsers.add_parser("checkpoint-create", help="Create a hash-backed local trace passport checkpoint.")
    checkpoint_create_parser.add_argument("--root", default=".")
    checkpoint_create_parser.add_argument("--stage", required=True)
    checkpoint_create_parser.add_argument("--summary", required=True)
    checkpoint_create_parser.add_argument("--artifact", action="append", default=[])
    checkpoint_create_parser.add_argument("--status", default="needs_review", choices=["draft", "needs_review", "accepted", "superseded"])
    checkpoint_create_parser.add_argument("--resume-hint", default=None)
    checkpoint_create_parser.add_argument("--unresolved-finding", action="append", default=[])
    checkpoint_create_parser.add_argument("--pending-human-decision", action="append", default=[])

    checkpoint_summary_parser = subparsers.add_parser("checkpoint-summary", help="Summarize trace passport checkpoints and stale artifacts.")
    checkpoint_summary_parser.add_argument("--root", default=".")
    checkpoint_summary_parser.add_argument("--output", default=None)
    checkpoint_summary_parser.add_argument("--json", default=None)

    checkpoint_resume_parser = subparsers.add_parser("checkpoint-resume-plan", help="Generate a compact resume plan from the latest or selected checkpoint.")
    checkpoint_resume_parser.add_argument("--root", default=".")
    checkpoint_resume_parser.add_argument("--checkpoint-id", default=None)
    checkpoint_resume_parser.add_argument("--output", default=None)
    checkpoint_resume_parser.add_argument("--json", default=None)

    review_pack_parser = subparsers.add_parser(
        "workspace-review-pack",
        help="Generate readiness, next-action, summary, goals, weekly, dashboard, profile, source, approval, report, bibliography, reference-corpus, citation-support, trace-passport, and trace artifacts in one local review pack.",
    )
    review_pack_parser.add_argument("--root", default=".")
    review_pack_parser.add_argument("--reports-dir", default=None)
    review_pack_parser.add_argument("--state-dir", default=None)
    review_pack_parser.add_argument("--max-actions", type=int, default=5)

    verify_review_pack_parser = subparsers.add_parser("verify-review-pack", help="Verify review-pack generated artifacts against saved hashes.")
    verify_review_pack_parser.add_argument("manifest_json")

    verify_sources_parser = subparsers.add_parser("verify-evidence-sources", help="Verify evidence index source files against saved source hashes.")
    verify_sources_parser.add_argument("evidence_index_json")
    verify_sources_parser.add_argument("--root", default=None)
    verify_sources_parser.add_argument("--inbox", default=None)
    verify_sources_parser.add_argument("--output", default=None)
    verify_sources_parser.add_argument("--json", default=None)

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
        payload = _load_json(args.evidence_json)
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
        payload = _load_json(args.papers_json)
        rendered = generate_literature_matrix(
            [PaperRecord.model_validate(item) for item in payload],
            args.output,
        )
        print(rendered)
        return 0
    if args.command == "bib-import":
        result = import_bibliography(args.bibliography_file, args.state_dir, args.literature_matrix)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "bib-lit-matrix":
        entries = load_bibliography_index(args.bibliography_index_json)
        rendered = generate_literature_matrix(paper_records_from_bibliography(entries), args.output)
        print(rendered)
        return 0
    if args.command == "bib-integrity":
        result = generate_workspace_bibliography_integrity(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "reference-corpus":
        result = build_reference_corpus(
            args.root,
            references_dir=args.references,
            output_path=args.output,
            json_path=args.json,
            rejection_json_path=args.rejections,
        )
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "bib-review-record":
        record = create_bibliography_review_record(
            bibliography_id=args.bibliography_id,
            decision=args.decision,
            reviewer=args.reviewer,
            citation_key=args.citation_key,
            paper_id=args.paper_id,
            notes=args.note,
            risk_flags=args.risk_flag,
            reviewed_at=args.reviewed_at,
        )
        if not args.print_only:
            write_bibliography_review_record(record, args.reviews_dir)
        print(record.model_dump_json(indent=2))
        return 0
    if args.command == "bib-review-summary":
        records = load_bibliography_review_records(args.review_records)
        rendered = generate_bibliography_review_summary(records, args.output)
        print(rendered)
        return 0
    if args.command == "bib-review-status":
        records = load_bibliography_review_records(args.review_records)
        print(json.dumps(bibliography_review_status(records, args.bibliography_id), ensure_ascii=False, indent=2))
        return 0
    if args.command == "citation-support-record":
        record = create_citation_support_record(
            bibliography_id=args.bibliography_id,
            claim=args.claim,
            decision=args.decision,
            reviewer=args.reviewer,
            citation_key=args.citation_key,
            paper_id=args.paper_id,
            locator=args.locator,
            quote=args.quote,
            evidence_ids=args.evidence_id,
            notes=args.note,
            risk_flags=args.risk_flag,
            reviewed_at=args.reviewed_at,
        )
        if not args.print_only:
            write_citation_support_record(record, args.support_dir)
        print(record.model_dump_json(indent=2))
        return 0
    if args.command == "citation-support-summary":
        records = load_citation_support_records(args.support_records)
        rendered = generate_citation_support_summary(records, args.output)
        print(rendered)
        return 0
    if args.command == "citation-support-status":
        records = load_citation_support_records(args.support_records)
        print(json.dumps(citation_support_status(records, args.bibliography_id, args.claim), ensure_ascii=False, indent=2))
        return 0
    if args.command == "citation-support-integrity":
        result = generate_workspace_citation_support_integrity(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "research-claim-import":
        result = import_research_claims(args.claim_file, state_dir=args.state_dir, markdown_path=args.markdown)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "research-claim-summary":
        claims = load_research_claims(args.claims_json)
        rendered = render_research_claims_markdown(claims, source_file=args.claims_json)
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
        print(rendered)
        return 0
    if args.command == "research-claim-matrix":
        result = generate_research_claim_matrix(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
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
        payload = _load_json(args.insights_json)
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
    if args.command == "budget-ledger-import":
        result = import_budget_ledger(args.ledger_file, state_dir=args.state_dir, markdown_path=args.markdown)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "budget-ledger-integrity":
        result = generate_workspace_budget_ledger(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
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
    if args.command == "profile-source-record":
        source_path = Path(args.profile_sources) if args.profile_sources else default_profile_sources_path(args.root)
        retrieved_at = args.retrieved_at or (utc_now_iso() if args.now else None)
        record = create_profile_source_record(
            profile_id=args.profile_id,
            title=args.title,
            source_url=args.source_url,
            source_file=args.source_file,
            retrieved_at=retrieved_at,
            source_hash=args.source_hash,
            verified_by=args.verified_by,
            review_status=args.review_status,
            validity_notes=args.validity_note,
            risk_flags=args.risk_flag,
            source_id=args.source_id,
            root=args.root,
        )
        if not args.print_only:
            record_profile_source(record, source_path)
        print(record.model_dump_json(indent=2))
        return 0
    if args.command == "profile-source-summary":
        result = summarize_profile_sources(
            args.root,
            profile_id=args.profile_id,
            profile_sources_path=args.profile_sources,
            profile_path=args.profile_path,
            output_path=args.output,
            json_path=args.json,
        )
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "profile-source-queue":
        result = generate_profile_source_queue(args.root, templates_root=args.templates_root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0 if result.status != "blocked" else 1
    if args.command == "profile-source-fix-plan":
        result = generate_profile_source_fix_plan(args.root, queue_path=args.queue, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0 if result.status not in {"blocked", "missing_queue", "unreadable_queue"} else 1
    if args.command == "profile-source-fix-record":
        record = create_profile_source_fix_review_record(
            args.root,
            action_id=args.action_id,
            decision=args.decision,
            reviewer=args.reviewer,
            fix_plan_hash=args.fix_plan_hash,
            fix_plan_path=args.fix_plan,
            reviewed_at=args.reviewed_at,
            notes=args.note,
            risk_flags=args.risk_flag,
        )
        if not args.print_only:
            reviews_dir = Path(args.reviews_dir) if args.reviews_dir else default_profile_source_fix_reviews_dir(args.root)
            write_profile_source_fix_review_record(record, reviews_dir)
        print(record.model_dump_json(indent=2))
        return 0
    if args.command == "profile-source-fix-summary":
        result = summarize_profile_source_fix_reviews(
            args.root,
            fix_plan_path=args.fix_plan,
            reviews_dir=args.reviews_dir,
            output_path=args.output,
            json_path=args.json,
        )
        print(result.model_dump_json(indent=2))
        return 0 if result.status != "blocked" else 1
    if args.command == "profile-integrity":
        result = generate_profile_integrity(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "profile-review":
        result = generate_profile_review(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0 if result.status != "blocked" else 1
    if args.command == "profile-promotion-record":
        record = create_profile_promotion_record(
            args.root,
            decision=args.decision,
            reviewer=args.reviewer,
            profile_review_hash=args.profile_review_hash,
            profile_review_path=args.profile_review,
            reviewed_at=args.reviewed_at,
            notes=args.note,
            risk_flags=args.risk_flag,
        )
        if not args.print_only:
            promotions_dir = Path(args.promotions_dir) if args.promotions_dir else default_profile_promotions_dir(args.root)
            write_profile_promotion_record(record, promotions_dir)
        print(record.model_dump_json(indent=2))
        return 0
    if args.command == "profile-promotion-summary":
        result = summarize_profile_promotions(
            args.root,
            promotions_dir=args.promotions_dir,
            output_path=args.output,
            json_path=args.json,
        )
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "profile-promotion-apply-plan":
        result = generate_profile_promotion_apply_plan(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0 if result.status in {"ready_to_apply", "already_applied"} else 1
    if args.command == "profile-promotion-apply":
        result = apply_profile_promotion_plan(
            args.root,
            apply_plan_path=args.apply_plan,
            apply_plan_hash=args.apply_plan_hash,
            output_path=args.output,
            json_path=args.json,
            backup_dir=args.backup_dir,
            applied_at=args.applied_at,
        )
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "profile-promotion-revoke-plan":
        result = generate_profile_promotion_revoke_plan(
            args.root,
            reviewer=args.reviewer,
            reason=args.reason,
            apply_result_path=args.apply_result,
            requested_at=args.requested_at,
            output_path=args.output,
            json_path=args.json,
        )
        print(result.model_dump_json(indent=2))
        return 0 if result.status in {"ready_to_revoke", "already_restored"} else 1
    if args.command == "profile-promotion-revoke":
        result = revoke_profile_promotion_plan(
            args.root,
            revoke_plan_path=args.revoke_plan,
            revoke_plan_hash=args.revoke_plan_hash,
            output_path=args.output,
            json_path=args.json,
            backup_dir=args.backup_dir,
            revoked_at=args.revoked_at,
        )
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "profile-lifecycle-ledger":
        result = generate_profile_lifecycle_ledger(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0 if result.status != "blocked" else 1
    if args.command == "profile-pack-readiness":
        result = generate_profile_pack_readiness(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0 if result.status != "blocked" else 1
    if args.command == "profile-pack-readiness-drilldown":
        result = generate_profile_pack_readiness_drilldown(args.root, readiness_path=args.readiness, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0 if result.status != "blocked" else 1
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
    if args.command == "discover-workspace":
        result = discover_workspace(args.root, output_path=args.output, json_path=args.json, max_items=args.max_items)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "artifact-authority":
        result = generate_artifact_authority(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "goals-init":
        result = initialize_project_goals(args.root, output_path=args.output, overwrite=args.force)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command in {"goals-review", "deadline-check"}:
        result = generate_goals_review(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "next-actions":
        result = generate_workspace_action_plan(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "approval-coverage":
        result = generate_workspace_approval_coverage(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "report-integrity":
        result = generate_workspace_report_integrity(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "workspace-summary":
        result = generate_workspace_summary(args.root, output_path=args.output, json_path=args.json, max_actions=args.max_actions)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "weekly-review":
        root = Path(args.root)
        review_date = args.date or date.today().isoformat()
        output = args.output or root / "reports" / f"weekly-review-{review_date}.md"
        json_output = args.json or root / "state" / f"weekly-review-{review_date}.json"
        result = generate_weekly_review(args.root, review_date=review_date, output_path=output, json_path=json_output, max_actions=args.max_actions)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "workspace-dashboard":
        root = Path(args.root)
        result = generate_workspace_dashboard(
            args.root,
            output_path=args.output or root / "reports" / "workspace-dashboard.md",
            json_path=args.json or root / "state" / "workspace-dashboard.json",
        )
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "workflow":
        root = Path(args.root)
        output = args.output or root / "reports" / f"workflow-{args.workflow}.md"
        json_output = args.json or root / "state" / f"workflow-{args.workflow}.json"
        result = generate_workflow_plan(
            args.root,
            args.workflow,
            output_path=output,
            json_path=json_output,
            execute=args.run,
            review_date=args.date,
            max_actions=args.max_actions,
        )
        print(result.model_dump_json(indent=2))
        return 0 if result.status != "failed" else 1
    if args.command == "workspace-trace":
        result = generate_workspace_trace(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "checkpoint-create":
        result = create_checkpoint(
            args.root,
            stage=args.stage,
            summary=args.summary,
            artifact_paths=args.artifact,
            status=args.status,
            resume_hint=args.resume_hint,
            unresolved_findings=args.unresolved_finding,
            pending_human_decisions=args.pending_human_decision,
        )
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "checkpoint-summary":
        result = generate_trace_passport(args.root, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "checkpoint-resume-plan":
        result = generate_checkpoint_resume_plan(args.root, checkpoint_id=args.checkpoint_id, output_path=args.output, json_path=args.json)
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
    if args.command == "verify-evidence-sources":
        result = verify_evidence_sources(args.evidence_index_json, root=args.root, inbox=args.inbox, output_path=args.output, json_path=args.json)
        print(result.model_dump_json(indent=2))
        return 0 if result.valid else 1
    raise AssertionError(f"Unhandled command: {args.command}")


def _load_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))
