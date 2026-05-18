# K-ResDev Next Planning

This planning note starts after `0.1.0b38`.

## Current Diagnosis

K-ResDev now has working local layers for evidence intake, document extraction, report integrity, approvals, budget ledger review, bibliography metadata, reference corpus adapters, read-only workspace discovery, bibliography review, citation support, research claim matrices, profile source records, profile integrity, a narrow source-backed IRIS/Innopolis profile seed, profile promotion review, hash-bound profile promotion records, non-destructive profile promotion apply plans, guarded profile promotion apply results/backups, workspace traceability graph, trace passport checkpoints, artifact authority labels, goals/deadline review, weekly operating reviews, workspace dashboards, thin local workflow router, workspace doctor, next actions, workspace summary, and review packs.

The next bottleneck is source/profile lifecycle rollback and revocation. K-ResDev can now promote a profile only through a hash-guarded apply plan with backup and result records, but it does not yet have a first-class command to revoke a profile promotion and restore or supersede the verified state.

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
- keep artifact authority levels visible across reports, evidence, approvals, bibliography, and claims;
- grow bibliography support into local corpus adapters for folder scans, Zotero exports, and Markdown notes;
- add read-only workspace discovery before setup or migration;
- use goals/deadline review and add a local weekly dashboard for ongoing project operation.

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

Status: implemented as a generic CSV/JSON ledger import and integrity layer. It does not infer official cost eligibility.

Expected scope:
- `BudgetLedgerItem` model for date, vendor, amount, currency, category, proof type, approval reference, evidence IDs, and review status.
- CSV/JSON import and Markdown ledger writer.
- duplicate invoice/vendor/date/amount warnings.
- amount rollups by category without agency-specific rule claims.
- doctor findings for missing proof type, missing approval reference, and ledger/evidence mismatch.
- Integration into workspace doctor, next actions, summary, review pack, and trace.

Safety boundary:
- Do not infer official eligibility.
- Treat budget categories as profile-driven labels until verified against official guidance.

### Beta 26 - Research Claim Matrix

Goal: connect paper claims, citation support decisions, experiment evidence, and insight candidates into a single reviewable research matrix.

Status: implemented as a local first pass in `src/k_resdev_skill/research_claims.py`, with CLI/API, schema/template, doctor, next-action, summary, review-pack, and trace integration.

Expected scope:
- `ResearchClaim` model.
- claim matrix writer for author claim, AI interpretation, supporting evidence, citation support, risk flags, and next checks.
- report/manuscript citation support coverage by claim, not only by citation key.
- optional export to literature-review matrix without changing raw bibliography files.

Safety boundary:
- Research claims stay `hypothesis`, `candidate`, or `needs_review` unless a human review record accepts them.

### Beta 27 - Trace Passport and Checkpoint Ledger

Goal: create compact, hash-backed resume checkpoints so a fresh session can understand the current workspace without loading every report, manifest, and evidence file.

Status: implemented as a local first pass in `src/k_resdev_skill/trace_passport.py`, with CLI/API, doctor, next-action, summary, review-pack, schema, template, and trace integration.

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

Status: implemented as a local first pass in `src/k_resdev_skill/reference_corpus.py`, with CLI/API, schema/template, doctor, next-action, summary, review-pack, and trace integration.

Expected scope:
- folder scan adapter for local PDFs/notes;
- Zotero exported JSON adapter, not the Zotero Web API by default;
- Markdown note/frontmatter adapter;
- `state/literature-corpus.json`, `state/reference-rejection-log.json`, and `reports/reference-corpus-summary.md`.

Safety boundary:
- Corpus adapters import metadata and user notes only. They do not verify paper relevance or claim support.

### Beta 29 - Workspace Discovery and Setup Planning

Goal: help a new team understand a folder before initializing or migrating it.

Status: implemented as a read-only first pass in `src/k_resdev_skill/workspace_discovery.py`, with CLI/API, schema/template, doctor, next-action, summary, and review-pack integration.

Expected scope:
- `discover-workspace` command.
- `state/workspace-discovery.json` and `reports/workspace-discovery.md`.
- additive setup proposals before initialization or migration.
- loose source candidate detection outside standard K-ResDev folders.

Safety boundary:
- Discovery is read-only by default. It must not move, rename, delete, or modify raw files.

### Beta 30 - Artifact Authority Levels

