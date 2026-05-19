# K-ResDev Agent Skill Pack

현재 릴리스: `0.1 BETA 59` (`0.1.0b59`)

K-ResDev는 GPT/Codex가 한국형 국책 R&D 업무를 도울 때 쓰는 **에이전트 스킬 팩**입니다.

핵심은 프로그램이 아니라 스킬입니다. Python 패키지와 CLI는 스킬이 더 안전하게 일하기 위한 **선택적 검증 코어**입니다.

## 한 줄 정의

```text
연구 활동과 행정 자료
-> evidence graph
-> 보고서/정산/감사/연구 projection
-> 사람 검토와 승인
```

## 원칙

```text
Evidence is source of truth.
Reports are projections.
Human approval is final authority.
```

K-ResDev는 보고서를 자동으로 확정하지 않습니다. 근거, 누락, 위험, 사람 결정이 필요한 지점을 드러내는 도구입니다.

## 무엇을 도와주나

### 1. 연구 행정

- 계획서, KPI, milestone 정리
- 월간/중간/최종 보고서 초안 점검
- 예산/정산 증빙 binder 점검
- 승인 누락, source hash drift, report overclaim 탐지
- 감사 대응용 evidence bundle과 Q&A 초안

### 2. 연구 보조

- 논문 카드와 literature matrix
- BibTeX/RIS/CSL JSON/Zotero export 기반 bibliography intake
- citation-support 기록 점검
- CSV/XLSX 데이터 profiling
- 실험 결과 비교와 hypothesis candidate 정리

### 3. Integrity / 운영 점검

- unsupported numeric claim
- KPI mismatch
- below-target overclaim
- approval coverage
- source/profile/reviewed-seed drift
- workspace doctor / next actions / review pack

## 무엇이 아닌가

- 공식 IRIS/NTIS/RCMS/Ezbaro 규칙 엔진이 아닙니다.
- 기관 제출물을 최종 확정하는 시스템이 아닙니다.
- 연구비 적격/부적격을 판정하지 않습니다.
- 논문 인용, 지표, 승인, 기관 규칙을 만들어내지 않습니다.
- 연구자나 과제 책임자의 최종 판단을 대체하지 않습니다.

## 구조

```text
SKILL.md
  GPT/Codex가 읽는 에이전트 스킬 진입점

guides/user-guide.md
  처음 쓰는 사람을 위한 한글 진입 문서와 사용 가이드

guides/documentation-map.md
  전체 문서 읽는 순서와 역할 지도

guides/operations-guide.md
  운영자/에이전트용 실행 흐름

guides/agent-skill-boundary.md
  스킬과 검증 코어의 경계

guides/verification-core.md
  Python CLI 검증 명령 지도

src/k_resdev_skill/
  선택적 검증 코어

schemas/
  로컬 artifact JSON schema

templates/
  starter artifact와 기관 profile 후보
```

## 문서 읽는 순서

처음부터 모든 문서를 읽을 필요는 없습니다.

```text
처음 쓰는 사용자
README.md -> guides/user-guide.md -> guides/verification-core.md

GPT/Codex 에이전트
SKILL.md -> guides/operations-guide.md -> guides/documentation-map.md

개발자
guides/agent-skill-boundary.md -> workflows/mvp-roadmap.md -> workflows/next-planning.md
```

문서가 많아 보이면 `guides/documentation-map.md`부터 보면 됩니다.

## 빠른 시작

### 1. 설치와 검증

```powershell
python -m pip install -e .
python -m k_resdev_skill --version
```

### 2. 워크스페이스 만들기

```powershell
python -m k_resdev_skill init-workspace --root . --project-id "PRJ-2026-0001" --title "Demo R&D Project"
```

생성되는 기본 구조:

```text
inbox/
state/
evidence/
references/
reports/
reports/analysis/
state/approvals/
```

### 3. 자료 넣기

원본 자료는 `inbox/`에 둡니다.

예:

```text
inbox/plan.docx
inbox/monthly-meeting.md
inbox/experiment-results.csv
inbox/budget-ledger.xlsx
references/library.bib
```

원본은 수정하지 않는 것이 원칙입니다.

### 4. Evidence intake

```powershell
python -m k_resdev_skill intake --inbox .\inbox --state-dir .\state --evidence-dir .\evidence
```

### 5. 현재 상태 진단

```powershell
python -m k_resdev_skill doctor --root . --output .\reports\readiness.md --json .\state\readiness.json
python -m k_resdev_skill next-actions --root . --output .\reports\next-actions.md --json .\state\next-actions.json
```

### 6. 전체 검토 pack 생성

```powershell
python -m k_resdev_skill workspace-review-pack --root .
python -m k_resdev_skill verify-review-pack .\state\workspace-review-pack.json
```

## GPT/Codex에서 쓰는 방식

에이전트에게 이렇게 말하면 됩니다.

```text
K-ResDev 스킬로 이 R&D 워크스페이스를 점검해줘.
먼저 evidence 상태, 보고서 위험, 승인 누락, 예산/정산 증빙 상태를 보고
사람이 결정해야 하는 항목과 다음 action을 정리해줘.
```

또는:

```text
K-ResDev Admin Evidence Mode로 월간보고서 제출 전 점검을 해줘.
근거 없는 수치, KPI mismatch, 승인 누락, source drift를 먼저 봐줘.
```

## 대표 워크플로

자세한 명령은 `guides/verification-core.md`에 있습니다.

1. 워크스페이스 시작/진단
2. 보고서 제출 전 점검
3. 예산/정산 binder 점검
4. 기관 profile 기반 행정 의무 점검
5. 논문/데이터/연구 claim 지원

## 안전 경계

- `reports/*.md`는 초안 또는 운영 projection입니다.
- `state/approvals/*.json`이 있어도 승인 범위와 hash drift를 다시 확인해야 합니다.
- `templates/agencies/*`는 공식 규칙이 아니라 profile 후보입니다.
- reviewed-seed admin obligation은 local `accepted_risk` 후보입니다.
- 연구 insight는 hypothesis/candidate이며 최종 결론이 아닙니다.

## 개발자용 검증

```powershell
python -m pytest
python -m compileall src
python quick_validate.py
```

새 기능을 추가하기 전에는 먼저 묻습니다.

```text
이 기능이 GPT/Codex 에이전트를 더 안전하고 명확하고 유용하게 만드는가?
```

그 답이 아니라 단순히 CLI 보고서 하나를 더 늘리는 것이라면 보류합니다.
