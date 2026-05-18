# Profile Source Fix Plan

> Proposal only. This translates local profile-source queue items into reviewable commands and manual steps; it does not fetch official sources, mutate profile packs, or mark sources verified.

## Summary

| Field | Value |
|---|---|
| Status | needs_review |
| Queue path | `state/profile-source-queue.json` |
| Actions | 1 |

## Actions

| Severity | Type | Profile | Source | Issue | Manual Step | Command | Follow-up Commands |
|---|---|---|---|---|---|---|---|
| medium | manual_then_command | national-rnd-basic | PRS-EXAMPLE0001 | profile_source_hash_missing | Hash a local official-source copy or source note if available. | `python -m k_resdev_skill profile-source-record ... --review-status needs_review` | Re-run profile-source-queue, profile-integrity, and profile-review. |
