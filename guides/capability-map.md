# K-ResDev가 지금 할 수 있는 일

이 문서는 현재 K-ResDev를 처음 보는 사용자가 “그래서 지금 뭘 맡길 수 있나?”를 빠르게 판단하기 위한 목록이다.

핵심 전제는 변하지 않는다.

```text
K-ResDev = GPT/Codex 에이전트 스킬
Python CLI = 선택적 검증 코어
```

따라서 아래 기능은 공식 제출, 적격 판정, 연구 결론 확정이 아니라 **검토 가능한 evidence/projection/위험 신호를 만드는 일**이다.

## 1. 워크스페이스 시작과 진단

할 수 있는 일:

- 표준 K-ResDev 폴더 구조를 만든다.
- `inbox/`, `references/`, `state/`, `evidence/`, `reports/` 흐름을 잡는다.
- 현재 workspace가 준비됐는지 doctor로 점검한다.
- 다음 action을 우선순위로 정리한다.
- 전체 review pack을 만들고 hash를 검증한다.

대표 명령:

```powershell
python -m k_resdev_skill init-workspace --root . --project-id "PRJ-2026-0001" --title "Demo R&D Project"
python -m k_resdev_skill doctor --root .
python -m k_resdev_skill next-actions --root .
python -m k_resdev_skill workspace-review-pack --root .
python -m k_resdev_skill verify-review-pack .\state\workspace-review-pack.json
```

## 2. Evidence intake와 원본 추적

할 수 있는 일:

- 원본 파일을 분류한다.
- evidence candidate를 만든다.
- source hash를 저장해 원본 drift를 찾는다.
- evidence index를 Markdown/JSON으로 만든다.
- 계획서 텍스트에서 KPI/milestone 후보를 뽑는다.

지원하는 주요 방향:

```text
plan / progress / experiment / budget / outcome / change / literature / data / unknown
```

대표 명령:

```powershell
python -m k_resdev_skill classify .\inbox\plan.docx
python -m k_resdev_skill intake --inbox .\inbox --state-dir .\state --evidence-dir .\evidence
python -m k_resdev_skill verify-evidence-sources .\state\evidence-index.json --root .
python -m k_resdev_skill map-plan .\inbox\plan.txt --output .\state\project-state.json
```

주의:

- 원본 파일은 수정하지 않는다.
- 불확실한 추출 결과는 `needs_review`로 둔다.

## 3. 보고서와 claim 점검

할 수 있는 일:

- evidence 없는 수치 claim을 찾는다.
- 과장 표현, KPI mismatch, below-target overclaim을 찾는다.
- 월간보고서 draft를 만든다.
- 보고서 artifact가 승인 record로 덮여 있는지 확인한다.
- approval target hash drift를 찾는다.

대표 명령:

```powershell
python -m k_resdev_skill check-claims .\reports\monthly.md .\state\evidence-index.json
python -m k_resdev_skill draft-report --state .\state\project-state.json --evidence .\state\evidence-index.json --output .\reports\monthly-draft.md
python -m k_resdev_skill report-integrity --root .
python -m k_resdev_skill approval-coverage --root .
python -m k_resdev_skill approval-gate --root . --target .\reports\monthly-draft.md
```

주의:

- draft report는 공식 제출물이 아니다.
- 승인 record가 있어도 현재 파일 hash와 맞는지 다시 확인한다.

## 4. 예산/정산/증빙 점검

할 수 있는 일:

- budget ledger를 가져온다.
- 금액, 비목, proof type, approval reference, evidence ID 연결을 점검한다.
- settlement binder를 만든다.
- source hash drift와 proof 누락 후보를 찾는다.

대표 명령:

```powershell
python -m k_resdev_skill budget-ledger-import .\inbox\budget-ledger.csv --root .
python -m k_resdev_skill budget-ledger-integrity --root .
python -m k_resdev_skill settlement-binder --root .
python -m k_resdev_skill budget-check .\state\evidence-index.json --output .\reports\budget-check.md
```

주의:

- 연구비 적격/부적격 판정을 하지 않는다.
- 기관별 정산 규칙은 profile과 사람 검토가 필요하다.

## 5. 행정 운영 레이어

할 수 있는 일:

- admin obligation graph를 만든다.
- 제출 후보, 정산 요구 후보, 승인 누락, evidence 연결 누락을 점검한다.
- 협약/변경/승인 ledger를 점검한다.
- admin calendar와 local deadline 상태를 확인한다.
- reviewed-seed drift와 repair action 후보를 정리한다.

대표 명령:

```powershell
python -m k_resdev_skill admin-obligations-init --root .
python -m k_resdev_skill admin-obligations-review --root .
python -m k_resdev_skill admin-change-ledger --root .
python -m k_resdev_skill admin-calendar-review --root .
python -m k_resdev_skill admin-reviewed-seed-drift --root .
```

