import json

import jsonschema


def test_sample_evidence_matches_json_schema():
    with open("schemas/evidence.schema.json", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open("examples/sample-evidence.json", encoding="utf-8") as handle:
        sample = json.load(handle)

    jsonschema.validate(sample, schema)
