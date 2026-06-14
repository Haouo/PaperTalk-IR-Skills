"""Unit tests for ir_common: escaping, atomic IO, and stage-aware validation."""

from __future__ import annotations

import json
import os

import pytest

import ir_common
from ir_common import IRValidationError, escape_latex, load_ir, save_ir, validate_ir


# --- escape_latex ----------------------------------------------------------

def test_escape_latex_handles_all_specials():
    assert escape_latex("50% & $x_i$ #{a}") == r"50\% \& \$x\_i\$ \#\{a\}"


def test_escape_latex_backslash_first():
    # The backslash must be escaped before the others, or the introduced
    # backslashes would be double-escaped.
    assert escape_latex("a\\b") == r"a\textbackslash{}b"


def test_escape_latex_coerces_non_strings():
    assert escape_latex(None) == ""
    assert escape_latex(42) == "42"
    assert escape_latex(3.5) == "3.5"


# --- atomic IO -------------------------------------------------------------

def test_save_then_load_roundtrip(tmp_path):
    path = os.path.join(tmp_path, "ir.json")
    data = {"meta": {"x": 1}, "unicode": "café — 中文"}
    save_ir(path, data)
    assert load_ir(path) == data


def test_save_is_atomic_no_temp_left_behind(tmp_path):
    path = os.path.join(tmp_path, "ir.json")
    save_ir(path, {"a": 1})
    leftovers = [p for p in os.listdir(tmp_path) if p.startswith(".ir-")]
    assert leftovers == []


def test_load_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_ir(os.path.join(tmp_path, "nope.json"))


def test_load_corrupt_json_raises_irvalidationerror(tmp_path):
    path = os.path.join(tmp_path, "bad.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{ not valid")
    with pytest.raises(IRValidationError):
        load_ir(path)


def test_load_non_object_raises(tmp_path):
    path = os.path.join(tmp_path, "list.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([1, 2, 3], fh)
    with pytest.raises(IRValidationError):
        load_ir(path)


# --- validation ------------------------------------------------------------

def _minimal_v0() -> dict:
    # Includes a valid intent block so stage validation at content/figure/layout
    # passes exercises the real fields rather than tripping on a missing intent.
    # The pure-frontend tests validate at stage "frontend", where intent is
    # simply ignored, so its presence is harmless there.
    return {
        "meta": {
            "schema": ir_common.SCHEMA_VERSION,
            "ir_version": "v0",
            "source_pdf": "/x.pdf",
            "produced_by_pass": "frontend",
        },
        "intent": {"occasion": "journal-club", "duration_min": 30, "language": "en"},
        "paper": {
            "title": "T",
            "sections": [{"id": "sec1", "title": "Intro", "text": "body"}],
        },
        "figures": [
            {"id": "fig1", "kind": "figure", "path": "figures/fig1.png"}
        ],
    }


def test_valid_v0_passes():
    validate_ir(_minimal_v0(), "frontend")


def test_wrong_schema_version_rejected():
    ir = _minimal_v0()
    ir["meta"]["schema"] = "0.9"
    with pytest.raises(IRValidationError) as exc:
        validate_ir(ir, "frontend")
    assert exc.value.path == "meta.schema"


def test_duplicate_section_id_rejected():
    ir = _minimal_v0()
    ir["paper"]["sections"].append({"id": "sec1", "title": "Dup", "text": "x"})
    with pytest.raises(IRValidationError):
        validate_ir(ir, "frontend")


def test_bad_figure_kind_rejected():
    ir = _minimal_v0()
    ir["figures"][0]["kind"] = "photo"
    with pytest.raises(IRValidationError):
        validate_ir(ir, "frontend")


def test_intent_required_after_intake():
    ir = _minimal_v0()
    del ir["intent"]
    # Without an intent block, validating at the intake stage must fail.
    with pytest.raises(IRValidationError):
        validate_ir(ir, "intent-intake")
    ir["intent"] = {"occasion": "defense", "duration_min": 45, "language": "en"}
    validate_ir(ir, "intent-intake")


def test_intent_bad_language_rejected():
    ir = _minimal_v0()
    ir["intent"] = {"occasion": "defense", "duration_min": 45, "language": "fr"}
    with pytest.raises(IRValidationError):
        validate_ir(ir, "intent-intake")


def test_claim_salience_out_of_range_rejected():
    ir = _minimal_v0()
    ir["claims"] = [
        {"id": "c1", "type": "result", "statement": "s", "salience": 1.5}
    ]
    with pytest.raises(IRValidationError):
        validate_ir(ir, "content-pass")


def test_claim_dangling_figure_ref_rejected():
    ir = _minimal_v0()
    ir["claims"] = [
        {"id": "c1", "type": "result", "statement": "s", "salience": 0.5,
         "figure_refs": ["figDOESNOTEXIST"]}
    ]
    with pytest.raises(IRValidationError):
        validate_ir(ir, "content-pass")


def test_story_more_than_one_primary_figure_rejected():
    ir = _minimal_v0()
    ir["claims"] = []
    ir["story"] = [
        {"id": "u1", "role": "method", "headline": "h",
         "figures": [
             {"figure_id": "fig1", "role": "primary"},
             {"figure_id": "fig1", "role": "primary"},
         ]}
    ]
    with pytest.raises(IRValidationError):
        validate_ir(ir, "figure-pass")


def test_story_one_primary_plus_secondary_ok():
    ir = _minimal_v0()
    ir["figures"].append({"id": "fig2", "kind": "figure", "path": "figures/fig2.png"})
    ir["claims"] = []
    ir["story"] = [
        {"id": "u1", "role": "method", "headline": "h",
         "figures": [
             {"figure_id": "fig1", "role": "primary"},
             {"figure_id": "fig2", "role": "context"},
         ]}
    ]
    validate_ir(ir, "figure-pass")


def test_slides_empty_rejected():
    ir = _minimal_v0()
    ir["claims"] = []
    ir["story"] = []
    ir["slides"] = []
    with pytest.raises(IRValidationError):
        validate_ir(ir, "layout-pass")


def test_slide_body_item_without_block_or_figure_rejected():
    ir = _minimal_v0()
    ir["claims"] = []
    ir["story"] = []
    ir["slides"] = [
        {"frame_type": "frame", "title": "t", "body": [{"oops": 1}]}
    ]
    with pytest.raises(IRValidationError):
        validate_ir(ir, "layout-pass")
