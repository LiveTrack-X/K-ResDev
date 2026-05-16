"""K-ResDev evidence-first R&D skill helpers."""

from .claim_checker import check_unsupported_claims
from .budget import budget_evidence_gaps, generate_budget_evidence_checklist
from .classifier import classify_file
from .data_profiler import profile_data_file
from .document_extractors import extract_document_text
from .evidence_extraction import extract_evidence_items_from_document
from .evidence_index import load_evidence_index, write_evidence_index
from .experiment_planner import generate_experiment_plan, generate_experiment_plan_bundle
from .audit import generate_audit_qna
from .intake import run_intake
from .literature import generate_literature_matrix
from .models import (
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
    ReportDraftPaths,
    ResearchInsight,
    SourceRecord,
)
from .plan_mapper import extract_project_state_from_text
from .profile_registry import generate_profile_registry, list_project_profiles, load_project_profile
from .research_assistant import (
    generate_data_insight_candidates,
    generate_data_insight_report,
    generate_experiment_comparison_table,
    generate_paper_card_markdown,
    generate_reproducibility_checklist,
    paper_card_from_text,
)
from .reporting import draft_monthly_report, write_monthly_report

__all__ = [
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
    "ReportDraftPaths",
    "ResearchInsight",
    "SourceRecord",
    "budget_evidence_gaps",
    "check_unsupported_claims",
    "classify_file",
    "draft_monthly_report",
    "extract_document_text",
    "extract_evidence_items_from_document",
    "extract_project_state_from_text",
    "generate_audit_qna",
    "generate_budget_evidence_checklist",
    "generate_data_insight_candidates",
    "generate_data_insight_report",
    "generate_experiment_plan",
    "generate_experiment_plan_bundle",
    "generate_experiment_comparison_table",
    "generate_literature_matrix",
    "generate_paper_card_markdown",
    "generate_profile_registry",
    "generate_reproducibility_checklist",
    "list_project_profiles",
    "load_evidence_index",
    "load_project_profile",
    "profile_data_file",
    "paper_card_from_text",
    "run_intake",
    "write_monthly_report",
    "write_evidence_index",
]

__version__ = "0.1.0b4"
