# paper2beamer — an LLVM-IR-inspired Paper→Beamer skill

**Status:** Design approved (pending spec review)
**Date:** 2026-06-15
**Repo:** paper2beamer-skills

## Goal

A Claude Code skill that turns an academic paper (PDF) into a Beamer slide deck.
It is **intent-aware** (every run starts by capturing the user's talk intent) and
**theme-aware** (the Beamer theme is a pluggable backend). It borrows five ideas
from LLVM: a single multi-stage pipeline, multi-level IR, the theme-as-ISA
(swappable backend), repair routed to the right IR level instead of regenerating
from scratch, and a once-per-target "build the backend" setup step.

Domain-agnostic: researchers in any field can use it.

## Non-goals (YAGNI)

- No arXiv / LaTeX-source ingest in v1 — **PDF only** (Docling covers the common case).
- No per-slide parallel emission in v1 (listed as a later optimization).
- No web-hosted output, no animation/transition authoring beyond what the theme offers.

## Core metaphor: the pipeline

Single pipeline, multi-stage generation. Three IR levels + one ISA layer.
**All IR is structured Markdown**, not strict JSON/YAML — it is produced and
consumed by an LLM, and the Narrative IR is also read by a human at the gate.

```
[Intent capture]   required every run; shapes the whole pipeline
      |
[Frontend: Docling]  PDF -> structure + figures   (deterministic, no LLM)
      |   paper-content.md, figures/
      v
[Narrative IR]   the talk's story (theme/domain-independent; shaped by intent)  -- LLM
      |   narrative.md
      v  ===== GATE: user reviews the story outline =====
      v
[Slide IR]       per-slide plan (ISA-aware)                                      -- LLM
      |   slides.md            ^ reads ISA
      v                        |
[Emission]       Beamer .tex (only ISA-provided instructions)                   -- LLM
      |   main.tex             ^ reads ISA
      v
[Compile/Verify] latexmk -xelatex -> main.pdf + signals   (deterministic)
      |   errors / overflow / page-count vs intent
      v
[Repair-at-the-right-level]  route each signal along provenance to the right
                             IR level; surgically fix only that unit; recompile.
```

### Two optional, persisted, bypassable setup operations

Both run once and persist their output; both are skipped on later runs.

1. **ISA setup (per theme).** `beamerthemeXXX.sty` (+ manual if present) ->
   `isa/<Theme>.md`. This is "building a backend for a new target." The bundled
   **Simple** theme ships with a pre-built `isa/Simple.md`.
2. **Domain setup (per workspace).** Investigate the field/domain ->
   `template/domain.md`. Signal source is **paper-inferred draft + a few
   clarifying questions** (audience, must-teach concepts) -> save. Consumed by
   the Narrative pass to calibrate background depth, terminology normalization,
   and what counts as "good evidence." If not run, the pipeline stays
   field-neutral (general graduate-level audience).

## The three IR levels and the ISA

### Narrative IR — `slides/<slug>/narrative.md`

Target- and domain-independent; the only thing that shapes it is **intent**.
One section per beat. Fields:

- `id` — stable, e.g. `N3`
- `goal` — what this beat accomplishes in the talk
- `key-message` — the single sentence the audience must retain
- `time-budget` — minutes (or "flex" when intent length is unbounded)
- `supporting-figures` — figure IDs from Docling that back this beat

### Slide IR — `slides/<slug>/slides.md`

ISA-aware. One section per slide. Fields:

- `id` — stable, e.g. `S07`
- `beat-ref` — the Narrative beat this slide serves, e.g. `N3` (provenance up)
- `title`
- `content` — bullet/structure-level content, not final LaTeX
- `figure` — assigned figure, if any
- `block-semantics` — which ISA block to use (claim / caveat / example), only
  if the ISA actually provides it

### `.tex` — `slides/<slug>/main.tex`

Real Beamer code. Every frame is preceded by a provenance comment:

```latex
% slide:S07 beat:N3
\begin{frame}{...}
```

### ISA — `isa/<Theme>.md`

The capability manifest for one theme: the contract between Slide IR and
emission. Four sections:

1. **instructions** — special frames (`\titleframe`, `\statementframe{...}`,
   section dividers), semantic block environments
   (`block`=claim, `alertblock`=caveat, `exampleblock`=desired/example),
   inline emphasis (`\alert`), semantic colors
   (`simpleAccent` / `simpleAlert` / `simpleExample`).
2. **options** — `\usetheme[...]` flags (`eyebrow=`, `density=normal|dense`,
   `divider=on|off`, `overflowguard=on|off`) and the legal way to override
   colors (`\providecolor` before `\usetheme`).
3. **constraints** — aspect ratio 16:9; engine requirements (XeLaTeX/CJK);
   rough per-frame capacity at normal vs dense; **forbidden zones** (the theme
   deliberately does not load `unicode-math` and does not call `\hypersetup`).
4. **idioms** — style contract ("mark blocks by color not decoration," "use
   color semantically").

The **Narrative IR never touches the ISA** (target-independent). Only Slide IR
and emission consult it. Swapping themes = swapping ISA + `theme.tex`; the
Narrative IR is reused.

## Provenance: what makes repair-at-the-right-level work

This is the LLVM debug-info / source-location analogue.

- Every IR unit has a **stable ID** (`N3`, `S07`).
- **Cross-level links**: `S07` declares `beat-ref: N3`; each `.tex` frame carries
  `% slide:S07 beat:N3`.
- Any signal therefore traces back to exactly one IR unit, at exactly one level.

## Intent — the required first gate

The first action of every run is to ask for the user's intent (free text).
The Narrative pass interprets it into two profiles:

- **time budget** — a stated duration ("15 minutes") -> a target page-count range
  (heuristic: ~1 content slide/minute + title/divider overhead). "Length
  unbounded, focus on conveying content" -> the page-count repair trigger is
  **disabled**.
- **depth/tone** — "stand-up technical report" vs "seminar for my advisor" vs
  "just convey the content" -> per-beat depth, whether proof detail is kept,
  narrative tone.

Intent also sets the direction repair cuts or expands.

## Repair-at-the-right-level

After each compile, a deterministic script extracts signals; each is routed to
the **lowest level that can resolve it**, and only that unit is rewritten before
recompiling.

| Signal | Repair level | Action |
|---|---|---|
| LaTeX compile error (undefined cmd / syntax) | `.tex` | locate the enclosing `% slide:Sxx` comment; re-emit only that frame |
| Frame overflow (`S07`) | Slide IR `S07` | split / trim / move-to-appendix; re-emit only `S07` |
| Total pages/time >> intent | Narrative IR | cut/merge beats, reduce depth (page-count mode only) |
| Wrong emphasis (caught by the human at the gate) | Narrative IR | before any slides exist — cheapest |

**Overflow becomes a precise signal**: builds run with the theme's
`overflowguard=on`, so an overflow is a hard error localized to a specific frame
rather than a guess.

**Escalation and stop-loss**: if a level fails to clear its signal after `K`
tries, escalate one level up (trimming can't fix overflow -> escalate to cutting
a beat in the Narrative). A total repair budget bounds the loop; on exhaustion the
skill hands back the best-effort PDF plus `repair-report.md` listing what remains
unresolved. Never loop indefinitely.

## Skill structure and execution model

- A single `SKILL.md` orchestrator + progressively-disclosed reference files
  (one per pass), following skill conventions.
- **Main-context driven**, because the gate needs user interaction and the repair
  loop needs to invoke the compiler.
- **Deterministic tooling is Python via `uv run`**: Docling extraction, and
  LaTeX-log parsing / signal extraction (errors, overfull boxes, page count).
  These are the unit-testable hard scaffolding.
- Emission is sequential per slide in v1; per-slide parallel emission is a later
  optimization.
- Reads `template/domain.md` (optional) to calibrate; field-neutral if absent.

## Workspace layout

```
isa/
  Simple.md              # pre-built, shipped with the skill
  <Theme>.md             # produced by ISA setup
template/                # existing theme infrastructure (.sty / manual / theme.tex / domain.md)
slides/
  <paper-slug>/
    source.pdf
    figures/             # Docling output
    paper-content.md     # Docling structured extraction
    narrative.md         # Narrative IR
    slides.md            # Slide IR
    main.tex             # carries provenance comments
    main.pdf
    repair-report.md     # only when signals remain unresolved
```

Themes are selected through the existing workspace `theme.tex` mechanism;
swapping a theme means editing `theme.tex` and providing the matching ISA.

## Testing strategy

For an LLM workflow the testable surface is the deterministic scaffolding; tests
focus there (in the spirit of the 80% bar).

- **Unit tests**: Docling extraction (fixture PDF), LaTeX-log parsing
  (fixture log -> correct signals), the **repair routing table** (synthetic
  signal -> correct level), ISA setup (run on `Simple.sty` -> structurally
  correct ISA).
- **Golden-path smoke E2E**: run the whole pipeline on a sample PDF with the
  pre-built Simple ISA; assert the PDF compiles, page count falls inside the
  intent range, and there is no overflow under `overflowguard=on`.
- LLM-generated content quality is not asserted with brittle checks
  (semi-deterministic); the gate plus the smoke test guard it.

## Error handling

- Docling failure (bad PDF) -> explicit error, stop.
- Missing `xelatex` / `latexmk` -> checked at startup, prompt the user.
- A theme is selected but `isa/<Theme>.md` is absent -> prompt to run ISA setup.
- Repair budget exhausted -> hand back best-effort PDF + `repair-report.md`.

## Environment assumptions

- `xelatex` and `latexmk` available locally.
- `uv` available for Python tooling (Docling et al.).
- Figure extraction is **deterministic via Docling**, never LLM-guessed.
