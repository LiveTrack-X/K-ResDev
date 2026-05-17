# K-ResDev Workspace Summary

> Operational projection only. This does not certify official agency compliance, submission readiness, or scientific validity.

## Status

| Field | Value |
|---|---|
| Root | `{{root}}` |
| Readiness status | `{{status}}` |
| Profile | `{{profile_id}}` |
| Evidence count | `{{evidence_count}}` |
| Approval count | `{{approval_count}}` |
| Action count | `{{action_count}}` |

## Evidence

| Category | Counts |
|---|---|
| By type | `{{evidence_by_type}}` |
| By status | `{{evidence_by_status}}` |
| Risk flags | `{{risk_flag_counts}}` |

## Operations

| Area | Counts | Paths |
|---|---:|---|
| Doctor findings | `{{finding_count}}` | `{{findings_by_severity}}` |
| Next actions | `{{action_count}}` | `{{actions_by_priority}}` |
| Report Markdown | `{{report_count}}` | `{{report_paths}}` |
| Projection exports | `{{export_count}}` | `{{export_paths}}` |
| Analysis manifests | `{{analysis_manifest_count}}` | `{{analysis_manifest_paths}}` |

Use `python -m k_resdev_skill workspace-summary` to generate a concrete local summary.
