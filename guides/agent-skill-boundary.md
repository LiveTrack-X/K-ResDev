# K-ResDev 스킬 경계

K-ResDev는 GPT/Codex 에이전트 스킬이 본체다.

Python 패키지는 선택적 검증 코어다. 해시, evidence ID, schema, source drift, approval record, budget ledger, 재현 가능한 분석처럼 자유서술로 처리하면 위험한 일을 deterministic하게 확인하기 위해 존재한다.

## 올바른 구조

```text
사용자 요청
-> GPT/Codex 스킬이 모드와 workflow 선택
-> 필요한 경우 Python 검증 코어 실행
-> 에이전트가 evidence, gap, risk, next action 설명
-> 사람이 승인/제출/수정 여부 결정
```

## 스킬에 속하는 것

- 어떤 상황에서 Admin Evidence Mode, Research Assistant Mode, Integrity Mode를 쓸지 판단한다.
- 에이전트가 절대 만들면 안 되는 claim, citation, approval, agency rule을 정의한다.
- 어떤 local artifact를 먼저 읽어야 하는지 정한다.
- 어떤 검증이 deterministic command로 내려가야 하는지 판단한다.
- 결과를 evidence-backed fact, projection, hypothesis, human decision required로 설명한다.

## 검증 코어에 속하는 것

- 파일 classification과 intake
- evidence index 생성
- JSON schema validation
- source hash verification
- unsupported claim check
- approval coverage check
- budget ledger / settlement binder check
- workspace doctor / next-actions / summary / review-pack / trace
- CSV/XLSX profiling과 재현 가능한 분석 artifact

## 하지 말아야 할 것

- 사용자가 모든 CLI 명령을 알아야만 쓸 수 있게 만들지 않는다.
- local review artifact를 공식 compliance로 말하지 않는다.
- 최신 공식 출처 없이 기관 규칙을 하드코딩하지 않는다.
- reviewed-seed profile data로 사람 승인을 우회하지 않는다.
- research insight를 최종 연구 결론처럼 말하지 않는다.

## 앞으로의 개발 기준

새 기능은 구현 전에 이 질문을 통과해야 한다.

```text
이 기능이 GPT/Codex 에이전트를 더 안전하고 명확하고 유용하게 만드는가?
```

아니라면 보류한다.

우선순위:

1. 더 작은 agent entrypoint
2. 더 좋은 workflow routing
3. 더 쉬운 한글 사용자 문서
4. top-level 문서에서 노출되는 명령 수 줄이기
5. 위험한 부분만 검증 코어로 내리기
