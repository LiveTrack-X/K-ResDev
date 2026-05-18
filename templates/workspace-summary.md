# K-ResDev Workspace Summary

> Operational projection only. This does not certify official agency compliance, submission readiness, or scientific validity.

## Status

| Field | Value |
|---|---|
| Root | `{{root}}` |
| Readiness status | `{{status}}` |
| Profile | `{{profile_id}}` |
| Profile integrity | `{{profile_integrity_status}}` |
| Profile sources | `{{profile_source_count}}` |
| Verified profile sources | `{{profile_verified_source_count}}` |
| Workspace discovery | `{{discovery_status}}` |
| Discovery loose candidates | `{{discovery_loose_candidate_count}}` |
| Budget ledger | `{{budget_ledger_status}}` |
| Budget ledger rows | `{{budget_ledger_count}}` |
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
| Workspace discovery | `{{discovery_scanned_count}}` | missing dirs: `{{discovery_missing_standard_dir_count}}`; proposals: `{{discovery_setup_proposal_count}}` |
| Budget ledger | `{{budget_ledger_count}}` | `{{budget_total_by_currency}}` |
| Profile integrity | `{{profile_integrity_finding_count}}` | `{{profile_integrity_status}}` |
| Workspace trace | `{{trace_node_count}}` | `{{trace_status}}` |

Use `python -m k_resdev_skill workspace-summary` to generate a concrete local summary.
