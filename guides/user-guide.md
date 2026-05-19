# K-ResDev 사용자 가이드

이 문서는 처음 쓰는 사람을 위한 한글 진입 문서다.

K-ResDev는 국책 R&D 과제에서 반복되는 행정 문서화, 증빙 정리, 보고서 점검, 연구 자료 정리를 GPT/Codex 에이전트가 evidence-first 방식으로 돕기 위한 스킬이다.

## 가장 먼저 알아야 할 것

K-ResDev는 자동 제출기가 아니다.

```text
원본 자료
-> evidence
-> 검토용 projection
-> 사람 승인
```

이 순서를 지킨다.

## 폴더 구조

기본 워크스페이스는 이렇게 생긴다.

```text
inbox/                 원본 자료를 넣는 곳
references/            논문, bibliography, 참고자료
state/                 evidence index, 검토 상태, 승인 기록
state/approvals/       사람 승인/검토 기록
evidence/              추출된 evidence item
reports/               보고서/점검/대시보드 projection
reports/analysis/      데이터 분석 결과와 replay script
```

원본 자료는 `inbox/`와 `references/`에 둔다. K-ResDev는 원본을 수정하지 않는 것을 원칙으로 한다.

## 10분 시작 흐름

### 1. 설치

```powershell
python -m pip install -e .
```

### 2. 워크스페이스 초기화

```powershell
python -m k_resdev_skill init-workspace --root . --project-id "PRJ-2026-0001" --title "Demo R&D Project"
```

### 3. 원본 넣기

예:

```text
inbox/plan.docx
inbox/monthly-progress.md
inbox/experiment-results.csv
inbox/budget-ledger.xlsx
references/library.bib
```

### 4. evidence intake

```powershell
python -m k_resdev_skill intake --inbox .\inbox --state-dir .\state --evidence-dir .\evidence
```

### 5. 상태 진단

```powershell
python -m k_resdev_skill doctor --root . --output .\reports\readiness.md --json .\state\readiness.json
python -m k_resdev_skill next-actions --root . --output .\reports\next-actions.md --json .\state\next-actions.json
```

### 6. 결과 읽기

먼저 볼 파일:

```text
reports/readiness.md
reports/next-actions.md
state/evidence-index.json
reports/workspace-summary.md
```

## 자주 쓰는 상황

### 월간보고서 제출 전

```powershell
python -m k_resdev_skill report-integrity --root . --output .\reports\report-integrity.md --json .\state\report-integrity.json
python -m k_resdev_skill approval-coverage --root . --output .\reports\approval-coverage.md --json .\state\approval-coverage.json
```

확인할 것:
- evidence 없는 수치
- KPI 목표와 다른 claim
- 승인 없는 report/export
- rejected 또는 needs_review evidence를 인용한 문장

### 정산/증빙 점검

```powershell
python -m k_resdev_skill budget-ledger-integrity --root . --output .\reports\budget-ledger.md --json .\state\budget-ledger-integrity.json
python -m k_resdev_skill settlement-binder --root . --output .\reports\settlement-binder.md --json .\state\settlement-binder.json
```

확인할 것:
- proof type 누락
- approval reference 누락
- evidence ID 연결 누락
- source hash drift

### 논문/서지 정리

```powershell
python -m k_resdev_skill bib-import .\references\library.bib --state-dir .\state --literature-matrix .\reports\literature-review-matrix.md
python -m k_resdev_skill citation-support-integrity --root . --output .\reports\citation-support.md --json .\state\citation-support.json
```

주의:
- bibliography metadata는 제공된 값만 사용한다.
- citation이 claim을 support하는지는 사람 검토 기록이 필요하다.

### 전체 상태를 한 번에 묶기

```powershell
python -m k_resdev_skill workspace-review-pack --root .
python -m k_resdev_skill verify-review-pack .\state\workspace-review-pack.json
```

review pack은 내부 검토용 bundle이다. 공식 제출물이 아니다.

## GPT/Codex에게 요청하는 예시

```text
K-ResDev 스킬로 이 워크스페이스를 점검해줘.
보고서 제출 전 evidence 누락, 승인 누락, KPI mismatch, source drift를 먼저 봐줘.
```

```text
K-ResDev Admin Evidence Mode로 예산/정산 증빙 상태를 정리해줘.
적격 판정은 하지 말고 누락/불일치/사람 검토 필요 항목만 보여줘.
```

```text
K-ResDev Research Assistant Mode로 references/library.bib와 실험 결과 CSV를 정리해줘.
논문 claim과 데이터 insight는 hypothesis/candidate로만 표시해줘.
```

## 결과 해석법

K-ResDev 결과는 보통 네 종류다.

```text
Evidence-backed fact
AI interpretation
Missing evidence
Human decision required
```

`ready`라고 해도 공식 제출 가능하다는 뜻이 아니다. local artifact 기준으로 큰 blocker가 없다는 뜻에 가깝다.

## 안전 수칙

- 공식 제출 전에는 반드시 사람이 최종 검토한다.
- 기관별 규칙은 최신 공식 출처로 다시 확인한다.
- AI가 만든 문장은 보고서 문체 초안일 뿐이다.
- 연구 insight는 결론이 아니라 검증 후보로 본다.
- 정산/예산 결과는 적격 판정이 아니라 검토 후보다.
