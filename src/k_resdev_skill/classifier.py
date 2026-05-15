from __future__ import annotations

from pathlib import Path

from .models import FileCategory, FileClassification


DATA_EXTENSIONS = {".csv", ".xlsx", ".xls", ".jsonl", ".parquet"}

KEYWORDS: dict[FileCategory, tuple[str, ...]] = {
    FileCategory.PLAN: (
        "plan",
        "rfp",
        "proposal",
        "project plan",
        "agreement",
        "project title",
        "사업계획",
        "연구개발계획",
        "과제계획",
        "과제명",
        "연구과제명",
        "연구기간",
        "사업기간",
        "협약",
        "공고",
    ),
    FileCategory.PROGRESS: (
        "progress",
        "weekly",
        "monthly",
        "meeting",
        "minutes",
        "회의록",
        "월간",
        "주간",
        "진도",
        "점검",
    ),
    FileCategory.EXPERIMENT: (
        "experiment",
        "baseline",
        "result",
        "metrics",
        "eval",
        "실험",
        "결과",
        "성능",
        "평가",
        "검증",
        "dice",
        "auc",
        "accuracy",
    ),
    FileCategory.BUDGET: (
        "budget",
        "receipt",
        "invoice",
        "estimate",
        "quotation",
        "vendor",
        "예산",
        "영수증",
        "세금계산서",
        "견적",
        "거래명세",
        "정산",
    ),
    FileCategory.OUTCOME: (
        "outcome",
        "deliverable",
        "patent",
        "prototype",
        "software",
        "성과",
        "논문성과",
        "특허",
        "시제품",
        "결과물",
        "등록",
    ),
    FileCategory.CHANGE: (
        "change request",
        "amendment",
        "approval",
        "revision",
        "변경",
        "승인",
        "변경신청",
        "수정",
        "조정",
    ),
    FileCategory.LITERATURE: (
        "paper",
        "literature",
        "review",
        "survey",
        "abstract",
        "doi",
        "arxiv",
        "pubmed",
        "논문",
        "선행연구",
        "문헌",
        "초록",
        "리뷰",
    ),
    FileCategory.DATA: (
        "dataset",
        "data",
        "table",
        "spreadsheet",
        "데이터",
        "데이터셋",
        "표",
        "csv",
        "xlsx",
    ),
}


def classify_file(path: str | Path, text: str | None = None) -> FileClassification:
    """Classify a source file without altering it."""

    source = Path(path)
    suffix = source.suffix.lower()
    haystack = " ".join(
        part.lower()
        for part in (source.name, source.stem.replace("_", " "), source.suffix, text or "")
    )

    scores: dict[FileCategory, int] = {category: 0 for category in FileCategory}
    reasons: dict[FileCategory, list[str]] = {category: [] for category in FileCategory}

    if suffix in DATA_EXTENSIONS:
        scores[FileCategory.DATA] += 5
        reasons[FileCategory.DATA].append(f"data extension: {suffix}")

    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in haystack:
                scores[category] += 1
                reasons[category].append(f"keyword: {keyword}")

    scores.pop(FileCategory.UNKNOWN, None)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_category, top_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0

    if top_score == 0:
        return FileClassification(
            category=FileCategory.UNKNOWN,
            confidence=0.2,
            reasons=["no matching extension or keyword"],
        )

    margin = max(0, top_score - second_score)
    confidence = min(0.95, 0.35 + (top_score * 0.09) + (margin * 0.04))
    return FileClassification(
        category=top_category,
        confidence=round(confidence, 2),
        reasons=reasons[top_category][:6],
    )
