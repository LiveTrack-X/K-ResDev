from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_default=True)


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class EvidenceStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EvidenceType(str, Enum):
    PLAN_GOAL = "plan_goal"
    KPI = "kpi"
    MILESTONE = "milestone"
    EXPERIMENT_RESULT = "experiment_result"
    BUDGET_EVIDENCE = "budget_evidence"
    MEETING_DECISION = "meeting_decision"
    RISK = "risk"
    OUTCOME = "outcome"
    CHANGE_REQUEST = "change_request"
    PAPER_CLAIM = "paper_claim"
    DATA_PROFILE = "data_profile"
    RESEARCH_INSIGHT = "research_insight"


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    REPORTING = "reporting"
    CLOSED = "closed"


class KPIStatus(str, Enum):
    PLANNED = "planned"
    NEEDS_REVIEW = "needs_review"
    ON_TRACK = "on_track"
    BELOW_TARGET = "below_target"
    MET = "met"
    MISSED = "missed"
    SUPERSEDED = "superseded"


class MilestoneStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    DELAYED = "delayed"
    NEEDS_REVIEW = "needs_review"
    SUPERSEDED = "superseded"


class InsightStatus(str, Enum):
    HYPOTHESIS = "hypothesis"
    NEEDS_REVIEW = "needs_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"
    REVOKED = "revoked"


class BibliographyReviewDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    SUPERSEDED = "superseded"


class CitationSupportDecision(str, Enum):
    SUPPORTS = "supports"
    PARTIALLY_SUPPORTS = "partially_supports"
    DOES_NOT_SUPPORT = "does_not_support"
    NEEDS_REVIEW = "needs_review"
    SUPERSEDED = "superseded"


class ProfileSourceFixReviewDecision(str, Enum):
    RESOLVED = "resolved"
    ACCEPTED_RISK = "accepted_risk"
    DEFERRED = "deferred"
    REJECTED = "rejected"


class ProfilePackPackageReceiptDecision(str, Enum):
    RECEIVED = "received"
    ACCEPTED_FOR_REVIEW = "accepted_for_review"
    NEEDS_CHANGES = "needs_changes"
    REJECTED = "rejected"


class AdminProfilePackReviewDecision(str, Enum):
    ACCEPTED = "accepted"
    ACCEPTED_RISK = "accepted_risk"
    NEEDS_CHANGES = "needs_changes"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class AdminProfilePackReviewTargetType(str, Enum):
    PACK = "pack"
    OBLIGATION = "obligation"
    SUBMISSION = "submission"
    SETTLEMENT_REQUIREMENT = "settlement_requirement"


class ResearchClaimStatus(str, Enum):
    HYPOTHESIS = "hypothesis"
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class TracePassportStatus(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"


class ApprovalTargetType(str, Enum):
    REPORT = "report"
    EVIDENCE = "evidence"
    INSIGHT = "insight"
    BUDGET = "budget"
    PROFILE = "profile"
    BUNDLE = "bundle"
    OTHER = "other"


class FileCategory(str, Enum):
    PLAN = "plan"
    PROGRESS = "progress"
    EXPERIMENT = "experiment"
    BUDGET = "budget"
    OUTCOME = "outcome"
    CHANGE = "change"
    LITERATURE = "literature"
    DATA = "data"
    UNKNOWN = "unknown"


class Provenance(StrictModel):
    page: int | None = None
    sheet: str | None = None
    cell_range: str | None = None
    line_range: str | None = None
    quote: str | None = None


class EvidenceItem(StrictModel):
    evidence_id: str
    source_file: str
    source_hash: str | None = None
    evidence_type: EvidenceType
    project: str | None = None
    linked_goal: str | None = None
    linked_kpi: str | None = None
    claim: str
    value: dict[str, Any] = Field(default_factory=dict)
    confidence: Confidence = Confidence.UNKNOWN
    status: EvidenceStatus = EvidenceStatus.NEEDS_REVIEW
    risk_flags: list[str] = Field(default_factory=list)
    provenance: Provenance = Field(default_factory=Provenance)

    @field_validator("evidence_id", "source_file", "claim")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class KPI(StrictModel):
    kpi_id: str
    name: str
    target: float | str
    metric: str | None = None
    unit: str | None = None
    current_value: float | str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    status: KPIStatus = KPIStatus.NEEDS_REVIEW
    notes: str | None = None


class Milestone(StrictModel):
    milestone_id: str
    name: str
    due_date: date | None = None
    deliverable: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    status: MilestoneStatus = MilestoneStatus.PLANNED
    notes: str | None = None


class ProjectState(StrictModel):
    project_id: str
    title: str
    period: str
    status: ProjectStatus
    agency: str | None = None
    program: str | None = None
    participants: list[str] = Field(default_factory=list)
    goals: list[dict[str, Any]] = Field(default_factory=list)
    kpis: list[KPI] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)
    budget_categories: list[dict[str, Any]] = Field(default_factory=list)


class ProjectObjective(StrictModel):
    objective_id: str
    title: str
    weight: float | None = None
    status: str = "active"
    linked_kpis: list[str] = Field(default_factory=list)
    linked_milestones: list[str] = Field(default_factory=list)
    linked_evidence_ids: list[str] = Field(default_factory=list)
    linked_report_paths: list[str] = Field(default_factory=list)
    review_status: str = "needs_review"
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("objective_id", "title", "status", "review_status")
    @classmethod
    def _objective_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProjectDeadline(StrictModel):
    deadline_id: str
    due_date: date
    title: str
    deliverable_type: str
    linked_objective_ids: list[str] = Field(default_factory=list)
    linked_kpis: list[str] = Field(default_factory=list)
    linked_milestones: list[str] = Field(default_factory=list)
    linked_evidence_ids: list[str] = Field(default_factory=list)
    linked_report_paths: list[str] = Field(default_factory=list)
    approval_required: bool = True
    status: str = "planned"
    review_status: str = "needs_review"
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("deadline_id", "title", "deliverable_type", "status", "review_status")
    @classmethod
    def _deadline_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProjectGoalsFile(StrictModel):
    project_id: str | None = None
    title: str | None = None
    status: str = "needs_review"
    objectives: list[ProjectObjective] = Field(default_factory=list)
    deadlines: list[ProjectDeadline] = Field(default_factory=list)
    notes: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ResearchInsight(StrictModel):
    insight_id: str
    claim: str
    basis: list[str]
    confidence: Confidence
    assumptions: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    next_checks: list[str] = Field(default_factory=list)
    status: InsightStatus = InsightStatus.HYPOTHESIS


class FileClassification(StrictModel):
    category: FileCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)


class NumericSummary(StrictModel):
    count: int
    min: float | None = None
    max: float | None = None
    mean: float | None = None


class Missingness(StrictModel):
    missing_count: int
    missing_ratio: float


class DataProfile(StrictModel):
    source_file: str
    file_type: str
    row_count: int
    column_count: int
    columns: list[str]
    missingness: dict[str, Missingness]
    numeric_summary: dict[str, NumericSummary]
    possible_metrics: list[str] = Field(default_factory=list)


class ExtractedSegment(StrictModel):
    text: str
    page: int | None = None
    sheet: str | None = None
    cell_range: str | None = None
    line_range: str | None = None
    quote: str | None = None


