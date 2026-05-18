# External Academic Workflow Ideas SPEC

Status: planning spec for later implementation.

This document records ideas worth adapting into K-ResDev from external academic AI workflow repositories and the Claude Code for Academics presentation. It is not a vendoring plan. K-ResDev should borrow concepts, not copy code or long text, unless license review and attribution are handled separately.

## Source Inventory

| Source | Useful slice | License boundary |
|---|---|---|
| `Imbad0202/academic-research-skills` | Material Passport, reset boundaries, claim verification, corpus adapters, staged integrity gates | CC BY-NC 4.0 observed in repository license; do not copy into commercial-facing K-ResDev assets without explicit license review |
| `Imbad0202/academic-research-skills-codex` | Single Codex router skill, workflow aliases, Codex runtime mapping, staged pipeline checkpoints, Zotero/folder/Obsidian corpus adapter pattern | CC BY-NC 4.0 observed in README/license; adapt architecture only |
| `aspi6246/Claude-Code-Presentation` `Presentations/main.pdf` | Start-small adoption tiers, project memory files, session logs, orient-plan-execute-verify loop, safety and data-boundary reminders, quality gates | Presentation license not verified; treat as cited inspiration only |
| `chrisblattman/claudeblattman` | Non-developer setup flow, project discovery before changes, goals/OKR file, weekly review dashboard, living research design and progress hub | MIT observed in repository README; still prefer concept adaptation over direct copying |

## K-ResDev Fit

K-ResDev is not an autonomous paper-writing engine. It is a Korean national R&D evidence operating layer with research-assistant helpers.

External ideas should be translated into this shape:

```text
raw project sources
-> extracted candidates
-> reviewed evidence and bibliography records
-> traceable reports, dashboards, claims, and review packs
-> human-approved projections
```

The imported design principle is:

```text
The AI may coordinate and draft.
The evidence graph and human review records decide what can be trusted.
Official submission and scientific acceptance remain human authority.
```

## Non-Goals

1. Do not vendor ARS or claudeblattman content into K-ResDev.
2. Do not register hidden slash-command behavior that bypasses the CLI/API.
3. Do not auto-spawn subagents unless the user explicitly asks for parallel agent work.
4. Do not add official IRIS, NTIS, ministry, or agency rules without current official source verification.
5. Do not directly update Google Docs, email, WhatsApp, Zotero Web API, or cloud drives in the default MVP.
6. Do not read or copy raw restricted data into generated public docs.
7. Do not treat accepted bibliography metadata as proof that a paper supports a claim.

## Concept A: Workspace Trace Passport

Inspired by Material Passport and reset-boundary patterns.

K-ResDev adaptation:
- Build a local `TracePassport` that summarizes what a fresh session needs to resume work without loading every artifact.
- Store checkpoint entries at important workflow boundaries such as intake complete, monthly report draft created, approval coverage reviewed, bibliography reviewed, citation support reviewed, and review pack generated.
- Use hashes and artifact references, not copied artifact bodies.

Proposed artifacts:
- `state/trace-passport.json`
- `state/checkpoints/<checkpoint-id>.json`
- `reports/trace-passport.md`

Proposed models:

```python
class TracePassportEntry(StrictModel):
    checkpoint_id: str
    created_at: datetime
    stage: str
    summary: str
    artifact_paths: list[str]
    artifact_hashes: dict[str, str]
    unresolved_findings: list[str] = []
    pending_human_decisions: list[str] = []
    resume_hint: str | None = None
    status: Literal["draft", "needs_review", "accepted", "superseded"] = "needs_review"


class WorkspaceTracePassport(StrictModel):
    workspace_root: str
    project_id: str | None = None
    generated_at: datetime
    entries: list[TracePassportEntry]
    latest_checkpoint_id: str | None = None
```

Proposed CLI:
- `checkpoint-create --root . --stage monthly-report --summary "..."`
- `checkpoint-summary --root . --output reports/trace-passport.md --json state/trace-passport.json`
- `checkpoint-resume-plan --root . --checkpoint-id <id>`

