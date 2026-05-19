# K-ResDev 운영 가이드

이 문서는 K-ResDev를 운영하는 GPT/Codex 에이전트와 프로젝트 관리자를 위한 문서다.

목표는 기능을 많이 노출하는 것이 아니라, 사용자가 R&D evidence와 행정 상태를 안전하게 판단할 수 있도록 돕는 것이다.

## 운영 원칙

1. 먼저 local artifact를 읽는다.
2. 없는 정보는 없다고 말한다.
3. 공식 규칙은 최신 출처와 사람 검토 없이는 확정하지 않는다.
4. projection과 approval을 분리한다.
5. CLI는 검증용으로만 쓴다.
6. 새 기능보다 진입 흐름과 판단 품질을 우선한다.

문서가 많아서 길을 잃을 때는 `guides/documentation-map.md`를 먼저 본다.

## 에이전트의 기본 순서

```text
1. 사용자 의도 확인
2. 모드 선택
3. workspace 구조 확인
4. evidence / approval / report / profile 상태 확인
5. 필요한 검증 코어 실행
6. 결과를 사람이 판단하기 쉬운 언어로 요약
```

## 모드 선택 기준

### Admin Evidence Mode

사용자가 다음을 말하면 선택한다.

```text
보고서, 계획서, KPI, 정산, 예산, 증빙, 승인, 감사, 마감, 변경신청
```

우선 확인할 artifact:

```text
state/evidence-index.json
state/project-state.json
state/project-profile.json
state/approvals/
reports/readiness.md
reports/report-integrity.md
reports/approval-coverage.md
```

### Research Assistant Mode

사용자가 다음을 말하면 선택한다.

```text
논문, bibliography, citation, literature review, 데이터, 실험 결과, hypothesis
```

우선 확인할 artifact:

```text
references/
state/bibliography-index.json
state/citation-support/
state/research-claims.json
reports/analysis/
```

### Integrity Mode

사용자가 다음을 말하면 선택한다.

```text
점검, 논리 오류, 과장, 근거 없음, 승인 누락, drift, mismatch, 제출 전 확인
```

우선 확인할 artifact:

```text
reports/readiness.md
reports/next-actions.md
reports/source-verification.md
reports/report-integrity.md
reports/workspace-trace.md
```

## 운영자가 자주 실행하는 bundle

### 빠른 상태 확인

```powershell
python -m k_resdev_skill doctor --root . --output .\reports\readiness.md --json .\state\readiness.json
python -m k_resdev_skill next-actions --root . --output .\reports\next-actions.md --json .\state\next-actions.json
python -m k_resdev_skill workspace-summary --root . --output .\reports\workspace-summary.md --json .\state\workspace-summary.json
```

### 제출 전 보고서 점검

```powershell
python -m k_resdev_skill verify-evidence-sources .\state\evidence-index.json --root . --output .\reports\source-verification.md --json .\state\source-verification.json
python -m k_resdev_skill report-integrity --root . --output .\reports\report-integrity.md --json .\state\report-integrity.json
python -m k_resdev_skill approval-coverage --root . --output .\reports\approval-coverage.md --json .\state\approval-coverage.json
```

### 행정 운영 레이어 점검

```powershell
python -m k_resdev_skill admin-obligations-review --root . --output .\reports\admin-obligations.md --json .\state\admin-obligations-review.json
python -m k_resdev_skill settlement-binder --root . --output .\reports\settlement-binder.md --json .\state\settlement-binder.json
python -m k_resdev_skill admin-calendar-review --root . --output .\reports\admin-calendar.md --json .\state\admin-calendar.json
```

### 전체 handoff pack

```powershell
python -m k_resdev_skill workspace-review-pack --root .
python -m k_resdev_skill verify-review-pack .\state\workspace-review-pack.json
```

## 보고 방식

운영 결과는 다음 형태로 요약한다.

```text
현재 상태
근거 있는 항목
위험/누락
사람 결정 필요
다음 action
```

좋은 예:

```text
보고서 초안에는 수치 claim 3개가 있으나 1개는 evidence ID가 없습니다.
APR-2026-0002 승인은 현재 report hash와 맞지 않아 재검토가 필요합니다.
정산 binder는 proof_type이 없는 ledger row 2개를 표시합니다.
```

나쁜 예:

```text
제출 가능합니다.
이 비용은 적격입니다.
이 논문이 해당 claim을 증명합니다.
기관 규정상 반드시 이 양식입니다.
```

## 기능 추가 기준

새 기능은 다음 중 하나를 개선해야 한다.

- agent가 어떤 workflow를 선택해야 하는지 더 명확해진다.
- evidence/projection/approval 경계가 더 안전해진다.
- 사람이 볼 next action이 더 줄어들거나 명확해진다.
- 반복 검증이 deterministic하게 바뀐다.

단순히 CLI 출력 파일이 하나 더 생기는 기능은 우선순위가 낮다.

## 문서 정리 기준

문서를 고칠 때는 다음 역할을 유지한다.

- `README.md`: 처음 보는 사람이 K-ResDev의 정체성과 첫 실행을 이해한다.
- `SKILL.md`: GPT/Codex 에이전트가 작업 중 따르는 짧은 운영 계약이다.
- `guides/user-guide.md`: 사용자 입장에서 실제 워크스페이스를 시작한다.
- `guides/operations-guide.md`: 반복 운영과 점검 bundle을 안내한다.
- `guides/verification-core.md`: CLI 명령 목록을 모아 둔다.
- `workflows/`: 구현 이력과 계획을 분리해서 기록한다.
- `templates/`: 공식 양식이 아니라 projection 예시임을 드러낸다.

README에 명령을 계속 추가하기보다, 상세 명령은 `guides/verification-core.md`로 보낸다.

## Release 전 확인

```powershell
python -m pytest
python -m compileall src
python quick_validate.py
python -m k_resdev_skill --version
```

문서-only 변경이라도 `SKILL.md`, `README.md`, `guides/user-guide.md`, `guides/operations-guide.md`의 역할이 겹치지 않는지 확인한다.
