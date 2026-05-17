# Evidence Source Verification

> Local source-hash verification only. This checks whether indexed source files are present and unchanged; it does not validate official compliance or scientific truth.

| Field | Value |
|---|---|
| Evidence index | `{{evidence_index_path}}` |
| Root | `{{root}}` |
| Inbox | `{{inbox}}` |
| Valid | `{{valid}}` |
| Source count | `{{source_count}}` |
| OK | `{{ok_count}}` |
| Missing | `{{missing_count}}` |
| Mismatch | `{{mismatch_count}}` |
| No expected hash | `{{no_hash_count}}` |

Use `python -m k_resdev_skill verify-evidence-sources state/evidence-index.json --root <workspace>` to generate a concrete local verification report.
