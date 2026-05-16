# K-ResDev Skill

Purpose: 한국형 국책 R&D 환경에서 연구 행정 문서화, 증빙 정합성, 보고서 생성, 논문/데이터 인사이트 보조를 evidence-first 방식으로 지원하는 Codex/Skill 프로젝트입니다.

Current release: `0.1 BETA 4` (`0.1.0b4`).

Core principle:

```text
Evidence is source of truth.
Reports, summaries, and research narratives are projections.
AI may draft and check, but human approval is required for submission or scientific claims.
```

Primary modes:

1. Admin Evidence Mode: 계획서, KPI, 예산, 증빙, 보고서, 정산, 감사 대응.
2. Research Assistant Mode: 논문 요약, 선행연구 맵, 데이터 분석, hypothesis generation, 실험 설계 보조.
3. Integrity Mode: 주장-근거 연결, 수치 검증, 과장 탐지, 재현성 체크, 누락 증빙 탐지.

This repository does not encode any single ministry/institution form as authoritative. Agency-specific templates should be added under `templates/agencies/` only after verification.

## Current implementation

- Pydantic models for evidence, project state, KPI, milestone, and research insights.
- Rule-based file classifier for plan/progress/experiment/budget/outcome/change/literature/data/unknown.
- CSV/XLSX data profiler with missingness, numeric summaries, and metric detection.
- Evidence index writer for `state/evidence-index.md` and `state/evidence-index.json`.
- Unsupported claim checker for numeric claims, superlatives, missing evidence IDs, KPI mismatch, and below-target overclaims.
- Literature review matrix writer.
- End-to-end intake pipeline that writes `state/raw-registry.json`, `evidence/*.json`, `state/evidence-index.*`, and `state/open-issues.md`.
- Stable source/evidence IDs derived from source hash plus inbox-relative path, so adding another file does not renumber existing evidence.
- Intake excludes its own `state/` and `evidence/` output folders when they are placed inside the inbox.
- Document text extraction for TXT/MD/CSV/JSON/LOG, DOCX, XLSX, HWPX, PDF, and optional HWP via `rhwp` CLI when installed.
- Draft monthly report writer plus claim-review sidecar.
- Draft audit-defense Q&A writer from evidence metadata.
- Conservative plan mapper for KPI/milestone draft extraction from text.
- Numeric evidence-mismatch detection when a report cites an evidence ID but uses unsupported numbers.
- Paper card extraction from supplied metadata text without citation invention.
- Data insight candidate reports that keep findings in hypothesis/review state.
- Experiment comparison table and reproducibility checklist generators.
- Hypothesis-to-experiment planner for turning `ResearchInsight` records into reviewable validation plans.
- Generic budget evidence completeness checklist that avoids hardcoding unverified agency rules.
- Agency profile registry/validator for `templates/agencies/` skeletons.
- `national-rnd-basic` agency template skeleton for annual/interim/final reports, change requests, and performance registration drafts.

## Local use

```powershell
python -m pip install -e .
python -m pytest
python -m k_resdev_skill intake --inbox .\inbox --project my-rnd-project
python -m k_resdev_skill map-plan .\inbox\plan.txt --output .\state\project-state.json
python -m k_resdev_skill draft-report .\state\evidence-index.json --project-state .\state\project-state.json --period 2026-05
python -m k_resdev_skill audit-qna .\state\evidence-index.json
python -m k_resdev_skill paper-card .\inbox\paper-notes.txt --markdown --output .\reports\paper-card.md
python -m k_resdev_skill data-insights .\inbox\metrics.csv --output .\reports\data-insights.md
python -m k_resdev_skill plan-experiment .\state\research-insights.json --evidence-index .\state\evidence-index.json --output .\reports\experiment-plan.md
python -m k_resdev_skill experiment-table .\state\evidence-index.json --output .\reports\experiment-table.md
python -m k_resdev_skill repro-check .\state\evidence-index.json --output .\reports\repro-check.md
python -m k_resdev_skill budget-check .\state\evidence-index.json --output .\reports\budget-checklist.md
python -m k_resdev_skill profiles --markdown --output .\reports\agency-profiles.md
python -m k_resdev_skill validate-profile .\templates\agencies\national-rnd-basic\project-profile.json
python -m k_resdev_skill classify .\inbox\plan.pdf --text "연구개발계획서 KPI"
python -m k_resdev_skill profile .\inbox\metrics.csv
```

The package name is `k_resdev_skill`; the Codex skill name is `k-resdev`.

For binary `.hwp` intake, install an `rhwp` CLI separately. K-ResDev treats it as an optional adapter and marks HWP extraction as `needs_review` when the CLI is unavailable.
