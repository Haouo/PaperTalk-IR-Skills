---
name: paper2beamer
description: Compile an academic paper PDF into a LaTeX Beamer deck (Simple theme) through an LLVM-style, IR-centric pass pipeline. Intent-aware (asks what talk you are giving) and theme-aware. Uses Docling to extract and embed the paper's ORIGINAL figures untouched. Use when the user wants to turn a paper / PDF into slides, a Beamer deck, a talk, a journal-club / conference / defense presentation, or says "paper to slides", "PDF to beamer", "make slides from this paper", "投影片", "簡報", "把論文做成投影片".
---

# paper2beamer — paper PDF → Beamer deck, the LLVM way

You are the **pass manager**. You compile a paper PDF into a `Simple`-theme
Beamer deck by running a pipeline over a single, versioned IR
(`ir.v0.json … ir.v4.json`). Mechanical stages are scripts; semantic stages are
**you**, following the per-pass instructions below.

```
PDF ─[frontend: Docling]→ ir.v0 ─[intent intake]→ ir.v0
   → content-pass → ir.v1 → narrative-pass → ir.v2
   → figure-pass → ir.v3 → layout-pass → ir.v4
   ─[backend: emit]→ deck.tex ─[build]→ deck.pdf
```

Read these references before the passes that use them (progressive disclosure):
- `references/pass-contracts.md` — the authoritative per-pass checklist.
- `references/ir-schema.md` — the IR field reference.
- `references/simple-theme-isa.md` — the theme "instruction set" (layout-pass).

## Setup (once per run)

1. Pick a build directory, default `build/<pdf-stem>/`. All IR versions, the
   `figures/`, `deck.tex`, and `deck.pdf` live there.
2. **Never hand-edit a `deck.tex`** — it is regenerated from the IR. To change the
   deck, change the IR and re-run from the affected pass.
3. The IR is the source of truth. After each semantic pass, **write the new
   `ir.vN.json` to disk** (do not keep it only in your head) so a pass can be
   re-run and a human can inspect/diff it.

## Run modes

- **staged (default).** Run the pipeline but **stop at three gates** for user
  review: ① after intent intake, ② after the narrative-pass (story arc),
  ③ after the layout-pass (slide plan, before building). At each gate, summarise
  what changed, point to the `ir.vN.json`, and wait for go / edits.
- **fast.** User says "just make the deck" / "one-shot" / "don't stop": run all
  passes through to `deck.pdf` without stopping. Still write every `ir.vN.json`.
- **-run-pass `<name>`.** Re-run a single pass: load the existing `ir.v{N-1}`,
  re-run pass N, overwrite `ir.vN` and invalidate later versions. Use this when
  the user wants to tweak one stage (e.g. "redo the figure choices").

Decide the mode from the user's phrasing; if ambiguous, default to **staged** and
say so.

---

## Stage 0 — frontend (script)

Extract structured content + original figures with Docling, via `uv` so the
dependency is isolated:

```bash
uv run --with docling python paper2beamer/scripts/frontend_docling.py \
    --pdf "<paper.pdf>" --out "build/<stem>/"
```

This writes `build/<stem>/ir.v0.json` and `build/<stem>/figures/*.png`. If it
reports zero sections, warn the user the PDF may be scanned/image-only.

## Stage 0.5 — intent intake (you) → augments `ir.v0`  · GATE ①

Interview the user briefly, then write an `intent` block into `ir.v0.json`
(load → add `intent` → save; keep everything else byte-for-byte). Ask, in one
short message (offer sensible defaults so they can one-word answer):

- **Occasion** — conference / journal-club / defense / lab-meeting?
- **Duration** — minutes? (drives the slide budget)
- **Audience** — who is in the room? (default: read `domain.md` if present)
- **Emphasis** — method, results, theory, application…?
- **Depth** — overview / balanced / deep-dive?
- **Language** — en / zh / bilingual?

Fill unanswered fields from occasion defaults. Validate
(`intent.duration_min > 0`, `language ∈ {en,zh,bilingual}`). Then, in staged
mode, **stop and confirm** the intent before continuing.

Intent is **frozen** after this — every later pass reads it but never edits it.

## Stage 1 — content-pass (you) → `ir.v1`

Read `references/pass-contracts.md#p1-content-pass`. Distil the paper into atomic
`claims[]`: one checkable assertion each, bound to its `section`, with
`evidence` **quotable from the section text** (never invent numbers), an
intent-weighted `salience ∈ [0,1]`, and `figure_refs` to supporting figures.
Untraceable assertions stay with `salience: 0`. Write `ir.v1.json`.

## Stage 2 — narrative-pass (you) → `ir.v2`  · GATE ②

Read `references/pass-contracts.md#p2-narrative-pass`. Select high-salience
claims and arrange a story arc (`story[]`) of beats with one-sentence
`headline`s and `est_minutes`. Keep Σ`est_minutes` ≈ `intent.duration_min`;
over budget → cut lowest-salience beats (claims remain in the IR). Write
`ir.v2.json`. In staged mode, **stop and show the arc** (roles + headlines +
total time) for approval before figures.

## Stage 3 — figure-pass (you) → `ir.v3`

Read `references/pass-contracts.md#p3-figure-pass`. For each beat, select the
original figure(s) that carry evidence words cannot — **≤ 1 primary per beat**
(an optional secondary for method/overview beats). Add them to `story[].figures`
with `role`. A beat with no useful figure stays text-only. Write `ir.v3.json`.

## Stage 4 — layout-pass (you) → `ir.v4`  · GATE ③

Read `references/simple-theme-isa.md` AND
`references/pass-contracts.md#p4-layout-pass`. Map beats to a concrete
`slides[]` sequence using only the theme ISA: first `titleframe`, last
`thanksframe`, big single messages as `statementframe`, content frames with
blocks chosen by **meaning** (result→`exampleblock`, caveat→`alertblock`,
neutral→`block`) and figures embedded by id. Respect the overflow budget (short
bullets; split crowded frames). Write `ir.v4.json`. In staged mode, **stop and
show the slide plan** before building.

## Stage 5 — backend + build (scripts)

```bash
python  paper2beamer/scripts/emit_beamer.py --ir "build/<stem>/ir.v4.json" \
                                            --out "build/<stem>/deck.tex"
bash    paper2beamer/scripts/build.sh           "build/<stem>/deck.tex"
```

`build.sh` exit codes: `0` ok · `2` usage/env · `3` **overflow** · `4` other
LaTeX error.

### Verifier loop (overflow → re-layout)

On exit code `3`, read the reported slide numbers, then **re-run the layout-pass
for just those slides** (shorten/split them, or set their `density_hint`), write
a new `ir.v4.json`, re-emit, and rebuild. Do this **at most once
automatically**; if it still overflows, stop and ask the user how to trim.

On exit code `4`, surface the first errors from `build.sh`'s output and fix the
IR/figure cause — do not patch `deck.tex` directly.

## Done

Report the path to `deck.pdf`, the slide count vs. the time budget, and any
figures that degraded to placeholders (missing images). Offer the user the
`-run-pass` option to iterate on any single stage.

## Guardrails

- Do not fabricate data, results, or citations. Everything on a slide must trace
  to the paper.
- Do not re-render or "improve" original figures; embed them as extracted.
- Always write each `ir.vN.json` to disk; the IR — not your context — is the
  state of the build.
- Keep the human in the loop at the three gates unless the user chose fast mode.
