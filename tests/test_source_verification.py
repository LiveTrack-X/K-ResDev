import hashlib
import json

from k_resdev_skill.cli import main
from k_resdev_skill.evidence_index import write_evidence_index
from k_resdev_skill.models import EvidenceItem
from k_resdev_skill.source_verification import verify_evidence_sources


def test_verify_evidence_sources_accepts_matching_source_hash(tmp_path):
    source = tmp_path / "inbox" / "metrics.csv"
    source.parent.mkdir()
    source.write_text("case_id,dice\nA,0.81\n", encoding="utf-8")
    paths = write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-0001",
                source_file="inbox/metrics.csv",
                source_hash=_sha256(source),
                evidence_type="experiment_result",
                claim="Metric candidate.",
            )
        ],
        tmp_path / "state",
    )

    result = verify_evidence_sources(paths.json_path, root=tmp_path, output_path=tmp_path / "reports" / "source-verification.md")

    assert result.valid is True
    assert result.ok_count == 1
    assert result.items[0].status == "ok"
    assert (tmp_path / "reports" / "source-verification.md").read_text(encoding="utf-8").startswith("# Evidence Source Verification")


def test_verify_evidence_sources_detects_changed_missing_and_unhashed_sources(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    changed = inbox / "changed.csv"
    no_hash = inbox / "notes.txt"
    changed.write_text("a\n1\n", encoding="utf-8")
    no_hash.write_text("needs review\n", encoding="utf-8")
    original_hash = _sha256(changed)
    changed.write_text("a\n2\n", encoding="utf-8")
    paths = write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-CHANGED",
                source_file="changed.csv",
                source_hash=original_hash,
                evidence_type="data_profile",
                claim="Changed source.",
            ),
            EvidenceItem(
                evidence_id="EVI-2026-MISSING",
                source_file="missing.csv",
                source_hash="sha256:" + "0" * 64,
                evidence_type="data_profile",
                claim="Missing source.",
            ),
            EvidenceItem(
                evidence_id="EVI-2026-NOHASH",
                source_file="notes.txt",
                evidence_type="meeting_decision",
                claim="No hash source.",
            ),
        ],
        tmp_path / "state",
    )

    result = verify_evidence_sources(paths.json_path, inbox=inbox, json_path=tmp_path / "state" / "source-verification.json")
    statuses = {item.source_file: item.status for item in result.items}

    assert result.valid is False
    assert result.mismatch_count == 1
    assert result.missing_count == 1
    assert result.no_hash_count == 1
    assert statuses["changed.csv"] == "mismatch"
    assert statuses["missing.csv"] == "missing"
    assert statuses["notes.txt"] == "no_expected_hash"
    assert json.loads((tmp_path / "state" / "source-verification.json").read_text(encoding="utf-8"))["valid"] is False


def test_verify_evidence_sources_cli_exit_codes(tmp_path, capsys):
    source = tmp_path / "metrics.csv"
    source.write_text("case_id,dice\nA,0.81\n", encoding="utf-8")
    paths = write_evidence_index(
        [
            EvidenceItem(
                evidence_id="EVI-2026-0001",
                source_file=str(source),
                source_hash=_sha256(source),
                evidence_type="experiment_result",
                claim="Metric candidate.",
            )
        ],
        tmp_path / "state",
    )

    assert main(["verify-evidence-sources", paths.json_path]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True

    source.write_text("case_id,dice\nA,0.12\n", encoding="utf-8")

    assert main(["verify-evidence-sources", paths.json_path]) == 1
    assert json.loads(capsys.readouterr().out)["mismatch_count"] == 1


def _sha256(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
