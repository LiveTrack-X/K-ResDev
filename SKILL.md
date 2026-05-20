---
name: k-resdev
description: GPT/Codex agent skill for evidence-first Korean national R&D administration. Use when an agent helps with Korean R&D evidence intake, KPI/report/budget/admin readiness, audit preparation, literature or data support, or K-ResDev workspace review. Treat the Python package as an optional verification core, not as the user-facing product.
---

# K-ResDev 에이전트 스킬

## 역할

K-ResDev는 GPT/Codex가 한국형 국책 R&D 업무를 도울 때 쓰는 **에이전트 스킬**이다.

Python 패키지와 CLI는 스킬의 본체가 아니라, 해시/스키마/승인/증빙/보고서 정합성처럼 자유서술로 처리하면 위험한 일을 검증하는 **선택적 검증 코어**다.

## 절대 원칙

1. Evidence가 source of truth다.
2. 보고서, 요약, 대시보드, 연구 narrative는 projection이다.
3. 최종 제출, 승인, 연구 결론은 사람이 결정한다.
4. 원본 파일은 수정하지 않는다.
5. 인용, 지표, 승인, 예산 적격성, 기관 규칙을 지어내지 않는다.
6. 기관 profile과 공식 시스템 매핑은 최신 출처와 사람 검토가 없으면 `needs_review`다.
7. 로컬 명령은 판단을 대체하지 않고, 검증과 누락 탐지에만 쓴다.

## 기본 진행 루프

```text
요청 이해
-> 모드 선택
-> 로컬 artifact 확인
-> evidence / projection / risk 분리
-> 필요할 때만 검증 코어 실행
-> 누락 증빙, 위험, 사람 결정 필요 사항 보고
```

생성물은 공식 제출물이 아니다. 항상 evidence-backed fact, AI interpretation, hypothesis, missing evidence, human decision required를 분리한다.

## 모드

### Admin Evidence Mode

대상:
- 계획서, KPI, milestone, 보고서
- 예산, 정산, 증빙, 승인
- 감사 대응, 마감, 변경 이력

행동:
- 먼저 evidence와 approval 상태를 확인한다.
- claim은 evidence ID에 연결하거나 `needs_evidence`로 표시한다.
- workspace가 있으면 doctor, next-actions, report-integrity, approval-coverage, budget-ledger, settlement-binder, admin-obligations를 우선 검토한다.
- IRIS/NTIS/RCMS/Ezbaro 규칙은 Python 코드에 하드코딩하지 않고 profile data와 사람 검토 기록으로만 다룬다.

### Research Assistant Mode

대상:
- 논문 카드, bibliography, literature matrix
- 데이터 profiling, 실험 결과 비교
- research claim, hypothesis candidate

행동:
- 제공된 서지 metadata만 보존한다.
- 누락된 DOI, 저자, 연도, venue를 invent하지 않는다.
- insight는 `hypothesis`, `candidate`, `needs_review`로 둔다.
- 데이터 분석은 재현 가능한 script/manifest와 가정을 남긴다.

### Integrity Mode

대상:
- unsupported claim
- 수치/지표 불일치
- approval/source/profile hash drift
- citation-support gap
- reviewed-seed drift

행동:
- evidence ID가 있어도 값, 상태, 승인, 해시가 맞는지 확인한다.
- finding과 repair action을 만들되, 공식 compliance 인증처럼 말하지 않는다.

## 대표 워크플로 5개

### 1. 워크스페이스 시작/진단

```powershell
python -m k_resdev_skill init-workspace --root . --project-id "<project-id>" --title "<project-title>"
python -m k_resdev_skill intake --inbox .\inbox --state-dir .\state --evidence-dir .\evidence
python -m k_resdev_skill doctor --root . --output .\reports\readiness.md --json .\state\readiness.json
python -m k_resdev_skill next-actions --root . --output .\reports\next-actions.md --json .\state\next-actions.json
```

### 2. 보고서 제출 전 점검

```powershell
python -m k_resdev_skill report-integrity --root . --output .\reports\report-integrity.md --json .\state\report-integrity.json
python -m k_resdev_skill approval-coverage --root . --output .\reports\approval-coverage.md --json .\state\approval-coverage.json
python -m k_resdev_skill verify-evidence-sources .\state\evidence-index.json --root . --output .\reports\source-verification.md --json .\state\source-verification.json
```

### 3. 예산/정산 binder 점검

```powershell
python -m k_resdev_skill budget-ledger-integrity --root . --output .\reports\budget-ledger.md --json .\state\budget-ledger-integrity.json
python -m k_resdev_skill settlement-binder --root . --output .\reports\settlement-binder.md --json .\state\settlement-binder.json
```

### 4. 기관 profile 기반 행정 의무 점검

```powershell
python -m k_resdev_skill profile-review --root . --output .\reports\profile-review.md --json .\state\profile-review.json
python -m k_resdev_skill admin-profile-pack-gate --root . --output .\reports\admin-profile-pack-gate.md --json .\state\admin-profile-pack-gate.json
python -m k_resdev_skill admin-obligations-review --root . --output .\reports\admin-obligations.md --json .\state\admin-obligations-review.json
python -m k_resdev_skill admin-reviewed-seed-drift --root . --output .\reports\admin-reviewed-seed-drift.md --json .\state\admin-reviewed-seed-drift.json
```

### 5. 연구 evidence 지원

```powershell
python -m k_resdev_skill bib-import .\references\library.bib --state-dir .\state --literature-matrix .\reports\literature-review-matrix.md
python -m k_resdev_skill citation-support-integrity --root . --output .\reports\citation-support.md --json .\state\citation-support.json
python -m k_resdev_skill run-analysis .\inbox\metrics.csv --output-dir .\reports\analysis --evidence-id "<evidence-id>"
python -m k_resdev_skill research-claim-matrix --root . --output .\reports\research-claim-matrix.md --json .\state\research-claim-matrix.json
```

## 검증 코어를 쓸 때

다음이면 Python 검증 코어를 쓴다:
- source hash, schema, approval, evidence ID, 수치 claim, budget ledger처럼 재현 가능한 검증이 필요한 경우
- workspace 상태를 진단해야 하는 경우
- 사람이 검토할 artifact를 남겨야 하는 경우

단순 개념 설명이나 기획 대화라면 CLI를 먼저 실행하지 말고 직접 답한다.

## 출력 형식

비교적 큰 작업은 이 순서로 답한다:

```text
Evidence-backed facts
Draft/projection output
Risks and missing evidence
Human decisions required
Suggested next actions
```

## 필요할 때만 읽는 문서

- `guides/user-guide.md`: 처음 쓰는 사람을 위한 한글 진입 문서.
- `guides/documentation-map.md`: 문서가 많을 때 읽는 순서와 역할 지도.
- `guides/capability-map.md`: 현재 할 수 있는 일과 하면 안 되는 말.
- `guides/operations-guide.md`: 운영자/에이전트용 실행 흐름.
- `guides/agent-skill-boundary.md`: 스킬과 검증 코어의 경계.
- `guides/verification-core.md`: 선택적 Python 검증 명령 지도.
- `guides/architecture.md`: evidence-first 구조와 authority layer.
- `guides/intake-rules.md`: 파일 intake 규칙.
- `guides/research-assistant-rules.md`: 논문/데이터/가설 안전 규칙.
- `workflows/mvp-roadmap.md`: 구현 로드맵과 beta 이력.
