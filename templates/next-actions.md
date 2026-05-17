# K-ResDev Next Actions

> Action plan projection only. Review commands before running and keep official submissions human-approved.

- Root: `{{root}}`
- Status: `{{status}}`
- Action count: `{{action_count}}`

| Priority | Action | Rationale | Command | Related Findings |
|---|---|---|---|---|
| high | Initialize the workspace skeleton | Standard K-ResDev folders are missing; initialize them before intake or report generation. | `python -m k_resdev_skill init-workspace ...` | profile_missing |
| high | Build or regenerate the evidence index | Evidence metadata is required before reports, bundles, and claim checks are meaningful. | `python -m k_resdev_skill intake ...` | missing_evidence_index |

Use this template shape for action-plan exports from `python -m k_resdev_skill next-actions`.
