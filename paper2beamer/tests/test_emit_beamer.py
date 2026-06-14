import json
from pathlib import Path

import pytest

from scripts.emit_beamer import assemble

FIX = Path(__file__).parent / "fixtures" / "golden-deck"


def test_assemble_writes_main_tex_with_provenance_comments(tmp_path):
    assemble(FIX, tmp_path)
    tex = (tmp_path / "main.tex").read_text()
    assert "% slide:S01 beat:N01" in tex
    assert "\\begin{document}" in tex and "\\end{document}" in tex
    # Frames appear in order.
    assert tex.index("First content frame") < tex.index("Second content frame")


def test_provenance_assigns_content_numbers_skipping_plain_frames(tmp_path):
    assemble(FIX, tmp_path)
    prov = json.loads((tmp_path / "provenance.json").read_text())
    by_id = {f["slide_id"]: f for f in prov["frames"]}
    # S00 is a plain title frame -> no content number.
    assert by_id["S00"]["content_number"] is None
    # S01, S02 are the 1st and 2nd numbered content frames.
    assert by_id["S01"]["content_number"] == 1
    assert by_id["S02"]["content_number"] == 2
    # Line ranges are present and ordered.
    assert by_id["S01"]["tex_start"] < by_id["S01"]["tex_end"] <= by_id["S02"]["tex_start"]


def test_assemble_rejects_missing_fragment(tmp_path):
    bad = tmp_path / "manifest"
    (bad / "frames").mkdir(parents=True)
    (bad / "preamble.tex").write_text("\\documentclass{beamer}")
    (bad / "order.txt").write_text("S01 beat:N01\n")  # fragment file missing
    with pytest.raises(FileNotFoundError):
        assemble(bad, tmp_path / "out")
