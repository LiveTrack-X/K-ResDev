"""K-ResDev evidence-first R&D skill helpers."""

from .claim_checker import check_unsupported_claims
from .classifier import classify_file
from .data_profiler import profile_data_file
from .document_extractors import extract_document_text
from .evidence_extraction import extract_evidence_items_from_document
from .evidence_index import load_evidence_index, write_evidence_index
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
    "check_unsupported_claims",
    "classify_file",
    "draft_monthly_report",
    "extract_document_text",
    "extract_evidence_items_from_document",
    "extract_project_state_from_text",
    "generate_audit_qna",
    "generate_literature_matrix",
    "load_evidence_index",
    "profile_data_file",
    "run_intake",
    "write_monthly_report",
    "write_evidence_index",
]

__version__ = "0.1.0b2"
