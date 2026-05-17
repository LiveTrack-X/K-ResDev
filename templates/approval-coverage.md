# Workspace Approval Coverage

> Human decision coverage only. This checks whether local report artifacts are linked to supplied approval records; it does not approve or certify any artifact.

| Field | Value |
|---|---|
| Root | `{{root}}` |
| Status | `{{status}}` |
| Artifact count | `{{artifact_count}}` |
| Approved | `{{approved_count}}` |
| Missing approval | `{{missing_count}}` |
| Not approved | `{{not_approved_count}}` |

## Artifacts

| Artifact | Path | Target ID | Approved | Decision | Approval ID |
|---|---|---|---|---|---|
| report_draft | `reports/monthly-report-YYYY-MM.md` | `monthly-report-YYYY-MM` | false | missing | - |

Use `python -m k_resdev_skill approval-coverage --root <workspace>` to generate a concrete local coverage report.
