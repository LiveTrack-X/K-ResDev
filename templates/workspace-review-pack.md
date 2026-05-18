# K-ResDev Workspace Review Pack

> Review pack projection only. It bundles local readiness, next-action, summary, source-verification, budget-ledger, approval-coverage, report-integrity, bibliography-integrity, reference-corpus, citation-support, research-claim-matrix, trace-passport, profile-integrity, and trace artifacts; it does not certify official agency compliance.

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
| Approval hash mismatch count | `{{approval_hash_mismatch_count}}` |
| Approval hash unverified count | `{{approval_hash_unverified_count}}` |
| Report integrity status | `{{report_integrity_status}}` |
| Report integrity finding count | `{{report_integrity_finding_count}}` |
| Report integrity high count | `{{report_integrity_high_count}}` |
| Budget ledger status | `{{budget_ledger_status}}` |
| Budget ledger count | `{{budget_ledger_count}}` |
| Budget ledger finding count | `{{budget_ledger_finding_count}}` |
| Budget ledger high count | `{{budget_ledger_high_count}}` |
| Bibliography integrity status | `{{bibliography_integrity_status}}` |
| Bibliography entry count | `{{bibliography_entry_count}}` |
| Bibliography review count | `{{bibliography_review_count}}` |
| Bibliography citation count | `{{bibliography_citation_count}}` |
| Bibliography integrity finding count | `{{bibliography_integrity_finding_count}}` |
| Bibliography integrity high count | `{{bibliography_integrity_high_count}}` |
| Reference corpus status | `{{reference_corpus_status}}` |
| Reference corpus count | `{{reference_corpus_count}}` |
| Reference rejection count | `{{reference_rejection_count}}` |
| Reference corpus high count | `{{reference_corpus_high_count}}` |
| Citation support status | `{{citation_support_status}}` |
| Citation support records | `{{citation_support_count}}` |
| Citation support citation count | `{{citation_support_citation_count}}` |
| Citation support finding count | `{{citation_support_finding_count}}` |
| Citation support high count | `{{citation_support_high_count}}` |
| Research claim matrix status | `{{research_claim_matrix_status}}` |
| Research claim count | `{{research_claim_count}}` |
| Research claim matrix finding count | `{{research_claim_matrix_finding_count}}` |
| Research claim matrix high count | `{{research_claim_matrix_high_count}}` |
| Profile integrity status | `{{profile_integrity_status}}` |
| Profile source count | `{{profile_source_count}}` |
| Profile verified source count | `{{profile_verified_source_count}}` |
| Profile integrity finding count | `{{profile_integrity_finding_count}}` |
| Profile integrity high count | `{{profile_integrity_high_count}}` |
| Workspace trace status | `{{workspace_trace_status}}` |
| Workspace trace finding count | `{{workspace_trace_finding_count}}` |
| Trace passport status | `{{trace_passport_status}}` |
| Checkpoint count | `{{checkpoint_count}}` |
| Latest checkpoint | `{{latest_checkpoint_id}}` |
| Trace passport finding count | `{{trace_passport_finding_count}}` |
| Trace passport high count | `{{trace_passport_high_count}}` |

## Generated Artifacts

| Artifact | Path |
|---|---|
| Readiness report | `reports/readiness.md` |
| Next actions | `reports/next-actions.md` |
| Workspace summary | `reports/workspace-summary.md` |
| Evidence source verification | `reports/source-verification.md` |
| Approval coverage | `reports/approval-coverage.md` |
| Report integrity | `reports/report-integrity.md` |
| Budget ledger integrity | `reports/budget-ledger.md` |
| Bibliography integrity | `reports/bibliography-integrity.md` |
| Reference corpus summary | `reports/reference-corpus-summary.md` |
| Citation support | `reports/citation-support.md` |
| Research claim matrix | `reports/research-claim-matrix.md` |
| Profile integrity | `reports/profile-integrity.md` |
| Workspace trace | `reports/workspace-trace.md` |
| Trace passport | `reports/trace-passport.md` |
| Review pack index | `reports/workspace-review-pack.md` |

## Manifest

- Review-pack JSON stores SHA-256 hashes for generated review artifacts.
- The manifest JSON is not self-hashed.
- Run `python -m k_resdev_skill verify-review-pack state/workspace-review-pack.json` before relying on a saved pack.

Use `python -m k_resdev_skill workspace-review-pack --root <workspace>` to generate a concrete local pack.
