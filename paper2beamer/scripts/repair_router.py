"""Route build signals to the lowest IR level that can resolve them.

This module is the heart of "repair-at-the-right-level". It is a pure function:
given what the build reported (Signals), how frames map to IR units (Provenance),
the intent's page budget, and how many times we have already tried each target,
it returns directives saying *edit this level, this unit, for this reason*. It
never regenerates the whole deck and it never mutates its inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from scripts.latex_log import Signals

# After this many failed attempts at one slide, stop trimming and escalate to
# cutting the beat in the Narrative IR (the design's stop-loss rule).
ESCALATION_THRESHOLD = 2


@dataclass(frozen=True)
class IntentBudget:
    """Target page range derived from a stated talk duration.

    A value of ``None`` passed to :func:`route` (not an instance with zero
    pages) means the intent left length unbounded, which disables page routing.
    """

    min_pages: int
    max_pages: int


@dataclass(frozen=True)
class Provenance:
    """Ordered frame records mapping deck frames back to their IR units.

    Each record is a dict with: ``slide_id``, ``beat_id``, ``content_number``
    (int for numbered content frames, ``None`` for plain/unnumbered ones),
    ``tex_start`` and ``tex_end`` (1-based inclusive line range in main.tex).
    """

    frames: tuple[dict, ...] = ()

    def frame_at_line(self, line: Optional[int]) -> Optional[dict]:
        """Find the frame whose tex line range contains ``line``."""
        if line is None:
            return None
        for f in self.frames:
            if f["tex_start"] <= line <= f["tex_end"]:
                return f
        return None

    def frame_by_content_number(self, n: Optional[int]) -> Optional[dict]:
        """Find the frame TeX numbered ``n`` among content (non-plain) frames."""
        if n is None:
            return None
        for f in self.frames:
            if f.get("content_number") == n:
                return f
        return None


@dataclass(frozen=True)
class RepairDirective:
    """One instruction: edit ``target_id`` at ``level`` because of ``reason``."""

    level: str  # "tex" | "slide" | "narrative"
    target_id: Optional[str]
    reason: str


def route(
    sig: Signals,
    prov: Provenance,
    budget: Optional[IntentBudget],
    attempts: dict[str, int],
) -> tuple[RepairDirective, ...]:
    """Produce repair directives from one build's signals. Pure function."""
    if not isinstance(attempts, dict):
        raise TypeError("attempts must be a dict of target_id -> count")

    directives: list[RepairDirective] = []

    # 1. Compile errors -> fix the .tex of the offending frame (or whole file).
    for err in sig.errors:
        frame = prov.frame_at_line(err.tex_line)
        directives.append(
            RepairDirective(
                level="tex",
                target_id=frame["slide_id"] if frame else None,
                reason=err.message,
            )
        )

    # 1b. ISA conformance violations (static, pre-build). Only errors route;
    #     warns are reported elsewhere. Mirrors compile->tex / overflow->slide.
    _VIOLATION_LEVEL = {
        "undeclared_instruction": "tex",
        "bad_option": "tex",
        "bad_aspectratio": "tex",
        "block_without_title": "slide",
    }
    for v in sig.violations:
        if v.severity != "error":
            continue
        level = _VIOLATION_LEVEL.get(v.kind, "tex")
        target = v.slide_id if v.slide_id is not None else "preamble"
        directives.append(
            RepairDirective(level=level, target_id=target, reason=v.detail)
        )

    # 2. Overflow -> trim that slide; escalate to Narrative after repeated tries.
    for ov in sig.overflows:
        frame = prov.frame_by_content_number(ov.slide_number)
        slide_id = frame["slide_id"] if frame else None
        tried = attempts.get(slide_id, 0) if slide_id else 0
        if slide_id and tried >= ESCALATION_THRESHOLD:
            directives.append(
                RepairDirective(
                    level="narrative",
                    target_id=frame["beat_id"],
                    reason=f"slide {slide_id} still overflows after {tried} trims; "
                    f"cut or shrink the beat",
                )
            )
        else:
            directives.append(
                RepairDirective(
                    level="slide",
                    target_id=slide_id,
                    reason="frame body overflows the safe area; split or trim",
                )
            )

    # 3. Page count vs intent budget -> Narrative cut/expand. Skipped if unbounded.
    if budget is not None and sig.page_count is not None:
        if sig.page_count > budget.max_pages:
            directives.append(
                RepairDirective(
                    level="narrative",
                    target_id=None,
                    reason=f"deck is {sig.page_count} pages, over the "
                    f"{budget.max_pages}-page budget; cut or merge beats",
                )
            )
        elif sig.page_count < budget.min_pages:
            directives.append(
                RepairDirective(
                    level="narrative",
                    target_id=None,
                    reason=f"deck is {sig.page_count} pages, under the "
                    f"{budget.min_pages}-page budget; expand or add depth",
                )
            )

    return tuple(directives)
