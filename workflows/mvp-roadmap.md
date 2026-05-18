# MVP Roadmap

## P0 - Admin evidence MVP

1. Folder scanner: `inbox/` → raw registry.
2. File classifier: plan/progress/experiment/budget/outcome/change/literature/data.
3. Evidence item generator.
4. Evidence index generator.
5. KPI/milestone mapper from project plan.
6. Monthly report draft from accepted/needs_review evidence.
7. Consistency checker: claim without evidence, below-target metrics, missing budget proof.

Status: implemented as a conservative first pass in `src/k_resdev_skill/`. Outputs remain draft projections and require human review before official use.

P0 intake hardening now includes DOCX/XLSX/HWPX/PDF text extraction, optional HWP extraction through an installed `rhwp` CLI, document-level evidence candidates, and provenance fields populated from line/page/sheet/cell hints.

## P1 - Research assistant MVP

1. Paper card generator.
2. Literature review matrix.
3. Dataset profiler for CSV/XLSX.
4. Research insight candidate generator.
5. Reproducibility checklist.
6. Hypothesis-to-experiment planner.

Status: paper card extraction, BibTeX/RIS/CSL JSON bibliography intake, reference corpus adapters for local PDFs/notes/Zotero exports, bibliography review records, citation support records, bibliography integrity checks, citation-support integrity checks, research claim import/matrix checks, literature matrix, data insight candidate report, experiment comparison table, reproducibility checklist, and hypothesis-to-experiment planning are implemented. Generated experiment plans and research claims remain validation drafts unless human-reviewed.

## P2 - Korean R&D specialization

1. Agency-specific report templates.
2. Budget category rules.
3. Change-request templates.
4. Audit-defense Q&A generator.
5. IRIS/NTIS-style field mapper after official template verification.

Status: `national-rnd-basic` is present as a generic needs-review template skeleton only. It is not an official agency profile. A profile registry/validator, profile-source record shell, profile-integrity checker, and generic budget evidence checklist are implemented so local profiles can be inspected without hardcoding unverified rules.

## P3 - Automation and validation

1. JSON schema validation.
2. Evidence/report citation check.
3. Data analysis script generation and execution.
4. Report export to Markdown/DOCX/HWP-compatible intermediate format.
5. Human approval workflow.

Status: JSON schema validation, evidence bundle indexes, human approval records/gates, reproducible CSV/XLSX analysis runs, Markdown projection export to DOCX/HTML/TXT, workspace initialization, readiness doctor checks, doctor-derived next-action plans, one-page workspace summaries, bundled workspace review packs, review-pack artifact hash verification, evidence source hash verification, source-integrity findings inside doctor/review-pack flows, report approval coverage checks, approval target hash binding, workspace report-integrity checks, cited evidence review-status checks, budget-ledger import/integrity checks, bibliography index/review/citation-support/research-claim schema validation, and bibliography/citation-support/research-claim doctor/review-pack checks are implemented as a first pass.

## P4 - Operational continuity

1. Workspace traceability graph across sources, evidence, reports, approvals, bibliography, citation support, analysis manifests, and generated artifacts.
2. Change impact review for source drift, approval target drift, bibliography source drift, and unresolved citation support.
3. Verified agency-specific profile packs for official templates and rules after current source verification.
4. Budget evidence ledger with category rollups and proof completeness checks.
5. Research claim matrix connecting paper claims, experiment evidence, citation support, and insight candidates.

Status: workspace traceability graph and impact review are implemented as a local first pass. Generic profile source records, budget ledgers, research claim matrices, and trace passport checkpoints now plug into the same doctor/review-pack/trace layer. Verified agency-specific packs should continue to plug into that trace layer instead of becoming separate disconnected checklists.

## P5 - Research operations workflow layer

1. Trace passport and checkpoint ledger for compact session resume and stale-artifact detection.
2. Artifact authority levels across raw sources, extracted candidates, reviewed evidence, draft projections, and approved projections.
3. Local reference corpus adapters for folder scans, Zotero exported JSON, and Markdown notes with rejection logs.
4. Read-only workspace discovery and setup proposals before initialization or migration.
5. Goals/deadline operating file linked to KPIs, milestones, evidence, and reports.
6. Local weekly review and workspace dashboard generated from K-ResDev artifacts.
7. Thin workflow router for Admin, Research, Integrity, and Weekly review paths after concrete commands are stable.

Status: trace passport/checkpoint ledger, artifact authority levels, reference corpus adapters, and read-only workspace discovery/setup proposals are implemented as local first passes. Artifact authority labels now keep raw sources, extracted candidates, evidence states, draft projections, approved projections, operating summaries, rejected artifacts, and superseded artifacts visibly separated across doctor, summary, review-pack, and trace flows. The remaining workflow-layer items are specified in `workflows/external-academic-workflow-ideas-spec.md` and should continue to adapt external academic workflow ideas into K-ResDev-native, evidence-first behavior without vendoring external skill content.
