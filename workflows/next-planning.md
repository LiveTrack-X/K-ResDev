# K-ResDev Next Planning

This planning note starts after `0.1.0b55`.

## Current Diagnosis

K-ResDev now has working local layers for evidence intake, document extraction, report integrity, approvals, budget ledger review, settlement binders, admin obligation graphs, admin profile-pack seed review, admin profile-pack human review receipts, admin change ledgers, admin calendars, bibliography metadata, reference corpus adapters, read-only workspace discovery, bibliography review, citation support, research claim matrices, profile source records, profile source-pack review queues, profile source fix plans, profile source fix review records, profile integrity, a narrow source-backed IRIS/Innopolis profile seed, profile promotion review, hash-bound profile promotion records, non-destructive profile promotion apply plans, guarded profile promotion apply results/backups, non-destructive profile promotion revocation plans, guarded profile promotion revocation results/backups, a profile lifecycle ledger, profile pack readiness dashboard, profile pack readiness drilldown, profile pack investigation bundle, profile pack investigation package manifest/ZIP, profile pack package reviewer receipts, workspace traceability graph, trace passport checkpoints, artifact authority labels, goals/deadline review, weekly operating reviews, workspace dashboards, thin local workflow router, workspace doctor, next actions, workspace summary, and review packs.

The next bottleneck is verified agency profile expansion. Beta 49-55 closed the generated package handoff loop, added a generic Korean R&D admin operating layer, made admin obligation seeds profile-data driven, and added row-level human review receipts for those admin seeds. Official IRIS/NTIS/RCMS/Ezbaro details still must remain source-backed profile data, not hardcoded Python logic.

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

### Beta 54 - Verified Admin Profile Pack Package

Goal: turn the generic Admin Operating Layer into verified, pluggable agency/program profile data after current official-source review.

Status: implemented as a guarded first pass.

Expected scope:
- collect source records for selected IRIS/NTIS/GAIA/RCMS/Ezbaro profile candidates;
- keep all profile rows `needs_review` until a supplied human source-review record accepts them;
- encode field maps, submission candidate labels, settlement proof hints, and calendar templates as profile data under `templates/agencies/`, not Python rules;
- extend `admin-obligations-init` so verified profile data can seed local obligations while generic `national-rnd-basic` remains conservative;
- add review-pack and trace checks that distinguish generic admin candidates from source-backed profile candidates.

Implemented scope:
- added `AdminObligationProfilePack` and `AdminObligationProfilePackReviewResult`;
- added `admin-profile-pack-review`;
- added profile-pack seed loading to `admin-obligations-init`;
- added `templates/agencies/national-rnd-basic/admin-obligations.json`;
- added a narrow `templates/agencies/iris-innopolis-2026-017795/admin-obligations.json`;
- integrated admin profile-pack findings into doctor, next-actions, summary, review-pack, and trace.

### Beta 55 - Admin Profile Pack Source Review Records

Goal: add supplied human review receipts specifically for admin obligation profile-pack rows before any pack can be promoted beyond `needs_review`.

Status: implemented as a guarded first pass.

Expected scope:
- hash-bind reviewer records to `templates/agencies/<profile-id>/admin-obligations.json`;
- record row-level decisions for obligations, submission candidates, settlement requirements, and calendar hints;
- block non-review admin obligation seeding when pack/source/reviewer hashes drift;
- keep promotion separate from loading so `admin-obligations-init` remains non-destructive and conservative.

Implemented scope:
- added `AdminProfilePackReviewRecord`, `AdminProfilePackReviewFinding`, and `AdminProfilePackReviewSummaryResult`;
- added `admin-profile-pack-review-record` and `admin-profile-pack-review-summary`;
- hash-bound review records to current `admin-obligations.json` pack files;
- supported pack-level and row-level targets for obligations, submissions, and settlement requirements;
- added stale-hash, missing target, rejected, needs_changes, deferred, accepted_risk, and missing-review findings;
- integrated admin profile-pack human review summaries into doctor, next-actions, summary, review-pack, and trace.

### Beta 56 - Admin Profile Pack Promotion Gate

Goal: prevent profile-driven admin obligation seeds from becoming trusted unless profile source records, admin profile-pack review records, and promotion decisions all agree on current hashes.

