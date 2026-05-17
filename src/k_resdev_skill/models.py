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


class WorkspaceReviewPackResult(StrictModel):
    root: str
    status: str
    evidence_count: int = 0
    approval_count: int = 0
    finding_count: int = 0
    action_count: int = 0
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
