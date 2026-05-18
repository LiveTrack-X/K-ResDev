import json

import jsonschema


def test_sample_evidence_matches_json_schema():
    with open("schemas/evidence.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("examples/sample-evidence.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_project_profile_template_matches_json_schema():
    with open("schemas/project_profile.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/project-profile.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_national_rnd_basic_profile_matches_json_schema():
    with open("schemas/project_profile.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/agencies/national-rnd-basic/project-profile.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_approval_record_template_matches_json_schema():
    with open("schemas/approval_record.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/approval-record.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_bibliography_entry_template_matches_json_schema():
    with open("schemas/bibliography_entry.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/bibliography-entry.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_bibliography_review_record_template_matches_json_schema():
    with open("schemas/bibliography_review_record.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/bibliography-review-record.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_citation_support_record_template_matches_json_schema():
    with open("schemas/citation_support_record.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/citation-support-record.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_profile_source_template_matches_json_schema():
    with open("schemas/profile_source.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/profile-source.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)


def test_budget_ledger_item_template_matches_json_schema():
    with open("schemas/budget_ledger_item.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("templates/budget-ledger-item.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)
