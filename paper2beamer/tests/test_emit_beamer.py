"""Tests for the deterministic backend (emit_beamer): golden render + behaviours."""

from __future__ import annotations

import os

import pytest

import emit_beamer
import ir_common
from ir_common import IRValidationError


def _load_sample(fixtures_dir: str) -> dict:
    return ir_common.load_ir(os.path.join(fixtures_dir, "sample_build", "ir.v4.json"))


def test_golden_render_matches(fixtures_dir):
    """The sample IR must render byte-for-byte to the frozen golden deck.

    This locks the backend's output: any accidental change to spacing, escaping,
    or command choice shows up as a diff here.
    """
    ir = _load_sample(fixtures_dir)
    out_dir = os.path.join(fixtures_dir, "sample_build")
    rendered = emit_beamer.render(ir, out_dir)
    with open(os.path.join(fixtures_dir, "deck.expected.tex"), encoding="utf-8") as fh:
        expected = fh.read()
    assert rendered == expected


def test_render_escapes_special_characters(fixtures_dir):
    ir = _load_sample(fixtures_dir)
    out_dir = os.path.join(fixtures_dir, "sample_build")
    tex = emit_beamer.render(ir, out_dir)
    assert r"50\% \& more" in tex          # escaped
    assert "50% & more" not in tex          # raw must not survive


def test_safe_width_whitelist():
    assert emit_beamer._safe_width("0.7\\textwidth") == "0.7\\textwidth"
    assert emit_beamer._safe_width("\\linewidth") == "\\linewidth"
    assert emit_beamer._safe_width("5cm") == "5cm"
    # Injection / garbage falls back to the safe default.
    assert emit_beamer._safe_width("}\\evil{") == emit_beamer._DEFAULT_WIDTH
    assert emit_beamer._safe_width(None) == emit_beamer._DEFAULT_WIDTH
    assert emit_beamer._safe_width("99") == emit_beamer._DEFAULT_WIDTH


def test_missing_figure_emits_placeholder(fixtures_dir):
    ir = _load_sample(fixtures_dir)
    out_dir = os.path.join(fixtures_dir, "sample_build")
    tex = emit_beamer.render(ir, out_dir)
    assert "[missing figure: figmissing]" in tex
    assert "does-not-exist.png" not in tex   # never \includegraphics a missing file


def test_present_figure_is_included(fixtures_dir):
    ir = _load_sample(fixtures_dir)
    out_dir = os.path.join(fixtures_dir, "sample_build")
    tex = emit_beamer.render(ir, out_dir)
    assert r"\includegraphics" in tex
    assert "figures/fig1.png" in tex


def test_theme_options_dense_for_short_talk():
    intent = {"occasion": "conference", "duration_min": 10}
    opts = emit_beamer._theme_options(intent)
    assert "density=dense" in opts
    assert "overflowguard=on" in opts
    assert "eyebrow={CONFERENCE TALK}" in opts


def test_theme_options_normal_for_long_talk():
    intent = {"occasion": "defense", "duration_min": 45}
    opts = emit_beamer._theme_options(intent)
    assert "density=normal" in opts


def test_render_rejects_incomplete_ir():
    # A v0 IR (no slides) must be rejected when fed to the backend's run().
    ir = {
        "meta": {"schema": ir_common.SCHEMA_VERSION, "ir_version": "v0",
                 "source_pdf": "/x", "produced_by_pass": "frontend"},
        "paper": {"title": "t", "sections": [{"id": "s1", "title": "a", "text": "b"}]},
        "figures": [],
    }
    with pytest.raises(IRValidationError):
        ir_common.validate_ir(ir, "layout-pass")


def test_run_writes_file(tmp_path, fixtures_dir):
    ir_path = os.path.join(fixtures_dir, "sample_build", "ir.v4.json")
    out = os.path.join(tmp_path, "deck.tex")
    emit_beamer.run(ir_path, out)
    assert os.path.isfile(out)
    assert open(out, encoding="utf-8").read().rstrip().endswith(r"\end{document}")
