"""K-ResDev evidence-first R&D skill helpers."""

from .approval import (
    approval_gate_status,
    create_approval_record,
    generate_approval_summary,
    latest_approval_for_target,
    load_approval_records,
    write_approval_record,
)
from .analysis import generate_analysis_script, run_data_analysis
from .claim_checker import check_unsupported_claims
from .budget import budget_evidence_gaps, generate_budget_evidence_checklist
from .classifier import classify_file
from .data_profiler import profile_data_file
from .document_extractors import extract_document_text
from .evidence_bundle import generate_evidence_bundle_index
from .evidence_extraction import extract_evidence_items_from_document
from .evidence_index import load_evidence_index, write_evidence_index
from .experiment_planner import generate_experiment_plan, generate_experiment_plan_bundle
from .audit import generate_audit_qna
from .intake import run_intake
from .literature import generate_literature_matrix
from .models import (
    ApprovalRecord,
    AnalysisRunResult,
    CheckFinding,
    DataProfile,
    EvidenceItem,
    ExtractedDocument,
    ExtractedSegment,
    FileClassification,
    IntakeResult,
    KPI,
    Milestone,
    PaperRecord,
    ProjectState,
    ProjectProfile,
    ProjectionExportResult,
    ReportDraftPaths,
    ResearchInsight,
    SourceRecord,
    WorkspaceActionItem,
    WorkspaceActionPlan,
    WorkspaceDoctorFinding,
    WorkspaceDoctorResult,
    WorkspaceInitResult,
)
from .plan_mapper import extract_project_state_from_text
from .profile_registry import generate_profile_registry, list_project_profiles, load_project_profile
from .projection_export import export_projection, write_projection_docx, write_projection_html, write_projection_text
from .research_assistant import (
    generate_data_insight_candidates,
    generate_data_insight_report,
    generate_experiment_comparison_table,
    generate_paper_card_markdown,
    generate_reproducibility_checklist,
    paper_card_from_text,
)
from .reporting import draft_monthly_report, write_monthly_report
from .schema_tools import validate_json_file, validate_json_files
from .workspace import initialize_workspace, render_doctor_markdown, run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan, render_action_plan_markdown

__all__ = [
    "ApprovalRecord",
    "AnalysisRunResult",
    "CheckFinding",
    "DataProfile",
    "EvidenceItem",
    "ExtractedDocument",
    "ExtractedSegment",
    "FileClassification",
    "IntakeResult",
    "KPI",
    "Milestone",
    "PaperRecord",
    "ProjectState",
    "ProjectProfile",
    "ProjectionExportResult",
    "ReportDraftPaths",
    "ResearchInsight",
    "SourceRecord",
    "WorkspaceActionItem",
    "WorkspaceActionPlan",
    "WorkspaceDoctorFinding",
    "WorkspaceDoctorResult",
    "WorkspaceInitResult",
    "approval_gate_status",
    "budget_evidence_gaps",
    "create_approval_record",
    "check_unsupported_claims",
    "classify_file",
    "draft_monthly_report",
    "extract_document_text",
    "extract_evidence_items_from_document",
    "extract_project_state_from_text",
    "export_projection",
    "generate_audit_qna",
    "generate_approval_summary",
    "generate_analysis_script",
    "generate_budget_evidence_checklist",
    "generate_data_insight_candidates",
    "generate_data_insight_report",
    "generate_experiment_plan",
    "generate_experiment_plan_bundle",
    "generate_experiment_comparison_table",
    "generate_evidence_bundle_index",
    "generate_literature_matrix",
    "generate_paper_card_markdown",
    "generate_profile_registry",
    "generate_reproducibility_checklist",
    "generate_workspace_action_plan",
    "initialize_workspace",
    "list_project_profiles",
    "latest_approval_for_target",
    "load_approval_records",
    "load_evidence_index",
    "load_project_profile",
    "profile_data_file",
    "paper_card_from_text",
    "run_intake",
    "run_data_analysis",
    "write_monthly_report",
    "render_doctor_markdown",
    "render_action_plan_markdown",
    "run_workspace_doctor",
    "validate_json_file",
    "validate_json_files",
    "write_approval_record",
    "write_evidence_index",
    "write_projection_docx",
    "write_projection_html",
    "write_projection_text",
]

__version__ = "0.1.0b9"
