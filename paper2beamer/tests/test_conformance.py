from pathlib import Path

from scripts.isa_resolve import resolve
from scripts.conformance import check

ISA_DIR = Path(__file__).resolve().parents[1] / "isa"
EFF = resolve("Simple", ISA_DIR)


def test_clean_fragment_yields_no_violations():
    frames = {"S01": "\\begin{frame}{Title}\n\\begin{itemize}\\item Hi\\end{itemize}\n\\end{frame}"}
    out = check(EFF, frames=frames, preamble="")
    assert out == ()


def test_undeclared_macro_is_an_error_routed_by_slide():
    frames = {"S02": "\\begin{frame}{T}\\fancybox{x}\\end{frame}"}
    out = check(EFF, frames=frames, preamble="")
    kinds = {(v.kind, v.slide_id, v.severity) for v in out}
    assert ("undeclared_instruction", "S02", "error") in kinds


def test_declared_special_frame_is_allowed():
    frames = {"S00": "\\statementframe{One big idea}"}
    out = check(EFF, frames=frames, preamble="")
    assert out == ()


def test_block_without_title_is_an_error():
    frames = {"S03": "\\begin{frame}{T}\\begin{block}{}body\\end{block}\\end{frame}"}
    out = check(EFF, frames=frames, preamble="")
    assert any(v.kind == "block_without_title" and v.slide_id == "S03" for v in out)


def test_block_with_title_is_clean():
    frames = {"S04": "\\begin{frame}{T}\\begin{block}{Claim}body\\end{block}\\end{frame}"}
    out = check(EFF, frames=frames, preamble="")
    assert all(v.kind != "block_without_title" for v in out)


def test_undeclared_usetheme_option_is_an_error():
    preamble = "\\usetheme[density=normal,bogus=1]{Simple}"
    out = check(EFF, frames={}, preamble=preamble)
    assert any(v.kind == "bad_option" and v.severity == "error" for v in out)


def test_missing_overflowguard_on_is_an_error():
    preamble = "\\usetheme[density=normal]{Simple}"  # overflowguard not set to on
    out = check(EFF, frames={}, preamble=preamble)
    assert any(v.kind == "bad_option" and "overflowguard" in v.detail for v in out)
