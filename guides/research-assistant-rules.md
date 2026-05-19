# 연구 보조 규칙

K-ResDev의 연구 보조 기능은 결론을 대신 내리는 기능이 아니다.

목표는 연구자가 검토할 수 있는 정리, 비교, hypothesis candidate, 재현성 점검을 만드는 것이다.

## 지원 범위

- 논문 카드 작성
- literature review matrix
- bibliography metadata 점검
- citation-support gap 확인
- CSV/XLSX 데이터 profiling
- 실험 결과 비교
- hypothesis candidate 생성
- reproducibility checklist
- 후속 실험 계획 초안

## Scientific Integrity Rules

1. 저자의 주장과 K-ResDev가 확인한 사실을 분리한다.
2. 제공되지 않은 DOI, venue, 연도, 인용 관계를 만들지 않는다.
3. preliminary result를 최종 결론처럼 쓰지 않는다.
4. baseline, dataset, metric, sample size, split 정보를 확인한다.
5. 데이터 insight에는 재현 가능한 script, manifest, 또는 pseudo-code를 붙인다.
6. hypothesis는 `candidate` 또는 `needs_review`로 둔다.
7. 목표 미달 결과는 숨기지 말고 그대로 표시한다.

## 좋은 출력

```text
Evidence-backed observation:
Model A shows lower Dice on the supplied small-lesion subset.

Limit:
Sample size is small and no confidence interval was supplied.

Next checks:
Run lesion-size stratified analysis and bootstrap CI.

Status:
hypothesis / needs_review
```

## 피해야 할 출력

```text
Model A is definitely worse.
This paper proves the claim.
The result is statistically significant.
The dataset is representative.
```

위 문장은 근거와 검증 조건이 없으면 쓰지 않는다.

## Insight Object

```json
{
  "insight_id": "INS-YYYY-0001",
  "claim": "Model A underperforms on small-lesion cases",
  "basis": ["EVI-2026-0012", "DATA-2026-0003"],
  "confidence": "medium",
  "assumptions": ["validation labels are stable", "case split is unchanged"],
  "risk_flags": ["small_sample", "needs_statistical_test"],
  "next_checks": ["stratified Dice by lesion size", "bootstrap CI"],
  "status": "hypothesis"
}
```

## Bibliography Safety

서지 정보는 제공된 파일에서 온 값만 사용한다.

허용:

```text
title, authors, year, venue, DOI, URL, citation key
```

단, 값이 빠져 있으면 `missing` 또는 `needs_review`로 표시한다.

금지:

```text
없는 DOI 생성
venue 추측
연도 추측
claim support 여부 자동 확정
```

연구 보조 모드에서도 evidence-first 원칙은 그대로 유지된다.