class ExtractedDocument(StrictModel):
    source_file: str
    file_type: str
    text: str
    segments: list[ExtractedSegment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CheckFinding(StrictModel):
    code: str
    severity: str
    message: str
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_action: str | None = None


class EvidenceIndexPaths(StrictModel):
    markdown_path: str
    json_path: str


class SourceRecord(StrictModel):
    source_id: str
    path: str
    source_hash: str
    size_bytes: int
    modified_time_utc: str | None = None
    classification: FileClassification
    evidence_ids: list[str] = Field(default_factory=list)


class IntakeResult(StrictModel):
    source_count: int
    evidence_count: int
    raw_registry_path: str
    evidence_dir: str
    evidence_index_markdown_path: str
    evidence_index_json_path: str
    open_issues_path: str


class ReportDraftPaths(StrictModel):
    report_path: str
    review_path: str | None = None


class AnalysisRunResult(StrictModel):
    analysis_id: str
    source_file: str
    source_hash: str
    profile_path: str
    insight_report_path: str
    script_path: str | None = None
    manifest_path: str
    evidence_ids: list[str] = Field(default_factory=list)
    status: str = "draft"
    warnings: list[str] = Field(default_factory=list)


class ProjectionExportResult(StrictModel):
    export_id: str
    source_path: str
    source_hash: str
    output_path: str
    output_format: str
    status: str = "draft"
    warnings: list[str] = Field(default_factory=list)


class BudgetLedgerItem(StrictModel):
    ledger_id: str
    date: str | None = None
    vendor: str | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: str = "KRW"
    category: str | None = None
    proof_type: str | None = None
    approval_reference: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    invoice_id: str | None = None
    source_file: str | None = None
    source_hash: str | None = None
    review_status: str = "needs_review"
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("ledger_id")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class BudgetLedgerImportResult(StrictModel):
    source_file: str
    source_hash: str
    source_format: str
    item_count: int = 0
    ledger_json_path: str
    ledger_markdown_path: str
    warnings: list[str] = Field(default_factory=list)


class BudgetLedgerFinding(StrictModel):
    code: str
    severity: str
    message: str
    ledger_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None


class SettlementBinderItem(StrictModel):
    ledger_id: str
    date: str | None = None
    vendor: str | None = None
    amount: float | None = None
    currency: str = "KRW"
    category: str | None = None
    proof_type: str | None = None
    approval_reference: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    source_file: str | None = None
    source_hash: str | None = None
    review_status: str = "needs_review"
    finding_codes: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("ledger_id", "currency", "review_status")
    @classmethod
    def _settlement_item_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class WorkspaceSettlementBinderResult(StrictModel):
    root: str
    status: str
    item_count: int = 0
    linked_evidence_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    items: list[SettlementBinderItem] = Field(default_factory=list)
    findings: list[BudgetLedgerFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WorkspaceBudgetLedgerResult(StrictModel):
    root: str
    status: str
    ledger_count: int = 0
    linked_evidence_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_by_currency: dict[str, float] = Field(default_factory=dict)
    amount_by_category: dict[str, float] = Field(default_factory=dict)
    items: list[BudgetLedgerItem] = Field(default_factory=list)
    findings: list[BudgetLedgerFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class BibliographyEntry(StrictModel):
    bibliography_id: str
    paper_id: str
    citation_key: str | None = None
    entry_type: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    keywords: list[str] = Field(default_factory=list)
    source_file: str
    source_format: str
    source_hash: str | None = None
    status: str = "needs_review"
    risk_flags: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("bibliography_id", "paper_id", "entry_type", "title", "source_file", "source_format")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class BibliographyImportResult(StrictModel):
    source_file: str
    source_hash: str
    source_format: str
    entry_count: int = 0
    bibliography_index_markdown_path: str
    bibliography_index_json_path: str
    literature_matrix_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ReferenceCorpusItem(StrictModel):
    reference_id: str
    adapter: str
    source_file: str
    source_hash: str | None = None
    source_format: str
    citation_key: str | None = None
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    keywords: list[str] = Field(default_factory=list)
    user_notes: str | None = None
    status: str = "needs_review"
    risk_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reference_id", "adapter", "source_file", "source_format")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ReferenceCorpusRejection(StrictModel):
    rejection_id: str
    adapter: str
    source_file: str
    reason: str
    message: str
    severity: str = "medium"
    source_hash: str | None = None
    citation_key: str | None = None
    reference_id: str | None = None
    path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("rejection_id", "adapter", "source_file", "reason", "message")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ReferenceCorpusResult(StrictModel):
    root: str
    references_dir: str
    status: str
    item_count: int = 0
    rejection_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    items: list[ReferenceCorpusItem] = Field(default_factory=list)
    rejections: list[ReferenceCorpusRejection] = Field(default_factory=list)
    summary_markdown_path: str | None = None
    corpus_json_path: str | None = None
    rejection_log_json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class BibliographyReviewRecord(StrictModel):
    review_id: str
    bibliography_id: str
    decision: BibliographyReviewDecision
    reviewer: str
    reviewed_at: str
    citation_key: str | None = None
    paper_id: str | None = None
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("review_id", "bibliography_id", "reviewer", "reviewed_at")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class CitationSupportRecord(StrictModel):
    support_id: str
    bibliography_id: str
    claim: str
    decision: CitationSupportDecision
    reviewer: str
    reviewed_at: str
    citation_key: str | None = None
    paper_id: str | None = None
    locator: str | None = None
    quote: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("support_id", "bibliography_id", "claim", "reviewer", "reviewed_at")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ResearchClaim(StrictModel):
    claim_id: str
    claim: str
    claim_type: str = "research"
    evidence_ids: list[str] = Field(default_factory=list)
    citation_keys: list[str] = Field(default_factory=list)
    bibliography_ids: list[str] = Field(default_factory=list)
    support_ids: list[str] = Field(default_factory=list)
    insight_ids: list[str] = Field(default_factory=list)
    status: ResearchClaimStatus = ResearchClaimStatus.NEEDS_REVIEW
    confidence: Confidence = Confidence.UNKNOWN
    risk_flags: list[str] = Field(default_factory=list)
    next_checks: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("claim_id", "claim", "claim_type")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ResearchClaimImportResult(StrictModel):
    source_file: str
    source_hash: str
    source_format: str
    claim_count: int = 0
    claims_json_path: str
    claims_markdown_path: str
    warnings: list[str] = Field(default_factory=list)


class ResearchClaimMatrixFinding(StrictModel):
    code: str
    severity: str
    message: str
    claim_id: str | None = None
    evidence_id: str | None = None
    citation_key: str | None = None
    bibliography_id: str | None = None
    support_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None


class WorkspaceResearchClaimMatrixResult(StrictModel):
    root: str
    status: str
    claim_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    claims: list[ResearchClaim] = Field(default_factory=list)
    findings: list[ResearchClaimMatrixFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class BibliographyIntegrityFinding(StrictModel):
    code: str
    severity: str
    message: str
    path: str | None = None
    citation_key: str | None = None
    bibliography_id: str | None = None
    suggested_action: str | None = None


class WorkspaceBibliographyIntegrityResult(StrictModel):
    root: str
    status: str
    entry_count: int = 0
    review_count: int = 0
    citation_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    findings: list[BibliographyIntegrityFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class CitationSupportFinding(StrictModel):
    code: str
    severity: str
    message: str
    path: str | None = None
    citation_key: str | None = None
    bibliography_id: str | None = None
    support_id: str | None = None
    suggested_action: str | None = None


class WorkspaceCitationSupportResult(StrictModel):
    root: str
    status: str
    support_count: int = 0
    citation_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    findings: list[CitationSupportFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WorkspaceInitResult(StrictModel):
    root: str
    project_id: str
    profile_id: str
    created_paths: list[str] = Field(default_factory=list)
    skipped_existing: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WorkspaceDiscoveryItem(StrictModel):
    path: str
    path_type: str
    role: str
    size_bytes: int | None = None
    suffix: str | None = None
    confidence: str = "medium"
    risk_flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("path", "path_type", "role", "confidence")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class WorkspaceSetupProposal(StrictModel):
    proposal_id: str
    priority: str
    title: str
    rationale: str
    command: str | None = None
    operation_type: str = "review"
    destructive: bool = False
    creates_paths: list[str] = Field(default_factory=list)
    review_paths: list[str] = Field(default_factory=list)
    related_roles: list[str] = Field(default_factory=list)

    @field_validator("proposal_id", "priority", "title", "rationale", "operation_type")
    @classmethod
    def _proposal_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class WorkspaceDiscoveryResult(StrictModel):
    root: str
    status: str
    scanned_count: int = 0
    file_count: int = 0
    directory_count: int = 0
    standard_dir_count: int = 0
    missing_standard_dirs: list[str] = Field(default_factory=list)
    missing_starter_files: list[str] = Field(default_factory=list)
    loose_candidate_count: int = 0
    role_counts: dict[str, int] = Field(default_factory=dict)
    items: list[WorkspaceDiscoveryItem] = Field(default_factory=list)
    proposals: list[WorkspaceSetupProposal] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ArtifactAuthorityRecord(StrictModel):
    artifact_id: str
    path: str | None = None
    artifact_type: str
    authority_level: str
    status: str | None = None
    ref_id: str | None = None
    target_id: str | None = None
    approval_id: str | None = None
    source_hash: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_id", "artifact_type", "authority_level")
    @classmethod
    def _authority_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ArtifactAuthorityFinding(StrictModel):
    code: str
    severity: str
    message: str
    path: str | None = None
    artifact_id: str | None = None
    authority_level: str | None = None
    suggested_action: str | None = None

    @field_validator("code", "severity", "message")
    @classmethod
    def _finding_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class WorkspaceArtifactAuthorityResult(StrictModel):
    root: str
    status: str
    artifact_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    authority_level_counts: dict[str, int] = Field(default_factory=dict)
    records: list[ArtifactAuthorityRecord] = Field(default_factory=list)
    findings: list[ArtifactAuthorityFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class GoalsReviewFinding(StrictModel):
    code: str
    severity: str
    message: str
    objective_id: str | None = None
    deadline_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None

    @field_validator("code", "severity", "message")
    @classmethod
    def _goals_finding_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class WorkspaceGoalsReviewResult(StrictModel):
    root: str
    status: str
    project_id: str | None = None
    title: str | None = None
    objective_count: int = 0
    deadline_count: int = 0
    due_soon_count: int = 0
    overdue_count: int = 0
    at_risk_deadline_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    objectives: list[ProjectObjective] = Field(default_factory=list)
    deadlines: list[ProjectDeadline] = Field(default_factory=list)
    findings: list[GoalsReviewFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WeeklyReviewItem(StrictModel):
    item_id: str
    category: str
    title: str
    severity: str = "medium"
    status: str = "needs_review"
    message: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)
    due_date: date | None = None
    suggested_action: str | None = None

    @field_validator("item_id", "category", "title", "severity", "status")
    @classmethod
    def _weekly_review_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class WorkspaceWeeklyReviewResult(StrictModel):
    root: str
    review_date: date
    status: str
    evidence_count: int = 0
    report_count: int = 0
    approval_count: int = 0
    action_count: int = 0
    high_action_count: int = 0
    objective_count: int = 0
    deadline_count: int = 0
    due_soon_count: int = 0
    overdue_count: int = 0
    open_finding_count: int = 0
    high_finding_count: int = 0
    item_count: int = 0
    items: list[WeeklyReviewItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class DashboardCard(StrictModel):
    card_id: str
    title: str
    status: str
    value: str | int | float | None = None
    severity: str = "medium"
    detail: str | None = None
    artifact_paths: list[str] = Field(default_factory=list)

    @field_validator("card_id", "title", "status", "severity")
    @classmethod
    def _dashboard_card_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class WorkspaceDashboardResult(StrictModel):
    root: str
    generated_at: str
    status: str
    evidence_count: int = 0
    report_count: int = 0
    approval_count: int = 0
    finding_count: int = 0
    high_finding_count: int = 0
    action_count: int = 0
    high_action_count: int = 0
    objective_count: int = 0
    deadline_count: int = 0
    due_soon_count: int = 0
    overdue_count: int = 0
    budget_ledger_status: str | None = None
    artifact_authority_status: str | None = None
    reference_corpus_status: str | None = None
    research_claim_matrix_status: str | None = None
    trace_status: str | None = None
    checkpoint_count: int = 0
    card_count: int = 0
    cards: list[DashboardCard] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WorkflowStep(StrictModel):
    step_id: str
    title: str
    command: str
    operation_id: str
    output_paths: list[str] = Field(default_factory=list)
    status: str = "planned"
    safety_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("step_id", "title", "command", "operation_id", "status")
    @classmethod
    def _workflow_step_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class WorkspaceWorkflowPlan(StrictModel):
    root: str
    workflow: str
    status: str
    execute: bool = False
    step_count: int = 0
    steps: list[WorkflowStep] = Field(default_factory=list)
    generated_paths: list[str] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WorkspaceDoctorFinding(StrictModel):
    code: str
    severity: str
    message: str
    path: str | None = None
    suggested_action: str | None = None


class WorkspaceDoctorResult(StrictModel):
    root: str
    status: str
    evidence_count: int = 0
    approval_count: int = 0
    finding_count: int = 0
    findings: list[WorkspaceDoctorFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None


class AdminObligation(StrictModel):
    obligation_id: str
    title: str
    obligation_type: str
    profile_id: str = "national-rnd-basic"
    source_system: str = "local"
    due_date: date | None = None
    cadence: str | None = None
    required_evidence_types: list[str] = Field(default_factory=list)
    required_approval: bool = True
    linked_deadline_id: str | None = None
    status: str = "needs_review"
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("obligation_id", "title", "obligation_type", "profile_id", "source_system", "status")
    @classmethod
    def _admin_obligation_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class AdminSubmission(StrictModel):
    submission_id: str
    obligation_id: str
    title: str
    artifact_path: str | None = None
    target_system: str | None = None
    submitted_at: str | None = None
    approval_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    status: str = "needs_review"
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("submission_id", "obligation_id", "title", "status")
    @classmethod
    def _admin_submission_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class SettlementEvidenceRequirement(StrictModel):
    requirement_id: str
    ledger_id: str | None = None
    category: str | None = None
    proof_type_required: bool = True
    approval_required: bool = True
    evidence_required: bool = True
    status: str = "needs_review"
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("requirement_id", "status")
    @classmethod
    def _settlement_requirement_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class AdminObligationProfilePack(StrictModel):
    profile_id: str
    status: str = "needs_review"
    profile_status: str | None = None
    source_record_ids: list[str] = Field(default_factory=list)
    obligations: list[AdminObligation] = Field(default_factory=list)
    submissions: list[AdminSubmission] = Field(default_factory=list)
    settlement_requirements: list[SettlementEvidenceRequirement] = Field(default_factory=list)
    notes: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("profile_id", "status")
    @classmethod
    def _admin_obligation_profile_pack_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class AdminFinding(StrictModel):
    code: str
    severity: str
    message: str
    obligation_id: str | None = None
    submission_id: str | None = None
    ledger_id: str | None = None
    change_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None

    @field_validator("code", "severity", "message")
    @classmethod
    def _admin_finding_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class AdminObligationGraphResult(StrictModel):
    root: str
    status: str
    profile_id: str | None = None
    profile_status: str | None = None
    obligation_count: int = 0
    submission_count: int = 0
    settlement_requirement_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    obligations: list[AdminObligation] = Field(default_factory=list)
    submissions: list[AdminSubmission] = Field(default_factory=list)
    settlement_requirements: list[SettlementEvidenceRequirement] = Field(default_factory=list)
    findings: list[AdminFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class AdminObligationProfilePackReviewResult(StrictModel):
    root: str
    status: str
    profile_id: str
    profile_status: str | None = None
    pack_path: str | None = None
    source_record_count: int = 0
    verified_source_count: int = 0
    needs_review_source_count: int = 0
    obligation_count: int = 0
    submission_count: int = 0
    settlement_requirement_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    pack: AdminObligationProfilePack | None = None
    findings: list[AdminFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("root", "status", "profile_id")
    @classmethod
    def _admin_profile_pack_review_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class AdminCalendarResult(StrictModel):
    root: str
    status: str
    obligation_count: int = 0
    linked_deadline_count: int = 0
    due_soon_count: int = 0
    overdue_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    obligations: list[AdminObligation] = Field(default_factory=list)
    findings: list[AdminFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class AdminChangeRecord(StrictModel):
    change_id: str
    change_type: str
    target_id: str
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    requested_at: str | None = None
    decision: str = "needs_review"
    reviewer: str | None = None
    approved_at: str | None = None
    approval_id: str | None = None
    target_path: str | None = None
    target_hash: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    status: str = "needs_review"
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("change_id", "change_type", "target_id", "decision", "status")
    @classmethod
    def _admin_change_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class AdminChangeLedgerResult(StrictModel):
    root: str
    status: str
    change_count: int = 0
    approved_count: int = 0
    pending_count: int = 0
    rejected_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    changes: list[AdminChangeRecord] = Field(default_factory=list)
    findings: list[AdminFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WorkspaceActionItem(StrictModel):
    action_id: str
    priority: str
    title: str
    rationale: str
    command: str | None = None
    related_findings: list[str] = Field(default_factory=list)
    status: str = "pending"


class WorkspaceActionPlan(StrictModel):
    root: str
    status: str
    action_count: int = 0
    actions: list[WorkspaceActionItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None


class WorkspaceApprovalCoverageItem(StrictModel):
    path: str
    artifact_type: str
    target_type: str = "report"
    target_id: str
    target_id_candidates: list[str] = Field(default_factory=list)
    approved: bool = False
    decision: str = "missing"
    approval_id: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    expected_target_hash: str | None = None
    actual_target_hash: str | None = None
    expected_size_bytes: int | None = None
    actual_size_bytes: int | None = None
    hash_status: str = "not_checked"
    warnings: list[str] = Field(default_factory=list)


class WorkspaceApprovalCoverageResult(StrictModel):
    root: str
    status: str
    artifact_count: int = 0
    approved_count: int = 0
    missing_count: int = 0
    not_approved_count: int = 0
    hash_mismatch_count: int = 0
    hash_unverified_count: int = 0
    items: list[WorkspaceApprovalCoverageItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WorkspaceReportIntegrityItem(StrictModel):
    path: str
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    findings: list[CheckFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WorkspaceReportIntegrityResult(StrictModel):
    root: str
    status: str
    report_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    items: list[WorkspaceReportIntegrityItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WorkspaceSummaryResult(StrictModel):
    root: str
    status: str
    profile_id: str | None = None
    profile_status: str | None = None
    evidence_count: int = 0
    approval_count: int = 0
    finding_count: int = 0
    action_count: int = 0
    evidence_by_type: dict[str, int] = Field(default_factory=dict)
    evidence_by_status: dict[str, int] = Field(default_factory=dict)
    risk_flag_counts: dict[str, int] = Field(default_factory=dict)
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
    actions_by_priority: dict[str, int] = Field(default_factory=dict)
    report_paths: list[str] = Field(default_factory=list)
    export_paths: list[str] = Field(default_factory=list)
    analysis_manifest_paths: list[str] = Field(default_factory=list)
    budget_ledger_status: str | None = None
    budget_ledger_count: int = 0
    budget_ledger_finding_count: int = 0
    budget_total_by_currency: dict[str, float] = Field(default_factory=dict)
    discovery_status: str | None = None
    discovery_scanned_count: int = 0
    discovery_missing_standard_dir_count: int = 0
    discovery_loose_candidate_count: int = 0
    discovery_setup_proposal_count: int = 0
    artifact_authority_status: str | None = None
    artifact_authority_count: int = 0
    artifact_authority_finding_count: int = 0
    artifact_authority_high_count: int = 0
    artifact_authority_level_counts: dict[str, int] = Field(default_factory=dict)
    goals_review_status: str | None = None
    objective_count: int = 0
    deadline_count: int = 0
    goals_review_finding_count: int = 0
    goals_review_high_count: int = 0
    goals_due_soon_count: int = 0
    goals_overdue_count: int = 0
    goals_at_risk_deadline_count: int = 0
    weekly_review_status: str | None = None
    weekly_review_item_count: int = 0
    weekly_review_high_count: int = 0
    dashboard_status: str | None = None
    dashboard_card_count: int = 0
    reference_corpus_status: str | None = None
    reference_corpus_count: int = 0
    reference_rejection_count: int = 0
    reference_corpus_high_count: int = 0
    research_claim_matrix_status: str | None = None
    research_claim_count: int = 0
    research_claim_matrix_finding_count: int = 0
    profile_integrity_status: str | None = None
    profile_source_count: int = 0
    profile_verified_source_count: int = 0
    profile_integrity_finding_count: int = 0
    profile_source_queue_status: str | None = None
    profile_source_queue_item_count: int = 0
    profile_source_queue_high_count: int = 0
    profile_source_fix_plan_status: str | None = None
    profile_source_fix_plan_action_count: int = 0
    profile_source_fix_plan_manual_count: int = 0
    profile_source_fix_plan_official_check_count: int = 0
    profile_source_fix_plan_high_count: int = 0
    profile_source_fix_review_status: str | None = None
    profile_source_fix_review_record_count: int = 0
    profile_source_fix_review_unresolved_count: int = 0
    profile_source_fix_review_high_unresolved_count: int = 0
    profile_source_fix_review_stale_count: int = 0
    profile_review_status: str | None = None
    profile_review_can_promote: bool = False
    profile_review_failed_count: int = 0
    profile_promotion_status: str | None = None
    profile_promotion_record_count: int = 0
    latest_profile_promotion_decision: str | None = None
    profile_promotion_apply_status: str | None = None
    profile_promotion_apply_can_apply: bool = False
    profile_promotion_apply_change_count: int = 0
    profile_promotion_apply_result_status: str | None = None
    profile_promotion_applied: bool = False
    profile_promotion_apply_backup_path: str | None = None
    profile_promotion_revoke_status: str | None = None
    profile_promotion_revoke_can_revoke: bool = False
    profile_promotion_revoke_change_count: int = 0
    profile_promotion_revoke_result_status: str | None = None
    profile_promotion_revoked: bool = False
    profile_promotion_revoke_backup_path: str | None = None
    profile_lifecycle_status: str | None = None
    profile_lifecycle_entry_count: int = 0
    profile_lifecycle_finding_count: int = 0
    profile_lifecycle_high_count: int = 0
    profile_pack_readiness_status: str | None = None
    profile_pack_readiness_profile_count: int = 0
    profile_pack_readiness_blocked_count: int = 0
    profile_pack_readiness_finding_count: int = 0
    profile_pack_readiness_high_count: int = 0
    profile_pack_drilldown_status: str | None = None
    profile_pack_drilldown_item_count: int = 0
    profile_pack_drilldown_missing_artifact_count: int = 0
    profile_pack_drilldown_unmatched_count: int = 0
    profile_pack_investigation_status: str | None = None
    profile_pack_investigation_item_count: int = 0
    profile_pack_investigation_missing_human_review_count: int = 0
    profile_pack_investigation_official_source_check_count: int = 0
    profile_pack_package_status: str | None = None
    profile_pack_package_included_artifact_count: int = 0
    profile_pack_package_excluded_artifact_count: int = 0
    profile_pack_package_missing_artifact_count: int = 0
    profile_pack_package_receipt_status: str | None = None
    profile_pack_package_receipt_count: int = 0
    profile_pack_package_receipt_unresolved_count: int = 0
    profile_pack_package_receipt_stale_count: int = 0
    admin_profile_pack_status: str | None = None
    admin_profile_pack_obligation_count: int = 0
    admin_profile_pack_finding_count: int = 0
    admin_profile_pack_review_status: str | None = None
    admin_profile_pack_review_record_count: int = 0
    admin_profile_pack_review_unresolved_count: int = 0
    admin_profile_pack_review_stale_count: int = 0
    admin_obligation_status: str | None = None
    admin_obligation_count: int = 0
    admin_submission_count: int = 0
    admin_obligation_finding_count: int = 0
    settlement_binder_status: str | None = None
    settlement_binder_item_count: int = 0
    settlement_binder_finding_count: int = 0
    admin_change_ledger_status: str | None = None
    admin_change_count: int = 0
    admin_change_finding_count: int = 0
    admin_calendar_status: str | None = None
    admin_calendar_linked_deadline_count: int = 0
    admin_calendar_due_soon_count: int = 0
    admin_calendar_overdue_count: int = 0
    trace_status: str | None = None
    trace_node_count: int = 0
    trace_edge_count: int = 0
    trace_finding_count: int = 0
    trace_passport_status: str | None = None
    checkpoint_count: int = 0
    latest_checkpoint_id: str | None = None
    trace_passport_finding_count: int = 0
    top_actions: list[WorkspaceActionItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None


class ReviewPackArtifact(StrictModel):
    path: str
    artifact_type: str
    sha256: str
    byte_count: int


class ReviewPackVerificationItem(StrictModel):
    path: str
    artifact_type: str
    expected_sha256: str | None = None
    actual_sha256: str | None = None
    byte_count: int | None = None
    status: str


class EvidenceSourceVerificationItem(StrictModel):
    source_file: str
    resolved_path: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    expected_hashes: list[str] = Field(default_factory=list)
    actual_hash: str | None = None
    byte_count: int | None = None
    status: str
    warnings: list[str] = Field(default_factory=list)


class EvidenceSourceVerificationResult(StrictModel):
    evidence_index_path: str
    root: str | None = None
    inbox: str | None = None
    valid: bool
    source_count: int = 0
    ok_count: int = 0
    missing_count: int = 0
    mismatch_count: int = 0
    no_hash_count: int = 0
    conflict_count: int = 0
    items: list[EvidenceSourceVerificationItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WorkspaceTraceNode(StrictModel):
    node_id: str
    node_type: str
    label: str
    path: str | None = None
    ref_id: str | None = None
    status: str | None = None
    sha256: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceTraceEdge(StrictModel):
    source: str
    target: str
    relation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceTraceFinding(StrictModel):
    code: str
    severity: str
    message: str
    node_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None


class WorkspaceTraceResult(StrictModel):
    root: str
    status: str
    node_count: int = 0
    edge_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    nodes: list[WorkspaceTraceNode] = Field(default_factory=list)
    edges: list[WorkspaceTraceEdge] = Field(default_factory=list)
    findings: list[WorkspaceTraceFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class TracePassportEntry(StrictModel):
    checkpoint_id: str
    created_at: str
    stage: str
    summary: str
    artifact_paths: list[str] = Field(default_factory=list)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    unresolved_findings: list[str] = Field(default_factory=list)
    pending_human_decisions: list[str] = Field(default_factory=list)
    resume_hint: str | None = None
    status: TracePassportStatus = TracePassportStatus.NEEDS_REVIEW

    @field_validator("checkpoint_id", "created_at", "stage", "summary")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class TracePassportFinding(StrictModel):
    code: str
    severity: str
    message: str
    checkpoint_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None


class WorkspaceTracePassport(StrictModel):
    workspace_root: str
    project_id: str | None = None
    generated_at: str
    status: str
    entries: list[TracePassportEntry] = Field(default_factory=list)
    latest_checkpoint_id: str | None = None
    checkpoint_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    findings: list[TracePassportFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class CheckpointCreateResult(StrictModel):
    root: str
    checkpoint_id: str
    checkpoint_path: str
    passport_json_path: str
    stage: str
    artifact_count: int = 0
    status: str = "needs_review"
    warnings: list[str] = Field(default_factory=list)


class CheckpointResumeAction(StrictModel):
    priority: str
    title: str
    rationale: str
    command: str | None = None


class CheckpointResumePlan(StrictModel):
    root: str
    status: str
    checkpoint_id: str | None = None
    artifact_count: int = 0
    stale_count: int = 0
    missing_count: int = 0
    actions: list[CheckpointResumeAction] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class WorkspaceReviewPackResult(StrictModel):
    root: str
    status: str
    evidence_count: int = 0
    approval_count: int = 0
    finding_count: int = 0
    action_count: int = 0
    source_verification_valid: bool | None = None
    source_missing_count: int = 0
    source_mismatch_count: int = 0
    approval_coverage_status: str | None = None
    approval_missing_count: int = 0
    approval_not_approved_count: int = 0
    approval_hash_mismatch_count: int = 0
    approval_hash_unverified_count: int = 0
    report_integrity_status: str | None = None
    report_integrity_finding_count: int = 0
    report_integrity_high_count: int = 0
    discovery_status: str | None = None
    discovery_scanned_count: int = 0
    discovery_missing_standard_dir_count: int = 0
    discovery_loose_candidate_count: int = 0
    discovery_setup_proposal_count: int = 0
    artifact_authority_status: str | None = None
    artifact_authority_count: int = 0
    artifact_authority_finding_count: int = 0
    artifact_authority_high_count: int = 0
    goals_review_status: str | None = None
    objective_count: int = 0
    deadline_count: int = 0
    goals_review_finding_count: int = 0
    goals_review_high_count: int = 0
    goals_due_soon_count: int = 0
    goals_overdue_count: int = 0
    goals_at_risk_deadline_count: int = 0
    weekly_review_status: str | None = None
    weekly_review_item_count: int = 0
    weekly_review_high_count: int = 0
    dashboard_status: str | None = None
    dashboard_card_count: int = 0
    bibliography_integrity_status: str | None = None
    bibliography_entry_count: int = 0
    bibliography_review_count: int = 0
    bibliography_citation_count: int = 0
    bibliography_integrity_finding_count: int = 0
    bibliography_integrity_high_count: int = 0
    reference_corpus_status: str | None = None
    reference_corpus_count: int = 0
    reference_rejection_count: int = 0
    reference_corpus_high_count: int = 0
    citation_support_status: str | None = None
    citation_support_count: int = 0
    citation_support_citation_count: int = 0
    citation_support_finding_count: int = 0
    citation_support_high_count: int = 0
    research_claim_matrix_status: str | None = None
    research_claim_count: int = 0
    research_claim_matrix_finding_count: int = 0
    research_claim_matrix_high_count: int = 0
    budget_ledger_status: str | None = None
    budget_ledger_count: int = 0
    budget_ledger_finding_count: int = 0
    budget_ledger_high_count: int = 0
    profile_integrity_status: str | None = None
    profile_source_count: int = 0
    profile_verified_source_count: int = 0
    profile_integrity_finding_count: int = 0
    profile_integrity_high_count: int = 0
    profile_source_queue_status: str | None = None
    profile_source_queue_item_count: int = 0
    profile_source_queue_high_count: int = 0
    profile_source_fix_plan_status: str | None = None
    profile_source_fix_plan_action_count: int = 0
    profile_source_fix_plan_manual_count: int = 0
    profile_source_fix_plan_official_check_count: int = 0
    profile_source_fix_plan_high_count: int = 0
    profile_source_fix_review_status: str | None = None
    profile_source_fix_review_record_count: int = 0
    profile_source_fix_review_unresolved_count: int = 0
    profile_source_fix_review_high_unresolved_count: int = 0
    profile_source_fix_review_stale_count: int = 0
    profile_review_status: str | None = None
    profile_review_can_promote: bool = False
    profile_review_failed_count: int = 0
    profile_promotion_status: str | None = None
    profile_promotion_record_count: int = 0
    latest_profile_promotion_decision: str | None = None
    profile_promotion_apply_status: str | None = None
    profile_promotion_apply_can_apply: bool = False
    profile_promotion_apply_change_count: int = 0
    profile_promotion_apply_result_status: str | None = None
    profile_promotion_applied: bool = False
    profile_promotion_apply_backup_path: str | None = None
    profile_promotion_revoke_status: str | None = None
    profile_promotion_revoke_can_revoke: bool = False
    profile_promotion_revoke_change_count: int = 0
    profile_promotion_revoke_result_status: str | None = None
    profile_promotion_revoked: bool = False
    profile_promotion_revoke_backup_path: str | None = None
    profile_lifecycle_status: str | None = None
    profile_lifecycle_entry_count: int = 0
    profile_lifecycle_finding_count: int = 0
    profile_lifecycle_high_count: int = 0
    profile_pack_readiness_status: str | None = None
    profile_pack_readiness_profile_count: int = 0
    profile_pack_readiness_blocked_count: int = 0
    profile_pack_readiness_finding_count: int = 0
    profile_pack_readiness_high_count: int = 0
    profile_pack_drilldown_status: str | None = None
    profile_pack_drilldown_item_count: int = 0
    profile_pack_drilldown_missing_artifact_count: int = 0
    profile_pack_drilldown_unmatched_count: int = 0
    profile_pack_investigation_status: str | None = None
    profile_pack_investigation_item_count: int = 0
    profile_pack_investigation_missing_human_review_count: int = 0
    profile_pack_investigation_official_source_check_count: int = 0
    profile_pack_package_status: str | None = None
    profile_pack_package_included_artifact_count: int = 0
    profile_pack_package_excluded_artifact_count: int = 0
    profile_pack_package_missing_artifact_count: int = 0
    profile_pack_package_receipt_status: str | None = None
    profile_pack_package_receipt_count: int = 0
    profile_pack_package_receipt_unresolved_count: int = 0
    profile_pack_package_receipt_stale_count: int = 0
    admin_profile_pack_status: str | None = None
    admin_profile_pack_obligation_count: int = 0
    admin_profile_pack_finding_count: int = 0
    admin_profile_pack_review_status: str | None = None
    admin_profile_pack_review_record_count: int = 0
    admin_profile_pack_review_unresolved_count: int = 0
    admin_profile_pack_review_stale_count: int = 0
    admin_obligation_status: str | None = None
    admin_obligation_count: int = 0
    admin_submission_count: int = 0
    admin_obligation_finding_count: int = 0
    settlement_binder_status: str | None = None
    settlement_binder_item_count: int = 0
    settlement_binder_finding_count: int = 0
    admin_change_ledger_status: str | None = None
    admin_change_count: int = 0
    admin_change_finding_count: int = 0
    admin_calendar_status: str | None = None
    admin_calendar_linked_deadline_count: int = 0
    admin_calendar_due_soon_count: int = 0
    admin_calendar_overdue_count: int = 0
    workspace_trace_status: str | None = None
    workspace_trace_node_count: int = 0
    workspace_trace_edge_count: int = 0
    workspace_trace_finding_count: int = 0
    workspace_trace_high_count: int = 0
    trace_passport_status: str | None = None
    checkpoint_count: int = 0
    latest_checkpoint_id: str | None = None
    trace_passport_finding_count: int = 0
    trace_passport_high_count: int = 0
    generated_paths: list[str] = Field(default_factory=list)
    artifacts: list[ReviewPackArtifact] = Field(default_factory=list)
    index_path: str
    json_path: str


class WorkspaceReviewPackVerificationResult(StrictModel):
    manifest_path: str
    valid: bool
    checked_count: int = 0
    ok_count: int = 0
    missing_count: int = 0
    mismatch_count: int = 0
    unchecked_count: int = 0
    items: list[ReviewPackVerificationItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ApprovalRecord(StrictModel):
    approval_id: str
    target_type: ApprovalTargetType
    target_id: str
    target_path: str | None = None
    target_hash: str | None = None
    target_size_bytes: int | None = None
    decision: ApprovalDecision
    reviewer: str
    reviewed_at: str
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("approval_id", "target_id", "reviewer", "reviewed_at")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProjectProfile(StrictModel):
    profile_id: str
    agency: str | None = None
    program: str | None = None
    report_cycle: str | None = None
    required_outputs: list[str] = Field(default_factory=list)
    budget_categories: list[str] = Field(default_factory=list)
    field_map: dict[str, str] = Field(default_factory=dict)
    status: str = "needs_review"
    notes: str | None = None


class ProfileSource(StrictModel):
    source_id: str
    profile_id: str
    title: str
    source_url: str | None = None
    source_file: str | None = None
    retrieved_at: str | None = None
    source_hash: str | None = None
    source_size_bytes: int | None = None
    verified_by: str | None = None
    review_status: str = "needs_review"
    validity_notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("source_id", "profile_id", "title")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class VerifiedProfilePack(StrictModel):
    profile_id: str
    profile_path: str | None = None
    profile_status: str | None = None
    status: str
    source_count: int = 0
    verified_source_count: int = 0
    needs_review_source_count: int = 0
    rejected_source_count: int = 0
    missing_retrieved_at_count: int = 0
    missing_hash_count: int = 0
    latest_retrieved_at: str | None = None
    sources: list[ProfileSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None


class ProfileIntegrityFinding(StrictModel):
    code: str
    severity: str
    message: str
    source_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None


class ProfileIntegrityResult(StrictModel):
    root: str
    profile_id: str | None = None
    profile_status: str | None = None
    status: str
    source_count: int = 0
    verified_source_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    findings: list[ProfileIntegrityFinding] = Field(default_factory=list)
    profile_pack: VerifiedProfilePack | None = None
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProfileSourceQueueItem(StrictModel):
    queue_id: str
    scope: str
    profile_id: str
    profile_status: str | None = None
    profile_path: str | None = None
    source_id: str | None = None
    source_title: str | None = None
    source_status: str | None = None
    source_url: str | None = None
    source_file: str | None = None
    source_record_path: str | None = None
    issue_code: str
    severity: str
    message: str
    suggested_action: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("queue_id", "scope", "profile_id", "issue_code", "severity", "message")
    @classmethod
    def _profile_source_queue_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfileSourceQueueResult(StrictModel):
    root: str
    status: str
    templates_root: str | None = None
    profile_count: int = 0
    template_profile_count: int = 0
    workspace_profile_count: int = 0
    source_count: int = 0
    queue_item_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    items: list[ProfileSourceQueueItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProfileSourceFixPlanAction(StrictModel):
    action_id: str
    queue_id: str | None = None
    scope: str | None = None
    profile_id: str | None = None
    source_id: str | None = None
    issue_code: str
    severity: str
    action_type: str
    title: str
    rationale: str
    manual_step: str | None = None
    command: str | None = None
    followup_commands: list[str] = Field(default_factory=list)
    source_record_path: str | None = None
    source_file: str | None = None
    requires_human_review: bool = True
    requires_official_source_check: bool = False

    @field_validator("action_id", "issue_code", "severity", "action_type", "title", "rationale")
    @classmethod
    def _profile_source_fix_plan_action_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfileSourceFixPlanResult(StrictModel):
    root: str
    status: str
    queue_path: str
    queue_hash: str | None = None
    queue_status: str | None = None
    queue_item_count: int = 0
    profile_count: int = 0
    action_count: int = 0
    command_count: int = 0
    manual_count: int = 0
    human_review_count: int = 0
    official_source_check_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    actions: list[ProfileSourceFixPlanAction] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProfileSourceFixReviewRecord(StrictModel):
    review_id: str
    action_id: str
    decision: ProfileSourceFixReviewDecision
    reviewer: str
    reviewed_at: str
    fix_plan_path: str
    fix_plan_hash: str
    fix_plan_status: str | None = None
    action_issue_code: str | None = None
    action_severity: str | None = None
    profile_id: str | None = None
    source_id: str | None = None
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("review_id", "action_id", "decision", "reviewer", "reviewed_at", "fix_plan_path", "fix_plan_hash")
    @classmethod
    def _profile_source_fix_review_record_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfileSourceFixReviewFinding(StrictModel):
    code: str
    severity: str
    message: str
    action_id: str | None = None
    review_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None

    @field_validator("code", "severity", "message")
    @classmethod
    def _profile_source_fix_review_finding_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfileSourceFixReviewSummaryResult(StrictModel):
    root: str
    status: str
    fix_plan_path: str
    fix_plan_hash: str | None = None
    fix_plan_status: str | None = None
    action_count: int = 0
    record_count: int = 0
    resolved_count: int = 0
    accepted_risk_count: int = 0
    deferred_count: int = 0
    rejected_count: int = 0
    unresolved_count: int = 0
    high_unresolved_count: int = 0
    stale_record_count: int = 0
    missing_action_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    records: list[ProfileSourceFixReviewRecord] = Field(default_factory=list)
    findings: list[ProfileSourceFixReviewFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProfilePackReadinessProfile(StrictModel):
    profile_id: str
    status: str
    profile_status: str | None = None
    queue_item_count: int = 0
    fix_action_count: int = 0
    fix_review_record_count: int = 0
    fix_review_unresolved_count: int = 0
    profile_review_status: str | None = None
    profile_review_can_promote: bool = False
    promotion_status: str | None = None
    promotion_record_count: int = 0
    latest_promotion_decision: str | None = None
    apply_status: str | None = None
    apply_can_apply: bool = False
    apply_applied: bool = False
    revoke_status: str | None = None
    revoke_can_revoke: bool = False
    revoke_revoked: bool = False
    lifecycle_status: str | None = None
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("profile_id", "status")
    @classmethod
    def _profile_pack_readiness_profile_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackReadinessFinding(StrictModel):
    code: str
    severity: str
    message: str
    profile_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None

    @field_validator("code", "severity", "message")
    @classmethod
    def _profile_pack_readiness_finding_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackReadinessResult(StrictModel):
    root: str
    status: str
    profile_count: int = 0
    ready_count: int = 0
    needs_review_count: int = 0
    blocked_count: int = 0
    profile_without_findings_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    profiles: list[ProfilePackReadinessProfile] = Field(default_factory=list)
    findings: list[ProfilePackReadinessFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProfilePackReadinessDrilldownArtifact(StrictModel):
    artifact_type: str
    path: str
    exists: bool = False
    sha256: str | None = None
    status: str | None = None
    item_count: int = 0
    warning: str | None = None

    @field_validator("artifact_type", "path")
    @classmethod
    def _profile_pack_drilldown_artifact_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackReadinessDrilldownItem(StrictModel):
    drilldown_id: str
    finding_code: str
    severity: str
    profile_id: str | None = None
    finding_message: str
    finding_path: str | None = None
    finding_suggested_action: str | None = None
    source_artifact: str
    source_artifact_path: str | None = None
    source_artifact_hash: str | None = None
    source_index: int | None = None
    source_ref_id: str | None = None
    source_code: str | None = None
    source_status: str | None = None
    source_message: str | None = None
    source_path: str | None = None
    related_ids: list[str] = Field(default_factory=list)
    command: str | None = None
    match_status: str = "matched"

    @field_validator("drilldown_id", "finding_code", "severity", "finding_message", "source_artifact", "match_status")
    @classmethod
    def _profile_pack_drilldown_item_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackReadinessDrilldownResult(StrictModel):
    root: str
    status: str
    readiness_path: str
    readiness_hash: str | None = None
    readiness_status: str | None = None
    readiness_finding_count: int = 0
    drilldown_count: int = 0
    matched_count: int = 0
    unmatched_count: int = 0
    missing_artifact_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    artifacts: list[ProfilePackReadinessDrilldownArtifact] = Field(default_factory=list)
    items: list[ProfilePackReadinessDrilldownItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("root", "status", "readiness_path")
    @classmethod
    def _profile_pack_drilldown_result_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackInvestigationArtifact(StrictModel):
    artifact_type: str
    path: str
    exists: bool = False
    sha256: str | None = None
    status: str | None = None
    item_count: int = 0
    warning: str | None = None

    @field_validator("artifact_type", "path")
    @classmethod
    def _profile_pack_investigation_artifact_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackInvestigationItem(StrictModel):
    bundle_item_id: str
    profile_id: str | None = None
    finding_code: str
    severity: str
    readiness_message: str
    readiness_path: str | None = None
    readiness_suggested_action: str | None = None
    drilldown_id: str | None = None
    drilldown_match_status: str | None = None
    source_artifact: str | None = None
    source_artifact_path: str | None = None
    source_artifact_hash: str | None = None
    source_ref_id: str | None = None
    source_code: str | None = None
    source_status: str | None = None
    source_message: str | None = None
    source_path: str | None = None
    related_ids: list[str] = Field(default_factory=list)
    command: str | None = None
    human_review_status: str
    human_review_ref_id: str | None = None
    human_review_decision: str | None = None
    human_review_reviewer: str | None = None
    human_review_reviewed_at: str | None = None
    requires_human_review: bool = True
    requires_official_source_check: bool = False
    next_step: str | None = None

    @field_validator("bundle_item_id", "finding_code", "severity", "readiness_message", "human_review_status")
    @classmethod
    def _profile_pack_investigation_item_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackInvestigationBundleResult(StrictModel):
    root: str
    status: str
    bundle_id: str
    profile_id: str | None = None
    finding_code: str | None = None
    readiness_path: str
    readiness_hash: str | None = None
    readiness_status: str | None = None
    drilldown_path: str
    drilldown_hash: str | None = None
    drilldown_status: str | None = None
    readiness_finding_count: int = 0
    drilldown_item_count: int = 0
    bundle_item_count: int = 0
    matched_count: int = 0
    missing_artifact_count: int = 0
    unmatched_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    human_review_missing_count: int = 0
    human_review_supplied_count: int = 0
    official_source_check_count: int = 0
    artifacts: list[ProfilePackInvestigationArtifact] = Field(default_factory=list)
    items: list[ProfilePackInvestigationItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("root", "status", "bundle_id", "readiness_path", "drilldown_path")
    @classmethod
    def _profile_pack_investigation_result_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackInvestigationPackageArtifact(StrictModel):
    artifact_type: str
    role: str
    path: str
    exists: bool = False
    included: bool = False
    sha256: str | None = None
    byte_count: int | None = None
    warning: str | None = None

    @field_validator("artifact_type", "role", "path")
    @classmethod
    def _profile_pack_package_artifact_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackInvestigationPackageExclusion(StrictModel):
    path: str
    reason: str
    related_id: str | None = None

    @field_validator("path", "reason")
    @classmethod
    def _profile_pack_package_exclusion_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackInvestigationPackageResult(StrictModel):
    root: str
    status: str
    package_id: str
    profile_id: str | None = None
    finding_code: str | None = None
    selection_policy: str
    bundle_path: str
    bundle_hash: str | None = None
    bundle_status: str | None = None
    bundle_item_count: int = 0
    selected_item_count: int = 0
    schema_valid: bool = False
    schema_error_count: int = 0
    review_pack_manifest_path: str | None = None
    review_pack_manifest_hash: str | None = None
    artifact_count: int = 0
    included_artifact_count: int = 0
    missing_artifact_count: int = 0
    excluded_artifact_count: int = 0
    zip_path: str | None = None
    zip_hash: str | None = None
    artifacts: list[ProfilePackInvestigationPackageArtifact] = Field(default_factory=list)
    exclusions: list[ProfilePackInvestigationPackageExclusion] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("root", "status", "package_id", "selection_policy", "bundle_path")
    @classmethod
    def _profile_pack_package_result_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackPackageReceiptRecord(StrictModel):
    receipt_id: str
    package_id: str
    package_manifest_path: str
    package_manifest_hash: str
    decision: ProfilePackPackageReceiptDecision
    reviewer: str
    reviewed_at: str
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("receipt_id", "package_id", "package_manifest_path", "package_manifest_hash", "decision", "reviewer", "reviewed_at")
    @classmethod
    def _profile_pack_receipt_record_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackPackageReceiptFinding(StrictModel):
    code: str
    severity: str
    message: str
    receipt_id: str | None = None
    package_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None

    @field_validator("code", "severity", "message")
    @classmethod
    def _profile_pack_receipt_finding_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePackPackageReceiptSummaryResult(StrictModel):
    root: str
    status: str
    package_path: str
    package_hash: str | None = None
    package_id: str | None = None
    package_status: str | None = None
    record_count: int = 0
    received_count: int = 0
    accepted_for_review_count: int = 0
    needs_changes_count: int = 0
    rejected_count: int = 0
    unresolved_count: int = 0
    stale_record_count: int = 0
    missing_package_id_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    records: list[ProfilePackPackageReceiptRecord] = Field(default_factory=list)
    findings: list[ProfilePackPackageReceiptFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("root", "status", "package_path")
    @classmethod
    def _profile_pack_receipt_summary_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class AdminProfilePackReviewRecord(StrictModel):
    review_id: str
    profile_id: str
    target_type: AdminProfilePackReviewTargetType = AdminProfilePackReviewTargetType.PACK
    target_id: str | None = None
    profile_pack_path: str
    profile_pack_hash: str
    decision: AdminProfilePackReviewDecision
    reviewer: str
    reviewed_at: str
    source_record_ids: list[str] = Field(default_factory=list)
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("review_id", "profile_id", "target_type", "profile_pack_path", "profile_pack_hash", "decision", "reviewer", "reviewed_at")
    @classmethod
    def _admin_pack_review_record_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class AdminProfilePackReviewFinding(StrictModel):
    code: str
    severity: str
    message: str
    review_id: str | None = None
    profile_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None

    @field_validator("code", "severity", "message")
    @classmethod
    def _admin_pack_review_finding_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class AdminProfilePackReviewSummaryResult(StrictModel):
    root: str
    status: str
    profile_id: str
    profile_status: str | None = None
    profile_pack_path: str
    profile_pack_hash: str | None = None
    profile_pack_status: str | None = None
    target_count: int = 0
    reviewed_target_count: int = 0
    missing_target_review_count: int = 0
    record_count: int = 0
    accepted_count: int = 0
    accepted_risk_count: int = 0
    needs_changes_count: int = 0
    rejected_count: int = 0
    deferred_count: int = 0
    unresolved_count: int = 0
    stale_record_count: int = 0
    target_mismatch_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    records: list[AdminProfilePackReviewRecord] = Field(default_factory=list)
    findings: list[AdminProfilePackReviewFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("root", "status", "profile_id", "profile_pack_path")
    @classmethod
    def _admin_pack_review_summary_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfileReviewChecklistItem(StrictModel):
    check_id: str
    title: str
    status: str
    severity: str
    message: str
    source_id: str | None = None
    path: str | None = None
    suggested_action: str | None = None

    @field_validator("check_id", "title", "status", "severity", "message")
    @classmethod
    def _profile_review_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfileReviewResult(StrictModel):
    root: str
    profile_id: str | None = None
    profile_status: str | None = None
    status: str
    can_promote: bool = False
    checklist_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    warning_count: int = 0
    source_count: int = 0
    verified_source_count: int = 0
    checklist: list[ProfileReviewChecklistItem] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProfilePromotionRecord(StrictModel):
    promotion_id: str
    profile_id: str
    decision: str
    reviewer: str
    reviewed_at: str
    profile_review_path: str
    profile_review_hash: str
    profile_review_status: str
    profile_review_can_promote: bool
    notes: str | None = None
    risk_flags: list[str] = Field(default_factory=list)

    @field_validator("promotion_id", "profile_id", "decision", "reviewer", "reviewed_at", "profile_review_path", "profile_review_hash", "profile_review_status")
    @classmethod
    def _profile_promotion_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePromotionSummaryResult(StrictModel):
    root: str
    status: str
    profile_id: str | None = None
    record_count: int = 0
    verified_count: int = 0
    latest_promotion_id: str | None = None
    latest_decision: str | None = None
    latest_reviewer: str | None = None
    latest_reviewed_at: str | None = None
    current_profile_review_hash: str | None = None
    hash_mismatch_count: int = 0
    records: list[ProfilePromotionRecord] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProfilePromotionApplyChange(StrictModel):
    field: str
    before: Any = None
    after: Any = None
    rationale: str

    @field_validator("field", "rationale")
    @classmethod
    def _profile_apply_change_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePromotionApplyPlanResult(StrictModel):
    root: str
    status: str
    can_apply: bool = False
    profile_id: str | None = None
    profile_path: str | None = None
    current_profile_status: str | None = None
    proposed_profile_status: str | None = None
    profile_review_path: str | None = None
    profile_review_hash: str | None = None
    promotion_id: str | None = None
    promotion_decision: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    rollback_note: str | None = None
    change_count: int = 0
    changes: list[ProfilePromotionApplyChange] = Field(default_factory=list)
    proposed_profile: dict[str, Any] = Field(default_factory=dict)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProfilePromotionApplyResult(StrictModel):
    root: str
    status: str
    applied: bool = False
    profile_id: str | None = None
    profile_path: str | None = None
    backup_path: str | None = None
    apply_plan_path: str
    apply_plan_hash: str
    promotion_id: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    applied_at: str
    applied_fields: list[str] = Field(default_factory=list)
    before_profile: dict[str, Any] = Field(default_factory=dict)
    after_profile: dict[str, Any] = Field(default_factory=dict)
    rollback_note: str | None = None
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("root", "status", "apply_plan_path", "apply_plan_hash", "applied_at")
    @classmethod
    def _profile_apply_result_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePromotionRevocationChange(StrictModel):
    field: str
    current: Any = None
    restore_to: Any = None
    rationale: str

    @field_validator("field", "rationale")
    @classmethod
    def _profile_revoke_change_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePromotionRevocationPlanResult(StrictModel):
    root: str
    status: str
    can_revoke: bool = False
    profile_id: str | None = None
    profile_path: str | None = None
    apply_result_path: str | None = None
    apply_result_hash: str | None = None
    promotion_id: str | None = None
    reviewer: str
    reason: str
    requested_at: str
    current_profile_status: str | None = None
    restore_profile_status: str | None = None
    backup_path: str | None = None
    backup_hash: str | None = None
    backup_available: bool = False
    current_matches_applied_profile: bool = False
    change_count: int = 0
    changes: list[ProfilePromotionRevocationChange] = Field(default_factory=list)
    restored_profile: dict[str, Any] = Field(default_factory=dict)
    rollback_note: str | None = None
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("root", "status", "reviewer", "reason", "requested_at")
    @classmethod
    def _profile_revoke_plan_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfilePromotionRevocationResult(StrictModel):
    root: str
    status: str
    revoked: bool = False
    profile_id: str | None = None
    profile_path: str | None = None
    pre_revoke_backup_path: str | None = None
    restore_backup_path: str | None = None
    revoke_plan_path: str
    revoke_plan_hash: str
    apply_result_path: str | None = None
    apply_result_hash: str | None = None
    promotion_id: str | None = None
    reviewer: str | None = None
    reason: str | None = None
    requested_at: str | None = None
    revoked_at: str
    revoked_fields: list[str] = Field(default_factory=list)
    before_profile: dict[str, Any] = Field(default_factory=dict)
    after_profile: dict[str, Any] = Field(default_factory=dict)
    rollback_note: str | None = None
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("root", "status", "revoke_plan_path", "revoke_plan_hash", "revoked_at")
    @classmethod
    def _profile_revoke_result_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfileLifecycleLedgerEntry(StrictModel):
    entry_id: str
    entry_type: str
    status: str
    artifact_path: str | None = None
    artifact_hash: str | None = None
    occurred_at: str | None = None
    profile_id: str | None = None
    promotion_id: str | None = None
    reviewer: str | None = None
    decision: str | None = None
    backup_path: str | None = None
    related_paths: list[str] = Field(default_factory=list)
    notes: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("entry_id", "entry_type", "status")
    @classmethod
    def _profile_lifecycle_entry_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfileLifecycleLedgerFinding(StrictModel):
    code: str
    severity: str
    message: str
    path: str | None = None
    suggested_action: str | None = None

    @field_validator("code", "severity", "message")
    @classmethod
    def _profile_lifecycle_finding_field_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class ProfileLifecycleLedgerResult(StrictModel):
    root: str
    status: str
    profile_id: str | None = None
    current_profile_status: str | None = None
    entry_count: int = 0
    finding_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    entries: list[ProfileLifecycleLedgerEntry] = Field(default_factory=list)
    findings: list[ProfileLifecycleLedgerFinding] = Field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    warnings: list[str] = Field(default_factory=list)


class PaperRecord(StrictModel):
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    method: str | None = None
    dataset: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    key_claims: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    status: str = "needs_review"
    notes: str | None = None
