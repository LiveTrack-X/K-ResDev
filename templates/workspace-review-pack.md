# K-ResDev Workspace Review Pack

> Review pack projection only. It bundles local readiness, next-action, summary, source-verification, approval-coverage, and report-integrity artifacts; it does not certify official agency compliance.

| Field | Value |
|---|---|
| Root | `{{root}}` |
| Status | `{{status}}` |
| Evidence count | `{{evidence_count}}` |
| Approval count | `{{approval_count}}` |
| Finding count | `{{finding_count}}` |
| Action count | `{{action_count}}` |
| Source verification valid | `{{source_verification_valid}}` |
| Source missing count | `{{source_missing_count}}` |
| Source mismatch count | `{{source_mismatch_count}}` |
| Approval coverage status | `{{approval_coverage_status}}` |
| Approval missing count | `{{approval_missing_count}}` |
| Approval not approved count | `{{approval_not_approved_count}}` |
| Report integrity status | `{{report_integrity_status}}` |
| Report integrity finding count | `{{report_integrity_finding_count}}` |
| Report integrity high count | `{{report_integrity_high_count}}` |

## Generated Artifacts

| Artifact | Path |
|---|---|
| Readiness report | `reports/readiness.md` |
| Next actions | `reports/next-actions.md` |
| Workspace summary | `reports/workspace-summary.md` |
| Evidence source verification | `reports/source-verification.md` |
| Approval coverage | `reports/approval-coverage.md` |
| Report integrity | `reports/report-integrity.md` |
| Review pack index | `reports/workspace-review-pack.md` |

## Manifest

- Review-pack JSON stores SHA-256 hashes for generated review artifacts.
- The manifest JSON is not self-hashed.
- Run `python -m k_resdev_skill verify-review-pack state/workspace-review-pack.json` before relying on a saved pack.

Use `python -m k_resdev_skill workspace-review-pack --root <workspace>` to generate a concrete local pack.
