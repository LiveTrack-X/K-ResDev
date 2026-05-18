# K-ResDev Reference Corpus Summary

> Reference corpus projection only. This imports local metadata and short user notes for review; it does not verify paper relevance, citation correctness, or claim support.

| Field | Value |
|---|---|
| Root | `{{root}}` |
| References dir | `{{references_dir}}` |
| Status | `{{status}}` |
| Corpus items | `{{item_count}}` |
| Rejection log entries | `{{rejection_count}}` |

Use `python -m k_resdev_skill reference-corpus --root <workspace> --output reports/reference-corpus-summary.md --json state/literature-corpus.json --rejections state/reference-rejection-log.json` to generate a concrete local summary.