Status: proposed next slice.

Expected scope:
- add a promotion readiness gate that joins profile-review, profile-promotion, profile-pack review, and admin profile-pack review summaries;
- require current-hash accepted/accepted-risk row coverage before non-review admin obligation seeding can be considered;
- keep `admin-obligations-init` conservative by default and add an explicit reviewed-seed mode only when all gates pass;
- surface mismatches in doctor, trace, and review-pack without mutating official templates.

Safety boundary:
- Do not hardcode official rules from memory or stale manuals.
- Treat every official-system mapping as a profile candidate until current source metadata, retrieval date, hash, and reviewer decision are recorded.

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

Status: implemented in `src/k_resdev_skill/profile_promotion_revoke.py` with `profile-promotion-revoke-plan`, `ProfilePromotionRevocationPlanResult`, schema/template coverage, doctor, next-action, workspace-summary, review-pack, operational Markdown filtering, and trace integration.

Expected scope:
- `profile-promotion-revoke-plan` command that reads `state/profile-promotion-apply-result.json`, `state/profile-backups/`, and current `state/project-profile.json`;
- generate `reports/profile-promotion-revoke-plan.md` and `state/profile-promotion-revoke-plan.json`;
- require a supplied revocation reason and reviewer;
- show whether rollback can restore the backup cleanly or whether current profile drift requires manual review;
- optionally add a later guarded `profile-promotion-revoke` command, but beta.39 should stay proposal-first unless the rollback rules are trivial and fully tested;
- integrate revocation plans into doctor, next actions, summary, review pack, and trace.

Safety boundary:
- Revocation plans are local profile-lifecycle controls only. They must not certify official agency status or erase the promotion/audit trail.

### Beta 40 - Guarded Profile Promotion Revoke Command

Goal: optionally execute a reviewed revocation plan with a hash guard and an additional backup of the currently verified profile.

Status: implemented in `src/k_resdev_skill/profile_promotion_revoke.py` with `profile-promotion-revoke`, `ProfilePromotionRevocationResult`, schema/template coverage, doctor, next-action, workspace-summary, review-pack, operational Markdown filtering, and trace integration.

Expected scope:
- `profile-promotion-revoke` command that requires `--revoke-plan state/profile-promotion-revoke-plan.json` and `--revoke-plan-hash <sha256>`;
- refuse to run unless the revocation plan status is `ready_to_revoke`, `can_revoke=true`, and the hash matches the supplied plan artifact;
- write a timestamped pre-revoke backup under `state/profile-backups/` before restoring `state/project-profile.json`;
- restore only the fields listed in the revocation plan, initially limited to `ProjectProfile` schema fields;
- write `state/profile-promotion-revoke-result.json` and `reports/profile-promotion-revoke-result.md`;
- keep apply-result, original backup, revoke-plan, and revoke-result artifacts visible in doctor, next actions, summary, review pack, and trace.

Safety boundary:
- The revoke command must be explicit and hash-guarded. It must never delete promotion/apply history, infer official agency compliance, or alter raw source files.

### Beta 41 - Profile Lifecycle Ledger

Goal: make profile lifecycle state readable as one chronological operating ledger.

Status: implemented in `src/k_resdev_skill/profile_lifecycle.py` with CLI/API, schema/template coverage, doctor, next-action, workspace-summary, review-pack, operational Markdown filtering, and trace integration. The ledger also avoids false apply-drift alarms when a later guarded revoke result explains the current profile state.

Expected scope:
- `profile-lifecycle-ledger` command that reads profile-review, profile-promotion records, apply plans/results, revoke plans/results, and current `state/project-profile.json`;
- write `reports/profile-lifecycle-ledger.md` and `state/profile-lifecycle-ledger.json`;
- show timeline entries for review, promotion, apply, revoke-plan, and revoke-result artifacts with hashes, status, reviewer, and backup paths;
- flag orphaned apply results, ready revoke plans without results, missing backups, profile drift from latest lifecycle result, and superseded transitions;
- integrate the ledger into doctor, next actions, workspace-summary, review-pack, operational Markdown filtering, and trace.

Safety boundary:
- The ledger is an operating projection only. It must not certify agency compliance, alter profile state, or collapse human review decisions into AI-generated facts.

