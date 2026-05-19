# 선택적 검증 코어 명령 지도

이 문서는 GPT/Codex 에이전트가 deterministic local check가 필요할 때만 읽는다.

CLI는 사용자 경험의 중심이 아니다. 스킬이 위험한 부분을 검증하기 위해 호출하는 보조 레이어다.

## 설치와 기본 확인

```powershell
python -m pip install -e .
python -m k_resdev_skill --version
```

개발 또는 release 전:

```powershell
python -m pytest
python -m compileall src
python quick_validate.py
```

## 워크스페이스 시작

```powershell
python -m k_resdev_skill init-workspace --root . --project-id "<project-id>" --title "<project-title>"
python -m k_resdev_skill doctor --root . --output .\reports\readiness.md --json .\state\readiness.json
python -m k_resdev_skill next-actions --root . --output .\reports\next-actions.md --json .\state\next-actions.json
```

언제 쓰나:
- 새 R&D 폴더를 시작할 때
- 현재 상태를 빠르게 진단할 때
- 무엇부터 해야 할지 정리할 때

## Evidence intake

```powershell
python -m k_resdev_skill intake --inbox .\inbox --state-dir .\state --evidence-dir .\evidence
python -m k_resdev_skill verify-evidence-sources .\state\evidence-index.json --root . --output .\reports\source-verification.md --json .\state\source-verification.json
```

언제 쓰나:
- 원본 파일이 추가/변경됐을 때
- evidence index가 없거나 오래됐을 때
- source hash drift를 확인해야 할 때

## 보고서 readiness

```powershell
python -m k_resdev_skill report-integrity --root . --output .\reports\report-integrity.md --json .\state\report-integrity.json
python -m k_resdev_skill approval-coverage --root . --output .\reports\approval-coverage.md --json .\state\approval-coverage.json
python -m k_resdev_skill workspace-summary --root . --output .\reports\workspace-summary.md --json .\state\workspace-summary.json
```

언제 쓰나:
- 보고서 초안이 evidence와 맞는지 확인할 때
- 승인 record와 draft hash drift를 확인할 때
- 제출 전 review checklist가 필요할 때

## 예산/정산

```powershell
python -m k_resdev_skill budget-ledger-integrity --root . --output .\reports\budget-ledger.md --json .\state\budget-ledger-integrity.json
python -m k_resdev_skill settlement-binder --root . --output .\reports\settlement-binder.md --json .\state\settlement-binder.json
```

언제 쓰나:
- ledger row와 evidence/proof/approval/source hash를 연결할 때
- 증빙 누락, 승인 누락, 금액/출처 불일치 후보를 볼 때

주의:
- 이 명령은 적격/부적격을 판정하지 않는다.
- 공식 판단은 기관 규정과 사람이 한다.

## 기관 profile 기반 행정 의무

```powershell
python -m k_resdev_skill profile-review --root . --output .\reports\profile-review.md --json .\state\profile-review.json
python -m k_resdev_skill admin-profile-pack-gate --root . --output .\reports\admin-profile-pack-gate.md --json .\state\admin-profile-pack-gate.json
python -m k_resdev_skill admin-obligations-review --root . --output .\reports\admin-obligations.md --json .\state\admin-obligations-review.json
python -m k_resdev_skill admin-reviewed-seed-drift --root . --output .\reports\admin-reviewed-seed-drift.md --json .\state\admin-reviewed-seed-drift.json
```

언제 쓰나:
- `templates/agencies/<profile-id>/` 기반 행정 의무 후보를 검토할 때
- reviewed-seed가 현재 profile/review/gate hash와 맞는지 확인할 때

주의:
- profile pack은 공식 규칙이 아니라 local candidate다.
- reviewed-seed는 local `accepted_risk` 후보이며 official compliance가 아니다.

## 연구 지원

```powershell
python -m k_resdev_skill bib-import .\references\library.bib --state-dir .\state --literature-matrix .\reports\literature-review-matrix.md
python -m k_resdev_skill citation-support-integrity --root . --output .\reports\citation-support.md --json .\state\citation-support.json
python -m k_resdev_skill run-analysis .\inbox\metrics.csv --output-dir .\reports\analysis --evidence-id "<evidence-id>"
python -m k_resdev_skill research-claim-matrix --root . --output .\reports\research-claim-matrix.md --json .\state\research-claim-matrix.json
```

언제 쓰나:
- 논문 metadata를 보존하고 literature matrix를 만들 때
- cited paper가 claim을 support하는지 사람 검토 기록을 확인할 때
- 데이터 분석 artifact와 replay script가 필요할 때

주의:
- citation support는 자동 추론하지 않는다.
- insight는 hypothesis/candidate다.

## 전체 review pack

```powershell
python -m k_resdev_skill workspace-review-pack --root .
python -m k_resdev_skill verify-review-pack .\state\workspace-review-pack.json
```

언제 쓰나:
- 사람이 전체 상태를 빠르게 검토할 bundle이 필요할 때
- fresh chat / handoff / audit prep 전에 상태를 고정하고 싶을 때

주의:
- review pack은 official submission이 아니다.
- artifact hash 검증은 내용의 진실성이나 공식 적합성을 증명하지 않는다.
