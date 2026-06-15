"""Detect instructions that must be lowered when swapping to a target theme.

When a deck written for one theme is re-targeted to another, any instruction the
target theme does NOT provide (because it lacks the extension that defines it)
must be lowered to its Base equivalent. The lowering description is declared by
the defining extension (see each extension's `lowering:` block) and carried on the
source theme's EffectiveISA. This module reports those degradations; it does not
rewrite LaTeX (the emission pass does that, guided by these descriptions). RQ4
reports the degradation count as the honest measure that portability is
"portable with K degradations," not a binary.
"""
from __future__ import annotations

from dataclasses import dataclass

from scripts.isa_resolve import EffectiveISA


@dataclass(frozen=True)
class Degradation:
    """One instruction the target lacks, with the Base equivalent to emit instead."""

    instruction: str
    lowering: str


def find_degradations(used, source: EffectiveISA, target: EffectiveISA) -> tuple:
    """Instructions in `used` that the target cannot express, with their lowering.

    `used` is the set of macro/environment names the deck actually uses. An
    instruction degrades if the target provides neither the macro nor the
    environment of that name; its lowering comes from the source theme's
    extension that defines it.
    """
    target_known = target.allowed_macros | target.allowed_environments
    out = []
    for instr in sorted(used):
        if instr in target_known:
            continue
        lowering = source.lowering.get(instr)
        if lowering is not None:
            out.append(Degradation(instruction=instr, lowering=lowering))
    return tuple(out)
