# Intake Rules

## File categories

| Category | Examples | Extract |
|---|---|---|
| plan | RFP, project plan, agreement | goals, KPIs, milestones, obligations |
| progress | meeting notes, weekly/monthly notes | decisions, action items, risks |
| experiment | logs, result tables, notebooks | metrics, conditions, baselines, datasets |
| budget | receipts, invoices, estimates | amount, category, date, vendor, evidence status |
| outcome | papers, patents, SW, prototypes | outcome type, submission status, KPI link |
| change | change request, approval mail | before/after, reason, impact, approval evidence |
| literature | papers, abstracts, reviews | claims, methods, datasets, metrics, limitations |
| data | CSV/XLSX/JSONL | schema, row count, missing values, metric candidates |

## Intake steps

1. Register source file metadata.
2. Classify document type.
3. Extract candidate evidence.
4. Link evidence to project plan fields when possible.
5. Mark unsupported or ambiguous items as `needs_review`.
6. Never overwrite the raw source.
7. Never create a final report from raw text alone; use evidence items.
