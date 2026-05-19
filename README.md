# K-ResDev Skill

Purpose: 한국형 국책 R&D 환경에서 연구 행정 문서화, 증빙 정합성, 보고서 생성, 논문/데이터 인사이트 보조를 evidence-first 방식으로 지원하는 Codex/Skill 프로젝트입니다.

Current release: `0.1 BETA 57` (`0.1.0b57`).

Core principle:

```text
Evidence is source of truth.
Reports, summaries, and research narratives are projections.
AI may draft and check, but human approval is required for submission or scientific claims.
```

Primary modes:

1. Admin Evidence Mode: 계획서, KPI, 예산, 증빙, 보고서, 정산, 감사 대응.
2. Research Assistant Mode: 논문 요약, 선행연구 맵, 데이터 분석, hypothesis generation, 실험 설계 보조.
3. Integrity Mode: 주장-근거 연결, 수치 검증, 과장 탐지, 재현성 체크, 누락 증빙 탐지.

This repository does not encode any single ministry/institution form as authoritative. Agency-specific templates should be added under `templates/agencies/` only after verification.

## Current implementation

- Pydantic models for evidence, project state, KPI, milestone, and research insights.
- Rule-based file classifier for plan/progress/experiment/budget/outcome/change/literature/data/unknown.
- CSV/XLSX data profiler with missingness, numeric summaries, and metric detection.
- Evidence index writer for `state/evidence-index.md` and `state/evidence-index.json`.
- Unsupported claim checker for numeric claims, superlatives, missing evidence IDs, KPI mismatch, and below-target overclaims.
- Literature review matrix writer.
- End-to-end intake pipeline that writes `state/raw-registry.json`, `evidence/*.json`, `state/evidence-index.*`, and `state/open-issues.md`.
- Stable source/evidence IDs derived from source hash plus inbox-relative path, so adding another file does not renumber existing evidence.
- Intake excludes its own `state/` and `evidence/` output folders when they are placed inside the inbox.
- Document text extraction for TXT/MD/CSV/JSON/LOG, DOCX, XLSX, HWPX, PDF, and optional HWP via `rhwp` CLI when installed.
- Draft monthly report writer plus claim-review sidecar.
- Draft audit-defense Q&A writer from evidence metadata.
- Conservative plan mapper for KPI/milestone draft extraction from text.
- Numeric evidence-mismatch detection when a report cites an evidence ID but uses unsupported numbers.
- Paper card extraction from supplied metadata text without citation invention.
- Bibliography management import for BibTeX/RIS/CSL JSON into `state/bibliography-index.*`, with optional literature matrix projection.
- Reference corpus adapter bridge for local PDFs, Markdown notes/frontmatter, BibTeX/RIS/CSL JSON, and Zotero JSON exports into `state/literature-corpus.json` plus `state/reference-rejection-log.json`.
- Bibliography review records for supplied human metadata decisions under `state/bibliography-reviews/`.
- Bibliography integrity checker for Markdown citation keys, duplicate citation metadata, and bibliography source hash drift.
- Citation support records for supplied human paper-claim support decisions under `state/citation-support/`.
- Citation support integrity checker for Markdown citations against supplied paper-claim support records.
- Research claim import and matrix checks for supplied claims against local evidence, bibliography, and citation-support records.
- Workspace traceability graph for local source, evidence, report, approval, bibliography, citation-support, research claims, analysis, and review-pack impact review.
- Profile source records for official-source metadata, retrieved date, hash, reviewer, and review status without hardcoding agency rules.
- Profile source pack review queue for missing source locators, retrieved dates, hashes, reviewers, unresolved risk flags, stale local hashes, and non-verified source statuses.
- Profile source queue fix-plan workflow that converts source-pack queue items into reviewable local commands and manual official-source checks without executing or verifying them.
- Profile source fix-review records for supplied human decisions on individual fix-plan actions, bound to the current fix-plan SHA-256 and summarized without mutating source/profile state.
- Profile integrity checker for profile source drift, missing source records, and invalid verified profile states.
- Data insight candidate reports that keep findings in hypothesis/review state.
- Experiment comparison table and reproducibility checklist generators.
- Hypothesis-to-experiment planner for turning `ResearchInsight` records into reviewable validation plans.
- Generic budget evidence completeness checklist that avoids hardcoding unverified agency rules.
- Budget evidence ledger import and integrity checks for generic amount/proof/approval/evidence-link review without inferring official eligibility.
- Agency profile registry/validator for `templates/agencies/` skeletons.
- Human approval record workflow for supplied reviewer decisions, approval summaries, and approval gates.
- Evidence bundle index generator for audit/review packages without copying or altering raw files.
- Workspace approval coverage checker for report drafts/exports against supplied human decisions.
- Approval target hash binding so changed report artifacts can be detected after approval.
- Workspace report integrity checker for Markdown report drafts against indexed evidence claims.
- Report integrity checks for cited evidence status, including `needs_review`, `draft`, `rejected`, and `superseded` evidence.
- JSON schema validation CLI for bundled schemas such as evidence, project profile, research insight, and approval record.
- Reproducible CSV/XLSX analysis run workflow that writes profile JSON, insight candidate Markdown, replay script, and manifest.
- Projection export workflow for Markdown drafts to DOCX, TXT, HTML, or HWPX-compatible HTML review files.
- Workspace initializer and readiness doctor for standard local workspace setup and pre-reporting checks.
- Read-only workspace discovery and additive setup planning for new or messy R&D folders before initialization or migration.
- Artifact authority level classifier for raw sources, extracted candidates, evidence states, draft/reviewed/approved projections, and operating summaries.
- Goals/deadlines operating file and review checker for local objectives, KPIs, milestones, evidence links, report drafts, and approval readiness.
- Local weekly operating review and workspace dashboard generated from local K-ResDev artifacts.
- Thin local workflow router for Admin, Research, Integrity, and Weekly review command plans.
- Narrow IRIS/Innopolis 2026 source-backed profile seed that installs hash-backed profile source notes while keeping official-use status as `needs_review`.
- Profile promotion review workflow that checks source hashes, reviewer identity, applicability notes, and unresolved risk flags before any profile can be treated as ready for human-controlled promotion.
- Profile promotion record workflow for supplied human decisions bound to a passing `state/profile-review.json` SHA-256 hash, without mutating project profiles by default.
- Profile promotion apply-plan workflow that proposes exact `project-profile.json` field changes without writing them.
- Guarded profile promotion apply workflow that requires an apply-plan hash, writes `state/profile-backups/`, and records the mutation result before a profile status change is accepted.
- Profile promotion revocation-plan workflow that checks the saved apply result, backup profile, and current profile drift before any rollback is considered.
- Guarded profile promotion revocation workflow that requires a revoke-plan hash, writes a pre-revoke backup, and restores only reviewed `ProjectProfile` fields.
- Profile lifecycle ledger that combines current profile status, profile-review, human promotion records, guarded apply plans/results, and guarded revoke plans/results into one chronological operating projection.
- Agency profile pack readiness dashboard that aggregates profile-source queue, fix-plan, fix-review, profile-review, promotion, apply/revoke, and lifecycle blockers into one scan-friendly profile view.
- Profile pack readiness drilldown that links readiness findings to upstream artifact rows, IDs, commands, and SHA-256 hashes.
- Profile pack investigation bundle that filters by profile ID or readiness finding code and condenses readiness rows, drilldown rows, upstream hashes, suggested commands, and supplied human-review status without copying raw official-source bodies.
- Profile pack investigation package manifest and optional ZIP that transfer generated metadata artifacts while explicitly excluding raw official-source bodies.
- Profile pack package reviewer receipt records and summaries that bind supplied transfer/review decisions to the current package manifest SHA-256.
- Profile-driven admin obligation pack loader/reviewer for `templates/agencies/<profile-id>/admin-obligations.json`, with `needs_review` guards unless profile/source records are human-verified.
- Admin profile-pack human review records and summaries that bind pack-level or row-level supplied decisions to the current admin obligation profile-pack SHA-256.
- Admin profile-pack promotion gate that joins current profile review, hash-bound profile promotion, profile-pack review, and admin profile-pack human review receipts before any reviewed-seed mode is considered.
- Explicit reviewed-seed admin obligation initialization mode that only runs when the admin profile-pack promotion gate passes, records gate/profile/pack/review hashes, and keeps rows as local `accepted_risk` candidates rather than official rules.
- `national-rnd-basic` and narrow `iris-innopolis-2026-017795` admin obligation profile-pack seeds that remain local candidates rather than official rules.
- Admin obligation graph starter/reviewer for local reporting, settlement, performance, agreement/change, budget, approval, and equipment obligation candidates without hardcoding official IRIS/NTIS/RCMS/Ezbaro rules.
- Settlement evidence binder that joins budget ledger rows, proof metadata, approval references, evidence IDs, source hashes, and review findings without deciding cost eligibility.
- Admin change ledger review for agreement, KPI, budget, period, and approval changes, including warnings when unapproved changes appear in report drafts.
- Admin calendar review that links local admin obligation candidates to reviewed project-goals deadlines and due-soon/overdue state.
- Workspace next-action planner that converts doctor findings into deterministic, reviewable commands.
- Workspace summary report that combines readiness, next actions, evidence counts, approvals, reports, exports, and analysis manifests.
- Workspace review pack command that refreshes discovery, readiness, next actions, workspace summary, artifact-authority, goals-review, weekly-review, workspace-dashboard, budget-ledger, settlement-binder, admin profile-pack review, admin profile-pack human review summary, admin profile-pack promotion gate, admin obligations, admin change ledger, admin calendar, profile-source-queue, profile-source-fix-plan, profile-source-fix-summary, profile-integrity, profile-promotion-summary, profile-promotion-apply-plan, profile-promotion-apply-result when present, profile-promotion-revoke-plan/result when present, profile-lifecycle-ledger, profile-pack-readiness, profile-pack-readiness-drilldown, profile-pack-investigation-bundle, profile-pack-investigation-package, package receipt summary, source-verification, approval-coverage, report-integrity, bibliography-integrity, reference-corpus, citation-support, research-claim-matrix, and workspace-trace artifacts together.
- Review pack artifact hash manifest and verifier for detecting missing or changed generated artifacts.
- Evidence source verifier that checks indexed source files against saved source hashes.
- Workspace doctor and review pack integration for local evidence-source presence/hash drift checks.
- Workspace doctor, next-action, summary, and review-pack integration for workspace discovery/setup findings.
- Workspace doctor, next-action, summary, review-pack, and trace metadata integration for artifact authority findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for goals/deadline findings.
- Next-action routing for source-integrity findings.
- Workspace doctor and review pack integration for report approval coverage.
- Workspace doctor and review pack integration for report claim integrity findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for budget ledger findings.
- Workspace doctor and review pack integration for bibliography integrity findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for reference corpus rejection logs.
- Workspace doctor and review pack integration for citation support findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for research claim matrix findings.
- Workspace doctor, next-action, summary, and review-pack integration for profile source integrity findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for profile source queue findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for profile source fix-plan findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for profile source fix-review findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for profile lifecycle ledger findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for profile pack readiness findings.
- Workspace doctor, next-action, summary, review-pack, and trace integration for profile pack readiness drilldown gaps.
- Workspace doctor, next-action, summary, review-pack, and trace integration for profile pack investigation bundle handoff gaps.
- Workspace doctor, next-action, summary, review-pack, and trace integration for generated profile pack investigation package handoffs and package reviewer receipts.
- Workspace doctor, next-action, summary, review-pack, and trace integration for admin profile packs, admin profile-pack human reviews, admin profile-pack promotion gates, admin obligations, settlement binder, admin change ledger, and admin calendar findings.
- Workspace doctor, next-action, summary, and review-pack integration for trace impact findings.
- Trace passport and checkpoint ledger for compact resume checkpoints, artifact hash drift detection, and checkpoint-based resume plans.
- `national-rnd-basic` agency template skeleton for annual/interim/final reports, change requests, and performance registration drafts.

