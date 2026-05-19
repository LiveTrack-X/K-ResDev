import json

from k_resdev_skill.admin_operating import (
    initialize_admin_obligations,
    load_admin_obligation_profile_pack,
    review_admin_obligation_profile_pack,
    review_admin_obligations,
)
from k_resdev_skill.approval import create_approval_record, write_approval_record
from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor


def test_admin_obligations_init_creates_needs_review_starter_without_overwrite(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    result = initialize_admin_obligations(tmp_path, profile_id="national-rnd-basic")

    obligations_path = tmp_path / "state" / "admin-obligations.json"
    submissions_path = tmp_path / "state" / "admin-submissions.json"
    assert obligations_path.exists()
    assert submissions_path.exists()
    assert result.obligation_count == 6
    assert result.status == "needs_review"
    assert {item.status for item in result.obligations} == {"needs_review"}
    assert all("official_source_needs_review" in item.risk_flags for item in result.obligations)

    original = obligations_path.read_text(encoding="utf-8")
    obligations_path.write_text(original.replace("Generic Korean national R&D admin obligation skeleton only.", "Custom local admin obligation starter."), encoding="utf-8")
    initialize_admin_obligations(tmp_path, profile_id="national-rnd-basic")
    assert "Custom local admin obligation starter." in obligations_path.read_text(encoding="utf-8")


def test_admin_obligations_init_uses_profile_pack_without_claiming_official_rules(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    result = initialize_admin_obligations(tmp_path, profile_id="iris-innopolis-2026-017795")

    obligations_path = tmp_path / "state" / "admin-obligations.json"
    payload = json.loads(obligations_path.read_text(encoding="utf-8"))
    assert payload["source_record_ids"] == ["PRS-IRIS-017795-20260519"]
    assert payload["status"] == "needs_review"
    assert result.obligation_count == 4
    assert {item.profile_id for item in result.obligations} == {"iris-innopolis-2026-017795"}
    assert {item.status for item in result.obligations} == {"needs_review"}
    assert all("official_source_needs_review" in item.risk_flags for item in result.obligations)


def test_admin_profile_pack_review_and_loader_keep_needs_review_guards(tmp_path):
    pack = load_admin_obligation_profile_pack("iris-innopolis-2026-017795")
    assert pack.status == "needs_review"
    assert len(pack.obligations) == 4
    assert all(item.status == "needs_review" for item in pack.obligations)

    review = review_admin_obligation_profile_pack(
        "iris-innopolis-2026-017795",
        output_path=tmp_path / "admin-profile-pack.md",
        json_path=tmp_path / "admin-profile-pack.json",
    )
    codes = {finding.code for finding in review.findings}
    assert review.status == "needs_review"
    assert review.obligation_count == 4
    assert review.source_record_count == 1
    assert "admin_profile_pack_source_needs_review" in codes
    assert (tmp_path / "admin-profile-pack.md").exists()
    assert (tmp_path / "admin-profile-pack.json").exists()


def test_admin_obligations_review_warnings_reduce_with_submission_evidence_and_approval(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    initialize_admin_obligations(tmp_path, profile_id="national-rnd-basic")

    before = review_admin_obligations(tmp_path)
    before_codes = {finding.code for finding in before.findings}
    assert "admin_obligation_missing_evidence_type" in before_codes
    assert "admin_obligation_submission_missing" in before_codes

    evidence = EvidenceItem(
        evidence_id="EVI-2026-BUDGET1",
        source_file="inbox/receipt.pdf",
        evidence_type="budget_evidence",
        claim="Budget proof candidate.",
        status="accepted",
    )
    write_evidence_index([evidence], tmp_path / "state")
    approval = create_approval_record(
        "other",
        "SUB-2026-BUDGET1",
        "approved",
        "Reviewer",
        target_path="reports/admin-budget.md",
        evidence_ids=["EVI-2026-BUDGET1"],
        reviewed_at="2026-05-19T00:00:00Z",
    )
    write_approval_record(approval, tmp_path / "state" / "approvals")
    report = tmp_path / "reports" / "admin-budget.md"
    report.write_text("# Admin Budget\n", encoding="utf-8")
    (tmp_path / "state" / "admin-submissions.json").write_text(
        json.dumps(
            {
                "submissions": [
                    {
                        "submission_id": "SUB-2026-BUDGET1",
                        "obligation_id": "ADM-BUDGET-001",
                        "title": "Budget proof package",
                        "artifact_path": "reports/admin-budget.md",
                        "approval_id": approval.approval_id,
                        "evidence_ids": ["EVI-2026-BUDGET1"],
                        "status": "accepted",
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    after = review_admin_obligations(tmp_path)
    after_codes = {finding.code for finding in after.findings}
    assert after.submission_count == 1
    assert "admin_submission_approval_unlinked" not in after_codes
    assert "admin_submission_evidence_missing" not in after_codes
    assert "admin_submission_not_accepted" not in after_codes
    assert sum(1 for finding in after.findings if finding.code == "admin_obligation_missing_evidence_type") < sum(
        1 for finding in before.findings if finding.code == "admin_obligation_missing_evidence_type"
    )


def test_workspace_doctor_surfaces_admin_obligation_findings(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    initialize_admin_obligations(tmp_path, profile_id="national-rnd-basic")

    result = run_workspace_doctor(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert "admin_obligations_review_findings" in codes


def test_admin_operating_layer_cli_smoke(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")

    assert main(["admin-obligations-init", "--root", str(tmp_path), "--profile", "national-rnd-basic", "--output", str(tmp_path / "reports" / "admin-obligations.md"), "--json", str(tmp_path / "state" / "admin-obligations-review.json")]) == 0
    assert main(["admin-obligations-review", "--root", str(tmp_path)]) == 0
    assert main(["admin-profile-pack-review", "--profile", "national-rnd-basic", "--output", str(tmp_path / "reports" / "admin-profile-pack.md"), "--json", str(tmp_path / "state" / "admin-profile-pack-review.json")]) == 0
    assert main(["settlement-binder", "--root", str(tmp_path)]) == 0
    assert main(["admin-change-ledger", "--root", str(tmp_path)]) == 0
    assert main(["admin-calendar-review", "--root", str(tmp_path)]) == 0
    assert main(["validate-json", "admin-obligations", str(tmp_path / "state" / "admin-obligations-review.json")]) == 0
