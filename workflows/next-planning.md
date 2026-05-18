# K-ResDev Next Planning

This planning note starts after `0.1.0b24`.

## Current Diagnosis

K-ResDev now has working local layers for evidence intake, document extraction, report integrity, approvals, bibliography metadata, bibliography review, citation support, profile source records, profile integrity, workspace traceability graph, workspace doctor, next actions, workspace summary, and review packs.

The next bottleneck is still operational continuity, but the first traceability and profile-source layers now exist. A real R&D workspace next needs a budget evidence ledger, compact checkpoints, explicit artifact authority levels, and eventually verified agency profile packs based on current official sources.

## Planning Principles

1. Keep evidence as source of truth.
2. Keep reports, review packs, agency profiles, and research narratives as projections.
3. Keep human review records separate from AI-generated checks.
4. Do not hardcode official agency rules without source verification.
5. Prefer cross-linking and impact analysis over more disconnected reports.
6. Borrow external academic workflow ideas only as K-ResDev-native concepts; do not vendor or copy external skill content without license review.

## External Ideas SPEC

`workflows/external-academic-workflow-ideas-spec.md` records implementation-ready ideas adapted from academic research workflow projects and the Claude Code for Academics presentation.

Most important takeaways:
- add a K-ResDev trace passport/checkpoint layer after the traceability graph;
- make artifact authority levels explicit across reports, evidence, approvals, bibliography, and claims;
- grow bibliography support into local corpus adapters for folder scans, Zotero exports, and Markdown notes;
- add read-only workspace discovery before setup or migration;
- add goals/deadline review and a local weekly dashboard for ongoing project operation.

## Priority Roadmap

### Beta 23 - Traceability Graph and Impact Review

Goal: create one deterministic workspace graph that links sources, evidence, KPIs, reports, approvals, bibliography entries, bibliography reviews, citation support records, analysis manifests, and generated artifacts.

Status: implemented as a local first pass in `src/k_resdev_skill/workspace_trace.py`, with CLI/API, doctor, next-action, summary, and review-pack integration.

Why now:
- The system already creates many useful artifacts.
- Users need to know which downstream reports or reviews are affected when a source, evidence item, bibliography file, or approval target changes.
- Current doctor checks are useful but still siloed.

Expected scope:
- `workspace-trace` public API and CLI.
- `state/workspace-trace.json` and `reports/workspace-trace.md`.
- Nodes for source files, evidence items, report artifacts, approvals, bibliography entries, bibliography reviews, citation support records, and generated review-pack artifacts.
- Edges such as `source_of`, `cites`, `approves`, `supports_claim`, `derived_from`, and `generated_artifact`.
- Impact findings for changed/missing source hashes, approval target drift, bibliography source drift, and unresolved citation support.
- Integration into `doctor`, `next-actions`, `workspace-summary`, and `workspace-review-pack`.

Safety boundary:
- The graph is a local traceability projection only.
- It must not certify official compliance, scientific truth, or approval validity.

Suggested tests:
- Graph includes evidence source and report citation nodes.
- Changed evidence source marks linked report and approval nodes impacted.
- Missing citation support marks cited report/manuscript path impacted.
- Review pack includes trace artifacts and manifest hashes.

### Beta 24 - Verified Profile Source Pack

Goal: add a pluggable profile-source registry that can distinguish generic needs-review profiles from profiles backed by cited official source documents.

Status: implemented as a generic local source-recording and integrity shell. No official agency rules or forms are hardcoded.

Implementation note:
- The generic shell is implemented.
- Adding a specific verified agency profile still requires checking current official sources first.
- Rules and forms are time-sensitive and should not be invented from memory.

Expected scope:
- `ProfileSource` and `VerifiedProfilePack` models.
- `state/profile-sources.json`.
- profile fields for `source_url`, `retrieved_at`, `source_hash`, `verified_by`, `review_status`, and `validity_notes`.
- CLI commands for `profile-source-record`, `profile-source-summary`, and `profile-integrity`.
- Keep official rules as data profiles, not hardcoded Python logic.
- Integration into workspace doctor, next actions, summary, review pack, and trace.

Safety boundary:
- Browse and cite official sources before adding any agency-specific profile pack.
- If a source cannot be verified, keep the profile status as `needs_review`.

