from scripts.latex_log import CompileError, Overflow, Signals
from scripts.repair_router import (
    IntentBudget,
    Provenance,
    RepairDirective,
    route,
)

# A tiny provenance map: S07 is content frame 7, spanning tex lines 40-55.
PROV = Provenance(
    frames=(
        {"slide_id": "S07", "beat_id": "N03", "content_number": 7, "tex_start": 40, "tex_end": 55},
        {"slide_id": "S08", "beat_id": "N03", "content_number": 8, "tex_start": 56, "tex_end": 70},
    )
)


def test_compile_error_routes_to_tex_level_resolving_frame_by_line():
    sig = Signals(
        compile_ok=False,
        errors=(CompileError("Undefined control sequence", tex_line=42, raw=""),),
    )
    out = route(sig, PROV, budget=None, attempts={})
    assert out == (
        RepairDirective(level="tex", target_id="S07", reason="Undefined control sequence"),
    )


def test_overflow_routes_to_slide_level_resolving_by_content_number():
    sig = Signals(compile_ok=False, overflows=(Overflow(slide_number=7, detail="..."),))
    out = route(sig, PROV, budget=None, attempts={})
    assert out[0].level == "slide"
    assert out[0].target_id == "S07"


def test_page_over_budget_routes_to_narrative_cut():
    sig = Signals(compile_ok=True, page_count=30)
    out = route(sig, PROV, budget=IntentBudget(min_pages=12, max_pages=18), attempts={})
    assert out[0].level == "narrative"
    assert "cut" in out[0].reason.lower()


def test_unbounded_intent_never_routes_page_count():
    sig = Signals(compile_ok=True, page_count=300)
    out = route(sig, PROV, budget=None, attempts={})  # None = "length unbounded"
    assert all(d.level != "narrative" for d in out)


def test_slide_overflow_escalates_to_narrative_after_two_attempts():
    sig = Signals(compile_ok=False, overflows=(Overflow(slide_number=7, detail="..."),))
    out = route(sig, PROV, budget=None, attempts={"S07": 2})
    assert out[0].level == "narrative"  # trimming twice didn't help -> cut the beat
    assert out[0].target_id == "N03"


def test_clean_build_within_budget_yields_no_directives():
    sig = Signals(compile_ok=True, page_count=15)
    out = route(sig, PROV, budget=IntentBudget(min_pages=12, max_pages=18), attempts={})
    assert out == ()
