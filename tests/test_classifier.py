from k_resdev_skill import classify_file


def test_classifier_detects_plan_from_korean_filename():
    result = classify_file("2026_연구개발계획서.pdf")

    assert result.category == "plan"
    assert result.confidence > 0.4


def test_classifier_detects_plan_text_even_with_metric_terms():
    result = classify_file("plan.txt", "과제명: AI 진단\n연구기간: 2026\nKPI: Validation Dice 목표: 0.85")

    assert result.category == "plan"


def test_classifier_prioritizes_tabular_data_files():
    result = classify_file("experiment_metrics_2026_05.xlsx")

    assert result.category == "data"
    assert "data extension: .xlsx" in result.reasons


def test_classifier_detects_budget_text():
    result = classify_file("proof.pdf", "세금계산서와 견적서 정산 증빙")

    assert result.category == "budget"


def test_classifier_returns_unknown_when_no_signal():
    result = classify_file("misc.bin")

    assert result.category == "unknown"
