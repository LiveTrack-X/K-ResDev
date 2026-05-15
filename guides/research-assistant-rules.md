# Research Assistant Rules

## Purpose

Support research work itself, not only administration.

Supported tasks:
- literature review and paper comparison
- dataset profiling
- experimental result interpretation
- hypothesis generation
- method comparison
- failure analysis
- reproducibility planning
- figure/table draft planning

## Scientific integrity rules

1. Separate author claim from verified fact.
2. Do not overstate preliminary results.
3. Record baseline, dataset, metric, and statistical assumptions.
4. Any generated hypothesis must include verification steps.
5. For data insights, provide reproducible analysis code or pseudo-code.
6. For paper summaries, preserve citation metadata and uncertainty.
7. If a result is below target, state it plainly and propose follow-up checks.

## Insight object structure

```json
{
  "insight_id": "INS-YYYY-0001",
  "claim": "Model A underperforms on small-lesion cases",
  "basis": ["EVI-2026-0012", "DATA-2026-0003"],
  "confidence": "medium",
  "assumptions": ["validation labels are stable", "case split is unchanged"],
  "risk_flags": ["small_sample", "needs_statistical_test"],
  "next_checks": ["stratified Dice by lesion size", "bootstrap CI"]
}
```
