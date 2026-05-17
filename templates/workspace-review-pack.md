# K-ResDev Workspace Review Pack

> Review pack projection only. It bundles local readiness, next-action, summary, and source-verification artifacts; it does not certify official agency compliance.

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

## Generated Artifacts

| Artifact | Path |
|---|---|
| Readiness report | `reports/readiness.md` |
| Next actions | `reports/next-actions.md` |
| Workspace summary | `reports/workspace-summary.md` |
| Evidence source verification | `reports/source-verification.md` |
| Review pack index | `reports/workspace-review-pack.md` |

## Manifest

- Review-pack JSON stores SHA-256 hashes for generated review artifacts.
- The manifest JSON is not self-hashed.
- Run `python -m k_resdev_skill verify-review-pack state/workspace-review-pack.json` before relying on a saved pack.

Use `python -m k_resdev_skill workspace-review-pack --root <workspace>` to generate a concrete local pack.
