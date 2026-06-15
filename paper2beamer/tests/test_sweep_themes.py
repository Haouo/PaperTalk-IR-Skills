"""Theme-swap sweep harness. Heavy: builds decks across the theme matrix.

Run with:  uv run pytest tests/test_sweep_themes.py -m heavy
"""
from pathlib import Path

import pytest

from scripts.sweep_themes import swap_and_measure


def _manifest(tmp: Path) -> Path:
    (tmp / "frames").mkdir(parents=True)
    (tmp / "preamble.tex").write_text(
        "\\documentclass[aspectratio=169]{beamer}\n"
        "\\usetheme[overflowguard=on]{Simple}\n"
        "\\title[T]{T}\\author{A}\\date{}\n")
    (tmp / "order.txt").write_text("S00 beat:N00 plain\nS01 beat:N01\nS02 beat:N02 plain\n")
    (tmp / "frames" / "S00.tex").write_text("\\titleframe\n")
    (tmp / "frames" / "S01.tex").write_text(
        "\\begin{frame}{C}\\begin{itemize}\\item a\\item b\\end{itemize}"
        "\\begin{block}{Claim}x\\end{block}\\end{frame}\n")
    (tmp / "frames" / "S02.tex").write_text("\\thanksframe[Thanks][Q?]\n")
    return tmp


@pytest.mark.heavy
def test_sweep_swaps_compile_and_degrade_special_frames(tmp_path):
    m = _manifest(tmp_path / "manifest")
    rows = swap_and_measure(m, "Simple", ["Simple", "Madrid"], tmp_path / "out")
    by = {r["target"]: r for r in rows}
    # source theme: no degradations
    assert by["Simple"]["compiles"] and by["Simple"]["conformant"]
    assert by["Simple"]["degradations"] == []
    # stock theme lacking SpecialFrames: compiles + conforms after lowering the 2 frames
    assert by["Madrid"]["compiles"] and by["Madrid"]["conformant"]
    assert set(by["Madrid"]["degradations"]) == {"titleframe", "thanksframe"}
