from pathlib import Path

import pytest

from scripts.latex_log import parse_log

FIX = Path(__file__).parent / "fixtures"


def test_clean_log_has_no_errors_and_reads_page_count():
    sig = parse_log((FIX / "clean.log").read_text(), exit_code=0)
    assert sig.compile_ok is True
    assert sig.errors == ()
    assert sig.overflows == ()
    assert sig.page_count == 3


def test_error_log_captures_undefined_control_sequence_with_tex_line():
    sig = parse_log((FIX / "error.log").read_text(), exit_code=1)
    assert sig.compile_ok is False
    assert len(sig.errors) == 1
    assert "Undefined control sequence" in sig.errors[0].message
    assert sig.errors[0].tex_line == 42


def test_overflow_log_captures_slide_number():
    sig = parse_log((FIX / "overflow.log").read_text(), exit_code=1)
    assert len(sig.overflows) == 1
    assert sig.overflows[0].slide_number == 7
    assert sig.page_count == 9


def test_parse_log_rejects_non_string_input():
    with pytest.raises(TypeError):
        parse_log(None, exit_code=0)  # defensive: bad input fails fast


from scripts.latex_log import Signals, Violation


def test_signals_defaults_to_no_violations():
    sig = Signals(compile_ok=True)
    assert sig.violations == ()


def test_violation_record_is_frozen_and_carries_fields():
    v = Violation(slide_id="S03", kind="undeclared_instruction",
                  detail="\\fancybox not in ISA", severity="error")
    assert v.slide_id == "S03"
    assert v.severity == "error"


def test_overflow_guard_message_parses_even_when_log_wraps_the_slide_number():
    # LaTeX wraps log lines at ~79 cols, so the slide number can land on the
    # next line. The parser must still recover it.
    wrapped = (
        "! Package beamerthemeSimple Error: Frame body overflows the safe area on slide \n"
        "1: content is 707.25pt tall but only 234.98pt fits.\n"
    )
    sig = parse_log(wrapped, exit_code=12)
    assert any(o.slide_number == 1 for o in sig.overflows)
