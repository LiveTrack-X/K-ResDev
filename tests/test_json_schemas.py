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
