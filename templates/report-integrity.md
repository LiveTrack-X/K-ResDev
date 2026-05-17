# Workspace Report Integrity

> Report integrity projection only. This checks local Markdown report drafts against indexed evidence; it does not certify official compliance, scientific validity, or human approval.

| Field | Value |
|---|---|
| Root | `{{root}}` |
| Status | `{{status}}` |
| Report count | `{{report_count}}` |
| Finding count | `{{finding_count}}` |
| High | `{{high_count}}` |
| Medium | `{{medium_count}}` |
| Low | `{{low_count}}` |

## Findings

| Severity | Code | Report | Claim | Evidence IDs | Suggested Action |
|---|---|---|---|---|---|
| high | unsupported_numeric_claim | `reports/monthly-report-YYYY-MM.md` | Draft claim | - | Attach evidence or mark needs_evidence. |

Use `python -m k_resdev_skill report-integrity --root <workspace>` to generate a concrete local integrity report.
