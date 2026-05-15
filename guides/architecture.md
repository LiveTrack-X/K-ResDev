# Architecture

## Core lifecycle

```text
Inbox files
→ Raw registry
→ Parsed artifacts
→ Evidence items
→ KPI/milestone/budget/research claim links
→ Consistency checks
→ Report/research projections
→ Human review
→ Submission-ready package
```

## Layer model

| Layer | Purpose | Examples |
|---|---|---|
| Raw | Preserve original files | PDFs, XLSX, CSV, logs, receipts |
| Parsed | Extracted text/tables | text, CSV summaries, OCR if needed |
| Evidence | Auditable units | metric result, receipt proof, meeting decision |
| Semantic maps | Link evidence to structure | KPI, milestone, budget, paper claim |
| Projection | Generated output | monthly report, final report, literature review |
| Review | Human decision | approved, rejected, needs follow-up |

## Two-track design

### Admin track
Focuses on compliance, reporting, budget, milestones, and audit readiness.

### Research track
Focuses on literature, methods, datasets, experimental results, insights, and hypotheses.

Both tracks share evidence and provenance, but they must not mix authority: an administrative report can cite a scientific insight only if its status is approved or clearly marked as draft/hypothesis.
