# Intake 규칙

Intake는 원본 파일을 evidence 후보로 연결하는 단계다.

원본 파일은 수정하지 않는다. 확실하지 않은 추출 결과는 `needs_review`로 둔다.

## 파일 분류

| Category | 예시 | 주로 보는 내용 |
|---|---|---|
| `plan` | 계획서, RFP, 협약서 | 목표, KPI, milestone, 의무 |
| `progress` | 회의록, 월간 기록, 주간 기록 | 결정, action item, 위험 |
| `experiment` | 실험 log, 결과표, notebook | metric, 조건, baseline, dataset |
| `budget` | 영수증, invoice, 견적서, ledger | 금액, 비목, 날짜, vendor, 증빙 상태 |
| `outcome` | 논문, 특허, SW, 시제품 | 성과 유형, 제출 상태, KPI 연결 |
| `change` | 변경신청, 승인 메일 | 변경 전/후, 사유, 영향, 승인 근거 |
| `literature` | 논문, 초록, review | claim, method, dataset, metric, limitation |
| `data` | CSV, XLSX, JSONL | schema, row count, missingness, metric 후보 |
| `unknown` | 판단 어려운 파일 | 파일 단위 후보로만 등록 |

## Intake 순서

1. source file metadata를 등록한다.
2. 파일 category를 보수적으로 분류한다.
3. 문서/표/데이터에서 candidate evidence를 만든다.
4. 가능한 경우 KPI, milestone, budget, paper claim에 연결한다.
5. ambiguous item은 `needs_review`로 둔다.
6. 원본 파일은 덮어쓰지 않는다.
7. report draft는 raw text가 아니라 evidence item을 통해 만든다.

## 보수적으로 처리할 상황

다음은 자동 확정하지 않는다.

- 기관 제출 양식 여부
- 연구비 적격/부적격
- 논문 claim의 실제 support 여부
- 통계적으로 유의한 개선 여부
- 승인 범위가 현재 report/export hash까지 포함하는지 여부
- HWP/HWPX/PDF에서 추출된 표나 페이지가 불완전한 경우

## Provenance

가능하면 evidence에 출처 힌트를 남긴다.

```text
source_file
source_hash
page
sheet
cell_range
line_range
quote
```

출처 힌트가 없으면 evidence 자체가 더 강해지는 것이 아니다. 오히려 review에서 먼저 확인해야 할 항목으로 남긴다.

## 실패 처리

읽을 수 없는 파일은 조용히 무시하지 않는다.

```text
classification: unknown
status: needs_review
risk_flags: extraction_failed, manual_review_required
```

이 방식이 불편해 보여도, 행정/감사/논문 맥락에서는 누락을 숨기는 것보다 드러내는 편이 안전하다.
