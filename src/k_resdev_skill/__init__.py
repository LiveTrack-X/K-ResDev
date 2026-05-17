"""K-ResDev evidence-first R&D skill helpers."""

from .approval import (
    approval_gate_status,
    create_approval_record,
    generate_approval_summary,
    latest_approval_for_target,
    load_approval_records,
    write_approval_record,
)
from .approval_coverage import generate_workspace_approval_coverage, render_approval_coverage_markdown
from .analysis import generate_analysis_script, run_data_analysis
from .bibliography import (
    import_bibliography,
    load_bibliography_index,
    paper_records_from_bibliography,
    parse_bibliography_file,
    render_bibliography_index,
)
from .bibliography_integrity import (
    extract_markdown_citation_keys,
    generate_workspace_bibliography_integrity,
    render_bibliography_integrity_markdown,
)
from .bibliography_review import (
    bibliography_review_status,
    create_bibliography_review_record,
    generate_bibliography_review_summary,
    latest_bibliography_review,
    load_bibliography_review_records,
    write_bibliography_review_record,
)
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
    BibliographyEntry,
    BibliographyIntegrityFinding,
    BibliographyImportResult,
    BibliographyReviewDecision,
    BibliographyReviewRecord,
    CheckFinding,
    DataProfile,
    EvidenceSourceVerificationItem,
    EvidenceSourceVerificationResult,
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
    ReviewPackArtifact,
    ReviewPackVerificationItem,
    ResearchInsight,
    SourceRecord,
    WorkspaceActionItem,
    WorkspaceActionPlan,
    WorkspaceApprovalCoverageItem,
    WorkspaceApprovalCoverageResult,
    WorkspaceBibliographyIntegrityResult,
    WorkspaceDoctorFinding,
    WorkspaceDoctorResult,
    WorkspaceInitResult,
    WorkspaceReportIntegrityItem,
    WorkspaceReportIntegrityResult,
    WorkspaceReviewPackResult,
    WorkspaceReviewPackVerificationResult,
    WorkspaceSummaryResult,
)
from .plan_mapper import extract_project_state_from_text
from .profile_registry import generate_profile_registry, list_project_profiles, load_project_profile
from .projection_export import export_projection, write_projection_docx, write_projection_html, write_projection_text
from .report_integrity import generate_workspace_report_integrity, render_report_integrity_markdown
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
from .source_verification import render_evidence_source_verification_markdown, verify_evidence_sources
from .workspace import initialize_workspace, render_doctor_markdown, run_workspace_doctor
from .workspace_actions import generate_workspace_action_plan, render_action_plan_markdown
from .workspace_review import (
    generate_workspace_review_pack,
    render_workspace_review_pack_markdown,
    verify_workspace_review_pack,
)
from .workspace_summary import generate_workspace_summary, render_workspace_summary_markdown

__all__ = [
    "ApprovalRecord",
    "AnalysisRunResult",
    "BibliographyEntry",
    "BibliographyIntegrityFinding",
    "BibliographyImportResult",
    "BibliographyReviewDecision",
    "BibliographyReviewRecord",
    "CheckFinding",
    "DataProfile",
    "EvidenceSourceVerificationItem",
    "EvidenceSourceVerificationResult",
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
    "ReviewPackArtifact",
    "ReviewPackVerificationItem",
    "ResearchInsight",
    "SourceRecord",
    "WorkspaceActionItem",
    "WorkspaceActionPlan",
    "WorkspaceApprovalCoverageItem",
    "WorkspaceApprovalCoverageResult",
    "WorkspaceBibliographyIntegrityResult",
    "WorkspaceDoctorFinding",
    "WorkspaceDoctorResult",
    "WorkspaceInitResult",
    "WorkspaceReportIntegrityItem",
    "WorkspaceReportIntegrityResult",
    "WorkspaceReviewPackResult",
    "WorkspaceReviewPackVerificationResult",
    "WorkspaceSummaryResult",
    "approval_gate_status",
    "bibliography_review_status",
    "budget_evidence_gaps",
    "create_approval_record",
    "create_bibliography_review_record",
    "check_unsupported_claims",
    "classify_file",
    "draft_monthly_report",
    "extract_document_text",
    "extract_evidence_items_from_document",
    "extract_project_state_from_text",
    "export_projection",
    "extract_markdown_citation_keys",
    "generate_audit_qna",
    "generate_approval_summary",
    "generate_analysis_script",
    "generate_budget_evidence_checklist",
    "generate_bibliography_review_summary",
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
    "generate_workspace_approval_coverage",
    "generate_workspace_bibliography_integrity",
    "generate_workspace_report_integrity",
    "generate_workspace_review_pack",
    "generate_workspace_summary",
    "import_bibliography",
    "initialize_workspace",
    "load_bibliography_index",
    "list_project_profiles",
    "latest_approval_for_target",
    "latest_bibliography_review",
    "load_approval_records",
    "load_bibliography_review_records",
    "load_evidence_index",
    "load_project_profile",
    "profile_data_file",
    "paper_records_from_bibliography",
    "paper_card_from_text",
    "parse_bibliography_file",
    "render_bibliography_index",
    "render_bibliography_integrity_markdown",
    "run_intake",
    "run_data_analysis",
    "write_monthly_report",
    "render_doctor_markdown",
    "render_action_plan_markdown",
    "render_approval_coverage_markdown",
    "render_evidence_source_verification_markdown",
    "render_report_integrity_markdown",
    "render_workspace_review_pack_markdown",
    "render_workspace_summary_markdown",
    "run_workspace_doctor",
    "validate_json_file",
    "validate_json_files",
    "verify_evidence_sources",
    "verify_workspace_review_pack",
    "write_approval_record",
    "write_bibliography_review_record",
    "write_evidence_index",
    "write_projection_docx",
    "write_projection_html",
    "write_projection_text",
]

__version__ = "0.1.0b21"
