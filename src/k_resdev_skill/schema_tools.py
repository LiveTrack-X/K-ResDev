from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCHEMA_ALIASES = {
    "approval": "approval_record.schema.json",
    "artifact-authority": "artifact_authority.schema.json",
    "artifact_authority": "artifact_authority.schema.json",
    "artifact-authority-record": "artifact_authority_record.schema.json",
    "artifact_authority_record": "artifact_authority_record.schema.json",
    "artifact-authority-finding": "artifact_authority_finding.schema.json",
    "artifact_authority_finding": "artifact_authority_finding.schema.json",
    "bibliography": "bibliography_entry.schema.json",
    "bibliography-entry": "bibliography_entry.schema.json",
    "bibliography-review": "bibliography_review_record.schema.json",
    "bibliography_review": "bibliography_review_record.schema.json",
    "budget-ledger": "budget_ledger_item.schema.json",
    "budget_ledger": "budget_ledger_item.schema.json",
    "budget-ledger-item": "budget_ledger_item.schema.json",
    "citation-support": "citation_support_record.schema.json",
    "citation_support": "citation_support_record.schema.json",
    "evidence": "evidence.schema.json",
    "profile-source": "profile_source.schema.json",
    "profile_source": "profile_source.schema.json",
    "project-profile": "project_profile.schema.json",
    "project_state": "project_state.schema.json",
    "project-state": "project_state.schema.json",
    "reference-corpus": "reference_corpus.schema.json",
    "reference_corpus": "reference_corpus.schema.json",
    "reference-corpus-item": "reference_corpus_item.schema.json",
    "reference_corpus_item": "reference_corpus_item.schema.json",
    "reference-rejection": "reference_rejection.schema.json",
    "reference_rejection": "reference_rejection.schema.json",
    "research-insight": "research_insight.schema.json",
    "research_insight": "research_insight.schema.json",
    "research-claim": "research_claim.schema.json",
    "research_claim": "research_claim.schema.json",
    "trace-passport": "trace_passport.schema.json",
    "trace_passport": "trace_passport.schema.json",
    "checkpoint": "trace_passport_entry.schema.json",
    "trace-passport-entry": "trace_passport_entry.schema.json",
    "trace_passport_entry": "trace_passport_entry.schema.json",
    "workspace-discovery": "workspace_discovery.schema.json",
    "workspace_discovery": "workspace_discovery.schema.json",
    "workspace-discovery-item": "workspace_discovery_item.schema.json",
    "workspace_discovery_item": "workspace_discovery_item.schema.json",
    "workspace-setup-proposal": "workspace_setup_proposal.schema.json",
    "workspace_setup_proposal": "workspace_setup_proposal.schema.json",
}


def bundled_schema_path(schema: str) -> Path:
    candidate = SCHEMA_ALIASES.get(schema, schema)
    path = Path(candidate)
    if path.exists():
        return path
    repo_root = Path(__file__).resolve().parents[2]
    bundled = repo_root / "schemas" / candidate
    if bundled.exists():
        return bundled
    raise FileNotFoundError(f"Schema not found: {schema}")


def validate_json_file(json_path: str | Path, schema: str | Path) -> dict[str, object]:
    document_path = Path(json_path)
    schema_path = bundled_schema_path(str(schema))
    document = json.loads(document_path.read_text(encoding="utf-8"))
    schema_payload = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema_payload)
    errors = []
    for path_prefix, item in _validation_targets(document, schema_payload):
        for error in validator.iter_errors(item):
            errors.append(_format_error(error, path_prefix))
    errors.sort(key=lambda item: item["path"])
    return {
        "valid": not errors,
        "json_path": str(document_path),
        "schema_path": str(schema_path),
        "error_count": len(errors),
        "errors": errors,
    }


def validate_json_files(json_paths: list[str | Path], schema: str | Path) -> dict[str, object]:
    results = [validate_json_file(path, schema) for path in json_paths]
    return {
        "valid": all(result["valid"] for result in results),
        "schema": str(schema),
        "file_count": len(results),
        "results": results,
    }


def _validation_targets(document: Any, schema_payload: dict[str, Any]) -> list[tuple[str, Any]]:
    title = schema_payload.get("title")
    if title in {
        "ApprovalRecord",
        "ArtifactAuthorityFinding",
        "ArtifactAuthorityRecord",
        "BibliographyEntry",
        "BibliographyReviewRecord",
        "BudgetLedgerItem",
        "CitationSupportRecord",
        "EvidenceItem",
        "ProfileSource",
        "ReferenceCorpusItem",
        "ReferenceCorpusRejection",
        "ResearchClaim",
        "ResearchInsight",
        "TracePassportEntry",
        "WorkspaceDiscoveryItem",
        "WorkspaceSetupProposal",
    }:
        if isinstance(document, list):
            return [(f"$[{index}]", item) for index, item in enumerate(document)]
        if title == "WorkspaceSetupProposal" and isinstance(document, dict) and isinstance(document.get("proposals"), list):
            return [(f"$.proposals[{index}]", item) for index, item in enumerate(document["proposals"])]
        if title == "ArtifactAuthorityRecord" and isinstance(document, dict) and isinstance(document.get("records"), list):
            return [(f"$.records[{index}]", item) for index, item in enumerate(document["records"])]
        if title == "ArtifactAuthorityFinding" and isinstance(document, dict) and isinstance(document.get("findings"), list):
            return [(f"$.findings[{index}]", item) for index, item in enumerate(document["findings"])]
        if isinstance(document, dict) and isinstance(document.get("items"), list):
            return [(f"$.items[{index}]", item) for index, item in enumerate(document["items"])]
    return [("$", document)]


def _format_error(error, path_prefix: str = "$") -> dict[str, str]:
    suffix = ".".join(str(part) for part in error.path)
    path = path_prefix if not suffix else f"{path_prefix}.{suffix}"
    schema_path = ".".join(str(part) for part in error.schema_path) or "$"
    return {
        "path": path,
        "schema_path": schema_path,
        "message": error.message,
    }
