import json
from pathlib import Path

import jsonschema

ISA_DIR = Path(__file__).resolve().parents[1] / "isa"


def _schema() -> dict:
    return json.loads((ISA_DIR / "isa.schema.json").read_text())


def test_schema_accepts_a_minimal_extension_spec():
    spec = {"extension": "Base", "version": 1, "instructions": []}
    # Should not raise.
    jsonschema.validate(spec, _schema()["$defs"]["extension"])


def test_schema_rejects_extension_missing_version():
    spec = {"extension": "Base", "instructions": []}
    try:
        jsonschema.validate(spec, _schema()["$defs"]["extension"])
        raised = False
    except jsonschema.ValidationError:
        raised = True
    assert raised, "extension without 'version' must be rejected"
