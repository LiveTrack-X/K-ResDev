import json

from k_resdev_skill.bibliography import import_bibliography, load_bibliography_index
from k_resdev_skill.citation_support import create_citation_support_record, write_citation_support_record
from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem, ResearchClaim
from k_resdev_skill.research_claims import (
    generate_research_claim_matrix,
    import_research_claims,
    load_research_claims,
    render_research_claim_matrix_markdown,
    write_research_claims,
)
from k_resdev_skill.workspace import initialize_workspace, run_workspace_doctor
from k_resdev_skill.workspace_actions import generate_workspace_action_plan
from k_resdev_skill.workspace_review import generate_workspace_review_pack
from k_resdev_skill.workspace_summary import generate_workspace_summary
from k_resdev_skill.workspace_trace import generate_workspace_trace


def test_research_claim_import_round_trip_json_and_markdown(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    source = tmp_path / "references" / "research-claims.json"
    source.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "claim_id": "RCL-2026-0001",
                        "claim": "Model A appears to underperform on small-lesion cases.",
                        "claim_type": "research",
                        "evidence_ids": ["EVI-2026-0001"],
                        "citation_keys": ["kim2026"],
                        "bibliography_ids": [],
                        "support_ids": [],
                        "insight_ids": ["INS-2026-0001"],
                        "status": "candidate",
                        "confidence": "medium",
                        "risk_flags": ["small_sample"],
                        "next_checks": ["Run stratified Dice analysis"],
                        "notes": "Imported candidate.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = import_research_claims(source, tmp_path / "state", markdown_path=tmp_path / "reports" / "research-claims.md")
    claims = load_research_claims(tmp_path / "state" / "research-claims.json")

    assert result.claim_count == 1
    assert result.source_hash.startswith("sha256:")
    assert claims[0].claim_id == "RCL-2026-0001"
    assert "Research Claims" in (tmp_path / "reports" / "research-claims.md").read_text(encoding="utf-8")


def test_research_claim_matrix_ready_for_accepted_claim_with_evidence_and_support(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    _write_evidence(tmp_path, status="accepted")
    entry = _write_sample_bibliography(tmp_path)
    support = create_citation_support_record(
        bibliography_id=entry.bibliography_id,
        citation_key="kim2026",
        paper_id=entry.paper_id,
        claim="Model A appears to underperform on small-lesion cases.",
        decision="supports",
        reviewer="Reviewer",
        evidence_ids=["EVI-2026-ABCD1234"],
        locator="Results, p. 4",
        quote="Small-lesion subgroup performance is lower.",
        reviewed_at="2026-05-18T09:00:00Z",
    )
    write_citation_support_record(support, tmp_path / "state" / "citation-support")
    write_research_claims(
        [
            ResearchClaim(
                claim_id="RCL-2026-0001",
                claim="Model A appears to underperform on small-lesion cases.",
                claim_type="manuscript",
                evidence_ids=["EVI-2026-ABCD1234"],
                citation_keys=["kim2026"],
                status="accepted",
                confidence="medium",
            )
        ],
        tmp_path / "state" / "research-claims.json",
    )

    result = generate_research_claim_matrix(tmp_path, tmp_path / "reports" / "research-claim-matrix.md", tmp_path / "state" / "research-claim-matrix.json")
    rendered = render_research_claim_matrix_markdown(result)

    assert result.status == "ready"
    assert result.finding_count == 0
    assert result.claim_count == 1
    assert "Research-claim projection only" in rendered
    assert json.loads((tmp_path / "state" / "research-claim-matrix.json").read_text(encoding="utf-8"))["status"] == "ready"


def test_research_claim_matrix_blocks_unknown_evidence_and_negative_support(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    entry = _write_sample_bibliography(tmp_path)
    support = create_citation_support_record(
        bibliography_id=entry.bibliography_id,
        citation_key="kim2026",
        claim="Model A appears to underperform on small-lesion cases.",
        decision="does_not_support",
        reviewer="Reviewer",
        reviewed_at="2026-05-18T09:00:00Z",
    )
    write_citation_support_record(support, tmp_path / "state" / "citation-support")
    write_research_claims(
        [
            ResearchClaim(
                claim_id="RCL-2026-BLOCKED",
                claim="Model A appears to underperform on small-lesion cases.",
                claim_type="manuscript",
                evidence_ids=["EVI-2026-MISSING"],
                citation_keys=["kim2026"],
                support_ids=[support.support_id],
                status="accepted",
                confidence="medium",
            )
        ],
        tmp_path / "state" / "research-claims.json",
    )

    result = generate_research_claim_matrix(tmp_path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "blocked"
    assert "research_claim_unknown_evidence" in codes
    assert "research_claim_negative_support" in codes
    assert result.high_count >= 2


def test_research_claim_matrix_integrates_with_workspace_operations(tmp_path):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    _write_evidence(tmp_path, status="needs_review")
    write_research_claims(
        [
            ResearchClaim(
                claim_id="RCL-2026-REVIEW",
                claim="Dice reached 0.81 but needs split verification.",
                evidence_ids=["EVI-2026-ABCD1234"],
                status="candidate",
                confidence="low",
                next_checks=["Confirm test split"],
            )
        ],
        tmp_path / "state" / "research-claims.json",
    )

    doctor = run_workspace_doctor(tmp_path)
    actions = generate_workspace_action_plan(tmp_path, doctor_result=doctor)
    summary = generate_workspace_summary(tmp_path, doctor_result=doctor, action_plan=actions)
    pack = generate_workspace_review_pack(tmp_path)
    trace = generate_workspace_trace(tmp_path)
    doctor_codes = {finding.code for finding in doctor.findings}
    node_types = {node.node_type for node in trace.nodes}

    assert "research_claim_matrix_review_findings" in doctor_codes
    assert any(action.title == "Review research claim matrix" for action in actions.actions)
    assert summary.research_claim_count == 1
    assert summary.research_claim_matrix_finding_count >= 1
    assert pack.research_claim_count == 1
    assert pack.research_claim_matrix_finding_count >= 1
    assert "research_claim" in node_types
    assert (tmp_path / "reports" / "research-claim-matrix.md").exists()
    assert (tmp_path / "state" / "research-claim-matrix.json").exists()


def test_research_claim_cli_and_schema(tmp_path, capsys):
    initialize_workspace(tmp_path, "PRJ-2026-0001", "Demo Project")
    source = tmp_path / "references" / "research-claims.csv"
    source.write_text(
        "claim_id,claim,claim_type,evidence_ids,citation_keys,status,confidence,next_checks\n"
        "RCL-2026-CSV,Claim from CSV.,research,EVI-2026-CSV,,needs_review,unknown,Add evidence review\n",
        encoding="utf-8",
    )

    assert main(["research-claim-import", str(source), "--state-dir", str(tmp_path / "state"), "--markdown", str(tmp_path / "reports" / "research-claims.md")]) == 0
    import_payload = json.loads(capsys.readouterr().out)
    assert import_payload["claim_count"] == 1

    assert main(["research-claim-summary", str(tmp_path / "state" / "research-claims.json"), "--output", str(tmp_path / "reports" / "research-claims-summary.md")]) == 0
    assert "Research Claims" in capsys.readouterr().out

    assert (
        main(
            [
                "research-claim-matrix",
                "--root",
                str(tmp_path),
                "--output",
                str(tmp_path / "reports" / "research-claim-matrix.md"),
                "--json",
                str(tmp_path / "state" / "research-claim-matrix.json"),
            ]
        )
        == 0
    )
    matrix_payload = json.loads(capsys.readouterr().out)
    assert matrix_payload["claim_count"] == 1

    assert main(["validate-json", "research-claim", str(tmp_path / "state" / "research-claims.json")]) == 0
    assert main(["validate-json", "research-claim", "templates/research-claim.json"]) == 0


def _write_evidence(tmp_path, status="accepted"):
    write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-ABCD1234",
                source_file="inbox/metrics.csv",
                evidence_type="experiment_result",
                claim="Dice reached 0.81.",
                value={"metric": "dice", "score": 0.81},
                status=status,
            )
        ],
        tmp_path / "state",
    )


def _write_sample_bibliography(tmp_path):
    bib = tmp_path / "references" / "library.bib"
    bib.write_text(
        """@article{kim2026,
  title = {Small Lesion Evidence},
  author = {Kim, Mina},
  year = {2026},
  journal = {Journal of Research Operations}
}
""",
        encoding="utf-8",
    )
    import_bibliography(bib, tmp_path / "state")
    return load_bibliography_index(tmp_path / "state" / "bibliography-index.json")[0]
