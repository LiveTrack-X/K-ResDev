# K-ResDev 구조

K-ResDev의 구조는 단순하다.

```text
원본 자료
-> evidence
-> 연결 관계
-> projection
-> 사람 검토
```

보고서, 정산 binder, 논문 요약, 대시보드는 모두 projection이다. 원본과 evidence가 source of truth이고, 최종 판단은 사람이 한다.

## Core Lifecycle

```text
inbox/ and references/
-> raw source registry
-> parsed text/table metadata
-> evidence items
-> KPI, milestone, budget, claim links
-> integrity checks
-> reports, dashboards, research drafts
-> human review records
-> review-ready package
```

## Layer Model

| Layer | 역할 | 예시 |
|---|---|---|
| Raw | 원본을 보존 | PDF, HWPX, DOCX, XLSX, CSV, 영수증 |
| Parsed | 원본에서 읽은 중간 산출물 | 텍스트, 표, sheet 요약, page hint |
| Evidence | 감사 가능한 근거 단위 | 실험 metric, 회의 결정, 예산 증빙 |
| Link | evidence를 구조에 연결 | KPI, milestone, 비목, 논문 claim |
| Projection | 사람이 검토할 출력 | 월간보고서, 정산 binder, literature matrix |
| Review | 사람이 남긴 결정 | approved, rejected, accepted_risk, needs_follow_up |

## Track

### Admin Evidence Track

계획서, KPI, milestone, 예산, 정산, 승인, 변경, 감사 대응을 다룬다.

중요한 질문:

```text
이 문장이나 금액은 어떤 evidence와 승인에 연결되는가?
```

### Research Assistant Track

논문, bibliography, citation support, 데이터, 실험 결과, hypothesis candidate를 다룬다.

중요한 질문:

```text
이 claim은 제공된 문헌/데이터/실험 evidence로 어디까지 말할 수 있는가?
```

### Integrity Track

두 track을 가로질러 unsupported claim, 과장, KPI mismatch, source hash drift, 승인 누락을 찾는다.

## Authority Rule

서로 다른 layer의 권위를 섞지 않는다.

- Raw source는 수정하지 않는다.
- Evidence는 근거 후보 또는 검토된 근거다.
- Projection은 제출물이 아니라 초안이다.
- Review record는 사람이 supplied decision으로 남긴 기록이다.
- Profile은 공식 규칙이 아니라 source-backed 후보이며, 검토 전에는 `needs_review`다.

이 규칙 때문에 K-ResDev는 자동작성기보다 운영 레이어에 가깝다.
