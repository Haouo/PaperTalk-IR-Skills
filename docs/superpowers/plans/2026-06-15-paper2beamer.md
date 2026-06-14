# paper2beamer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an LLVM-IR-inspired Claude Code skill that turns a paper PDF into a Beamer deck through three Markdown IR levels (Narrative → Slide → `.tex`) plus a pluggable theme-as-ISA layer, with intent capture, one human review gate, and provenance-driven repair-at-the-right-level.

**Architecture:** A single `paper2beamer/SKILL.md` orchestrator drives the pipeline in the main context. Deterministic work (Docling figure/structure extraction, LaTeX-log signal parsing, deck assembly, repair routing) lives in small, unit-tested Python modules under `paper2beamer/scripts/`, run via `uv`. The creative passes (Narrative IR, Slide IR, per-frame LaTeX emission) are LLM steps guided by reference files under `paper2beamer/references/`. Compilation uses `latexmk -xelatex`; the bundled Simple theme's `overflowguard=on` turns frame overflow into a hard, per-frame signal. Provenance (`Nxx`/`Sxx` IDs + `% slide:Sxx beat:Nyy` comments + `provenance.json`) lets every compile signal route back to exactly one IR unit at the right level.

**Tech Stack:** Python 3.11+ via `uv`, Docling (PDF ingest), LaTeX (`xelatex`/`latexmk`), pytest, GitHub Actions, Beamer.

**Cross-cutting requirements (apply to EVERY task):**
- **Defensive programming.** Validate every input at the boundary (file exists, type, value range). Fail fast with a clear, actionable message. Never trust external data (PDF, LaTeX log, IR files). No silent failures.
- **Full comments in clear, simple English.** Every module, public function, and non-obvious block gets a comment explaining *why*, not just *what*.
- **Immutability.** Pure functions where possible; return new values rather than mutating inputs.
- **Small focused files** (<400 lines target, 800 hard max).

---

## File Structure

```
paper2beamer/                       # the skill package
  SKILL.md                          # orchestrator: the pipeline, gate, repair loop
  references/                       # progressively-disclosed pass guides (LLM-read)
    pipeline-overview.md
    ir-format.md                    # the structured-Markdown schemas + provenance rules
    intent.md
    ingest.md
    narrative-ir.md
    review-gate.md
    slide-ir.md
    emission.md
    compile-verify.md
    repair.md
    isa-setup.md
    domain-setup.md
  isa/
    Simple.md                       # PRE-BUILT ISA for the bundled Simple theme
  scripts/                          # deterministic, unit-tested Python + shell
    __init__.py
    frontend_docling.py             # PDF -> figures/ + paper-content.md (Docling)
    latex_log.py                    # main.log + exit status -> normalized signals
    repair_router.py                # signals + provenance + intent -> repair directives
    emit_beamer.py                  # build manifest -> main.tex + provenance.json
    build.sh                        # latexmk -xelatex wrapper (2 passes, TEXINPUTS)
  tests/
    __init__.py
    test_latex_log.py
    test_repair_router.py
    test_emit_beamer.py
    test_frontend_docling.py
    fixtures/
      overflow.log
      error.log
      clean.log
      golden-deck/                  # tiny build manifest for emit_beamer + smoke build
        preamble.tex
        order.txt
        frames/S01.tex
        frames/S02.tex
  pyproject.toml                    # uv project; deps: docling; dev: pytest
template/                           # EXISTING workspace theme scaffolding (do not move)
  beamerthemeSimple.sty
  beamerthemeSimple-manual.md
  theme.tex
  demo-theme.tex
  domain.md
docs/
  design-philosophy.md             # academic-style English: the LLVM analogy & rationale
  ir-and-isa.md                    # academic-style English: IR levels, ISA, provenance deep-dive
  VERIFICATION.md                  # the full verification plan (manual + automated)
README.md
README-zh-TW.md
CONTRIBUTING.md
TUTORIAL.md
TUTORIAL-zh-TW.md
.github/workflows/ci.yml
.gitignore                          # add: slides/, **/__pycache__, .pytest_cache, *.aux/.log build junk
```

**Working directories created at runtime (gitignored), NOT in the repo:**
```
isa/<Theme>.md                      # user themes, written by ISA setup
slides/<paper-slug>/                # one folder per converted paper
  source.pdf  figures/  paper-content.md  narrative.md  slides.md
  build/{preamble.tex,order.txt,frames/*.tex}  main.tex  provenance.json  main.pdf
  repair-report.md
```

---

## Phase 0 — Branch, tooling foundation, CI

### Task 0.1: Create the feature branch

- [ ] **Step 1: Branch off main**

Run:
```bash
git checkout -b feat/paper2beamer-skill
git status
```
Expected: on branch `feat/paper2beamer-skill`; untracked `template/`, `LICENSE.md`, `.gitignore`, `docs/`.

- [ ] **Step 2: Commit the already-written design + plan + existing template as the baseline**

```bash
git add docs/ template/ LICENSE.md .gitignore .claude/settings.local.json
git commit -m "chore: baseline design, plan, and Simple theme scaffolding"
```

### Task 0.2: Python project for the deterministic scripts (`uv`)

**Files:**
- Create: `paper2beamer/pyproject.toml`
- Create: `paper2beamer/scripts/__init__.py` (empty)
- Create: `paper2beamer/tests/__init__.py` (empty)

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "paper2beamer"
version = "0.1.0"
description = "Deterministic tooling for the paper2beamer skill (ingest, log parsing, deck assembly, repair routing)."
requires-python = ">=3.11"
# Docling is the deterministic PDF ingest engine. Pinned to a major line so the
# extraction behaviour the skill relies on does not shift under us.
dependencies = [
    "docling>=2,<3",
]

