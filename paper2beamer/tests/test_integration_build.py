"""End-to-end integration: ir.v4 -> emit_beamer -> build.sh -> deck.pdf.

These tests invoke the real backend and the real XeLaTeX build, so they are the
strongest signal that the bundled theme + generated TeX actually compile. They
skip cleanly when xelatex is unavailable (e.g. minimal CI image) rather than
failing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
FIXTURES = os.path.join(HERE, "fixtures")

needs_xelatex = pytest.mark.skipif(
    shutil.which("xelatex") is None, reason="xelatex not installed"
)


def _prepare_build(tmp_path, fixture_name: str) -> str:
    """Copy a fixture build dir into tmp and return the deck.tex path after emit."""
    src = os.path.join(FIXTURES, fixture_name)
    work = os.path.join(tmp_path, fixture_name)
    shutil.copytree(src, work)
    ir = os.path.join(work, "ir.v4.json")
    deck = os.path.join(work, "deck.tex")
    emit = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "emit_beamer.py"), "--ir", ir, "--out", deck],
        capture_output=True, text=True,
    )
    assert emit.returncode == 0, emit.stderr
    assert os.path.isfile(deck)
    return deck


@needs_xelatex
def test_happy_path_builds_pdf(tmp_path):
    deck = _prepare_build(tmp_path, "sample_build")
    result = subprocess.run(
        ["bash", os.path.join(SCRIPTS, "build.sh"), deck],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    pdf = deck[:-4] + ".pdf"
    assert os.path.isfile(pdf)
    assert os.path.getsize(pdf) > 0


@needs_xelatex
def test_overflow_returns_exit_code_3(tmp_path):
    deck = _prepare_build(tmp_path, "overflow_build")
    result = subprocess.run(
        ["bash", os.path.join(SCRIPTS, "build.sh"), deck],
        capture_output=True, text=True,
    )
    # The verifier signal: overflow is exit 3, with the offending slide reported.
    assert result.returncode == 3, (
        f"expected overflow exit 3, got {result.returncode}\n{result.stderr}"
    )
    assert "overflow" in result.stderr.lower()


@needs_xelatex
def test_build_rejects_missing_deck(tmp_path):
    result = subprocess.run(
        ["bash", os.path.join(SCRIPTS, "build.sh"), os.path.join(tmp_path, "nope.tex")],
        capture_output=True, text=True,
    )
    assert result.returncode == 2  # usage/env error
