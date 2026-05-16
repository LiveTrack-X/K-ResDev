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

Status: paper card extraction, literature matrix, data insight candidate report, experiment comparison table, reproducibility checklist, and hypothesis-to-experiment planning are implemented. Generated experiment plans remain validation drafts and require human approval before execution.

## P2 - Korean R&D specialization

1. Agency-specific report templates.
2. Budget category rules.
3. Change-request templates.
4. Audit-defense Q&A generator.
5. IRIS/NTIS-style field mapper after official template verification.

Status: `national-rnd-basic` is present as a generic needs-review template skeleton only. It is not an official agency profile. A profile registry/validator and generic budget evidence checklist are implemented so local profiles can be inspected without hardcoding unverified rules.

## P3 - Automation and validation

1. JSON schema validation.
2. Evidence/report citation check.
3. Data analysis script generation and execution.
4. Report export to Markdown/DOCX/HWP-compatible intermediate format.
5. Human approval workflow.
