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
    research_claim_matrix_status: str | None = None
    research_claim_count: int = 0
    research_claim_matrix_finding_count: int = 0
    profile_integrity_status: str | None = None
    profile_source_count: int = 0
    profile_verified_source_count: int = 0
    profile_integrity_finding_count: int = 0
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
    bibliography_integrity_status: str | None = None
    bibliography_entry_count: int = 0
    bibliography_review_count: int = 0
    bibliography_citation_count: int = 0
    bibliography_integrity_finding_count: int = 0
    bibliography_integrity_high_count: int = 0
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