Goal: make authority boundaries visible across raw sources, extracted candidates, reviewed evidence, draft projections, approved projections, and operating summaries.

Status: implemented as a local first pass in `src/k_resdev_skill/artifact_authority.py`, with CLI/API, doctor, next-action, summary, review-pack, schema, template, and trace metadata integration.

Expected scope:
- `artifact_authority_level` metadata for generated artifacts and trace nodes.
- authority summary in workspace summary and review pack.
- doctor warnings when draft projections are treated as approved artifacts.
- no automatic approval promotion.

Safety boundary:
- Authority levels are labels and checks only. They do not create approvals or certify truth.

### Beta 31 - Goals and Deadline Review

Goal: maintain local objectives/deadlines linked to KPIs, milestones, evidence, reports, and approvals.

Status: implemented as a local first pass in `src/k_resdev_skill/project_goals.py`, with `goals-init`, `goals-review`, `deadline-check`, schema/template, doctor, next-action, summary, review-pack, and trace integration.

Expected scope:
- `ProjectObjective` and `ProjectDeadline` models.
- `state/project-goals.json`, `reports/goals-review.md`, and deadline readiness checks.

Safety boundary:
- Goals review is a team operating summary, not a final official report or official schedule claim.

### Beta 32 - Local Weekly Review and Workspace Dashboard

Goal: generate a local R&D weekly review/dashboard from K-ResDev artifacts.

Status: implemented as a local first pass in `src/k_resdev_skill/weekly_review.py`, with `weekly-review`, `workspace-dashboard`, schema/template, doctor, next-action, summary, review-pack, and trace integration.

Expected scope:
- `weekly-review` and `workspace-dashboard` commands.
- local artifact-only inputs by default; no Gmail, WhatsApp, Google Docs, Slack, or Teams connector actions.
- sections for KPI movement, evidence added, goals/deadlines, open review findings, budget gaps, research insight candidates, and human decisions needed.

Safety boundary:
- Weekly reviews are team operating summaries, not final official reports or official schedule claims.

### Beta 33 - Thin Workflow Router

Goal: add a thin router for common Admin, Research, and Integrity review workflows.

Status: implemented as a local first pass in `src/k_resdev_skill/workflow_router.py`, with `workflow admin-review`, `workflow research-review`, `workflow integrity-review`, and `workflow weekly`, plus schema/template, operational Markdown filtering, and trace integration.

Expected scope:
- `workflow admin-review`, `workflow research-review`, and `workflow integrity-review` commands that print the concrete commands they run.

Safety boundary:
- Weekly reviews and workflow router outputs are convenience projections. They do not create approvals or final official reports.

### Beta 34 - Verified Agency Profile Pack Intake

Goal: create the first official-source-backed profile pack without hardcoding unverified agency rules.

Status: implemented as a narrow `iris-innopolis-2026-017795` source-backed profile seed. The pack records official IRIS URL metadata, a local hash-backed source note, retrieved date, and risk flags, and `init-workspace` can install those source records into a workspace without overwriting existing files. The profile remains `needs_review`.

Expected scope:
- select a narrow profile candidate only after checking current official sources;
- record source URL/file, retrieved date, hash, reviewer, and review status;
- add a pluggable profile data file under `templates/agencies/`;
- keep generated fields `needs_review` until supplied human verification;
- add profile-integrity tests around source records and drift.

Safety boundary:
- Official forms and rules are time-sensitive. Browse/cite current official sources before adding any specific profile pack.

### Beta 35 - Verified Profile Review Workflow

Goal: add a review workflow that can explain what is still missing before a source-backed profile may be promoted.

Status: implemented as a local first pass in `src/k_resdev_skill/profile_review.py`, with CLI/API, schema/template, doctor, next-action, workspace-summary, review-pack, operational Markdown filtering, and trace integration.

Expected scope:
- `profile-review` command over `state/project-profile.json` and `state/profile-sources.json`;
- promotion checklist for source freshness, hash match, reviewer identity, applicability notes, and unresolved risk flags;
- JSON/Markdown output under `state/profile-review.json` and `reports/profile-review.md`;
- no automatic promotion unless a supplied human review record is present;
- integration into doctor, next actions, summary, review pack, and trace.

Safety boundary:
- Promotion checks are guardrails only. They do not certify legal compliance or official submission readiness.

### Beta 36 - Profile Promotion Record Workflow