Acceptance tests:
- A checkpoint records only path/hash/summary metadata and does not copy raw source bodies.
- A changed artifact hash marks the checkpoint as stale.
- A superseded checkpoint remains visible but is not the default resume point.
- `workspace-review-pack` can include the latest trace passport summary.

Safety rule:
- A trace passport is an operational resume aid. It does not certify official compliance, source truth, or scientific correctness.

## Concept B: Artifact Authority Levels

Inspired by ARS `data_access_level` and K-ResDev's existing `needs_review` discipline.

K-ResDev adaptation:
- Add an explicit authority ladder so tools can reason about whether an artifact is raw input, AI extraction, reviewed evidence, or approved projection.

Proposed authority levels:

```text
raw_source
extracted_candidate
evidence_needs_review
accepted_evidence
draft_projection
reviewed_projection
approved_projection
superseded
rejected
```

Proposed implementation:
- Add `authority_level` as optional metadata to generated artifacts and trace graph nodes.
- Derive default authority from existing status fields where possible.
- Doctor warnings should fire when high-authority outputs cite low-authority inputs without a human review record.

Acceptance tests:
- A report citing `evidence_needs_review` remains review-blocked.
- An export with no approval record never becomes `approved_projection`.
- A rejected evidence item cited by a report creates a high-severity finding.

Safety rule:
- Authority levels are local workflow metadata. They are not legal, institutional, or scientific certification.

## Concept C: Claim Registry And Claim Verification Matrix

Inspired by ARS claim verification and claim-reference alignment gates.

K-ResDev adaptation:
- Promote report/manuscript claims to first-class review objects.
- Keep paper claims, R&D performance claims, KPI claims, and AI insight claims separate but linkable.

Proposed artifacts:
- `state/claim-registry.json`
- `reports/claim-matrix.md`
- `state/claim-verification.json`

Proposed model:

```python
class ResearchClaimRecord(StrictModel):
    claim_id: str
    claim_type: Literal["rnd_performance", "kpi", "budget", "paper", "insight", "method", "dataset"]
    claim_text: str
    artifact_path: str | None = None
    locator: str | None = None
    evidence_ids: list[str] = []
    bibliography_ids: list[str] = []
    citation_support_ids: list[str] = []
    analysis_manifest_ids: list[str] = []
    authority_level: str = "extracted_candidate"
    verdict: Literal["unsupported", "partially_supported", "supported", "contradicted", "needs_review"] = "needs_review"
    risk_flags: list[str] = []
    next_checks: list[str] = []
```

Proposed CLI:
- `claim-extract --root . --path reports/monthly-report.md`
- `claim-matrix --root . --output reports/claim-matrix.md --json state/claim-verification.json`
- `claim-status --root . --claim-id <id>`

Acceptance tests:
- Numeric claims without evidence IDs are unsupported.
- Claims with citation keys but no citation-support record remain `needs_review`.
- Accepted bibliography review alone does not mark a claim as supported.
- Below-target KPI language remains flagged when wording overclaims achievement.

Safety rule:
- A supported local claim means the local evidence/support records are consistent. It does not prove scientific truth.

## Concept D: Reference Corpus Adapter Bridge

Inspired by ARS folder, Zotero, and Obsidian adapter contracts.

K-ResDev adaptation:
- Extend existing bibliography intake with a corpus adapter bridge that imports local reference collections into reviewable bibliography entries and rejection logs.
- Keep all adapters local-first and file-based.

Proposed artifacts:
- `state/literature-corpus.json`
- `state/reference-rejection-log.json`
- `reports/reference-corpus-summary.md`

Proposed adapters:
- `reference-folder-scan`: scan a local folder of PDFs or notes and infer minimal metadata from filenames.
- `zotero-json-import`: read exported Better BibTeX or CSL JSON files, not the Zotero Web API.
- `markdown-note-import`: read Markdown notes with optional frontmatter fields such as `citation_key`, `title`, `authors`, `year`, `doi`, `url`, and `tags`.

