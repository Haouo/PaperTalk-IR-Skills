# Design: `paper2beamer` — an LLVM-IR-inspired Paper-PDF → LaTeX-Beamer Skill

**Date:** 2026-06-15
**Status:** Approved (design); pending implementation plan
**Workspace:** `papertalk-ir-skills`

## 1. Summary

A Claude Code skill that compiles an academic paper PDF into a LaTeX Beamer
deck, structured as a small compiler. It mirrors LLVM's **Frontend → IR +
Passes → Backend** architecture: a deterministic frontend extracts structured
content and original figures, a set of semantic optimization passes transform a
versioned intermediate representation (IR), and a deterministic backend emits
and compiles `deck.tex`.

The flow is **intent-aware** (the user's talk intent is captured up front and
drives every pass, analogous to LLVM's target triple / optimization goal) and
**theme-aware** (the backend deeply understands the bundled `Simple` Beamer
theme's "instruction set" — special frames, semantic blocks, density,
CJK/XeLaTeX).

## 2. Goals / Non-Goals

### Goals
- Turn a paper PDF into a compilable, well-structured Simple-theme Beamer deck.
- Use **Docling** to extract original figures/tables and embed them untouched.
- Make the pipeline an explicit, inspectable **pass pipeline** over a versioned
  IR, faithful to the LLVM mental model.
- Be intent-aware (occasion, duration, audience, emphasis, language, depth).
- Be theme-aware for the `Simple` theme, producing decks that use theme
  features correctly and do not overflow.
- Support two run modes: **staged** (review gates, default) and **fast**
  (one-shot), plus `-run-pass` to re-run a single pass.

### Non-Goals (YAGNI)
- Multiple/pluggable Beamer themes. We focus on `Simple` and do it deeply. A
  theme-capability abstraction is explicitly deferred.
- Re-rendering or beautifying figures. Original figures are embedded as-is.
- Authoring new scientific content. The skill summarizes/organizes; it does not
  invent claims or data.

## 3. Architecture

LLVM-faithful three-stage pipeline over a versioned, accumulative IR.

```
PDF ──[Frontend: Docling script]──▶ ir.v0  (paper + figures/, cropped originals)
                                       │
              ┌─────────────────────────┴── intent intake (LLM) writes `intent` block
              ▼
   ┌─ Middle: Optimization Passes (semantic, LLM; read vN → write vN+1) ─────────┐
   │  P1 content-pass    extract claims / evidence / salience          → ir.v1   │
   │  P2 narrative-pass  compress into an intent-driven story arc       → ir.v2   │
   │  P3 figure-pass     auto-select relevant original figures per beat → ir.v3   │
   │  P4 layout-pass     map beats to Simple-theme frame/block sequence → ir.v4   │
   └─────────────────────────────────────────────────────────────────────────────┘
              ▼
   ir.v4 ──[Backend: emit_beamer.py]──▶ deck.tex ──[build.sh: latexmk -xelatex]──▶ deck.pdf
```

### LLVM correspondence

| LLVM | This skill |
|---|---|
| Frontend (source → AST → IR) | Docling script: PDF → structured IR + cropped figures |
| `target triple` / `-O2` | **intent block** drives every pass |
| Optimization passes | content / narrative / figure / layout passes |
| Pass manager (`opt`) | SKILL.md orchestration: staged gates, `-run-pass` |
| SSA (immutable values) | Versioned IR `ir.v0…v4`; each pass writes a new version, diffable |
| Target backend knows the ISA | Backend deeply knows the `Simple` theme's command vocabulary |
| Compile-to-machine-code verify | `latexmk -xelatex` actually builds the PDF; `overflowguard` as verifier |

### Run modes
- **staged (default):** stop at three review gates so the user can inspect / edit
  IR before continuing.
- **fast:** skip gates, run straight to `deck.pdf`.
- **`-run-pass <name>`:** re-run a single pass from the existing `ir.v{N-1}`,
  overwriting `ir.vN` and later versions.

### Review gates (staged mode)
1. After the **intent** block is written (gate ①).
2. After **narrative-pass** — the story arc is finalized (gate ②).
3. Before the **backend** — the slide plan `ir.v4` is finalized (gate ③).

### Verifier loop
`build.sh` detects overflow via `overflowguard=on`. The overflowing-frame list is
fed back into `layout-pass` for a localized re-layout. **Auto-retry at most once**
to avoid infinite loops; if it still overflows, report to the user.

## 4. Environment

- **Python** via **`uv`** — all Python helpers run as `uv run --with docling ...`
  so they do not depend on system site-packages (the system `pip3`/`python3` were
  observed to disagree on `docling` visibility). uv manages the environment.
- **Docling** 2.99.0 (available) for PDF parsing + figure extraction.
- **LaTeX:** `xelatex` (nix) + `latexmk` (available); two-pass build for correct
  frame totals.
- **Theme assets:** reuse the workspace's existing
  `template/beamerthemeSimple.sty`, `template/theme.tex`, `template/domain.md`.

## 5. IR Schema (`ir.vN.json`, accumulative)

Each pass only **adds/refines its own fields**; it never deletes earlier fields
and never re-renders original figures. `meta.source_pdf` and `intent` are
immutable for the whole run (SSA spirit).

```jsonc
{
  "meta": {
    "schema": "1.0",
    "ir_version": "v2",
    "source_pdf": "paper.pdf",
    "produced_by_pass": "narrative-pass"
  },

  // intent block: written once after intake, immutable thereafter; read by every pass
  "intent": {
    "occasion": "journal-club",        // conference | journal-club | defense | lab-meeting
    "duration_min": 30,
    "audience": "NLP graduate students",
    "emphasis": ["method", "results"], // facets to foreground
    "language": "en",                  // en | zh | bilingual
    "depth": "balanced",               // overview | balanced | deep-dive
    "domain_ref": "template/domain.md" // audience-calibration source
  },

  // frontend (Docling script): v0
  "paper": {
    "title": "...", "authors": ["..."], "venue": "...", "abstract": "...",
    "sections": [ { "id": "s1", "title": "Introduction", "level": 1, "text": "..." } ],
    "references": [ { "key": "smith21", "text": "..." } ]
  },
  "figures": [                          // registry of cropped originals, untouched
    { "id": "fig3", "kind": "figure",   // figure | table | equation
      "page": 5, "path": "figures/fig3.png",
      "caption": "Figure 3: ...",       // Docling-extracted original caption
      "referenced_in": ["s4"] }         // best-effort: sections that cite it
  ],

  // content-pass: v1
  "claims": [
    { "id": "c1", "section": "s4",
      "type": "result",                 // problem|method|result|contribution|limitation|background
      "statement": "one-sentence claim",
      "evidence": ["+3.2 BLEU over baseline"],
      "figure_refs": ["fig3"],          // figures supporting this claim
      "salience": 0.9 }                 // importance for THIS talk (intent-aware)
  ],

  // narrative-pass: v2 (compressed story arc, total time ~ intent.duration_min)
  "story": [
    { "id": "u1", "role": "result",     // hook|problem|gap|idea|method|result|takeaway|closing
      "headline": "the one-line message of this beat",
      "claim_refs": ["c1", "c2"],
      "figures": [ { "figure_id": "fig3", "role": "evidence" } ],  // filled by figure-pass
      "est_minutes": 2.0,
      "notes": "speaker-note seed" }
  ],

  // layout-pass: v4 (concrete Simple-theme frame sequence)
  "slides": [
    { "index": 1, "frame_type": "titleframe" },
    { "index": 2, "frame_type": "frame", "title": "...", "story_ref": "u1",
      "body": [ { "block": "exampleblock", "title": "Result",
                  "items": ["+3.2 BLEU", "..."] },
                { "figure": "fig3", "caption": "...", "width": "0.7\\textwidth" } ],
      "density_hint": "normal", "notes": "..." },
    { "index": 7,  "frame_type": "statementframe", "text": "One big takeaway." },
    { "index": 18, "frame_type": "thanksframe", "headline": "Thanks", "subtitle": "..." }
  ]
}
```

## 6. Pass Contracts

| Pass | Type | Reads | Writes (new fields) | Key invariants / behavior | Failure handling |
|---|---|---|---|---|---|
| **frontend** `frontend_docling.py` | script | `paper.pdf` | `paper`, `figures` → **ir.v0** | Crop + register originals untouched; no semantic judgment | Docling failure → explicit error, no half-baked IR |
| **intent intake** | LLM (interactive) | v0 + `domain.md` | `intent` (write once) → **ir.v0** | Staged mode stops here = **gate ①** | Unanswered → fill from occasion defaults |
| **P1 content-pass** | LLM | v0 | `claims` → **ir.v1** | Each claim bound to a section + salience; no fabricated data; evidence must trace to `paper.text` | Untraceable claim → `salience:0`, not dropped |
| **P2 narrative-pass** | LLM | v1 + intent | `story` → **ir.v2** | **Compress**: pick high-salience claims into an arc; Σ`est_minutes` ≈ `duration_min`; **dropped claims stay in IR, never deleted** | Over time budget → lower depth / cut lowest-salience beats |
| **P3 figure-pass** | LLM | v2 | story[].`figures` → **ir.v3** | Select only from `figures[]`; **≤1 primary figure per beat**, with an optional secondary side-by-side for method/overview beats; carry original caption | No suitable figure → text-only beat |
| **P4 layout-pass** | LLM | v3 + `simple-theme-isa.md` | `slides` → **ir.v4** | Map to legal theme frames/blocks; big messages → `statementframe`; respect density; avoid overflow | — |
| **backend** `emit_beamer.py` | script | v4 | `deck.tex` | **Pure rendering**, zero semantic decisions; uses theme commands | Schema mismatch → stop and name the field |
| **build** `build.sh` | script | `deck.tex` | `deck.pdf` | `latexmk -xelatex` two passes; `overflowguard=on` as verifier | Overflow/compile error → report + suggest re-running layout-pass |

### Figure rule (resolved)
A beat carries **at most one primary figure**. For method/overview beats,
`layout-pass` may add **one optional secondary supporting figure side-by-side**.
This keeps slides uncluttered while allowing the common "two-panel method
overview" case raised during design.

## 7. Deliverables

A single skill plus bundled scripts and references (progressive disclosure):

```
paper2beamer/
├─ SKILL.md                  # pass-manager orchestration + per-pass instructions
├─ scripts/
│  ├─ frontend_docling.py    # uv run --with docling: PDF → ir.v0 + figures/
│  ├─ emit_beamer.py         # ir.v4 → deck.tex (theme-aware template)
│  └─ build.sh               # latexmk -xelatex (two passes)
├─ references/
│  ├─ ir-schema.md           # IR JSON schema + example
│  ├─ simple-theme-isa.md    # Simple theme "instruction set" cheat-sheet for layout/backend
│  └─ pass-contracts.md      # per-pass input/output contracts
└─ assets/                   # reuse existing template/beamerthemeSimple.sty etc.
```

## 8. Testing Strategy

- **frontend_docling.py:** unit test against a small fixture PDF → asserts
  sections + figure registry shape; figures exist on disk and are referenced.
- **emit_beamer.py:** golden-file test — a fixed `ir.v4` renders to an expected
  `deck.tex`; pure-function, deterministic.
- **build.sh:** integration — emitted `deck.tex` compiles with `xelatex` to a
  non-empty PDF; overflow case triggers the verifier path.
- **IR schema:** schema-validation test for each `ir.vN` produced in a sample run.
- **End-to-end:** one fixture paper → staged run → compilable deck; assert frame
  count is within the intent's duration budget tolerance.

## 9. Open Questions / Future Work

- Pluggable theme adapters (deferred; `simple-theme-isa.md` is the seam).
- Optional `bilingual` language path needs CJK font availability checks at build.
- Parallelizing `content-pass` per-section via subagents if long papers strain a
  single context (borrow approach B locally).

## 10. Decisions Log

- IR depth: **full pass pipeline** (composable, ordered, individually re-runnable).
- IR form: **single accumulative structured file**, versioned per pass (SSA-like).
- Run control: **staged with gates (default) + fast one-shot**, plus `-run-pass`.
- Figures: **figure-pass auto-selects** relevant originals; embedded untouched.
- Intent: **opening intake interview → written to IR top**, read by every pass.
- Theme: **focus on `Simple` theme deeply** (single-theme, YAGNI).
- Implementation shape: **hybrid (approach C)** — deterministic stages as scripts,
  semantic stages as LLM passes; **uv** manages the Python environment.
- claims are **never deleted, only salience-marked**; **≤1 primary figure/beat**
  (optional secondary for overview); **verifier auto-retry once**.
