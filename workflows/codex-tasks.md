# Codex Task Handoff

## Goal

Implement `K-ResDev Skill` as a file-based evidence-first project with parsers, schemas, report templates, validation scripts, and safe research-assistant helpers.

## Project structure

```text
K-ResDev/
  SKILL.md
  README.md
  guides/
  schemas/
  templates/
  workflows/
  examples/
  src/k_resdev_skill/
  tests/
```

## Implemented tasks

### Task 1: Repository scaffold

Create the local Skill Pack layout and keep agency-specific templates pluggable.

### Task 2: Pydantic models

Implement:
- EvidenceItem
- ProjectState
- KPI
- Milestone
- ResearchInsight

### Task 3: Intake classifier

Implement a rule-based classifier using filename, extension, and extracted text hints.

Categories:
- plan
- progress
- experiment
- budget
- outcome
- change
- literature
- data
- unknown

### Task 4: CSV/XLSX data profiler

Implement:
- row/column count
- column names
- missingness summary
- numeric metric summary
- possible metric detection: dice, iou, auc, accuracy, f1, recall, precision, loss, latency

### Task 5: Evidence index writer

Generate:
- `state/evidence-index.md`
- `state/evidence-index.json`

### Task 6: Report claim checker

Given a report draft and evidence index, flag:
- unsupported numeric claims
- unsupported superlatives
- missing evidence IDs
- KPI mismatch
- below-target but overclaimed results

### Task 7: Literature matrix generator

Given paper metadata and notes, generate a literature matrix. Do not invent citations.

### Task 8: Tests

Add unit tests for:
- classifier
- model validation
- data profiler
- unsupported claim detector
- evidence index writer
- literature matrix writer

### Task 9: End-to-end P0 workflow

Implement:
- inbox scanner
- raw registry writer
- candidate evidence JSON writer
- open issues writer
- monthly report draft writer
- report claim-review sidecar
- audit-defense Q&A draft writer
- conservative plan text mapper

### Task 10: Correctness hardening

Implement:
- stable source/evidence IDs that do not depend on sorted file order
- duplicate-content file distinction using inbox-relative path
- derived output exclusion during intake reruns
- enum value rendering in Markdown outputs
- numeric mismatch checks for evidence-linked claims

### Task 11: Korean document intake foundation

Implement:
- TXT/MD/CSV/JSON/LOG text extraction
- DOCX XML text extraction
- XLSX row text extraction with sheet/row provenance
- HWPX zip/XML text extraction
- PDF text extraction via `pypdf`
- optional binary HWP extraction through `rhwp dump` when available
- document-level evidence candidates with quote/provenance fields
- project profile template/schema for verified agency profiles later

### Task 12: Research assistant P1 helpers

Implement:
- paper card extraction from supplied metadata text
- data insight candidate report generation
- experiment comparison table generation
- reproducibility checklist generation
- `national-rnd-basic` agency template skeletons marked `needs_review`

### Task 13: Planning and registry beta workflows

Implement:
- hypothesis-to-experiment plan generation from `ResearchInsight` JSON
- generic budget evidence completeness checklist
- agency profile registry and profile validator for `templates/agencies/`
- CLI commands for `plan-experiment`, `budget-check`, `profiles`, and `validate-profile`

Keep all outputs as drafts/projections. Do not encode unverified agency rules as authoritative requirements.

### Task 14: Validation and approval beta workflows

Implement:
- JSON schema validation CLI for bundled and custom schemas
- approval record creation for supplied human decisions
- approval summaries and target approval gate checks
- evidence bundle index generation with unresolved/risk review hints

Approval records are logs of human decisions, not decisions made by the tool. Bundle indexes must never copy, modify, or certify raw source files.

### Task 15: Reproducible analysis beta workflow

Implement:
- deterministic CSV/XLSX analysis run command
- profile JSON, insight candidate Markdown, replay script, and manifest outputs
- source hash and safety metadata proving the raw file was not modified

Analysis outputs remain draft candidates. Human review and statistical validation are still required before research or report claims are accepted.

### Task 16: Projection export beta workflow

Implement:
- Markdown projection export to DOCX, HTML, TXT, and HWPX-compatible HTML intermediate
- automatic draft/human-approval notice in exported documents
- source hash and export metadata for traceability

Exports are review artifacts. They are not final official submissions or verified agency forms.

### Task 17: Workspace init and readiness doctor