주의:

- IRIS/NTIS/RCMS/Ezbaro 공식 규칙을 하드코딩하지 않는다.
- 기관 profile은 source-backed 후보이며, 검토 전에는 `needs_review`다.

## 6. 기관 profile과 source review

할 수 있는 일:

- profile template 목록을 본다.
- profile JSON을 검증한다.
- source record를 등록하고 summary를 만든다.
- profile source queue와 fix plan을 만든다.
- human review receipt를 기록한다.
- profile promotion, apply, revoke lifecycle을 hash-bound로 관리한다.
- profile pack readiness/drilldown/investigation package를 만든다.

대표 명령:

```powershell
python -m k_resdev_skill profiles
python -m k_resdev_skill validate-profile .\state\project-profile.json
python -m k_resdev_skill profile-source-queue --root .
python -m k_resdev_skill profile-review --root .
python -m k_resdev_skill profile-pack-readiness --root .
python -m k_resdev_skill profile-lifecycle-ledger --root .
```

주의:

- profile promotion은 local 운영 상태일 뿐 공식 compliance 인증이 아니다.
- 공식 출처가 최신인지 사람 검토가 필요하다.

## 7. 서지/논문/연구 보조

할 수 있는 일:

- BibTeX, RIS, CSL JSON bibliography를 가져온다.
- 논문 카드와 literature matrix를 만든다.
- bibliography metadata review record를 남긴다.
- citation support record를 남기고 integrity를 확인한다.
- research claim matrix를 만든다.

대표 명령:

```powershell
python -m k_resdev_skill bib-import .\references\library.bib --state-dir .\state
python -m k_resdev_skill bib-integrity --root .
python -m k_resdev_skill citation-support-integrity --root .
python -m k_resdev_skill research-claim-matrix --root .
python -m k_resdev_skill paper-card .\references\paper.txt --output .\reports\paper-card.md
```

주의:

- 없는 DOI, venue, year, citation 관계를 만들지 않는다.
- citation이 claim을 support한다는 판단은 supplied human review가 필요하다.

## 8. 데이터/실험/재현성

할 수 있는 일:

- CSV/XLSX data profile을 만든다.
- missingness와 numeric summary를 확인한다.
- metric 후보를 찾는다.
- data insight candidate report를 만든다.
- reproducible analysis script와 manifest를 만든다.
- experiment comparison table과 reproducibility checklist를 만든다.
- hypothesis-to-experiment plan을 만든다.

대표 명령:

```powershell
python -m k_resdev_skill profile .\inbox\metrics.csv
python -m k_resdev_skill data-insights .\inbox\metrics.csv --output .\reports\data-insights.md
python -m k_resdev_skill run-analysis .\inbox\metrics.csv --output-dir .\reports\analysis
python -m k_resdev_skill experiment-table .\state\evidence-index.json --output .\reports\experiment-table.md
python -m k_resdev_skill repro-check .\state\evidence-index.json --output .\reports\repro-check.md
```

주의:

- insight는 hypothesis/candidate다.
- 통계적 유의성, 재현성, 일반화 가능성은 별도 검증이 필요하다.

## 9. 운영 요약과 trace

할 수 있는 일:

- workspace summary를 만든다.
- weekly review와 dashboard를 만든다.
- workflow plan을 만든다.
- workspace traceability graph를 만든다.
- checkpoint를 만들고 resume plan을 만든다.
- artifact authority risk를 점검한다.
- goals/deadlines를 운영 파일로 관리한다.

대표 명령:

```powershell
python -m k_resdev_skill workspace-summary --root .
python -m k_resdev_skill weekly-review --root .
python -m k_resdev_skill workspace-dashboard --root .
python -m k_resdev_skill workspace-trace --root .
python -m k_resdev_skill checkpoint-create --root . --label "before-report-review"
python -m k_resdev_skill checkpoint-resume-plan --root .
```

## 아직 하면 안 되는 말

K-ResDev 결과를 보고 다음처럼 말하면 안 된다.

```text
공식 제출 가능하다.
이 연구비는 적격이다.
이 기관 규정은 확정이다.
이 논문이 claim을 증명한다.
이 실험 결과는 최종 결론이다.
```

대신 이렇게 말한다.

```text
local artifact 기준 blocker가 줄었다.
이 항목은 evidence/approval/source review가 필요하다.
이 결과는 hypothesis candidate다.
공식 제출 전 사람 검토와 최신 기관 양식 확인이 필요하다.
```

## 한 줄 판단

지금 K-ResDev는 단순 scaffold가 아니라, **로컬 evidence-first R&D 운영 점검 스킬**로 사용할 수 있다.

다만 제품처럼 자동 제출하거나 규정을 판정하는 도구가 아니라, GPT/Codex 에이전트가 사용자를 대신해 evidence, risk, approval, next action을 정리하는 보조 레이어다.
