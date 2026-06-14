# Verification plan

How we know `paper2beamer` works. The suite is layered so the fast, hermetic
checks run everywhere and the heavier checks degrade to skips when a tool is
absent — nothing silently passes by doing nothing.

## How to run

```bash
# From the skill root. uv provisions pytest (and, for the e2e check, docling)
# without touching system packages.
cd paper2beamer
uv run --with pytest python -m pytest tests/ -q

# Include the optional live-Docling end-to-end (slow; downloads models once):
uv run --with pytest --with docling python -m pytest tests/ -q -m e2e
```

Requirements per layer:
- Unit + golden + schema: Python only.
- Integration build: `xelatex` on PATH (tests `skipif` otherwise).
- Live frontend e2e: `docling` + `xelatex` (opt-in, marked `e2e`).

## What each layer covers

### 1. Unit — `test_ir_common.py`
The enforced contract and the primitives every stage relies on.
- `escape_latex`: all ten TeX specials, single-pass correctness (the
  backslash/brace interaction that a naive sequential escaper gets wrong),
  non-string coercion.
- Atomic IO: round-trip, **no temp file left behind**, and the three distinct
  load failures (missing / corrupt JSON / non-object) each raise their own type.
- `validate_ir` stage-awareness: valid v0; rejects wrong schema version,
  duplicate section/figure ids, bad figure kind, missing intent after intake,
  bad language, out-of-range salience, dangling figure refs, **>1 primary figure
  per beat**, empty deck, and malformed body items.

### 2. Backend golden + behaviour — `test_emit_beamer.py`
The renderer is a pure function, so we pin it with a golden file.
- `deck.expected.tex` must match byte-for-byte (catches any accidental output
  drift).
- Special characters are escaped in the rendered deck.
- `width` whitelist accepts safe dims and **rejects injection**, falling back to
  the default.
- A missing figure image emits a labelled placeholder and never
  `\includegraphics` a missing file; a present figure is embedded.
- Theme options: short talks → `density=dense`, long talks → `normal`, always
  `overflowguard=on`, occasion → eyebrow.
- The backend refuses an incomplete (non-v4) IR.

### 3. Schema consistency — `test_schema_consistency.py`
Prevents the JSON-Schema mirror and the human docs from drifting from the
enforced validator: every enum in `references/ir_schema.json` (figure kinds,
claim types, story roles, frame types, block types, languages, schema version)
must equal the corresponding `ir_common` constant. Also validates the sample
fixture against `ir_common`.

### 4. Frontend helpers — `test_frontend_helpers.py`
Docling is heavy and needs a real PDF, so the deterministic extraction logic is
tested against a hand-built fake document:
- sections grouped by headers, frontmatter preserved, captions not leaking into
  bodies, unique ids;
- best-effort figure cross-reference linking by number;
- version-tolerant label/provenance reads;
- an un-renderable picture is skipped, not fatal.

### 5. Integration build — `test_integration_build.py`
The strongest signal: the generated TeX + bundled theme actually compile.
- Happy path: sample IR → emit → `build.sh` → a non-empty `deck.pdf`, exit 0.
- **Verifier signal**: the overstuffed fixture overflows and `build.sh` returns
  exit 3 with the offending slide reported.
- A missing deck path is a usage error (exit 2).

## Manual end-to-end with a real paper

The automated suite deliberately avoids downloading Docling models. To validate
the *whole* pipeline on a real PDF once:

```bash
# 1. Frontend (Docling) — extract content + original figures
uv run --with docling python paper2beamer/scripts/frontend_docling.py \
    --pdf yourpaper.pdf --out build/yourpaper/

# 2..5. Run the semantic passes through the SKILL (content/narrative/figure/
#       layout), which write ir.v1..ir.v4 — then:
python paper2beamer/scripts/emit_beamer.py \
    --ir build/yourpaper/ir.v4.json --out build/yourpaper/deck.tex
bash   paper2beamer/scripts/build.sh build/yourpaper/deck.tex
```

Expected: `build/yourpaper/figures/*.png` are the paper's original figures, and
`build/yourpaper/deck.pdf` opens as a 16:9 Simple-theme deck.

## Pre-commit checklist

- [ ] `uv run --with pytest python -m pytest tests/ -q` is green.
- [ ] No stray build artifacts staged (`*.aux *.log *.pdf *.xdv *.nav *.snm
      *.toc *.fls *.fdb_latexmk *.build.out` are git-ignored).
- [ ] If the IR shape changed: `ir_common`, `ir_schema.json`, `ir-schema.md`,
      and the golden fixture are all updated together (schema-consistency test
      enforces the first two).
- [ ] If the backend output changed intentionally: regenerate and re-inspect
      `deck.expected.tex`, and confirm it still compiles.
