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


def test_simple_theme_validates_and_declares_expected_extensions():
    data = yaml.safe_load((ISA_DIR / "Simple.yaml").read_text())
    _validate(data, "theme")
    provided = {p.split("@")[0] for p in data["provides"]}
    assert provided == {"Base", "Zsem", "SpecialFrames", "Density", "OverflowGuard", "Theorems", "Columns"}
    assert data["meta"]["aspectratio"] == "169"


from scripts.isa_resolve import resolve


def test_resolve_simple_unions_extension_and_base_instructions():
    eff = resolve("Simple", ISA_DIR)
    # From SpecialFrames + Zsem + Base:
    assert "statementframe" in eff.allowed_macros
    assert "alert" in eff.allowed_macros
    assert "section" in eff.allowed_macros
    # From the base allowlist:
    assert "textbf" in eff.allowed_macros
    assert "itemize" in eff.allowed_environments
    # Zsem blocks require a title:
    assert "block" in eff.blocks_requiring_title


def test_resolve_carries_options_and_aspectratio():
    eff = resolve("Simple", ISA_DIR)
    assert eff.aspectratio == "169"
    assert eff.options["overflowguard"]["required_value"] == "on"


def test_resolve_provides_argspecs_for_known_custom_macros():
    eff = resolve("Simple", ISA_DIR)
    # statementframe takes one mandatory arg -> pylatexenc spec "{".
    assert eff.macro_argspecs["statementframe"] == "{"
    # thanksframe takes two optional args -> "[[".
    assert eff.macro_argspecs["thanksframe"] == "[["


def test_theorems_and_columns_extensions_validate():
    for name in ["Theorems", "Columns"]:
        data = yaml.safe_load((EXT_DIR / f"{name}.yaml").read_text())
        _validate(data, "extension")
        assert data["extension"] == name



def test_madrid_real_theme_resolves_with_divergent_profile():
    data = yaml.safe_load((ISA_DIR / "Madrid.yaml").read_text())
    _validate(data, "theme")
    provided = {p.split("@")[0] for p in data["provides"]}
    # Madrid is external: shares Base+Zsem+Theorems+Columns, but provides NEITHER
    # our SpecialFrames NOR our invented OverflowGuard.
    assert {"Base", "Zsem", "Theorems", "Columns"} <= provided
    assert "SpecialFrames" not in provided
    assert "OverflowGuard" not in provided
    eff = resolve("Madrid", ISA_DIR)
    assert "theorem" in eff.allowed_environments
    assert "columns" in eff.allowed_environments
    assert "statementframe" not in eff.allowed_macros   # SpecialFrames absent
    assert "block" in eff.blocks_requiring_title        # shared Zsem


def test_resolve_collects_lowering_from_extensions():
    eff = resolve("Simple", ISA_DIR)
    # SpecialFrames declares how statementframe lowers to a Base equivalent.
    assert "statementframe" in eff.lowering
    assert eff.lowering["statementframe"]