Rejection reasons:
- `missing_title`
- `missing_author`
- `missing_year`
- `missing_source_pointer`
- `duplicate_citation_key`
- `invalid_field_format`
- `unsupported_file_type`
- `copyright_risk_text_field`

Acceptance tests:
- Missing required citation metadata writes a rejection entry instead of inventing metadata.
- Duplicate citation keys are made visible, not silently overwritten.
- Adapter outputs are deterministic and sorted.
- Imported notes with long abstracts or copied article text are flagged for copyright review before public sharing.

Safety rule:
- Corpus adapters import metadata and user notes only. They do not verify paper relevance or claim support.

## Concept E: Workspace Discovery Before Setup

Inspired by claudeblattman's project-management setup flow.

K-ResDev adaptation:
- Add a discovery-only command before workspace initialization or migration.
- Report current folders, likely raw sources, existing reports, references, approvals, analysis files, and missing K-ResDev operating folders.
- Never move, delete, or reorganize files during discovery.

Proposed artifacts:
- `reports/workspace-discovery.md`
- `state/workspace-discovery.json`
- `reports/workspace-setup-proposal.md`

Proposed CLI:
- `workspace-discover --root .`
- `workspace-setup-plan --root . --profile national-rnd-basic`
- `init-workspace --from-plan state/workspace-setup-plan.json`

Acceptance tests:
- Discovery never creates or modifies project files unless output paths are explicitly supplied.
- Existing files are reported as existing, not overwritten.
- Setup proposal marks all agency-profile assumptions as `needs_review`.

Safety rule:
- Discovery is read-only by default. Initialization remains additive and non-destructive.

## Concept F: Goals, KPI, And Deadline Operating File

Inspired by claudeblattman's goals/OKR template, adapted to Korean R&D KPI and milestone tracking.

K-ResDev adaptation:
- Add a local operating file that bridges quarterly research objectives, R&D KPIs, report deadlines, and evidence readiness.

Proposed artifact:
- `state/project-goals.json`
- optional starter projection `templates/project-goals.json`
- `reports/goals-review.md`

Proposed model:

```python
class ProjectObjective(StrictModel):
    objective_id: str
    title: str
    weight: float | None = None
    status: Literal["active", "paused", "dormant", "completed"] = "active"
    linked_kpis: list[str] = []
    linked_milestones: list[str] = []
    linked_evidence_ids: list[str] = []
    review_status: Literal["draft", "needs_review", "accepted"] = "needs_review"


class ProjectDeadline(StrictModel):
    deadline_id: str
    due_date: date
    title: str
    deliverable_type: str
    linked_objective_ids: list[str] = []
    linked_report_paths: list[str] = []
    status: Literal["planned", "at_risk", "submitted", "approved", "missed"] = "planned"
```

Proposed CLI:
- `goals-init --root .`
- `goals-review --root . --output reports/goals-review.md --json state/goals-review.json`
- `deadline-check --root .`

Acceptance tests:
- Objective weights are optional but, when present, are checked for reasonable sum.
- Deadlines with missing report drafts or missing approvals are marked `at_risk`.
- KPI links are checked against `state/project-state.json`.

Safety rule:
- Goals review is an operating projection. It does not replace official reporting schedules.

## Concept G: Local Weekly Review And Living Dashboard

Inspired by claudeblattman's weekly review and living dashboard pattern.

K-ResDev adaptation:
- Generate a local weekly R&D dashboard from existing workspace artifacts, supplied meeting notes, progress logs, evidence index, approvals, citations, and analysis manifests.
- Defer direct Gmail, WhatsApp, Google Docs, Slack, and Teams integrations until connector policy is explicit.

Proposed artifacts:
- `reports/weekly-review-YYYY-MM-DD.md`
- `state/weekly-review-YYYY-MM-DD.json`
- `reports/workspace-dashboard.md`

Inputs:
- `inbox/` files classified as progress, meeting notes, change, experiment, outcome, budget, literature, and data.
- `state/evidence-index.json`
- `state/project-goals.json`
- `state/approvals/`
- `state/bibliography-index.json`
- `state/citation-support/`
- `reports/analysis/*.manifest.json`

