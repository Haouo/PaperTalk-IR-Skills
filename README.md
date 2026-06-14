# papertalk-ir-skills

**Turn a paper PDF into a LaTeX Beamer talk — the way a compiler turns source
into a binary.**

`paper2beamer` is a [Claude Code](https://claude.com/claude-code) skill that
compiles an academic paper into a clean, 16:9 Beamer deck. It borrows LLVM's
architecture: a deterministic **frontend** extracts structured content and the
paper's *original figures*, a series of semantic **optimization passes** rewrite
a versioned **intermediate representation (IR)**, and a deterministic
**backend** emits and compiles the `.tex`.

The flow is **intent-aware** (it asks what talk you are giving and tailors the
deck to it) and **theme-aware** (the backend speaks the bundled *Simple* theme's
vocabulary fluently, and never overflows a slide).

繁體中文版： [README-zh-TW.md](./README-zh-TW.md)

---

## Why "IR-inspired"?

A normal "PDF → slides" tool is a black box. This one is a **pipeline you can
inspect, edit, and re-run stage by stage**, exactly like `clang`/`opt`:

| LLVM | paper2beamer |
|---|---|
| Frontend (source → AST → IR) | Docling: PDF → `ir.v0` + cropped original figures |
| `target triple` / `-O2` | **intent block** (occasion, duration, audience, emphasis…) drives every pass |
| Optimization passes | `content` → `narrative` → `figure` → `layout` |
| Pass manager (`opt`) | the skill orchestrates passes, with review gates and `-run-pass` |
| SSA (immutable values) | versioned IR `ir.v0 … ir.v4`; each pass writes a new, diffable version |
| Target backend knows the ISA | the backend knows the Simple theme's frames/blocks |
| Compile + verify | `latexmk -xelatex` builds the PDF; the theme's overflow guard is the verifier |

```
PDF ─[frontend: Docling]→ ir.v0 ─[intent intake]→ ir.v0
   → content-pass → ir.v1 → narrative-pass → ir.v2
   → figure-pass → ir.v3 → layout-pass → ir.v4
   ─[backend: emit]→ deck.tex ─[build]→ deck.pdf
```

The IR is the single source of truth. Because each pass writes a new
`ir.vN.json`, you can open any stage, diff it, hand-edit it, and re-run just the
passes downstream.

---

## What you get

- **Original figures, untouched.** Docling crops the paper's actual figures and
  tables; the figure-pass *selects* which to show, and the backend embeds them
  as-is. Nothing is redrawn or hallucinated.
- **A talk, not a dump.** The narrative-pass compresses the paper into a story
  arc sized to your time budget; the layout-pass maps it to semantic blocks
  (results → green, caveats → gold) on the Simple theme.
- **A deck that actually builds.** The backend is a pure renderer with strict
  validation and LaTeX escaping; the build step compiles with XeLaTeX and fails
  loudly (with the offending slide) if anything overflows.
- **You stay in control.** Three review gates by default; or one-shot "fast"
  mode; or re-run a single pass to iterate.

---

## Requirements

| Tool | Why | Notes |
|---|---|---|
| [`uv`](https://docs.astral.sh/uv/) | runs the Docling frontend in an isolated env | recommended; avoids polluting system Python |
| **Docling** ≥ 2.99 | PDF parsing + figure extraction | provisioned on demand via `uv run --with docling` |
| **XeLaTeX** (TeX Live) | compiles the deck (`fontspec`, optional `xeCJK`) | `latexmk` used if present, else two `xelatex` passes |
| Claude Code | runs the skill | the passes are driven by the model |

For CJK decks you also need the TeX Live `langcjk` collection and a CJK font
(e.g. Noto Sans CJK) — see `paper2beamer/assets/beamerthemeSimple-manual.md`.

---

## Install

Place the skill where Claude Code discovers skills (e.g. `~/.claude/skills/`),
or keep it in this repo and point your skills path here. The skill is the
`paper2beamer/` directory; it is self-contained (it bundles the theme in
`assets/`).

```
~/.claude/skills/paper2beamer  ->  (this repo)/paper2beamer
```

---

## Quick start (in Claude Code)

Just ask:

> "Turn `attention.pdf` into a 20-minute journal-club talk."

The skill will:

1. Run the Docling **frontend** to produce `build/attention/ir.v0.json` and
   `build/attention/figures/*.png`.
2. **Interview you** briefly (occasion, duration, audience, emphasis, depth,
   language) and freeze that into the IR's `intent` block — **gate ①**.
3. Run the **content** and **narrative** passes, then show you the story arc —
   **gate ②**.
4. Run the **figure** and **layout** passes, then show you the slide plan —
   **gate ③**.
5. Emit `deck.tex` and build `deck.pdf`, automatically re-laying-out any slide
   that overflows (once).

Say *"just make the deck"* to skip the gates (**fast mode**), or *"redo the
figure choices"* to re-run a single pass (**`-run-pass`**).

---

## Running the deterministic stages by hand

The scripts are usable on their own (useful for debugging or scripting):

```bash
# Frontend — PDF -> ir.v0 + figures (isolated via uv)
uv run --with docling python paper2beamer/scripts/frontend_docling.py \
    --pdf paper.pdf --out build/paper/

# ... the model runs the content/narrative/figure/layout passes, writing
#     build/paper/ir.v1.json ... ir.v4.json ...

# Backend — ir.v4 -> deck.tex (pure, deterministic)
python paper2beamer/scripts/emit_beamer.py \
    --ir build/paper/ir.v4.json --out build/paper/deck.tex

# Build — deck.tex -> deck.pdf (XeLaTeX; overflow guard = verifier)
bash paper2beamer/scripts/build.sh build/paper/deck.tex
```

`build.sh` exit codes: `0` ok · `2` usage/env · `3` **overflow** (re-run the
layout-pass for the reported slides) · `4` other LaTeX error.

---

## The IR and the passes

The complete contract lives in `paper2beamer/references/`:

- [`ir-schema.md`](./paper2beamer/references/ir-schema.md) — every IR field.
- [`ir_schema.json`](./paper2beamer/references/ir_schema.json) — machine-checkable
  JSON Schema (mirrors the enforced validator in `scripts/ir_common.py`).
- [`pass-contracts.md`](./paper2beamer/references/pass-contracts.md) — the
  per-pass input/output checklist.
- [`simple-theme-isa.md`](./paper2beamer/references/simple-theme-isa.md) — the
  theme "instruction set" the layout-pass plans against.

Key invariants enforced in code:

- The IR is **accumulative**: a pass only adds its own fields; it never deletes a
  prior pass's output. `meta.source_pdf` and `intent` are frozen.
- **Claims are never deleted, only ranked** (`salience`); the narrative-pass
  *selects* from them.
- **≤ 1 primary figure per beat** (an optional secondary for method/overview
  beats).
- Evidence must trace to the paper — the content-pass cannot invent numbers.

---

## Layout

```
papertalk-ir-skills/
├─ paper2beamer/                  # the skill
│  ├─ SKILL.md                    # pass-manager orchestration (the brain)
│  ├─ scripts/
│  │  ├─ ir_common.py             # IR contract: validation, atomic IO, LaTeX escaping
│  │  ├─ frontend_docling.py      # PDF -> ir.v0 + figures (Docling)
│  │  ├─ emit_beamer.py           # ir.v4 -> deck.tex (pure renderer)
│  │  └─ build.sh                 # deck.tex -> deck.pdf (XeLaTeX + verifier)
│  ├─ references/                 # IR schema, theme ISA, pass contracts
│  ├─ assets/                     # bundled Simple theme (.sty + manual)
│  └─ tests/                      # unit + golden + schema + integration + e2e
├─ template/                      # workspace theme source + domain.md
├─ docs/superpowers/specs/        # the design spec
├─ README.md / README-zh-TW.md
├─ CONTRIBUTING.md
└─ LICENSE.md
```

---

## Verification

The test suite is layered so the fast checks run everywhere and the heavy ones
skip cleanly when a tool is missing. Full details:
[`paper2beamer/tests/VERIFICATION.md`](./paper2beamer/tests/VERIFICATION.md).

```bash
cd paper2beamer
# Fast, hermetic suite (unit + golden + schema + frontend helpers + integration):
uv run --with pytest python -m pytest tests/ -c tests/pytest.ini -q

# Opt-in live end-to-end (downloads Docling models, needs xelatex):
uv run --with pytest --with docling python -m pytest tests/ -c tests/pytest.ini -m e2e -q
```

---

## Troubleshooting

- **"Docling is not importable"** — run the frontend through `uv` (the message
  shows the exact command). The system `python` may not see the `pip`-installed
  Docling; `uv run --with docling` sidesteps that.
- **Build exits with code 3 (overflow)** — a slide is too full. The skill
  re-lays-out automatically once; if it persists, trim the slide or set
  `density=dense`.
- **A figure shows a "[missing figure]" box** — Docling could not extract that
  image; the build still succeeds. Re-run the frontend or supply the asset.
- **Scanned/image-only PDF** — the frontend warns when it finds no text; OCR
  output is unreliable, so prefer a born-digital PDF.

---

## License

[MIT](./LICENSE.md). The bundled *Simple* Beamer theme is self-contained (no
logos or third-party branding).
