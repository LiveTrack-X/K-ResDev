from k_resdev_skill import check_unsupported_claims
from k_resdev_skill.models import EvidenceItem, KPI


def test_claim_checker_flags_unsupported_numeric_and_superlative_claims():
    findings = check_unsupported_claims(
        "The model achieved 92% accuracy.\nThis is a world first result.",
        [],
    )

    codes = {finding.code for finding in findings}
    assert "unsupported_numeric_claim" in codes
    assert "unsupported_superlative" in codes
    assert "missing_evidence_for_claim" in codes


def test_claim_checker_flags_missing_evidence_id():
    findings = check_unsupported_claims("Result reached target per EVI-2026-9999.", [])

    assert any(finding.code == "missing_evidence_id" for finding in findings)


def test_claim_checker_flags_below_target_overclaim_and_kpi_mismatch():
    evidence = EvidenceItem(
        evidence_id="EVI-2026-0001",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Validation Dice reached 0.83.",
        value={"score": 0.83, "target": 0.85},
        linked_kpi="KPI-01",
    )
    kpi = KPI(kpi_id="KPI-01", name="Validation Dice", target=0.85)

    findings = check_unsupported_claims(
        "KPI-01 was achieved successfully based on EVI-2026-0001.",
        [evidence],
        [kpi],
    )

    codes = {finding.code for finding in findings}
    assert "below_target_overclaim" in codes
    assert "kpi_mismatch" in codes


def test_claim_checker_flags_numeric_mismatch_even_with_evidence_id():
    evidence = EvidenceItem(
        evidence_id="EVI-2026-ABCD1234",
        source_file="metrics.csv",
        evidence_type="experiment_result",
        claim="Validation Dice reached 0.83.",
        value={"score": 0.83, "target": 0.85},
    )

    findings = check_unsupported_claims(
        "Validation Dice reached 0.99 based on EVI-2026-ABCD1234.",
        [evidence],
    )

    assert any(finding.code == "numeric_evidence_mismatch" for finding in findings)