Output sections:
- Project status summary.
- KPI and milestone movement.
- Evidence added this period.
- Open review findings.
- Budget evidence gaps.
- Research insight candidates.
- Upcoming deadlines.
- Human decisions needed.

Acceptance tests:
- Weekly review cites only local evidence IDs, artifact paths, and hashes.
- Missing connectors are not treated as failures.
- Sensitive or raw source bodies are not copied into the dashboard by default.
- `needs_review` items remain visibly unresolved.

Safety rule:
- Weekly reviews are team operating summaries, not final official reports.

## Concept H: Tiered Adoption And Guardrails

Inspired by the Claude Code for Academics start-small tiers and safety slides.

K-ResDev adaptation:
- Keep the product path staged so a research team can get value before adopting advanced automation.

Tier 1:
- Workspace initialization.
- README and project profile.
- Evidence intake.
- Session/checkpoint logs.
- Readiness doctor.

Tier 2:
- Report integrity.
- Approval coverage.
- Bibliography and citation support.
- Goals review.
- Weekly dashboard.

Tier 3:
- Traceability graph.
- Claim matrix.
- Budget ledger.
- Verified profile source pack.
- Optional delegated review agents only when explicitly requested.

Guardrails:
- Raw files are never altered.
- Official reports are never final without explicit approval.
- Restricted data should be referenced by path/hash, not copied into prompts or public docs.
- Dangerous file operations are outside K-ResDev default workflows.
- Quality gates should be visible and boring: pass, warn, block, needs_review.

## Concept I: Single Router UX Without Hidden Magic

Inspired by ARS-Codex single-suite routing, but constrained to K-ResDev's CLI/API style.

K-ResDev adaptation:
- Add a thin command router later, but keep concrete commands callable and testable.

Possible commands:
- `k-resdev workflow admin-review --root .`
- `k-resdev workflow research-review --root .`
- `k-resdev workflow integrity-review --root .`
- `k-resdev workflow weekly --root .`

Router behavior:
- Print which concrete commands it will run.
- Run only local deterministic commands.
- Never hide official profile assumptions.
- Never turn a warning into an approval.

Acceptance tests:
- Router command emits an execution plan before running.
- Router output includes the exact artifact paths refreshed.
- Router does not run connector or network actions by default.

Safety rule:
- Router UX is convenience only. The underlying public APIs and CLI commands remain the source of testable behavior.

## Implementation Order

Recommended order after the traceability graph, research-claim matrix, and trace-passport first passes:

1. Implement corpus adapter bridge for folder, Zotero JSON export, and Markdown notes.
2. Add `artifact_authority_level` to trace nodes and generated artifact metadata.
3. Implement workspace discovery and setup proposal.
4. Implement goals/deadline operating file and goals review.
5. Implement local weekly review and dashboard.
6. Add thin workflow router only after the concrete commands are stable.

## Open Questions

1. Should `project-goals.json` be a new file, or should it extend `project-state.json`?
2. Should `workspace-review-pack` stay checkpoint-neutral, or should a separate opt-in flag create a checkpoint?
3. Should artifact authority levels be represented as trace-node metadata only, or also as a standalone schema for generated artifacts?
4. Should Zotero import support only exported files, or later add an optional Web API connector?
5. Should weekly review stay Markdown-only, or should DOCX/HTML export be added after the projection exporter?

## Traceability To Planned Tasks

| Concept | Existing or planned K-ResDev task |
|---|---|
| Trace graph and impact review | Task 32 |
| Verified profile sources | Task 33 |
| Budget ledger | Task 34 |
| Research claim matrix | Task 35 |
| Trace passport and checkpoints | Task 37 |
| Corpus adapter bridge | New Task 38 |
| Workspace discovery and setup proposal | New Task 39 |
| Goals/deadline operating file | New Task 39 |
| Local weekly review and dashboard | New Task 40 |
| Single router UX | New Task 41 |