Implement:
- standard workspace initializer for `inbox/`, `state/`, `evidence/`, `reports/`, `reports/analysis/`, and `state/approvals/`
- starter `project-state.json`, `project-profile.json`, and `README.k-resdev.md` without overwriting existing files
- readiness doctor for evidence index, profile status, approvals, reports, exports, analysis manifests, and budget metadata gaps

Doctor output is a readiness projection only and must not certify official IRIS/NTIS or agency compliance.

### Task 18: Workspace next-action planner

Implement:
- doctor finding to action-plan conversion
- Markdown and JSON action-plan outputs
- CLI command for `next-actions`
- deterministic IDs and priority ordering for reviewable next steps

Action plans are operational suggestions only. Generated commands must be reviewed before execution and do not replace human approval or official agency checks.

### Task 19: Workspace summary report

Implement:
- one-page workspace summary across doctor status, next actions, evidence counts, approvals, reports, exports, and analysis manifests
- Markdown and JSON outputs
- CLI command for `workspace-summary`
- public API model/result for handoff-friendly status reporting

Workspace summaries are local operational projections. They do not certify official submission readiness, agency compliance, or scientific validity.

### Task 20: Workspace review pack

Implement:
- one-command generation for readiness, next actions, workspace summary, and review-pack index artifacts
- Markdown and JSON pack index outputs
- CLI command for `workspace-review-pack`
- report-draft detection hardening so operational Markdown files do not satisfy the missing report draft check

Review packs are local operational bundles only. They must not be treated as official submissions, agency compliance evidence, or human approval.

### Task 21: Review-pack manifest verification

Implement:
- generated artifact manifest entries with path, artifact type, SHA-256, and byte count
- review-pack verifier for missing or changed generated artifacts
- CLI command for `verify-review-pack`
- tests for valid packs and tampered generated artifacts

Verification only checks generated artifact integrity. It does not validate raw source truth, official agency compliance, human approval, or scientific validity.

### Task 22: Evidence source hash verification

Implement:
- evidence-index source grouping by `source_file`
- local path resolution using absolute path, workspace root, and inbox hints
- SHA-256 comparison against `source_hash`
- CLI command for `verify-evidence-sources`
- Markdown and JSON verification outputs

Evidence source verification checks local file presence and hash equality only. It does not prove official validity, scientific correctness, or human approval.

### Task 23: Source integrity in doctor and review pack

Implement:
- workspace doctor findings for missing hashed sources, source hash mismatches, conflicting hashes, and unverifiable hashes
- next-action routing for source-integrity findings
- source-verification Markdown/JSON artifacts inside `workspace-review-pack`
- review-pack manifest hashing for generated source-verification artifacts

Doctor/review-pack integration is still local operational readiness only. It does not certify official compliance, scientific validity, or human approval.

### Task 24: Report approval coverage in workspace operations

Implement:
- approval-coverage report for Markdown report drafts and projection exports
- target matching by report target ID candidates and supplied `target_path`
- workspace doctor findings for missing or not-approved report artifacts
- next-action routing for approval-coverage findings
- approval-coverage Markdown/JSON artifacts inside `workspace-review-pack`

Approval coverage checks supplied human decision records only. It must not infer approval, certify official submission readiness, or treat a generated review pack as approval.

### Task 25: Report integrity in workspace operations

Implement:
- report-integrity report for Markdown report drafts
- reuse unsupported-claim checks across workspace report drafts
- workspace doctor findings for unchecked, high-severity, and review-level report claim issues
- next-action routing for report-integrity findings
- report-integrity Markdown/JSON artifacts inside `workspace-review-pack`

Report integrity is a local consistency projection only. It must not certify official compliance, scientific validity, or human approval.

### Task 26: Evidence review status in report integrity

Implement:
- report-integrity findings when report drafts cite evidence that is not `accepted`
- medium-severity findings for `draft` and `needs_review` evidence citations
- high-severity findings for `rejected` and `superseded` evidence citations

A known evidence ID is necessary but not sufficient for report readiness. The evidence review state must remain visible before approval or external review.

### Task 27: Approval target hash binding

Implement:
- optional `target_hash` and `target_size_bytes` fields on approval records
- automatic target hash capture when `approval-record --target-path` points to an existing file
- approval-coverage detection for approved artifacts changed after approval
- doctor and next-action routing for approval target hash mismatch/unverified approvals

Approval target hashes only detect local artifact drift after approval. They do not create, infer, or certify human approval.

### Task 28: Bibliography management intake

