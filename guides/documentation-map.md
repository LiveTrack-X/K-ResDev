# K-ResDev 문서 지도

이 문서는 전체 문서를 한 번에 다 읽지 않도록 돕는 길잡이다.

K-ResDev 문서는 세 층으로 나뉜다.

```text
SKILL.md / README.md
-> guides/
-> workflows/ and templates/
```

처음에는 상위 문서만 읽고, 실제 작업이 필요할 때만 세부 문서를 연다.

## 먼저 읽을 문서

| 상황 | 먼저 읽을 문서 | 목적 |
|---|---|---|
| 처음 쓰는 사용자 | `README.md`, `guides/user-guide.md` | 무엇을 하는 스킬인지, 첫 워크스페이스를 어떻게 만드는지 이해 |
| GPT/Codex 에이전트 | `SKILL.md`, `guides/operations-guide.md` | 모드 선택, 검증 코어 사용 시점, 보고 형식 확인 |
| 운영자/PM | `guides/operations-guide.md`, `guides/verification-core.md` | 점검 bundle과 제출 전 체크 흐름 확인 |
| 개발자 | `guides/agent-skill-boundary.md`, `workflows/mvp-roadmap.md` | 기능 추가 기준과 구현 로드맵 확인 |
| 기관 profile 작업자 | `workflows/next-planning.md`, `templates/agencies/` | source-backed profile 후보와 검토 상태 확인 |

## 문서별 역할

| 문서 | 역할 |
|---|---|
| `SKILL.md` | GPT/Codex가 실제 작업 중 읽는 에이전트 운영 계약 |
| `README.md` | 프로젝트 소개와 가장 짧은 시작 안내 |
| `guides/user-guide.md` | 처음 쓰는 사람을 위한 한글 진입 문서 |
| `guides/capability-map.md` | 지금 할 수 있는 일과 하면 안 되는 말을 한눈에 정리 |
| `guides/operations-guide.md` | 운영자와 에이전트가 반복 점검을 수행하는 방법 |
| `guides/verification-core.md` | Python CLI 검증 명령 지도 |
| `guides/agent-skill-boundary.md` | 스킬 본체와 선택적 검증 코어의 경계 |
| `guides/architecture.md` | evidence-first 구조와 artifact authority 모델 |
| `guides/intake-rules.md` | 파일 intake와 evidence 후보 생성 규칙 |
| `guides/research-assistant-rules.md` | 논문/데이터/실험 해석 보조의 안전 규칙 |
| `workflows/mvp-roadmap.md` | 구현된 범위와 다음 큰 방향 |
| `workflows/next-planning.md` | beta별 세부 계획과 구현 기록 |
| `workflows/codex-tasks.md` | Codex가 이어받아 작업할 상세 handoff |
| `templates/` | 생성 artifact의 예시 형식과 projection 문구 |

## 읽는 순서

초심자:

```text
README.md
-> guides/user-guide.md
-> guides/capability-map.md
-> guides/verification-core.md
```

에이전트/운영자:

```text
SKILL.md
-> guides/operations-guide.md
-> guides/documentation-map.md
-> guides/capability-map.md
-> 필요한 세부 guide
```

개발자:

```text
README.md
-> SKILL.md
-> guides/agent-skill-boundary.md
-> workflows/mvp-roadmap.md
-> workflows/next-planning.md
```

## 문서 유지 기준

1. `SKILL.md`는 짧게 유지한다.
2. 사용자가 처음 보는 설명은 한글 중심으로 쓴다.
3. 명령어 목록은 `guides/verification-core.md`로 모은다.
4. 공식 제출, 적격 판정, 기관 규칙 확정처럼 보이는 표현은 피한다.
5. `workflows/`는 구현된 사실과 계획을 분리해서 쓴다.
6. `templates/`는 항상 draft/projection/needs_review 경계를 드러낸다.

## 쓰지 않는 방식

다음처럼 쓰지 않는다.

```text
README에 모든 명령을 계속 추가
SKILL.md에 긴 개발 이력 추가
templates를 공식 양식처럼 설명
workflows 계획을 현재 구현처럼 표현
```

문서가 길어질수록 사용자는 덜 읽는다. K-ResDev 문서는 적게 읽고도 안전하게 움직이도록 설계한다.