Goal: record supplied human profile promotion decisions without making AI-generated profile checks authoritative.

Status: implemented as a data-only record and summary workflow in `src/k_resdev_skill/profile_promotion.py`, with CLI/API, schema/template, workspace doctor, next-action, summary, review-pack, and trace integration. The latest current record is checked against the current `state/profile-review.json` hash; historical stale records remain visible as mismatch counts without blocking a newer matching verified record.

Expected scope:
- `profile-promotion-record` command for supplied human decisions;
- require a passing `state/profile-review.json` hash before accepting a promotion record;
- record reviewer, reviewed_at, target profile ID, source review hash, decision, and notes;
- integrate promotion records into doctor, next actions, summary, review pack, and trace.

Safety boundary:
- The tool records supplied decisions only. It must not infer official verification, mutate profile status by default, or certify agency compliance.

### Beta 37 - Profile Promotion Apply Proposal

Goal: make a verified profile-promotion record operationally usable without silent profile mutation.

Status: implemented as a proposal-only workflow in `src/k_resdev_skill/profile_promotion_apply.py`, with CLI/API, schema/template, doctor, next-action, workspace-summary, review-pack, operational Markdown filtering, and trace integration.

Expected scope:
- `profile-promotion-apply-plan` command that reads `state/project-profile.json`, `state/profile-review.json`, and `state/profile-promotions/`;
- generate `reports/profile-promotion-apply-plan.md` and `state/profile-promotion-apply-plan.json`;
- show the exact proposed field changes, especially `status: needs_review -> verified`, reviewer metadata, source review hash, and rollback note;
- block the plan unless the latest promotion record is `verified` and hash-matches the current profile-review artifact;

Safety boundary:
- Apply plans are proposed diffs only. They must not rewrite profile files or certify official agency compliance.

### Beta 38 - Guarded Profile Promotion Apply Command

Goal: optionally apply a human-reviewed profile-promotion plan with a backup and hash guard.

Status: implemented in `src/k_resdev_skill/profile_promotion_apply.py` with `profile-promotion-apply`, `ProfilePromotionApplyResult`, schema/template coverage, doctor, next-action, workspace-summary, review-pack, operational Markdown filtering, and trace integration.

Expected scope:
- `profile-promotion-apply` command that requires `--apply-plan state/profile-promotion-apply-plan.json` and `--apply-plan-hash <sha256>`;
- refuse to run unless the apply plan status is `ready_to_apply`, `can_apply=true`, and the hash matches the supplied apply-plan artifact;
- write a timestamped backup under `state/profile-backups/` before changing `state/project-profile.json`;
- apply only the field changes listed in the plan, initially limited to existing `ProjectProfile` schema fields;
- write `state/profile-promotion-apply-result.json` and `reports/profile-promotion-apply-result.md`;
- integrate apply results into doctor, next actions, summary, review pack, and trace.

Safety boundary:
- The apply command must be explicit and hash-guarded. It must never infer official agency compliance or change raw source files.

### Beta 39 - Profile Promotion Revocation and Rollback Plan

Goal: make profile promotion revocation reviewable before a verified profile is restored or superseded.

Expected scope:
- `profile-promotion-revoke-plan` command that reads `state/profile-promotion-apply-result.json`, `state/profile-backups/`, and current `state/project-profile.json`;
- generate `reports/profile-promotion-revoke-plan.md` and `state/profile-promotion-revoke-plan.json`;
- require a supplied revocation reason and reviewer;
- show whether rollback can restore the backup cleanly or whether current profile drift requires manual review;
- optionally add a later guarded `profile-promotion-revoke` command, but beta.39 should stay proposal-first unless the rollback rules are trivial and fully tested;
- integrate revocation plans into doctor, next actions, summary, review pack, and trace.

Safety boundary:
- Revocation plans are local profile-lifecycle controls only. They must not certify official agency status or erase the promotion/audit trail.

## Deferred Ideas

- Direct official HWP/HWPX form generation.
- IRIS/NTIS field submission automation.
- OCR for scanned PDFs.
- Web UI.
- LLM-assisted extraction.

These should wait until traceability, impact analysis, and verified profile source handling are stable.

## Recommended Next Slice

Implement Beta 39 next.

Beta 39 should make profile promotion revocation and rollback reviewable before any verified profile state is restored or superseded.
