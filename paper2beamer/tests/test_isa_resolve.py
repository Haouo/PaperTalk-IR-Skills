import json
from pathlib import Path

import jsonschema
import yaml

ISA_DIR = Path(__file__).resolve().parents[1] / "isa"


def _schema() -> dict:
    return json.loads((ISA_DIR / "isa.schema.json").read_text())


def _validate(instance, defname: str) -> None:
    """Validate against a named $def while keeping $defs reachable for $ref."""
    full = _schema()
    jsonschema.validate(
        instance,
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": f"#/$defs/{defname}",
            "$defs": full["$defs"],
        },
    )


def test_schema_accepts_a_minimal_extension_spec():
    spec = {"extension": "Base", "version": 1, "instructions": []}
    _validate(spec, "extension")


def test_schema_rejects_extension_missing_version():
    spec = {"extension": "Base", "instructions": []}
    try:
        _validate(spec, "extension")
        raised = False
    except jsonschema.ValidationError:
        raised = True
    assert raised, "extension without 'version' must be rejected"


def test_base_allowlist_loads_and_includes_core_primitives():
    data = yaml.safe_load((ISA_DIR / "_base_latex.yaml").read_text())
    _validate(data, "base_allowlist")
    assert "textbf" in data["allowed_macros"]
    assert "item" in data["allowed_macros"]
    assert "itemize" in data["allowed_environments"]


EXT_DIR = ISA_DIR / "extensions"
EXPECTED_EXTS = ["Base", "Zsem", "SpecialFrames", "Density", "OverflowGuard"]


def test_all_standard_extensions_validate_against_schema():
    for name in EXPECTED_EXTS:
        data = yaml.safe_load((EXT_DIR / f"{name}.yaml").read_text())
        _validate(data, "extension")
        assert data["extension"] == name


def test_specialframes_declares_statementframe_and_its_lowering():
    data = yaml.safe_load((EXT_DIR / "SpecialFrames.yaml").read_text())
    cmds = [i["cmd"] for i in data["instructions"]]
    assert "statementframe" in cmds
    assert "statementframe" in data["lowering"]
