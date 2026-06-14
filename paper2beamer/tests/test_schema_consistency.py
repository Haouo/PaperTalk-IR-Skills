"""Guard against drift between ir_common (enforced) and ir_schema.json (mirror).

These three sources describe the same contract:
  * scripts/ir_common.py  — the enforced validator (source of truth)
  * references/ir_schema.json — JSON-Schema mirror for editors/tooling
  * references/*.md — human docs (not machine-checked here)

If someone adds a claim type or a frame type to one but not the other, this test
fails loudly so the docs cannot silently lie.
"""

from __future__ import annotations

import json
import os

import ir_common


def _load_schema(references_dir: str) -> dict:
    with open(os.path.join(references_dir, "ir_schema.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _enum(schema: dict, *path: str) -> set:
    node = schema
    for key in path:
        node = node[key]
    return set(node["enum"])


def test_schema_version_matches(references_dir):
    schema = _load_schema(references_dir)
    assert schema["properties"]["meta"]["properties"]["schema"]["const"] == ir_common.SCHEMA_VERSION


def test_figure_kinds_match(references_dir):
    schema = _load_schema(references_dir)
    assert _enum(schema, "$defs", "figure", "properties", "kind") == set(ir_common.FIGURE_KINDS)


def test_claim_types_match(references_dir):
    schema = _load_schema(references_dir)
    assert _enum(schema, "$defs", "claim", "properties", "type") == set(ir_common.CLAIM_TYPES)


def test_story_roles_match(references_dir):
    schema = _load_schema(references_dir)
    assert _enum(schema, "$defs", "beat", "properties", "role") == set(ir_common.STORY_ROLES)


def test_frame_types_match(references_dir):
    schema = _load_schema(references_dir)
    assert _enum(schema, "$defs", "slide", "properties", "frame_type") == set(ir_common.FRAME_TYPES)


def test_languages_match(references_dir):
    schema = _load_schema(references_dir)
    assert _enum(schema, "properties", "intent", "properties", "language") == set(ir_common.LANGUAGES)


def test_block_types_match(references_dir):
    schema = _load_schema(references_dir)
    # The block enum lives in the first branch of body_item.oneOf.
    block_branch = schema["$defs"]["body_item"]["oneOf"][0]
    assert set(block_branch["properties"]["block"]["enum"]) == set(ir_common.BLOCK_TYPES)


def test_sample_fixture_validates_against_ir_common(fixtures_dir):
    ir = ir_common.load_ir(os.path.join(fixtures_dir, "sample_build", "ir.v4.json"))
    ir_common.validate_ir(ir, "layout-pass")