Implement:
- BibTeX/RIS/CSL JSON bibliography import command
- `state/bibliography-index.md` and `state/bibliography-index.json` outputs
- conversion from bibliography entries to literature matrix paper records
- schema/template coverage for bibliography entry metadata
- workspace starter support for a `references/` folder

Bibliography intake must never fabricate citation metadata. Missing title, author, year, venue, DOI, or URL fields remain `needs_review` risk flags until a human verifies the source publication.

### Task 29: Bibliography integrity in workspace operations

Implement:
- bibliography-integrity report for Markdown citation keys and bibliography index metadata
- source hash drift checks for imported bibliography files
- duplicate citation key and duplicate DOI detection
- workspace doctor findings for missing citation keys, source drift, and review-level bibliography warnings
- next-action routing and review-pack artifacts for bibliography integrity

Bibliography integrity is a local metadata consistency check only. It must not certify citation correctness, paper relevance, or whether cited papers support the manuscript/report claim.

### Task 30: Bibliography review records

Implement:
- `bib-review-record` for supplied human bibliography metadata decisions
- `bib-review-summary` and `bib-review-status` commands
- JSON schema and template coverage for bibliography review records
- workspace skeleton support for `state/bibliography-reviews/`
- bibliography integrity status resolution from latest review records

Bibliography review records are human decision metadata only. They must not be inferred from import, and an accepted bibliography review still does not prove that the cited paper supports a report or manuscript claim.

### Task 31: Citation support records

Implemented:
- `citation-support-record` for supplied human paper-claim support decisions
- `citation-support-summary`, `citation-support-status`, and `citation-support-integrity` commands
- JSON schema and template coverage for citation support records
- workspace skeleton support for `state/citation-support/`
- workspace doctor, next-action, and review-pack integration for citation-support findings

Citation support records are human decision metadata only. They must not be inferred from bibliography import or accepted bibliography review records. A support record checks the local claim-support review state; it does not independently prove scientific truth.

### Task 32: Workspace traceability graph

Implemented:
- `workspace-trace` command and public API
- `state/workspace-trace.json` and `reports/workspace-trace.md`
- deterministic graph nodes for source files, evidence items, report artifacts, approvals, bibliography entries, bibliography reviews, citation support records, analysis manifests, and generated review-pack artifacts
- graph edges such as `source_of`, `cites`, `approves`, `supports_claim`, `derived_from`, and `generated_artifact`
- impact findings when a source hash changes, an approval target drifts, bibliography metadata changes, or citation support is unresolved
- integration into doctor, next actions, workspace summary, and workspace review pack

The traceability graph is a local operational projection. It must not certify official compliance, scientific validity, source truth, or approval validity.

### Task 33: Verified profile source pack

Implemented:
- `ProfileSource` and `VerifiedProfilePack` models
- `state/profile-sources.json`
- commands for recording and summarizing profile source verification
- profile fields for source URL, retrieval date, source hash, reviewer, and review status
- profile-integrity checks that keep unverified profiles in `needs_review`
- workspace doctor, next-action, summary, review-pack, and trace integration for profile source integrity

This task implements the generic source-recording and integrity shell only. It does not hardcode IRIS, NTIS, ministry, or agency rules from memory; any agency-specific verified profile still requires current official source review.

### Task 34: Budget evidence ledger

Implemented:
- `BudgetLedgerItem` model
- CSV/JSON ledger import and Markdown ledger writer
- duplicate vendor/date/amount and missing proof warnings
- amount rollups by profile-driven category labels
- doctor and next-action integration for ledger/evidence mismatch
- review-pack, workspace-summary, trace, schema, and template integration

Budget ledgers are review aids only. They must not infer official cost eligibility or agency compliance.

### Task 35: Research claim matrix

Implemented:
- `ResearchClaim` model
- JSON/CSV research claim import into `state/research-claims.json`
- claim summary and matrix writers connecting supplied claims, experiment evidence, citation support, risk flags, and next checks
- report/manuscript citation-support coverage by claim rather than citation key alone
- schema, template, CLI, workspace doctor, next-action, summary, review-pack, and trace integration

Research claims stay `hypothesis`, `candidate`, or `needs_review` unless a supplied human review record accepts them.

### Task 36: External academic workflow ideas SPEC