## Local use

```powershell
python -m pip install -e .
python -m pytest
python -m k_resdev_skill intake --inbox .\inbox --project my-rnd-project
python -m k_resdev_skill init-workspace --root .\demo-workspace --project-id PRJ-2026-0001 --title "Demo R&D Project"
python -m k_resdev_skill init-workspace --root .\iris-seed-workspace --project-id PRJ-2026-0002 --title "IRIS Seed Project" --profile iris-innopolis-2026-017795
python -m k_resdev_skill discover-workspace --root .\demo-workspace --output .\demo-workspace\reports\workspace-discovery.md --json .\demo-workspace\state\workspace-discovery.json
python -m k_resdev_skill artifact-authority --root .\demo-workspace --output .\demo-workspace\reports\artifact-authority.md --json .\demo-workspace\state\artifact-authority.json
python -m k_resdev_skill goals-init --root .\demo-workspace
python -m k_resdev_skill goals-review --root .\demo-workspace --output .\demo-workspace\reports\goals-review.md --json .\demo-workspace\state\goals-review.json
python -m k_resdev_skill deadline-check --root .\demo-workspace --output .\demo-workspace\reports\goals-review.md --json .\demo-workspace\state\goals-review.json
python -m k_resdev_skill weekly-review --root .\demo-workspace --date 2026-05-19
python -m k_resdev_skill workspace-dashboard --root .\demo-workspace
python -m k_resdev_skill workflow weekly --root .\demo-workspace --date 2026-05-19
python -m k_resdev_skill workflow weekly --root .\demo-workspace --date 2026-05-19 --run
python -m k_resdev_skill doctor --root .\demo-workspace --output .\demo-workspace\reports\readiness.md --json .\demo-workspace\state\readiness.json
python -m k_resdev_skill next-actions --root .\demo-workspace --output .\demo-workspace\reports\next-actions.md --json .\demo-workspace\state\next-actions.json
python -m k_resdev_skill approval-coverage --root .\demo-workspace --output .\demo-workspace\reports\approval-coverage.md --json .\demo-workspace\state\approval-coverage.json
python -m k_resdev_skill report-integrity --root .\demo-workspace --output .\demo-workspace\reports\report-integrity.md --json .\demo-workspace\state\report-integrity.json
python -m k_resdev_skill workspace-summary --root .\demo-workspace --output .\demo-workspace\reports\workspace-summary.md --json .\demo-workspace\state\workspace-summary.json
python -m k_resdev_skill workspace-review-pack --root .\demo-workspace
python -m k_resdev_skill verify-review-pack .\demo-workspace\state\workspace-review-pack.json
python -m k_resdev_skill checkpoint-create --root .\demo-workspace --stage beta-review --summary "Reviewed beta workspace state" --status needs_review
python -m k_resdev_skill checkpoint-summary --root .\demo-workspace --output .\demo-workspace\reports\trace-passport.md --json .\demo-workspace\state\trace-passport.json
python -m k_resdev_skill checkpoint-resume-plan --root .\demo-workspace --output .\demo-workspace\reports\checkpoint-resume-plan.md --json .\demo-workspace\state\checkpoint-resume-plan.json
python -m k_resdev_skill verify-evidence-sources .\demo-workspace\state\evidence-index.json --root .\demo-workspace --output .\demo-workspace\reports\source-verification.md --json .\demo-workspace\state\source-verification.json
python -m k_resdev_skill map-plan .\inbox\plan.txt --output .\state\project-state.json
python -m k_resdev_skill draft-report .\state\evidence-index.json --project-state .\state\project-state.json --period 2026-05
python -m k_resdev_skill audit-qna .\state\evidence-index.json
python -m k_resdev_skill paper-card .\inbox\paper-notes.txt --markdown --output .\reports\paper-card.md
python -m k_resdev_skill bib-import .\references\library.bib --state-dir .\state --literature-matrix .\reports\literature-review-matrix.md
python -m k_resdev_skill reference-corpus --root . --output .\reports\reference-corpus-summary.md --json .\state\literature-corpus.json --rejections .\state\reference-rejection-log.json
python -m k_resdev_skill bib-review-record --bibliography-id BIB-2026-ABCD1234 --decision accepted --reviewer reviewer-name --citation-key kim2026 --reviews-dir .\state\bibliography-reviews
python -m k_resdev_skill bib-review-summary .\state\bibliography-reviews --output .\reports\bibliography-review-summary.md
python -m k_resdev_skill bib-review-status .\state\bibliography-reviews --bibliography-id BIB-2026-ABCD1234
python -m k_resdev_skill bib-lit-matrix .\state\bibliography-index.json --output .\reports\literature-review-matrix.md
python -m k_resdev_skill bib-integrity --root . --output .\reports\bibliography-integrity.md --json .\state\bibliography-integrity.json
python -m k_resdev_skill citation-support-record --bibliography-id BIB-2026-ABCD1234 --citation-key kim2026 --claim "Model A underperforms on small-lesion cases." --decision needs_review --reviewer reviewer-name --support-dir .\state\citation-support
python -m k_resdev_skill citation-support-summary .\state\citation-support --output .\reports\citation-support-summary.md
python -m k_resdev_skill citation-support-status .\state\citation-support --bibliography-id BIB-2026-ABCD1234 --claim "Model A underperforms on small-lesion cases."
python -m k_resdev_skill citation-support-integrity --root . --output .\reports\citation-support.md --json .\state\citation-support.json
python -m k_resdev_skill research-claim-import .\references\research-claims.csv --state-dir .\state --markdown .\reports\research-claims.md
python -m k_resdev_skill research-claim-summary .\state\research-claims.json --output .\reports\research-claims-summary.md
python -m k_resdev_skill research-claim-matrix --root . --output .\reports\research-claim-matrix.md --json .\state\research-claim-matrix.json
python -m k_resdev_skill profile-source-record --profile-id national-rnd-basic --title "Official source snapshot" --source-url https://example.org/official-source --retrieved-at 2026-05-18 --review-status needs_review
python -m k_resdev_skill profile-source-summary --root . --output .\reports\profile-source-summary.md --json .\state\profile-source-summary.json
python -m k_resdev_skill profile-source-queue --root . --output .\reports\profile-source-queue.md --json .\state\profile-source-queue.json
python -m k_resdev_skill profile-source-fix-plan --root . --output .\reports\profile-source-fix-plan.md --json .\state\profile-source-fix-plan.json
python -m k_resdev_skill profile-source-fix-record --root . --action-id <PSF-ID> --decision resolved --reviewer reviewer-name --fix-plan-hash <sha256>
python -m k_resdev_skill profile-source-fix-summary --root . --output .\reports\profile-source-fix-summary.md --json .\state\profile-source-fix-summary.json
python -m k_resdev_skill profile-integrity --root . --output .\reports\profile-integrity.md --json .\state\profile-integrity.json
python -m k_resdev_skill profile-review --root . --output .\reports\profile-review.md --json .\state\profile-review.json
python -m k_resdev_skill profile-promotion-record --root . --decision verified --reviewer reviewer-name --profile-review .\state\profile-review.json --profile-review-hash <sha256>
python -m k_resdev_skill profile-promotion-summary --root . --output .\reports\profile-promotion-summary.md --json .\state\profile-promotion-summary.json
python -m k_resdev_skill profile-promotion-apply-plan --root . --output .\reports\profile-promotion-apply-plan.md --json .\state\profile-promotion-apply-plan.json
python -m k_resdev_skill profile-promotion-apply --root . --apply-plan .\state\profile-promotion-apply-plan.json --apply-plan-hash <sha256> --output .\reports\profile-promotion-apply-result.md --json .\state\profile-promotion-apply-result.json
python -m k_resdev_skill profile-promotion-revoke-plan --root . --reviewer reviewer-name --reason "Supplied revocation reason" --output .\reports\profile-promotion-revoke-plan.md --json .\state\profile-promotion-revoke-plan.json
python -m k_resdev_skill profile-promotion-revoke --root . --revoke-plan .\state\profile-promotion-revoke-plan.json --revoke-plan-hash <sha256> --output .\reports\profile-promotion-revoke-result.md --json .\state\profile-promotion-revoke-result.json
python -m k_resdev_skill profile-lifecycle-ledger --root . --output .\reports\profile-lifecycle-ledger.md --json .\state\profile-lifecycle-ledger.json
python -m k_resdev_skill profile-pack-readiness --root . --output .\reports\profile-pack-readiness.md --json .\state\profile-pack-readiness.json
python -m k_resdev_skill profile-pack-readiness-drilldown --root . --output .\reports\profile-pack-readiness-drilldown.md --json .\state\profile-pack-readiness-drilldown.json
python -m k_resdev_skill profile-pack-investigation-bundle --root . --profile-id national-rnd-basic --output .\reports\profile-pack-investigation-bundle.md --json .\state\profile-pack-investigation-bundle.json
python -m k_resdev_skill profile-pack-investigation-package --root . --profile-id national-rnd-basic --output .\reports\profile-pack-investigation-package.md --json .\state\profile-pack-investigation-package.json --zip .\reports\profile-pack-investigation-package.zip
python -m k_resdev_skill profile-pack-package-receipt-record --root . --decision received --reviewer reviewer-name --package-hash <sha256>
python -m k_resdev_skill profile-pack-package-receipt-summary --root . --output .\reports\profile-pack-package-receipt-summary.md --json .\state\profile-pack-package-receipt-summary.json
python -m k_resdev_skill admin-profile-pack-review --profile national-rnd-basic --output .\reports\admin-profile-pack.md --json .\state\admin-profile-pack-review.json
python -m k_resdev_skill admin-profile-pack-review-record --root . --profile national-rnd-basic --decision accepted_risk --reviewer reviewer-name --profile-pack-hash <sha256>
python -m k_resdev_skill admin-profile-pack-review-summary --root . --profile national-rnd-basic --output .\reports\admin-profile-pack-review-summary.md --json .\state\admin-profile-pack-review-summary.json
python -m k_resdev_skill admin-profile-pack-gate --root . --profile national-rnd-basic --output .\reports\admin-profile-pack-gate.md --json .\state\admin-profile-pack-gate.json
python -m k_resdev_skill admin-obligations-init --root . --profile national-rnd-basic --output .\reports\admin-obligations.md --json .\state\admin-obligations-review.json
python -m k_resdev_skill admin-obligations-init --root . --profile national-rnd-basic --reviewed-seed --output .\reports\admin-obligations.md --json .\state\admin-obligations-review.json
python -m k_resdev_skill admin-obligations-review --root . --output .\reports\admin-obligations.md --json .\state\admin-obligations-review.json
python -m k_resdev_skill workspace-trace --root . --output .\reports\workspace-trace.md --json .\state\workspace-trace.json
python -m k_resdev_skill budget-ledger-import .\references\budget-ledger.csv --state-dir .\state --markdown .\reports\budget-ledger-import.md
python -m k_resdev_skill budget-ledger-integrity --root . --output .\reports\budget-ledger.md --json .\state\budget-ledger-integrity.json
python -m k_resdev_skill settlement-binder --root . --output .\reports\settlement-binder.md --json .\state\settlement-binder.json
python -m k_resdev_skill admin-change-ledger --root . --output .\reports\admin-change-ledger.md --json .\state\admin-change-ledger-review.json
python -m k_resdev_skill admin-calendar-review --root . --output .\reports\admin-calendar.md --json .\state\admin-calendar.json
python -m k_resdev_skill data-insights .\inbox\metrics.csv --output .\reports\data-insights.md
python -m k_resdev_skill run-analysis .\inbox\metrics.csv --output-dir .\reports\analysis --evidence-id EVI-2026-0001
python -m k_resdev_skill analysis-script .\inbox\metrics.csv --output-dir .\reports\analysis --output .\reports\analysis\metrics-analysis.py
python -m k_resdev_skill plan-experiment .\state\research-insights.json --evidence-index .\state\evidence-index.json --output .\reports\experiment-plan.md
python -m k_resdev_skill experiment-table .\state\evidence-index.json --output .\reports\experiment-table.md
python -m k_resdev_skill repro-check .\state\evidence-index.json --output .\reports\repro-check.md
python -m k_resdev_skill budget-check .\state\evidence-index.json --output .\reports\budget-checklist.md
python -m k_resdev_skill profiles --markdown --output .\reports\agency-profiles.md
python -m k_resdev_skill validate-profile .\templates\agencies\national-rnd-basic\project-profile.json
python -m k_resdev_skill validate-profile .\templates\agencies\iris-innopolis-2026-017795\project-profile.json
python -m k_resdev_skill validate-json profile-source .\state\profile-sources.json
python -m k_resdev_skill validate-json profile-source-queue .\state\profile-source-queue.json
python -m k_resdev_skill validate-json profile-source-fix-plan .\state\profile-source-fix-plan.json
python -m k_resdev_skill validate-json profile-source-fix-review .\state\profile-source-fix-reviews\PSFR-2026-ABCD1234.json
python -m k_resdev_skill validate-json profile-source-fix-summary .\state\profile-source-fix-summary.json
python -m k_resdev_skill validate-json profile-promotion-apply-plan .\state\profile-promotion-apply-plan.json
python -m k_resdev_skill validate-json profile-promotion-apply-result .\state\profile-promotion-apply-result.json
python -m k_resdev_skill validate-json profile-promotion-revoke-plan .\state\profile-promotion-revoke-plan.json
python -m k_resdev_skill validate-json profile-promotion-revoke-result .\state\profile-promotion-revoke-result.json
python -m k_resdev_skill validate-json profile-lifecycle-ledger .\state\profile-lifecycle-ledger.json
python -m k_resdev_skill validate-json profile-pack-readiness .\state\profile-pack-readiness.json
python -m k_resdev_skill validate-json profile-pack-readiness-drilldown .\state\profile-pack-readiness-drilldown.json
python -m k_resdev_skill validate-json profile-pack-investigation-bundle .\state\profile-pack-investigation-bundle.json
python -m k_resdev_skill validate-json profile-pack-investigation-package .\state\profile-pack-investigation-package.json
python -m k_resdev_skill validate-json profile-pack-package-receipt-summary .\state\profile-pack-package-receipt-summary.json
python -m k_resdev_skill validate-json admin-profile-pack-review .\state\admin-profile-pack-review.json
python -m k_resdev_skill validate-json admin-profile-pack-review-summary .\state\admin-profile-pack-review-summary.json
python -m k_resdev_skill validate-json admin-profile-pack-gate .\state\admin-profile-pack-gate.json
python -m k_resdev_skill validate-json admin-obligations .\state\admin-obligations-review.json
python -m k_resdev_skill validate-json settlement-binder .\state\settlement-binder.json
python -m k_resdev_skill validate-json admin-change-ledger .\state\admin-change-ledger-review.json
python -m k_resdev_skill validate-json admin-calendar .\state\admin-calendar.json
python -m k_resdev_skill validate-json budget-ledger .\state\budget-ledger.json
python -m k_resdev_skill validate-json research-claim .\state\research-claims.json
python -m k_resdev_skill validate-json checkpoint .\templates\trace-passport-entry.json
python -m k_resdev_skill validate-json reference-corpus .\state\literature-corpus.json
python -m k_resdev_skill validate-json reference-corpus-item .\templates\reference-corpus-item.json
python -m k_resdev_skill validate-json reference-rejection .\state\reference-rejection-log.json
python -m k_resdev_skill validate-json workspace-discovery .\state\workspace-discovery.json
python -m k_resdev_skill validate-json workspace-discovery-item .\templates\workspace-discovery-item.json
python -m k_resdev_skill validate-json workspace-setup-proposal .\templates\workspace-setup-proposal.json
python -m k_resdev_skill validate-json artifact-authority .\state\artifact-authority.json
python -m k_resdev_skill validate-json artifact-authority-record .\templates\artifact-authority-record.json
python -m k_resdev_skill validate-json artifact-authority-finding .\templates\artifact-authority-finding.json
python -m k_resdev_skill validate-json project-goals .\state\project-goals.json
python -m k_resdev_skill validate-json goals-review .\state\goals-review.json
python -m k_resdev_skill validate-json weekly-review .\state\weekly-review-2026-05-19.json
python -m k_resdev_skill validate-json workspace-dashboard .\state\workspace-dashboard.json
python -m k_resdev_skill validate-json workflow-plan .\state\workflow-weekly.json
python -m k_resdev_skill validate-json project-objective .\templates\project-objective.json
python -m k_resdev_skill validate-json project-deadline .\templates\project-deadline.json
python -m k_resdev_skill validate-json evidence .\state\evidence-index.json
python -m k_resdev_skill validate-json bibliography-review .\templates\bibliography-review-record.json
python -m k_resdev_skill approval-record --target-type report --target-id monthly-2026-05 --target-path .\reports\monthly-report-2026-05.md --decision needs_changes --reviewer reviewer-name --approvals-dir .\state\approvals
python -m k_resdev_skill approval-summary .\state\approvals --output .\reports\approval-summary.md
python -m k_resdev_skill approval-gate .\state\approvals --target-type report --target-id monthly-2026-05
python -m k_resdev_skill bundle-index .\state\evidence-index.json --approval-records .\state\approvals --output .\reports\evidence-bundle-index.md
python -m k_resdev_skill export-projection .\reports\monthly-report-2026-05.md --output .\reports\monthly-report-2026-05.docx --format docx
python -m k_resdev_skill export-projection .\reports\monthly-report-2026-05.md --output .\reports\monthly-report-2026-05.hwpx.html --format hwpx-html
python -m k_resdev_skill classify .\inbox\plan.pdf --text "연구개발계획서 KPI"
python -m k_resdev_skill profile .\inbox\metrics.csv
```

The package name is `k_resdev_skill`; the Codex skill name is `k-resdev`.

For binary `.hwp` intake, install an `rhwp` CLI separately. K-ResDev treats it as an optional adapter and marks HWP extraction as `needs_review` when the CLI is unavailable.