[dependency-groups]
dev = [
    "pytest>=8",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
# Heavy, network/model-downloading tests are marked 'heavy' and skipped in CI.
markers = ["heavy: tests that run the full Docling model pipeline"]
addopts = "-m 'not heavy'"
```

- [ ] **Step 2: Create the empty package markers**

```bash
mkdir -p paper2beamer/scripts paper2beamer/tests/fixtures
touch paper2beamer/scripts/__init__.py paper2beamer/tests/__init__.py
```

- [ ] **Step 3: Verify the environment resolves**

Run: `cd paper2beamer && uv sync && uv run pytest -q`
Expected: dependencies resolve; pytest collects 0 tests and exits 0 (or "no tests ran").

- [ ] **Step 4: Commit**

```bash
git add paper2beamer/pyproject.toml paper2beamer/scripts/__init__.py paper2beamer/tests/__init__.py
git commit -m "chore: scaffold paper2beamer uv project and test layout"
```

### Task 0.3: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  python:
    name: Python tooling (lint + unit tests)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: paper2beamer
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Sync (dev deps only, skip heavy docling models)
        # We install the dev group but DO NOT run heavy Docling model tests in CI.
        run: uv sync --group dev
      - name: Unit tests (excludes 'heavy' marker by default)
        run: uv run pytest -q

  latex-smoke:
    name: LaTeX golden-deck smoke build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install TeX Live (xelatex + latexmk)
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends \
            texlive-xetex texlive-latex-extra latexmk
      - name: Assemble and build the golden deck
        run: |
          python3 paper2beamer/scripts/emit_beamer.py \
            --manifest paper2beamer/tests/fixtures/golden-deck \
            --out /tmp/golden
          bash paper2beamer/scripts/build.sh /tmp/golden
      - name: Assert the PDF exists and parse its log
        run: |
          test -f /tmp/golden/main.pdf
          python3 paper2beamer/scripts/latex_log.py /tmp/golden/main.log --assert-clean
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: python unit tests + latex golden-deck smoke build"
```

---

## Phase 1 — Deterministic core (TDD)

> Build order: `latex_log` → `repair_router` → `emit_beamer` → `frontend_docling`.
> Each is a pure-ish module with a thin CLI (`if __name__ == "__main__"`). Tests
> use only checked-in fixtures (no Docling, no LaTeX) except where noted.

### Task 1.1: `latex_log.py` — normalize a build into signals

A LaTeX/latexmk run produces a `.log`. This module turns the log text (plus the
process exit code) into a normalized, immutable `Signals` object the router can
consume. It recognizes three signal sources:
1. **Compile errors** — lines starting with `! ` (TeX error) and the Simple
   theme's `overflowguard` `Package beamerthemeSimple Error:` lines.
2. **Overflow** — both the theme's overflow error ("Frame body overflows the
   safe area on slide N") and generic `Overfull \vbox` warnings.
3. **Page count** — `Output written on ... (N page(s)`.

**Files:**
- Create: `paper2beamer/scripts/latex_log.py`
- Test: `paper2beamer/tests/test_latex_log.py`
- Fixtures: `paper2beamer/tests/fixtures/{clean,error,overflow}.log`

- [ ] **Step 1: Write the fixtures**

`clean.log` (minimal, success):
```
This is XeTeX, Version 3.141592653
[1] [2] [3]
Output written on main.pdf (3 pages, 12345 bytes).
Transcript written on main.log.
```

`error.log` (undefined control sequence):
```
This is XeTeX, Version 3.141592653
[1]
! Undefined control sequence.
l.42 \badmacro
              {x}
[2]
Output written on main.pdf (2 pages, 9999 bytes).
```

`overflow.log` (Simple theme overflowguard fired):
```
This is XeTeX, Version 3.141592653
[1] [2]
! Package beamerthemeSimple Error: Frame body overflows the safe area on slide 7: content is 210.0pt tall but only 180.0pt fits.
Overfull \vbox (30.0pt too high) detected at line 0
Output written on main.pdf (9 pages, 54321 bytes).
```

- [ ] **Step 2: Write the failing test**

```python
# paper2beamer/tests/test_latex_log.py
from pathlib import Path
from scripts.latex_log import parse_log, Signals

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
    import pytest
    with pytest.raises(TypeError):
        parse_log(None, exit_code=0)  # defensive: bad input fails fast
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_latex_log.py -q`
Expected: FAIL — `ModuleNotFoundError: scripts.latex_log` (set `PYTHONPATH=.`; add `[tool.pytest.ini_options] pythonpath = ["."]` to pyproject if needed).

- [ ] **Step 4: Implement `latex_log.py`**

```python
"""Parse a LaTeX/latexmk run into normalized, immutable build signals.

The rest of the pipeline never reads a raw .log. It reads the Signals object
produced here, so all the brittle string-matching lives in exactly one place.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Optional

# --- immutable signal records ------------------------------------------------


@dataclass(frozen=True)
class CompileError:
    """One TeX-level error. tex_line is the line in main.tex when TeX reports it."""
    message: str
    tex_line: Optional[int]
    raw: str


@dataclass(frozen=True)
class Overflow:
    """One frame whose body overflowed. slide_number is TeX's content frame number."""
    slide_number: Optional[int]
    detail: str


@dataclass(frozen=True)
class Signals:
    compile_ok: bool
    errors: tuple[CompileError, ...] = ()
    overflows: tuple[Overflow, ...] = ()
    page_count: Optional[int] = None


# --- regexes (compiled once) -------------------------------------------------

_ERR_LINE = re.compile(r"^! (.+)$", re.MULTILINE)
_TEX_LINE = re.compile(r"^l\.(\d+)", re.MULTILINE)
_OVERFLOW_GUARD = re.compile(r"Frame body overflows the safe area on slide (\d+)")
_OVERFULL_VBOX = re.compile(r"Overfull \\vbox \(([\d.]+pt) too high\)")
_PAGE_COUNT = re.compile(r"Output written on .*?\((\d+) pages?")


def parse_log(log_text: str, exit_code: int) -> Signals:
    """Turn raw log text + the process exit code into Signals.

    Defensive: rejects non-string log_text and non-int exit_code so a caller
    that passes the wrong thing fails loudly here, not three layers down.
    """
    if not isinstance(log_text, str):
        raise TypeError(f"log_text must be str, got {type(log_text).__name__}")
    if not isinstance(exit_code, int):
        raise TypeError(f"exit_code must be int, got {type(exit_code).__name__}")

    errors = _extract_errors(log_text)
    overflows = _extract_overflows(log_text)
    page_count = _extract_page_count(log_text)

    # The build is OK only if the process succeeded AND we saw no hard errors.
    compile_ok = exit_code == 0 and not errors

    return Signals(
        compile_ok=compile_ok,
        errors=tuple(errors),
        overflows=tuple(overflows),
        page_count=page_count,
    )


def _extract_errors(text: str) -> list[CompileError]:
    """Pair each `! ...` error with the nearest following `l.<n>` line, if any."""
    errors: list[CompileError] = []
    for match in _ERR_LINE.finditer(text):
        message = match.group(1).strip()
        # Look only at the slice AFTER this error for its line marker, so two
        # errors never steal each other's line numbers.
        tail = text[match.end():]
        line_match = _TEX_LINE.search(tail)
        tex_line = int(line_match.group(1)) if line_match else None
        errors.append(CompileError(message=message, tex_line=tex_line, raw=match.group(0)))
    return errors


def _extract_overflows(text: str) -> list[Overflow]:
    """Prefer the theme's precise per-slide error; fall back to Overfull vbox."""
    overflows = [
        Overflow(slide_number=int(m.group(1)), detail=m.group(0))
        for m in _OVERFLOW_GUARD.finditer(text)
    ]
    if not overflows:
        overflows = [
            Overflow(slide_number=None, detail=m.group(0))
            for m in _OVERFULL_VBOX.finditer(text)
        ]
    return overflows


def _extract_page_count(text: str) -> Optional[int]:
    matches = _PAGE_COUNT.findall(text)
    return int(matches[-1]) if matches else None  # last write wins (2-pass build)


def _main(argv: list[str]) -> int:
    """CLI: `latex_log.py <main.log> [--assert-clean]`. Prints a JSON summary."""
    import argparse
    import json
    from pathlib import Path

    ap = argparse.ArgumentParser(description="Summarize a LaTeX log into signals.")
    ap.add_argument("log", type=Path)
    ap.add_argument("--assert-clean", action="store_true",
                    help="exit non-zero if any error or overflow is present")
    args = ap.parse_args(argv)

    if not args.log.is_file():
        print(f"error: log file not found: {args.log}", file=sys.stderr)
        return 2

    sig = parse_log(args.log.read_text(errors="replace"), exit_code=0)
    print(json.dumps({
        "compile_ok": sig.compile_ok,
        "errors": [e.message for e in sig.errors],
        "overflows": [o.slide_number for o in sig.overflows],
        "page_count": sig.page_count,
    }, indent=2))

    if args.assert_clean and (sig.errors or sig.overflows):
        print("assert-clean failed: build has errors or overflows", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
```

- [ ] **Step 5: Add `pythonpath` so `scripts` imports work in tests**

In `paper2beamer/pyproject.toml` under `[tool.pytest.ini_options]` add:
```toml
pythonpath = ["."]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd paper2beamer && uv run pytest tests/test_latex_log.py -q`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add paper2beamer/scripts/latex_log.py paper2beamer/tests/test_latex_log.py paper2beamer/tests/fixtures/*.log paper2beamer/pyproject.toml
git commit -m "feat: latex_log signal parser with tests"
```

### Task 1.2: `repair_router.py` — route signals to the right IR level

Pure function. Given `Signals`, a provenance map, an intent page budget, and the
per-target attempt counts so far, produce an immutable list of `RepairDirective`s
that tell the orchestrator *which level to edit and which unit*. This is the
literal encoding of the design's routing table, including escalation.

**Files:**
- Create: `paper2beamer/scripts/repair_router.py`
- Test: `paper2beamer/tests/test_repair_router.py`

- [ ] **Step 1: Write the failing test**

```python
# paper2beamer/tests/test_repair_router.py
import pytest
from scripts.latex_log import Signals, CompileError, Overflow
from scripts.repair_router import route, RepairDirective, IntentBudget, Provenance

# A tiny provenance map: frame S07 is content frame number 7, spanning tex lines 40-55.
PROV = Provenance(frames=(
    {"slide_id": "S07", "beat_id": "N03", "content_number": 7, "tex_start": 40, "tex_end": 55},
    {"slide_id": "S08", "beat_id": "N03", "content_number": 8, "tex_start": 56, "tex_end": 70},
))


def test_compile_error_routes_to_tex_level_resolving_frame_by_line():
    sig = Signals(compile_ok=False,
                  errors=(CompileError("Undefined control sequence", tex_line=42, raw=""),))
    out = route(sig, PROV, budget=None, attempts={})
    assert out == (RepairDirective(level="tex", target_id="S07",
                                   reason="Undefined control sequence"),)


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


def test_clean_build_within_budget_yields_no_directives():
    sig = Signals(compile_ok=True, page_count=15)
    out = route(sig, PROV, budget=IntentBudget(min_pages=12, max_pages=18), attempts={})
    assert out == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_repair_router.py -q`
Expected: FAIL — `ModuleNotFoundError: scripts.repair_router`.

- [ ] **Step 3: Implement `repair_router.py`**

```python
"""Route build signals to the lowest IR level that can resolve them.

This module is the heart of "repair-at-the-right-level". It is a pure function:
given what the build reported (Signals), how frames map to IR units (Provenance),
the intent's page budget, and how many times we have already tried each target,
it returns directives saying *edit this level, this unit, for this reason*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from scripts.latex_log import Signals

# After this many failed attempts at one slide, stop trimming and escalate to
# cutting the beat in the Narrative IR (the design's stop-loss rule).
ESCALATION_THRESHOLD = 2


@dataclass(frozen=True)
class IntentBudget:
    """Target page range derived from a stated talk duration. None means unbounded."""
    min_pages: int
    max_pages: int


@dataclass(frozen=True)
class Provenance:
    """Ordered frame records: slide_id, beat_id, content_number, tex_start, tex_end."""
    frames: tuple[dict, ...] = ()

    def frame_at_line(self, line: Optional[int]) -> Optional[dict]:
        """Find the frame whose tex line range contains `line`."""
        if line is None:
            return None
        for f in self.frames:
            if f["tex_start"] <= line <= f["tex_end"]:
                return f
        return None

    def frame_by_content_number(self, n: Optional[int]) -> Optional[dict]:
        if n is None:
            return None
        for f in self.frames:
            if f.get("content_number") == n:
                return f
        return None


@dataclass(frozen=True)
class RepairDirective:
    level: str           # "tex" | "slide" | "narrative"
    target_id: Optional[str]
    reason: str


def route(sig: Signals, prov: Provenance, budget: Optional[IntentBudget],
          attempts: dict[str, int]) -> tuple[RepairDirective, ...]:
    """Produce repair directives. Pure; never mutates its inputs."""
    if not isinstance(attempts, dict):
        raise TypeError("attempts must be a dict of target_id -> count")

    directives: list[RepairDirective] = []

    # 1. Compile errors -> fix the .tex of the offending frame (or whole file).
    for err in sig.errors:
        frame = prov.frame_at_line(err.tex_line)
        directives.append(RepairDirective(
            level="tex",
            target_id=frame["slide_id"] if frame else None,
            reason=err.message,
        ))

    # 2. Overflow -> trim that slide; escalate to Narrative after repeated tries.
    for ov in sig.overflows:
        frame = prov.frame_by_content_number(ov.slide_number)
        slide_id = frame["slide_id"] if frame else None
        tried = attempts.get(slide_id, 0) if slide_id else 0
        if slide_id and tried >= ESCALATION_THRESHOLD:
            directives.append(RepairDirective(
                level="narrative",
                target_id=frame["beat_id"],
                reason=f"slide {slide_id} still overflows after {tried} trims; cut/shrink the beat",
            ))
        else:
            directives.append(RepairDirective(
                level="slide", target_id=slide_id,
                reason="frame body overflows the safe area; split or trim",
            ))

    # 3. Page count vs intent budget -> Narrative cut/expand. Skipped if unbounded.
    if budget is not None and sig.page_count is not None:
        if sig.page_count > budget.max_pages:
            directives.append(RepairDirective(
                level="narrative", target_id=None,
                reason=f"deck is {sig.page_count} pages, over the {budget.max_pages}-page "
                       f"budget; cut or merge beats",
            ))
        elif sig.page_count < budget.min_pages:
            directives.append(RepairDirective(
                level="narrative", target_id=None,
                reason=f"deck is {sig.page_count} pages, under the {budget.min_pages}-page "
                       f"budget; expand or add depth",
            ))

    return tuple(directives)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd paper2beamer && uv run pytest tests/test_repair_router.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/scripts/repair_router.py paper2beamer/tests/test_repair_router.py
git commit -m "feat: repair_router with routing table + escalation, tested"
```

### Task 1.3: `emit_beamer.py` — assemble main.tex + provenance.json

Deterministic assembler. The emission LLM writes a build manifest (a preamble, an
ordered frame list, and one LaTeX fragment per frame). This module stitches them
into `main.tex`, inserting `% slide:Sxx beat:Nyy` provenance comments, and writes
`provenance.json` recording each frame's tex line range and computed content
number (so `latex_log` slide numbers map back to slide IDs).

**Manifest format (input):**
- `<manifest>/preamble.tex` — documentclass, `\usetheme`, title metadata, `\begin{document}` is NOT included (emitter adds it).
- `<manifest>/order.txt` — one frame per line: `S01 beat:N01` plus optional ` plain` flag for unnumbered special frames (title/divider/statement/thanks).
- `<manifest>/frames/<Sxx>.tex` — the full `\begin{frame}...\end{frame}` (or `\titleframe` etc.) body for that id.

**Files:**
- Create: `paper2beamer/scripts/emit_beamer.py`
- Test: `paper2beamer/tests/test_emit_beamer.py`
- Fixtures: `paper2beamer/tests/fixtures/golden-deck/*`

- [ ] **Step 1: Write the golden-deck fixture**

`fixtures/golden-deck/preamble.tex`:
```latex
\documentclass[aspectratio=169]{beamer}
\usetheme[overflowguard=on]{Simple}
\title[Golden]{The Golden Smoke Deck}
\author{paper2beamer CI}
\date{2026}
```

`fixtures/golden-deck/order.txt`:
```
S00 beat:N00 plain
S01 beat:N01
S02 beat:N01
```

`fixtures/golden-deck/frames/S00.tex`:
```latex
\titleframe
```

`fixtures/golden-deck/frames/S01.tex`:
```latex
\begin{frame}{First content frame}
  \begin{itemize}\item A single, safe bullet.\end{itemize}
\end{frame}
```

`fixtures/golden-deck/frames/S02.tex`:
```latex
\begin{frame}{Second content frame}
  \begin{block}{Claim}A short claim.\end{block}
\end{frame}
```

- [ ] **Step 2: Write the failing test**

```python
# paper2beamer/tests/test_emit_beamer.py
import json
from pathlib import Path
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
    import pytest
    bad = tmp_path / "manifest"
    (bad / "frames").mkdir(parents=True)
    (bad / "preamble.tex").write_text("\\documentclass{beamer}")
    (bad / "order.txt").write_text("S01 beat:N01\n")  # fragment file missing
    with pytest.raises(FileNotFoundError):
        assemble(bad, tmp_path / "out")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_emit_beamer.py -q`
Expected: FAIL — `ModuleNotFoundError: scripts.emit_beamer`.

- [ ] **Step 4: Implement `emit_beamer.py`**

```python
"""Assemble a deck build manifest into main.tex + provenance.json.

Keeping assembly deterministic (rather than asking the LLM to write the whole
file) guarantees the provenance comments and line ranges are always correct, so
repair routing can trust them.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_ORDER_LINE = re.compile(r"^(?P<slide>S\w+)\s+beat:(?P<beat>N\w+)(?P<plain>\s+plain)?\s*$")


@dataclass(frozen=True)
class _Entry:
    slide_id: str
    beat_id: str
    plain: bool


def _parse_order(order_path: Path) -> list[_Entry]:
    """Parse order.txt defensively: every non-blank line must match the grammar."""
    entries: list[_Entry] = []
    for n, line in enumerate(order_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        m = _ORDER_LINE.match(line)
        if not m:
            raise ValueError(f"{order_path}:{n}: malformed order line: {line!r}")
        entries.append(_Entry(m.group("slide"), m.group("beat"), bool(m.group("plain"))))
    if not entries:
        raise ValueError(f"{order_path}: no frames declared")
    return entries


def assemble(manifest_dir: Path, out_dir: Path) -> Path:
    """Build out_dir/main.tex and out_dir/provenance.json from the manifest.

    Returns the path to main.tex. Validates every referenced file up front.
    """
    manifest_dir = Path(manifest_dir)
    out_dir = Path(out_dir)
    preamble = manifest_dir / "preamble.tex"
    order = manifest_dir / "order.txt"
    if not preamble.is_file():
        raise FileNotFoundError(f"missing preamble: {preamble}")
    if not order.is_file():
        raise FileNotFoundError(f"missing order file: {order}")

    entries = _parse_order(order)
    out_dir.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.extend(preamble.read_text().splitlines())
    lines.append("\\begin{document}")

    prov_frames: list[dict] = []
    content_number = 0
    for e in entries:
        fragment = manifest_dir / "frames" / f"{e.slide_id}.tex"
        if not fragment.is_file():
            raise FileNotFoundError(f"missing frame fragment: {fragment}")

        # Numbered content frames get a running number; plain frames do not.
        if e.plain:
            number = None
        else:
            content_number += 1
            number = content_number

        lines.append(f"% slide:{e.slide_id} beat:{e.beat_id}")
        tex_start = len(lines) + 1            # 1-based line of the frame's first line
        body = fragment.read_text().splitlines()
        lines.extend(body)
        tex_end = len(lines)

        prov_frames.append({
            "slide_id": e.slide_id,
            "beat_id": e.beat_id,
            "content_number": number,
            "tex_start": tex_start,
            "tex_end": tex_end,
        })

    lines.append("\\end{document}")

    main_tex = out_dir / "main.tex"
    main_tex.write_text("\n".join(lines) + "\n")
    (out_dir / "provenance.json").write_text(
        json.dumps({"frames": prov_frames}, indent=2) + "\n")
    return main_tex


def _main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Assemble a deck manifest into main.tex.")
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        path = assemble(args.manifest, args.out)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd paper2beamer && uv run pytest tests/test_emit_beamer.py -q`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add paper2beamer/scripts/emit_beamer.py paper2beamer/tests/test_emit_beamer.py paper2beamer/tests/fixtures/golden-deck
git commit -m "feat: emit_beamer deck assembler with provenance, tested"
```

### Task 1.4: `build.sh` — latexmk wrapper

**Files:**
- Create: `paper2beamer/scripts/build.sh`

- [ ] **Step 1: Write `build.sh`**

```bash
#!/usr/bin/env bash
# Build a deck directory containing main.tex into main.pdf with XeLaTeX.
# Usage: build.sh <deck_dir>
# Exit code is latexmk's; main.log is left in <deck_dir> for latex_log.py.
set -uo pipefail

DECK="${1:?usage: build.sh <deck_dir>}"
if [[ ! -f "$DECK/main.tex" ]]; then
  echo "build.sh: no main.tex in $DECK" >&2
  exit 2
fi

# Resolve the repo root so the Simple theme on TEXINPUTS is found regardless of
# where the deck lives. The template/ dir holds beamerthemeSimple.sty.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Trailing // tells kpathsea to search recursively; leading empty keeps defaults.
export TEXINPUTS="${REPO_ROOT}/template//:${TEXINPUTS:-}"

# -g forces a rebuild; nonstopmode so an error aborts instead of prompting.
latexmk -xelatex -interaction=nonstopmode -halt-on-error -g \
  -output-directory="$DECK" "$DECK/main.tex"
status=$?

# latexmk may name the log after the jobname; normalize to main.log.
[[ -f "$DECK/main.log" ]] || { [[ -f "$DECK/main.fls" ]] && true; }
exit $status
```

- [ ] **Step 2: Make it executable and smoke it locally (manual; needs LaTeX)**

```bash
chmod +x paper2beamer/scripts/build.sh
python3 paper2beamer/scripts/emit_beamer.py --manifest paper2beamer/tests/fixtures/golden-deck --out /tmp/golden
bash paper2beamer/scripts/build.sh /tmp/golden
python3 paper2beamer/scripts/latex_log.py /tmp/golden/main.log --assert-clean
```
Expected: `/tmp/golden/main.pdf` exists; `latex_log.py` prints `compile_ok: true`, `page_count: 2`, exits 0.

- [ ] **Step 3: Commit**

```bash
git add paper2beamer/scripts/build.sh
git commit -m "feat: build.sh latexmk/xelatex wrapper with theme on TEXINPUTS"
```

### Task 1.5: `frontend_docling.py` — deterministic PDF ingest

Wraps Docling to extract structure and figures deterministically. The CLI writes
`paper-content.md` (Markdown export with figure placeholders) and `figures/`
(extracted images named `figure-001.png`, ...). Pure helpers (path building,
filename sanitization) are unit-tested; the heavy Docling run is a `heavy`-marked
test skipped in CI and exercised in manual verification.

**Files:**
- Create: `paper2beamer/scripts/frontend_docling.py`
- Test: `paper2beamer/tests/test_frontend_docling.py`

- [ ] **Step 1: Write the failing test (pure helpers + defensive CLI)**

```python
# paper2beamer/tests/test_frontend_docling.py
import pytest
from pathlib import Path
from scripts.frontend_docling import figure_filename, ingest


def test_figure_filename_zero_pads_and_uses_index():
    assert figure_filename(1, "png") == "figure-001.png"
    assert figure_filename(42, "png") == "figure-042.png"


def test_ingest_rejects_missing_pdf(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest(tmp_path / "nope.pdf", tmp_path / "out")


def test_ingest_rejects_non_pdf_suffix(tmp_path):
    f = tmp_path / "paper.txt"
    f.write_text("not a pdf")
    with pytest.raises(ValueError):
        ingest(f, tmp_path / "out")


@pytest.mark.heavy
def test_ingest_real_pdf_produces_markdown_and_figures(tmp_path):
    # Manual/local only: requires a real sample.pdf and Docling models.
    out = tmp_path / "out"
    ingest(Path("tests/fixtures/sample.pdf"), out)
    assert (out / "paper-content.md").is_file()
    assert (out / "figures").is_dir()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_frontend_docling.py -q`
Expected: FAIL — `ModuleNotFoundError: scripts.frontend_docling`.

- [ ] **Step 3: Implement `frontend_docling.py`**

```python
"""Deterministic PDF ingest via Docling.

Figures and structure are extracted by Docling, never guessed by an LLM. The
output is a Markdown rendering of the paper plus an images directory; the
Narrative pass reads these, it never reads the raw PDF.
"""
from __future__ import annotations

import sys
from pathlib import Path


def figure_filename(index: int, ext: str) -> str:
    """Stable, sortable figure name: figure-001.png. index is 1-based."""
    if index < 1:
        raise ValueError("figure index is 1-based")
    return f"figure-{index:03d}.{ext}"


def ingest(pdf_path: Path, out_dir: Path) -> Path:
    """Extract `pdf_path` into out_dir/{paper-content.md, figures/}.

    Validates the input is an existing .pdf before importing Docling (so a bad
    path fails instantly instead of after a slow model import). Returns the
    path to paper-content.md.
    """
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"expected a .pdf, got {pdf_path.suffix!r}")

    # Imported lazily: Docling pulls heavy models; keep it out of the fast path
    # and out of CI's unit tests.
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import ImageRefMode

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    document = result.document

    # Export Markdown with figures referenced as files under figures/.
    md_path = out_dir / "paper-content.md"
    document.save_as_markdown(
        md_path,
        image_mode=ImageRefMode.REFERENCED,
        artifacts_dir=figures_dir,
    )
    return md_path


def _main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Ingest a paper PDF with Docling.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        md = ingest(args.pdf, args.out)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
```

> NOTE for the implementer: confirm the exact Docling export API against the
> installed version (`uv run python -c "import docling; print(docling.__version__)"`).
> If `save_as_markdown`'s signature differs, adapt to the installed API but keep
> the same contract: produce `paper-content.md` + `figures/`. This is the one
> place the plan cannot fully pin without the live package.

- [ ] **Step 4: Run unit tests (heavy test auto-skipped)**

Run: `cd paper2beamer && uv run pytest tests/test_frontend_docling.py -q`
Expected: 3 passed, 1 skipped.

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/scripts/frontend_docling.py paper2beamer/tests/test_frontend_docling.py
git commit -m "feat: frontend_docling deterministic PDF ingest with defensive guards"
```

---

## Phase 2 — The pre-built Simple ISA

### Task 2.1: Write `paper2beamer/isa/Simple.md`

The pre-built capability manifest for the bundled Simple theme. Distilled from
`template/beamerthemeSimple.sty` and its manual. Four sections: instructions,
options, constraints, idioms.

**Files:**
- Create: `paper2beamer/isa/Simple.md`

- [ ] **Step 1: Write the ISA**

````markdown
# ISA: Simple (beamerthemeSimple v3.2)

> Capability manifest for the bundled Simple theme. This is the contract the
> Slide IR and emission passes MUST obey: emit only instructions listed here,
> respect the constraints, follow the idioms. Build with `overflowguard=on`.

## 1. Instructions (what you may emit)

**Document shell**
- `\documentclass[aspectratio=169]{beamer}` — 16:9 is the only supported ratio.
- `\usetheme[<options>]{Simple}` — see options below.
- Title metadata: `\title[<short>]{<full>}`, `\author{}`, `\institute{}`, `\date{}`.
  ALWAYS give a short title; the footer clips a long one.

**Special frames (unnumbered, on-theme; prefer these for structural slides)**
- `\titleframe` — title page.
- `\statementframe{TEXT}` — one big centered statement.
- `\thanksframe[Headline][Subtitle]` — closing slide; both args optional, headline
  defaults to "Thank you".
- Section dividers are AUTOMATIC at each `\section{...}` (unless `divider=off`).

**Content frames**
- `\begin{frame}{Title}{Optional subtitle} ... \end{frame}` — numbered content.
- `\section{...}` for the eyebrow + auto divider. Keep section names SHORT (a long
  one wraps above the frame title).

**Semantic blocks (carry meaning by color; pick by intent)**
- `block` → neutral claim/definition (accent left rule).
- `alertblock` → caveat / warning (gold left rule).
- `exampleblock` → example / desired state (green left rule).
- An EMPTY block title prints no rule and no gap — give blocks a title.

**Inline semantics**
- `\alert{...}` → gold emphasis, matches `alertblock`.
- example text color matches `exampleblock`.

**Standard Beamer that works**: `itemize`/`enumerate`/`description`,
`theorem`/`definition`/`proof`, `figure` + `\caption` (captions are numbered,
labeled with a colon), `thebibliography`.

## 2. Options (`\usetheme[...]{Simple}`)

| Option | Values | Default | Effect |
|---|---|---|---|
| `eyebrow` | free text | empty | Small title-page label. Field-agnostic. |
| `density` | `normal`, `dense` | `normal` | `dense` tightens margins + shrinks titles/blocks for result-heavy slides. |
| `divider` | `on`, `off` | `on` | Auto section-divider frames. |
| `overflowguard` | `on`, `off` | `off` | **Builds MUST set `on`**: a frame body reaching the footer becomes a hard error naming the slide number. |

Color overrides: `\definecolor{<name>}{RGB}{r,g,b}` BEFORE `\usetheme` (all colors
use `\providecolor`, so your definition wins).

## 3. Constraints (calling conventions, capacity, forbidden zones)

- **Aspect ratio**: 16:9 only.
- **Engine**: XeLaTeX (or LuaLaTeX). CJK needs `xeCJK` (XeLaTeX) or `luatexja`
  (LuaLaTeX) + a CJK font; absent → CJK silently does not render, Latin is fine.
- **Capacity** (rough, for overflow budgeting): at `density=normal` a content
  frame comfortably holds ~6–8 short bullets OR one figure + 2–3 bullets OR two
  small blocks. `density=dense` adds ~25% headroom. When `overflowguard=on` fires,
  the slide is over — split it, trim it, or switch that build to `density=dense`.
- **Unnumbered frames**: title, dividers, statement, thanks do NOT count toward the
  footer frame total. Page-count budgeting should count content frames.
- **Forbidden zones** (the theme deliberately leaves these to the deck — do NOT
  emit them inside the theme's responsibility, only opt in at deck preamble if truly
  needed): the theme does NOT load `unicode-math`, does NOT set a math font, and does
  NOT call `\hypersetup`. Emitting `\usepackage{unicode-math}` or `\hypersetup{...}`
  is allowed at the deck preamble but is the deck's choice, not the theme's.

## 4. Idioms (style contract)

- Mark meaning with COLOR and the semantic block, not with decoration or filled
  headers. Choose `block`/`alertblock`/`exampleblock` by what the content *means*.
- Use color semantically: accent = structure, gold = caveat, green = example.
- Keep section names short; give every block a title; give every deck a short title.
- One idea per `\statementframe`. Prefer special frames for title/closing over
  hand-rolled layouts.
- Keep default colors unless the field demands otherwise — defaults clear WCAG AA
  on white.
````

- [ ] **Step 2: Commit**

```bash
git add paper2beamer/isa/Simple.md
git commit -m "feat: pre-built Simple theme ISA manifest"
```

---

## Phase 3 — The skill (SKILL.md + reference pass guides)

> These are LLM-read instruction files, not unit-testable code. Each task states
> the REQUIRED content precisely. After writing, the implementer verifies by
> reading the file back and checking every listed element is present.

### Task 3.1: `references/ir-format.md` — the IR schemas + provenance

**Files:**
- Create: `paper2beamer/references/ir-format.md`

- [ ] **Step 1: Write it. REQUIRED content:**
  - **Narrative IR** schema: a Markdown doc with a `## Talk meta` block
    (intent verbatim, derived time-budget, derived page budget min/max or
    "unbounded", depth/tone profile) followed by one `### N<NN> — <short label>`
    section per beat with fields `goal:`, `key-message:`, `time-budget:`,
    `supporting-figures:` (figure ids from paper-content.md, or "none").
  - **Slide IR** schema: a `## Deck meta` block (title, short title, author,
    institute, date, density) then one `### S<NN> — <title>` section per slide with
    fields `beat-ref:` (the `N<NN>` it serves), `title:`, `content:` (bullet/structure
    prose, NOT final LaTeX), `figure:` (id or none), `block-semantics:`
    (claim/caveat/example/none — only values the ISA supports).
  - **Provenance rules**: IDs are stable and never reused; `S` ids are assigned in
    final deck order; each Slide IR section MUST carry `beat-ref:`; emission writes
    `% slide:Sxx beat:Nyy` above each frame and the build manifest's `order.txt`.
  - A short worked example of each (2–3 beats, 3–4 slides) so the LLM has a concrete
    target.

- [ ] **Step 2: Commit** (`git add ... && git commit -m "docs: IR format + provenance reference"`)

### Task 3.2: `references/` pass guides

Create one focused guide per pass. Each is read by the orchestrator when that pass
runs. Write them as imperative instructions to the model.

**Files:** Create each of:
- `references/pipeline-overview.md`
- `references/intent.md`
- `references/ingest.md`
- `references/narrative-ir.md`
- `references/review-gate.md`
- `references/slide-ir.md`
- `references/emission.md`
- `references/compile-verify.md`
- `references/repair.md`
- `references/isa-setup.md`
- `references/domain-setup.md`

- [ ] **Step 1: Write `pipeline-overview.md`.** REQUIRED: the full stage list with
  the ASCII pipeline diagram from the design doc; the rule that Narrative IR is
  target/domain-independent and only Slide IR + emission read the ISA; where each
  artifact lands under `slides/<slug>/`; pointer to `ir-format.md`.

- [ ] **Step 2: Write `intent.md`.** REQUIRED: the FIRST action of every run is to
  ask the user for intent in free text; show 3 examples ("unbounded, convey content";
  "15-minute conference talk"; "seminar for my advisor"). Then translate intent into
  (a) a **page budget** — a stated duration → `min_pages`/`max_pages` using ~1 content
  slide/minute ±20% (e.g. 15 min → 12–18); "unbounded/length-free" → budget = none, and
  the page-count repair trigger is disabled; (b) a **depth/tone** profile. Record both
  in the Narrative IR `## Talk meta` block. Defensive: if intent is ambiguous about
  length, ASK one clarifying question rather than guessing.

- [ ] **Step 3: Write `ingest.md`.** REQUIRED: run
  `uv run --project paper2beamer paper2beamer/scripts/frontend_docling.py <pdf> --out slides/<slug>`;
  the output `paper-content.md` + `figures/` are the ONLY source for downstream passes
  (never re-read the PDF, never invent figures). Verify the figure count matches what
  Docling wrote; if Docling fails, stop and report — do not fall back to LLM figure
  guessing. Read `template/domain.md` if present to calibrate.

- [ ] **Step 4: Write `narrative-ir.md`.** REQUIRED: inputs are `paper-content.md`,
  the intent profile, and `template/domain.md` (optional). Produce `narrative.md` per
  the `ir-format.md` Narrative schema. Rules: theme-agnostic and domain-calibrated;
  allocate `time-budget` across beats to fit the intent; attach `supporting-figures`
  only from real Docling figure ids; one clear `key-message` per beat. Do NOT plan
  slides yet. End by handing off to the review gate.

- [ ] **Step 5: Write `review-gate.md`.** REQUIRED: present the Narrative IR to the
  user as a readable outline (beats, key messages, time allocation, chosen figures).
  Explicitly ask for approval or edits. Loop until approved. Only after approval
  proceed to Slide IR. This is the single human gate.

- [ ] **Step 6: Write `slide-ir.md`.** REQUIRED: inputs are approved `narrative.md`
  + the active ISA (`paper2beamer/isa/Simple.md`, or `isa/<Theme>.md`). Produce
  `slides.md` per the Slide schema. Rules: every slide has a `beat-ref`; choose
  `block-semantics` ONLY from ISA-listed blocks; respect ISA capacity (don't plan a
  slide the ISA says won't fit); assign each figure to exactly one slide; assign final
  `S` ids in deck order. Plan title/section-divider/closing using ISA special frames.

- [ ] **Step 7: Write `emission.md`.** REQUIRED: turn `slides.md` into a build
  manifest under `slides/<slug>/build/`: `preamble.tex` (documentclass, `\usetheme`
  with `overflowguard=on` + chosen density/eyebrow, title metadata), `order.txt`
  (one line per frame, `plain` flag for unnumbered special frames), and
  `frames/<Sxx>.tex` (the actual LaTeX per frame). Emit ONLY ISA instructions. Then run
  `python3 paper2beamer/scripts/emit_beamer.py --manifest slides/<slug>/build --out slides/<slug>`
  to assemble `main.tex` + `provenance.json`. Never hand-write main.tex.

- [ ] **Step 8: Write `compile-verify.md`.** REQUIRED: run
  `bash paper2beamer/scripts/build.sh slides/<slug>` then
  `python3 paper2beamer/scripts/latex_log.py slides/<slug>/main.log`. Read the signals.
  If `compile_ok` and (budget is none OR page_count in range) and no overflows → DONE,
  report the PDF path. Otherwise go to `repair.md`.

- [ ] **Step 9: Write `repair.md`.** REQUIRED: feed signals + `provenance.json` +
  intent budget + attempt counts to the routing logic (describe the routing table;
  optionally call `repair_router.py` for the directives). For each directive: `tex`
  level → edit only `build/frames/<Sxx>.tex`; `slide` level → revise that slide in
  `slides.md` then re-emit that fragment; `narrative` level → revise the beat in
  `narrative.md`, re-plan affected slides, re-emit. Re-assemble + rebuild. Track
  per-slide attempt counts; honor the escalation threshold; enforce a total repair
  budget (e.g. 6 rebuilds) then stop and write `repair-report.md` with the unresolved
  signals + the best-effort PDF path. NEVER regenerate the whole deck from scratch.

- [ ] **Step 10: Write `isa-setup.md`.** REQUIRED: OPTIONAL, once per theme. Input:
  a user `beamerthemeXxx.sty` (+ manual if present). Read the `.sty` source, extract
  the public API, and WRITE `isa/<Theme>.md` in the same four-section structure as
  `paper2beamer/isa/Simple.md`. If a manual exists, prefer it; otherwise infer from the
  `.sty`. Note when overflow detection must fall back to `Overfull \vbox` (themes
  without an overflowguard option). Confirm the result with the user.

- [ ] **Step 11: Write `domain-setup.md`.** REQUIRED: OPTIONAL, once per workspace.
  Approach C: read a representative paper the user provides, DRAFT a `template/domain.md`
  (field, audience, assumed background, must-teach concepts, terminology, what counts as
  good evidence) by inference, THEN ask a few clarifying questions for what a paper can't
  reveal (who exactly is the audience, what must always be taught). Save to
  `template/domain.md`. If skipped, the pipeline stays field-neutral.

- [ ] **Step 12: Commit** (`git add paper2beamer/references && git commit -m "docs: pipeline pass reference guides"`)

### Task 3.3: `paper2beamer/SKILL.md` — the orchestrator

**Files:**
- Create: `paper2beamer/SKILL.md`

- [ ] **Step 1: Write SKILL.md.** REQUIRED content:
  - YAML frontmatter: `name: paper2beamer`, a `description:` covering triggers
    ("convert paper to slides", "paper to beamer", "make a talk from this PDF",
    "投影片", "簡報") and what it does.
  - **Preflight checks** (defensive): verify `xelatex`, `latexmk`, `uv` exist; if a
    chosen theme has no ISA, point to `isa-setup.md`; PDF input only.
  - **The pipeline** as an ordered procedure, each step pointing to its reference file:
    intent → ingest (Docling) → Narrative IR → **review gate** → Slide IR → emission →
    compile-verify → repair loop. State the one gate explicitly.
  - **Optional setups** up front: ISA setup and Domain setup, both bypassable.
  - **Artifact map**: what lands in `slides/<slug>/` and `isa/`.
  - The non-negotiables: figures via Docling only; build with `overflowguard=on`;
    repair at the right level, never full regen; stop-loss repair budget.

- [ ] **Step 2: Verify** the skill loads (read it back; confirm frontmatter + every
  pass reference is linked).

- [ ] **Step 3: Commit** (`git commit -m "feat: paper2beamer SKILL.md orchestrator"`)

---

## Phase 4 — Documentation (academic-style English where noted)

### Task 4.1: Design-philosophy docs

**Files:**
- Create: `docs/design-philosophy.md`
- Create: `docs/ir-and-isa.md`

- [ ] **Step 1: Write `docs/design-philosophy.md`** in clean, academic English.
  REQUIRED: the LLVM analogy table (Source/Frontend, IR, MIR, MC, Assembler ↔ the
  pipeline stages); why an LLM workflow benefits from multi-level IR; why IR is
  structured Markdown rather than JSON; the intent-as-frontend-shaping argument; the
  theme-as-ISA argument; and the novel **repair-at-the-right-level** contribution
  contrasted with naive full regeneration. Reference the design doc.

- [ ] **Step 2: Write `docs/ir-and-isa.md`** in clean, academic English. REQUIRED: a
  precise description of the three IR levels and their fields; the ISA's four sections
  and its role as the Slide-IR↔emission contract; the provenance mechanism (IDs,
  comments, `provenance.json`) as the analogue of debug info / source locations; the
  routing table and escalation/stop-loss.

- [ ] **Step 3: Commit** (`git commit -m "docs: design philosophy and IR/ISA deep-dive"`)

### Task 4.2: README (EN + zh-TW)

**Files:**
- Create: `README.md`, `README-zh-TW.md`

- [ ] **Step 1: Write `README.md`.** REQUIRED: one-paragraph what/why; the pipeline
  diagram; quick start (install LaTeX + uv; how to invoke the skill; PDF in → PDF out);
  the optional setups; link to TUTORIAL, design-philosophy, CONTRIBUTING; requirements;
  license pointer (MIT, LICENSE.md). Add a language switch line linking to
  `README-zh-TW.md`.

- [ ] **Step 2: Write `README-zh-TW.md`** — a faithful Traditional-Chinese translation
  of `README.md`, linking back to `README.md`.

- [ ] **Step 3: Commit** (`git commit -m "docs: README (en + zh-TW)"`)

### Task 4.3: TUTORIAL (EN + zh-TW) + CONTRIBUTING

**Files:**
- Create: `TUTORIAL.md`, `TUTORIAL-zh-TW.md`, `CONTRIBUTING.md`

- [ ] **Step 1: Write `TUTORIAL.md`.** REQUIRED: an end-to-end walkthrough on a sample
  paper: (1) state an intent, (2) run ingest, (3) review the Narrative IR at the gate and
  edit one beat, (4) watch Slide IR + emission, (5) a deliberate overflow and how repair
  fixes it at the slide level, (6) swapping the theme via `theme.tex` + ISA setup, (7)
  optional domain setup. Show the actual commands and the artifacts produced.

- [ ] **Step 2: Write `TUTORIAL-zh-TW.md`** — faithful Traditional-Chinese translation.

- [ ] **Step 3: Write `CONTRIBUTING.md`.** REQUIRED: repo layout; how to run the
  Python tests (`cd paper2beamer && uv run pytest`); the `heavy` marker convention; how
  to add a new theme ISA; coding standards (defensive programming, full English comments,
  immutability, small files, TDD for deterministic code); commit message convention
  (`feat:`/`fix:`/`docs:`/...); the CI gate.

- [ ] **Step 4: Commit** (`git commit -m "docs: tutorial (en + zh-TW) and contributing guide"`)

---

## Phase 5 — Verification plan + final wiring

### Task 5.1: `docs/VERIFICATION.md` — the full verification plan

**Files:**
- Create: `docs/VERIFICATION.md`

- [ ] **Step 1: Write it.** REQUIRED content:
  - **Automated (CI):** `uv run pytest` (unit tests for latex_log, repair_router,
    emit_beamer, frontend_docling pure helpers); the golden-deck smoke build
    (emit_beamer → build.sh → latex_log `--assert-clean`). State expected results.
  - **Manual / local (needs LaTeX + Docling):** the `heavy` Docling ingest test on a
    real `sample.pdf`; a full pipeline dry-run on one real paper producing a compiling
    PDF; a deliberate-overflow run proving repair routes to the slide level and the
    deck recompiles; a theme-swap run proving the ISA layer is pluggable.
  - **Acceptance criteria** mapped to the design: PDF compiles; page count within the
    intent budget when bounded; no overflow under `overflowguard=on`; provenance
    comments present in `main.tex`; repair never triggers a full regen (verify by
    checking only the targeted fragment/section changed between rebuilds).
  - A checklist the maintainer ticks before merging.

- [ ] **Step 2: Run the automated suite and record results**

Run:
```bash
cd paper2beamer && uv run pytest -q
```
Expected: all unit tests pass, heavy test skipped. Paste the summary into the PR.

- [ ] **Step 3: Commit** (`git commit -m "docs: full verification plan"`)

### Task 5.2: `.gitignore` for runtime artifacts

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Append runtime-artifact ignores**

```gitignore
# paper2beamer runtime working dirs (generated per paper / per theme)
/slides/
/isa/
# python + latex build junk
__pycache__/
.pytest_cache/
*.aux
*.fls
*.fdb_latexmk
*.nav
*.snm
*.toc
*.out
.venv/
```
> NOTE: `/isa/` ignores the runtime user-theme dir at repo ROOT; the SHIPPED ISA
> lives at `paper2beamer/isa/Simple.md` and is NOT ignored. Verify
> `git status --porcelain paper2beamer/isa/Simple.md` shows it tracked.

- [ ] **Step 2: Commit** (`git commit -m "chore: ignore runtime slides/ and isa/ working dirs"`)

### Task 5.3: Open the PR

- [ ] **Step 1: Push and open PR**

```bash
git push -u origin feat/paper2beamer-skill
gh pr create --fill --base main
```

- [ ] **Step 2: Verify CI is green** on the PR before requesting review.

---

## Self-Review (completed during planning)

**Spec coverage check** — every design section maps to a task:
- Three Markdown IR levels → `ir-format.md` (3.1), narrative/slide guides (3.2).
- ISA layer + pre-built Simple → `isa/Simple.md` (2.1), `isa-setup.md` (3.2.10).
- Provenance + repair-at-right-level → `emit_beamer.py` (1.3), `repair_router.py` (1.2),
  `repair.md` (3.2.9), `ir-and-isa.md` (4.1).
- Intent gate → `intent.md` (3.2.2), SKILL.md (3.3).
- Single review gate → `review-gate.md` (3.2.5).
- Docling deterministic figures → `frontend_docling.py` (1.5), `ingest.md` (3.2.3).
- Compile + overflowguard signal → `build.sh` (1.4), `latex_log.py` (1.1).
- Two optional setups → `isa-setup.md`, `domain-setup.md` (3.2).
- PDF-only, workspace layout → File Structure, `ingest.md`, `.gitignore` (5.2).
- Testing strategy → Phase 1 tests + golden-deck smoke (CI 0.3) + `VERIFICATION.md` (5.1).
- Error handling → defensive guards in every script + preflight in SKILL.md.
- Docs (README/zh, CONTRIBUTING, TUTORIAL/zh, design philosophy) → Phase 4.
- CI → Task 0.3.

**Type consistency check** — `Signals`, `CompileError`, `Overflow` (latex_log) are
imported unchanged by `repair_router`; `Provenance`/`IntentBudget`/`RepairDirective`
defined in `repair_router` and used consistently in its tests; `assemble(manifest, out)`
signature matches its test and the CI invocation; provenance.json field names
(`slide_id`, `beat_id`, `content_number`, `tex_start`, `tex_end`) are identical across
`emit_beamer.py`, `repair_router.py`, and their tests.

**Placeholder scan** — no TBD/TODO; the one unavoidable live-API caveat (Docling export
signature) is called out explicitly in Task 1.5 with a concrete fallback contract.