### Beta 25 - Budget Evidence Ledger

Goal: move budget evidence from generic completeness checks into a reviewable ledger.

Expected scope:
- `BudgetLedgerItem` model for date, vendor, amount, currency, category, proof type, approval reference, evidence IDs, and review status.
- CSV/JSON import and Markdown ledger writer.
- duplicate invoice/vendor/date/amount warnings.
- amount rollups by category without agency-specific rule claims.
- doctor findings for missing proof type, missing approval reference, and ledger/evidence mismatch.

Safety boundary:
- Do not infer official eligibility.
- Treat budget categories as profile-driven labels until verified against official guidance.

### Beta 26 - Research Claim Matrix

Goal: connect paper claims, citation support decisions, experiment evidence, and insight candidates into a single reviewable research matrix.

Expected scope:
- `ResearchClaim` model.
- claim matrix writer for author claim, AI interpretation, supporting evidence, citation support, risk flags, and next checks.
- report/manuscript citation support coverage by claim, not only by citation key.
- optional export to literature-review matrix without changing raw bibliography files.

Safety boundary:
- Research claims stay `hypothesis`, `candidate`, or `needs_review` unless a human review record accepts them.

### Beta 27 - Trace Passport and Checkpoint Ledger

Goal: create compact, hash-backed resume checkpoints so a fresh session can understand the current workspace without loading every report, manifest, and evidence file.

Expected scope:
- `TracePassportEntry` and `WorkspaceTracePassport` models.
- `checkpoint-create`, `checkpoint-summary`, and `checkpoint-resume-plan` commands.
- `state/trace-passport.json`, `state/checkpoints/`, and `reports/trace-passport.md`.
- stale checkpoint findings when an artifact hash changes after checkpoint creation.
- optional inclusion in `workspace-review-pack`.

Safety boundary:
- Checkpoints are operational resume aids only. They must not copy raw restricted source bodies or certify compliance.

### Beta 28 - Reference Corpus Adapter Bridge

Goal: extend bibliography intake into local corpus adapters while keeping rejection logs explicit and non-fabricating.

Expected scope:
- folder scan adapter for local PDFs/notes;
- Zotero exported JSON adapter, not the Zotero Web API by default;
- Markdown note/frontmatter adapter;
- `state/literature-corpus.json`, `state/reference-rejection-log.json`, and `reports/reference-corpus-summary.md`.

Safety boundary:
- Corpus adapters import metadata and user notes only. They do not verify paper relevance or claim support.

### Beta 29 - Workspace Discovery, Goals, and Deadlines

Goal: help a new team understand a folder before initializing or migrating it, then maintain local objectives and deadlines linked to KPIs, milestones, evidence, and reports.

Expected scope:
- `workspace-discover` and `workspace-setup-plan` commands.
- `state/workspace-discovery.json` and `reports/workspace-discovery.md`.
- `state/project-goals.json`, `reports/goals-review.md`, and deadline readiness checks.

Safety boundary:
- Discovery is read-only by default. Goals review is an operating projection, not an official reporting schedule.

### Beta 30 - Local Weekly Review and Workflow Router

Goal: generate a local R&D weekly dashboard from workspace artifacts and add a thin router for common Admin, Research, and Integrity review workflows.

Expected scope:
- `weekly-review` and `workspace-dashboard` commands.
- local artifact-only inputs by default; no Gmail, WhatsApp, Google Docs, Slack, or Teams connector actions.
- `workflow admin-review`, `workflow research-review`, and `workflow integrity-review` commands that print the concrete commands they run.

Safety boundary:
- Weekly reviews and workflow router outputs are convenience projections. They do not create approvals or final official reports.

## Deferred Ideas

- Direct official HWP/HWPX form generation.
- IRIS/NTIS field submission automation.
- OCR for scanned PDFs.
- Web UI.
- LLM-assisted extraction.

These should wait until traceability, impact analysis, and verified profile source handling are stable.

## Recommended Next Slice

Implement Beta 25 next.

Beta 25 should add a generic budget evidence ledger without inferring official cost eligibility. Amount rollups, duplicate detection, and proof/approval gaps can be implemented locally while keeping budget categories profile-driven and needs-review until verified against official guidance.
