from pathlib import Path

from scripts.isa_resolve import resolve
from scripts.theme_swap import narrative_edit_rate, assess_swap, SwapReport

ISA_DIR = Path(__file__).resolve().parents[1] / "isa"
SIMPLE = resolve("Simple", ISA_DIR)
MADRID = resolve("Madrid", ISA_DIR)


def test_identical_narrative_has_zero_edit_rate():
    n = "N01 goal: motivate\nN02 goal: method\nN03 goal: results\n"
    assert narrative_edit_rate(n, n) == 0.0


def test_changed_narrative_has_positive_edit_rate():
    before = "N01 goal: motivate\nN02 goal: method\nN03 goal: results\n"
    after = "N01 goal: motivate\nN02 goal: NEW METHOD\nN03 goal: results\n"
    rate = narrative_edit_rate(before, after)
    assert 0.0 < rate <= 1.0


def test_assess_swap_reports_zero_edits_and_degradations_for_simple_to_madrid():
    narrative = "N01 goal: motivate\nN02 goal: method\n"
    used = {"statementframe", "frame", "itemize", "block"}  # statementframe absent in Madrid
    report = assess_swap(
        target_theme="Madrid",
        narrative_before=narrative,
        narrative_after=narrative,          # harness keeps the narrative fixed
        used_instructions=used,
        source_isa=SIMPLE,
        target_isa=MADRID,
        conformance_violations=(),
        compiles=True,
    )
    assert isinstance(report, SwapReport)
    assert report.narrative_edit_rate == 0.0           # the decoupling claim
    assert report.compiles is True
    assert report.conformant is True
    assert any(d.instruction == "statementframe" for d in report.degradations)


def test_assess_swap_marks_nonconformant_on_error_violation():
    from scripts.latex_log import Violation
    report = assess_swap(
        target_theme="Madrid",
        narrative_before="N01\n", narrative_after="N01\n",
        used_instructions={"frame"},
        source_isa=SIMPLE, target_isa=MADRID,
        conformance_violations=(Violation("S01", "undeclared_instruction", "x", "error"),),
        compiles=True,
    )
    assert report.conformant is False