### Beta 42 - Profile Source Pack Review Queue

Goal: make verified-agency-profile work easier to stage without hardcoding time-sensitive official rules.

Status: implemented in `src/k_resdev_skill/profile_source_queue.py` with CLI/API, schema/template coverage, doctor, next-action, workspace-summary, review-pack, operational Markdown filtering, and trace integration.

Expected scope:
- `profile-source-queue` command that scans `templates/agencies/` and workspace `state/profile-sources.json`;
- surface profiles with missing source URL/file, missing retrieved date, missing source hash, missing reviewer, unresolved risk flags, stale local source hash, or `needs_review`/`rejected` source records;
- write `reports/profile-source-queue.md` and `state/profile-source-queue.json`;
- group findings by profile ID and proposed next action;
- integrate queue counts into doctor, next actions, workspace-summary, review-pack, and trace;
- do not add new official agency packs unless current official sources have been checked and recorded.

Safety boundary:
- This queue is an operating projection only. It must not certify current law, ministry guidance, or agency forms.
- Any specific agency/profile pack still requires current official source verification before promotion.

### Beta 43 - Profile Source Queue Fix Plan

Goal: turn profile source queue items into a reviewable local remediation plan.

Status: implemented in `src/k_resdev_skill/profile_source_fix_plan.py` with CLI/API, schema/template coverage, doctor, next-action, workspace-summary, review-pack, operational Markdown filtering, and trace integration.

Expected scope:
- `profile-source-fix-plan` command that reads `state/profile-source-queue.json`;
- produce proposed next commands for each queue item without executing them;
- group actions by profile ID and severity;
- suggest local-only operations such as `profile-source-record`, `profile-source-summary`, `profile-integrity`, and `validate-json`;
- explicitly mark actions requiring current official-source browsing or human review as manual steps;
- write `reports/profile-source-fix-plan.md` and `state/profile-source-fix-plan.json`;
- integrate plan counts into doctor, next actions, workspace-summary, review-pack, and trace.

Safety boundary:
- The fix plan must never fetch official sources, mutate profile packs, or mark sources verified by itself.
- Any official source update still requires explicit human/source verification.

### Beta 44 - Profile Source Fix Review Records

Goal: record supplied human decisions about profile-source fix-plan actions without mutating profile/source state.

Status: implemented in `src/k_resdev_skill/profile_source_fix_review.py` with CLI/API, schema/template coverage, doctor, next-action, workspace-summary, review-pack, operational Markdown filtering, and trace integration.

Expected scope:
- `profile-source-fix-record` command for a supplied reviewer decision on one `action_id`;
- bind records to `state/profile-source-fix-plan.json` SHA-256 and the selected action;
- support decisions such as `resolved`, `accepted_risk`, `deferred`, and `rejected`;
- write review records under `state/profile-source-fix-reviews/`;
- `profile-source-fix-summary` command that compares the current fix plan against review records;
- flag stale plan hashes, missing action IDs, unresolved high/medium actions, and accepted-risk actions;
- integrate summary counts into doctor, next actions, workspace-summary, review-pack, and trace.

Safety boundary:
- Fix review records are supplied human decision records only.
- They must not edit `state/profile-sources.json`, fetch official documents, or promote source/profile status.

### Beta 45 - Agency Profile Pack Readiness Dashboard

Goal: make the profile/source operating state scan-friendly before adding more verified agency packs.

Status: implemented as a local first pass in `src/k_resdev_skill/profile_pack_readiness.py`, with CLI/API, schema/template, doctor, next-action, summary, review-pack, operational Markdown filtering, and trace integration.

Implemented scope:
- aggregate profile-source queue, fix-plan, fix-review, profile-review, profile-promotion, apply/revoke, and lifecycle status;
- show per-profile blockers such as missing source files, stale hashes, unresolved fix actions, unreviewed promotion decisions, and guarded mutation gaps;
- write `reports/profile-pack-readiness.md` and `state/profile-pack-readiness.json`;
- integrate readiness counts into doctor, next actions, workspace-summary, review-pack, and trace;
- keep all agency/profile readiness statuses as local operating projections.

Safety boundary:
- The dashboard must not fetch official sources, create agency rules, mutate profile/source records, or treat accepted risk as compliance proof.

