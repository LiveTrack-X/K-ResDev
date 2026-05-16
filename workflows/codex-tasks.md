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

## Safety constraints

- Never alter raw files.
- Never create final official report without explicit approval.
- Never fabricate metrics or citations.
- Mark uncertain extracted items as `needs_review`.
- Keep agency-specific official templates pluggable; do not hardcode unverified rules.
