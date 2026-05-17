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

## Safety constraints

- Never alter raw files.
- Never create final official report without explicit approval.
- Never fabricate metrics or citations.
- Mark uncertain extracted items as `needs_review`.
- Keep agency-specific official templates pluggable; do not hardcode unverified rules.
