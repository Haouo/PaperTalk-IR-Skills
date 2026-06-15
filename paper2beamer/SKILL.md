---
name: paper2beamer
description: >-
  Convert an academic paper (PDF) into a Beamer slide deck through an
  LLVM-IR-inspired pipeline: three Markdown IR levels (Narrative -> Slide ->
  .tex) plus a pluggable theme-as-ISA layer. Intent-aware (every run starts by
  capturing the talk's purpose and length) and theme-aware (swap themes via an
  ISA manifest). Figures are extracted deterministically with Docling; the deck
  is compiled with xelatex; failures are repaired at the right IR level instead
  of regenerating from scratch. Domain-agnostic. Use when the user wants to turn
  a paper / PDF into slides, a talk, a presentation, a beamer deck, 投影片, or 簡報.
---

# paper2beamer

Turn a paper PDF into a compiling Beamer deck, shaped by the user's intent and a
pluggable theme. Read `references/pipeline-overview.md` first for the big picture.

## Preflight (defensive — check before starting)

- Required tools on PATH: `xelatex`, `latexmk`, `uv`. If any is missing, tell the
  user and stop.
- Input must be a **PDF**. No arXiv id / LaTeX source ingest in this version.
- Pick the theme. Default is the bundled **Simple** theme with its pre-built
  `paper2beamer/isa/Simple.yaml`. If the workspace `template/theme.tex` selects a
  different theme and no `isa/<Theme>.yaml` exists, run `references/isa-setup.md`
  first.

## Optional setups (bypassable, run once, persisted)

- **ISA setup** — `references/isa-setup.md`: build `isa/<Theme>.yaml` from a
  `beamerthemeXxx.sty`. Only needed for non-Simple themes.
- **Domain setup** — `references/domain-setup.md`: build `template/domain.md`
  from a representative paper plus a few questions. Skipped → field-neutral.

## The pipeline (run in order)

Each step has a reference guide; follow it.

1. **Intent** — `references/intent.md`. ALWAYS first. Capture intent, derive the
   page budget and depth/tone.
2. **Ingest** — `references/ingest.md`. Docling extracts `paper-content.md` +
   `figures/`. Deterministic; never guess figures.
3. **Narrative IR** — `references/narrative-ir.md`. Write `narrative.md`
   (theme- and ISA-independent; shaped only by intent + domain).
4. **Review gate** — `references/review-gate.md`. THE single human checkpoint.
   Present the narrative, edit until approved. Do not proceed without approval.
5. **Slide IR** — `references/slide-ir.md`. Write `slides.md`, ISA-aware.
6. **Emission** — `references/emission.md`. Write the build manifest, then run
   `emit_beamer.py` to assemble `main.tex` + `provenance.json`. Never hand-write
   `main.tex`.
7. **Compile & verify** — `references/compile-verify.md`. `build.sh` then
   `latex_log.py`. Done when it compiles, no overflow, and pages fit the budget.
8. **Repair** — `references/repair.md`. Route each signal to the right level and
   fix only that unit. Loop back to step 7.

## Non-negotiables

- Figures come ONLY from Docling — never invent them.
- Build with the theme's `overflowguard=on` so overflow is a precise per-slide
  signal.
- Repair at the right level (`tex` < `slide` < `narrative`); NEVER regenerate the
  whole deck. Honour the escalation threshold (2 trims/slide) and the total
  repair budget (6 rebuilds), then hand back a best-effort PDF + `repair-report.md`.
- IR is structured Markdown with stable IDs and cross-level provenance
  (`ir-format.md`).

## Artifacts

Per paper, everything lands under `slides/<slug>/` (see
`references/pipeline-overview.md` for the full map). Themes' ISAs live in
`isa/<Theme>.yaml` (shipped Simple ISA is at `paper2beamer/isa/Simple.yaml`).

## Deterministic tooling (under `scripts/`)

- `frontend_docling.py` — PDF → `paper-content.md` + `figures/`.
- `emit_beamer.py` — build manifest → `main.tex` + `provenance.json`.
- `build.sh` — `latexmk -xelatex` wrapper (theme on `TEXINPUTS`).
- `latex_log.py` — `main.log` → signals (errors, overflows, page count).
- `repair_router.py` — signals + provenance + budget → repair directives.
