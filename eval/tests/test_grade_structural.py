"""Unit tests for the deterministic eval grader.

The clean-run fixture under tests/fixtures/clean-run mirrors a real
slides/<slug>/ output directory and should pass every decidable criterion. The
rest of the tests drive the pure per-criterion functions with crafted inputs so
each failure mode is pinned down without needing a full run on disk.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import grade_structural as gs  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "clean-run"
SLIDES = FIXTURE / "slides" / "sample"
MANIFEST = FIXTURE / "manifest.json"


# --- end-to-end on the clean fixture ----------------------------------------


def test_clean_run_has_no_failures():
    results = gs.grade(SLIDES, MANIFEST)
    failed = [c for c in results if c.status == gs.FAIL]
    assert failed == [], f"unexpected failures: {[(c.id, c.detail) for c in failed]}"


def test_clean_run_covers_all_seven_criteria():
    ids = {c.id for c in gs.grade(SLIDES, MANIFEST)}
    assert ids == {
        "compiles", "no_overflow", "page_budget", "provenance",
        "figures_from_docling", "local_repair", "one_gate",
    }


def test_missing_manifest_marks_process_criteria_unverified():
    results = {c.id: c for c in gs.grade(SLIDES, manifest_path=None)}
    assert results["local_repair"].status == gs.UNVERIFIED
    assert results["one_gate"].status == gs.UNVERIFIED


# --- page budget -------------------------------------------------------------


def test_parse_page_budget_bounded():
    assert gs.parse_page_budget("- page-budget: 12–18 content slides") == (12, 18)


def test_parse_page_budget_unbounded_returns_none():
    assert gs.parse_page_budget("- page-budget: none (unbounded)") is None


def test_parse_page_budget_unparseable_raises():
    with pytest.raises(ValueError):
        gs.parse_page_budget("- page-budget: lots")


def test_parse_page_budget_missing_line_raises():
    with pytest.raises(ValueError):
        gs.parse_page_budget("## Talk meta\n- time-budget: 15 minutes")


def test_count_content_frames_ignores_plain():
    prov = {"frames": [
        {"content_number": None}, {"content_number": 1}, {"content_number": 2},
    ]}
    assert gs.count_content_frames(prov) == 2


def test_page_budget_out_of_range_fails():
    narrative = "- page-budget: 12–18 content slides"
    prov = {"frames": [{"content_number": 1}, {"content_number": 2}]}
    assert gs.check_page_budget(narrative, prov).status == gs.FAIL


def test_page_budget_unbounded_skips():
    narrative = "- page-budget: none (unbounded)"
    prov = {"frames": [{"content_number": 1}]}
    assert gs.check_page_budget(narrative, prov).status == gs.SKIP


# --- provenance --------------------------------------------------------------


def _tex(*frames: str) -> str:
    head = ["\\documentclass{beamer}", "\\begin{document}"]
    return "\n".join(head + list(frames) + ["\\end{document}"])


def test_provenance_wrong_comment_fails():
    main_tex = _tex("% slide:S01 beat:N99", "\\begin{frame}{x}", "\\end{frame}")
    prov = {"frames": [{"slide_id": "S01", "beat_id": "N01", "content_number": 1,
                        "tex_start": 4, "tex_end": 5}]}
    assert gs.check_provenance(main_tex, prov).status == gs.FAIL


def test_provenance_duplicate_id_fails():
    prov = {"frames": [
        {"slide_id": "S01", "beat_id": "N01", "content_number": 1, "tex_start": 4, "tex_end": 5},
        {"slide_id": "S01", "beat_id": "N02", "content_number": 2, "tex_start": 6, "tex_end": 7},
    ]}
    assert gs.check_provenance(_tex(), prov).status == gs.FAIL


def test_provenance_overlap_fails():
    main_tex = "\n".join([
        "\\documentclass{beamer}", "\\begin{document}",
        "% slide:S01 beat:N01", "\\begin{frame}{a}", "\\end{frame}",
        "% slide:S02 beat:N02", "\\begin{frame}{b}", "\\end{frame}",
        "\\end{document}",
    ])
    prov = {"frames": [
        {"slide_id": "S01", "beat_id": "N01", "content_number": 1, "tex_start": 4, "tex_end": 7},
        {"slide_id": "S02", "beat_id": "N02", "content_number": 2, "tex_start": 7, "tex_end": 8},
    ]}
    assert gs.check_provenance(main_tex, prov).status == gs.FAIL


def test_provenance_empty_frames_fails():
    assert gs.check_provenance(_tex(), {"frames": []}).status == gs.FAIL


# --- figures -----------------------------------------------------------------


def test_figures_all_present_passes(tmp_path):
    figs = tmp_path / "figures"
    figs.mkdir()
    (figs / "figure-001.png").touch()
    main_tex = "\\includegraphics[width=\\linewidth]{figures/figure-001}"
    assert gs.check_figures(main_tex, figs).status == gs.PASS


def test_figures_missing_file_fails(tmp_path):
    figs = tmp_path / "figures"
    figs.mkdir()
    main_tex = "\\includegraphics{figures/figure-404}"
    assert gs.check_figures(main_tex, figs).status == gs.FAIL


def test_figures_outside_dir_fails(tmp_path):
    figs = tmp_path / "figures"
    figs.mkdir()
    (figs / "x.png").touch()
    main_tex = "\\includegraphics{/etc/passwd}"
    assert gs.check_figures(main_tex, figs).status == gs.FAIL


def test_figures_none_referenced_passes(tmp_path):
    figs = tmp_path / "figures"
    figs.mkdir()
    assert gs.check_figures("no graphics here", figs).status == gs.PASS


# --- process properties ------------------------------------------------------


def test_local_repair_full_regen_fails():
    manifest = {"rebuilds": [{"attempt": 1, "level": "tex", "full_regen": True}]}
    assert gs.check_local_repair(manifest).status == gs.FAIL


def test_local_repair_bad_level_fails():
    manifest = {"rebuilds": [{"attempt": 1, "level": "everything", "full_regen": False}]}
    assert gs.check_local_repair(manifest).status == gs.FAIL


def test_local_repair_no_repairs_passes():
    assert gs.check_local_repair({"rebuilds": []}).status == gs.PASS


def test_local_repair_no_manifest_unverified():
    assert gs.check_local_repair(None).status == gs.UNVERIFIED


def test_one_gate_two_approvals_fails():
    assert gs.check_one_gate({"gate_approvals": 2}).status == gs.FAIL


def test_one_gate_exactly_one_passes():
    assert gs.check_one_gate({"gate_approvals": 1}).status == gs.PASS


def test_one_gate_missing_field_unverified():
    assert gs.check_one_gate({}).status == gs.UNVERIFIED