### Beta 46 - Profile Pack Readiness Evidence Drilldown

Goal: make each readiness blocker traceable to the exact local input that produced it.

Status: implemented as a local first pass in `src/k_resdev_skill/profile_pack_drilldown.py`, with CLI/API, schema/template, doctor, next-action, summary, review-pack, operational Markdown filtering, and trace integration.

Implemented scope:
- `profile-pack-readiness-drilldown` command and public API;
- read-only drilldown over `state/profile-pack-readiness.json`, `state/profile-source-queue.json`, `state/profile-source-fix-plan.json`, `state/profile-source-fix-summary.json`, `state/profile-review.json`, promotion/apply/revoke artifacts, and `state/profile-lifecycle-ledger.json`;
- include source artifact paths, SHA-256 hashes, profile IDs, action IDs, review IDs, lifecycle entry IDs, and suggested next command;
- review-pack and trace integration after the standalone report is stable.

Safety boundary:
- Drilldown is an investigation aid only.
- It must not fetch official sources, edit profile/source records, promote profiles, or mark accepted risk as compliance proof.

### Beta 47 - Profile Pack Investigation Bundle

Goal: create a compact review handoff bundle for one profile ID or readiness blocker.

Status: implemented as a local first pass in `src/k_resdev_skill/profile_pack_investigation.py`, with CLI/API, schema/template, doctor, next-action, summary, review-pack, operational Markdown filtering, and trace integration.

Implemented scope:
- `profile-pack-investigation-bundle` command and public API;
- filter by `--profile-id` and/or `--finding-code`;
- include readiness rows, drilldown rows, upstream artifact hashes, suggested commands, and supplied review/promotion state;
- write Markdown and JSON bundle artifacts without copying raw official-source files;
- include in review-pack after the standalone bundle is stable.

Safety boundary:
- Bundles are handoff aids only.
- Do not copy official-source bodies, fetch external sources, mutate profile/source state, or certify compliance.

### Beta 48 - Profile Pack Investigation Bundle Packager

Goal: package generated investigation-bundle metadata for reviewer handoff without copying raw official-source bodies.

Status: implemented as a local first pass in `src/k_resdev_skill/profile_pack_investigation_package.py`, with CLI/API, schema/template coverage, optional ZIP output, doctor, next-action, summary, review-pack, operational Markdown filtering, and trace integration.

Implemented scope:
- `profile-pack-investigation-package` command and public API;
- select one profile ID, one readiness finding code, or all open high/medium blockers;
- include bundle Markdown/JSON, readiness and drilldown artifact hashes, schema validation status, and review-pack hash references;
- write a package manifest and optional ZIP that excludes raw official-source documents by default;
- make exclusions explicit so reviewers can see what was deliberately not copied.

Safety boundary:
- The package is a transfer aid only.
- It must not add official-source body copies, fetch current agency sources, mutate profile/source state, or certify compliance.

### Beta 49 - Profile Pack Package Reviewer Receipt

Goal: record supplied reviewer receipt or package-review decisions against a specific investigation package hash.

Expected scope:
- `profile-pack-package-receipt` command and public API;
- a receipt model with package ID, package manifest path, package manifest SHA-256, reviewer, decision, reviewed_at, notes, and risk flags;
- decisions such as `received`, `accepted_for_review`, `needs_changes`, and `rejected`;
- receipt records under `state/profile-pack-package-receipts/`;
- a package receipt summary that detects stale package hashes, missing package IDs, unresolved needs-changes decisions, and rejected packages;
- doctor, next-action, summary, review-pack, operational Markdown filtering, and trace integration.

Safety boundary:
- Receipt records are supplied human transfer/review metadata only.
- They must not promote profiles, mark official-source checks resolved, create approvals, or certify agency compliance.

## Deferred Ideas

- Direct official HWP/HWPX form generation.
- IRIS/NTIS field submission automation.
- OCR for scanned PDFs.
- Web UI.
- LLM-assisted extraction.

These should wait until traceability, impact analysis, and verified profile source handling are stable.

## Recommended Next Slice

Implement Beta 49 next.

Beta 49 should close the package handoff loop with hash-bound supplied reviewer receipt records, without turning reviewer receipt into profile verification or official compliance.