Implemented as planning documentation:
- `workflows/external-academic-workflow-ideas-spec.md`
- concept adaptation map for ARS, ARS-Codex, Claude Code for Academics, and claudeblattman ideas
- explicit license boundary: borrow concepts only unless license review permits reuse
- future implementation sequence for trace passport, authority levels, corpus adapters, workspace discovery, goals review, weekly dashboard, and router UX

This SPEC is planning input only. It must not be treated as implemented runtime behavior.

### Task 37: Trace passport and checkpoint ledger

Implemented:
- `TracePassportEntry`, `WorkspaceTracePassport`, `CheckpointCreateResult`, and `CheckpointResumePlan` models
- `checkpoint-create`, `checkpoint-summary`, and `checkpoint-resume-plan` commands
- `state/checkpoints/`, `state/trace-passport.json`, `reports/trace-passport.md`, and optional checkpoint resume-plan artifacts
- hash-backed artifact capture without copying raw artifact bodies
- stale/missing artifact detection when checkpoint artifacts change or disappear
- workspace doctor, next-action, summary, review-pack, schema, template, and trace integration

Trace passports are resume aids only. They must not copy raw restricted source bodies or certify compliance, approval, or scientific truth.

### Task 38: Reference corpus adapter bridge

Implemented:
- local folder scan adapter for PDFs, BibTeX/RIS/CSL JSON files, and Markdown/TXT notes
- Zotero exported JSON adapter without Web API access
- Markdown note/frontmatter adapter for user-supplied metadata and short user notes
- `state/literature-corpus.json`, `state/reference-rejection-log.json`, and `reports/reference-corpus-summary.md`
- deterministic rejection-log entries for duplicate references, invalid citation keys, unsupported files, unreadable files, and copyright-risk text fields that are omitted
- workspace doctor, next-action, summary, review-pack, schema, template, and trace integration

Adapters must never fabricate citation metadata, paper relevance, or claim support.

### Task 39: Workspace discovery and setup planning

Implemented:
- read-only `discover-workspace` command
- additive setup proposals before initialization or migration
- `WorkspaceDiscoveryItem`, `WorkspaceSetupProposal`, and `WorkspaceDiscoveryResult` models
- `state/workspace-discovery.json` and `reports/workspace-discovery.md`
- loose source candidate detection outside standard K-ResDev folders
- workspace doctor, next-action, summary, review-pack, schema, and template integration

Discovery is read-only by default. It must not move, rename, delete, or modify raw files.

### Task 40: Artifact authority levels

Implemented:
- `ArtifactAuthorityRecord`, `ArtifactAuthorityFinding`, and `WorkspaceArtifactAuthorityResult` models
- `artifact-authority` command
- `state/artifact-authority.json` and `reports/artifact-authority.md`
- default authority labels for raw sources, extracted candidates, evidence states, draft/reviewed/approved projections, operating summaries, rejected, and superseded artifacts
- high-severity warnings for final/submission-named projections without current approval and projections citing rejected or superseded evidence
- workspace doctor, next-action, summary, review-pack, schema, template, and trace metadata integration

Authority levels are workflow metadata only. They do not create approvals or certify official compliance, legal status, or scientific truth.

### Task 41: Goals and deadlines review

Planned:
- `ProjectObjective` and `ProjectDeadline` models
- `state/project-goals.json`, `reports/goals-review.md`, and deadline readiness checks
- KPI/milestone/evidence/report linkage without official agency schedule claims

Goals review is an operating projection only.

### Task 42: Local weekly review and workspace dashboard

Planned:
- local artifact-only weekly review generator
- `reports/weekly-review-YYYY-MM-DD.md`, `state/weekly-review-YYYY-MM-DD.json`, and `reports/workspace-dashboard.md`
- sections for KPI movement, evidence added, open review findings, budget gaps, research insight candidates, deadlines, and human decisions needed
- no default connector access to Gmail, WhatsApp, Google Docs, Slack, Teams, or cloud drives

Weekly reviews are team operating summaries, not final official reports.

### Task 43: Thin workflow router

Planned:
- `workflow admin-review`, `workflow research-review`, `workflow integrity-review`, and `workflow weekly`
- router prints concrete commands and artifact paths before running
- router uses only stable local deterministic commands by default
- hidden connector/network actions are out of scope

Router UX is convenience only. The underlying CLI commands and public APIs remain the source of testable behavior.

## Safety constraints

- Never alter raw files.
- Never create final official report without explicit approval.
- Never fabricate metrics or citations.
- Mark uncertain extracted items as `needs_review`.
- Keep agency-specific official templates pluggable; do not hardcode unverified rules.
