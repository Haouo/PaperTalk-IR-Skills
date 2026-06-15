"""Theme-swap invariance harness (RQ4): re-target a deck and measure the cost.

The decoupling claim is that swapping the backend theme leaves the Narrative IR
untouched and the deck still builds. This module computes the deterministic part
of that measurement:

  - narrative-edit rate: fraction of the narrative that changed (expected 0.0,
    because the harness keeps the narrative fixed across the swap);
  - conformance: whether the re-emitted deck has no error-severity violations;
  - degradations: instructions the target theme cannot express, lowered to Base
    (portability is "portable with K degradations", not a binary);
  - compiles: whether the swapped deck builds (a boolean produced by the build).

Re-emitting the Slide IR for the target theme is an agent step in the live
pipeline; the build is a heavy step. Both are run by the orchestrator/CLI and
their results are passed into `assess_swap`, keeping this function pure and
unit-testable.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass

from scripts.degrade import find_degradations
from scripts.isa_resolve import EffectiveISA


@dataclass(frozen=True)
class SwapReport:
    """RQ4 measurement for one (deck -> target theme) swap."""

    target_theme: str
    narrative_edit_rate: float
    compiles: bool
    conformant: bool
    degradations: tuple


def narrative_edit_rate(before: str, after: str) -> float:
    """Fraction of the original narrative's lines that changed across the swap.

    0.0 when the narrative is byte-identical (the decoupling claim). Otherwise the
    fraction of `before` lines not matched in `after`, via difflib.
    """
    a = before.splitlines()
    b = after.splitlines()
    if a == b:
        return 0.0
    sm = difflib.SequenceMatcher(None, a, b)
    matched = sum(block.size for block in sm.get_matching_blocks())
    total = max(len(a), 1)
    return round(1.0 - matched / total, 4)


def assess_swap(
    *,
    target_theme: str,
    narrative_before: str,
    narrative_after: str,
    used_instructions,
    source_isa: EffectiveISA,
    target_isa: EffectiveISA,
    conformance_violations,
    compiles: bool,
) -> SwapReport:
    """Combine the measured pieces of one theme swap into a SwapReport."""
    conformant = not any(v.severity == "error" for v in conformance_violations)
    return SwapReport(
        target_theme=target_theme,
        narrative_edit_rate=narrative_edit_rate(narrative_before, narrative_after),
        compiles=compiles,
        conformant=conformant,
        degradations=find_degradations(used_instructions, source_isa, target_isa),
    )
