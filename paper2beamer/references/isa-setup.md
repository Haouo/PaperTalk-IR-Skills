# Optional setup: author a theme's ISA

**Optional, once per theme.** This is "building a backend for a new target":
describe a Beamer theme's public API as a machine-readable ISA Set the Slide IR
and emission obey and the conformance linter verifies. The bundled `Simple` theme
and the stock `Madrid` theme already ship with their Sets under
`paper2beamer/isa/`, so you only do this for OTHER themes.

## Input

- a theme package `beamerthemeXxx.sty` (or a stock theme that ships with Beamer,
  e.g. Madrid), and its manual if one exists.

## Produce

Write `isa/<Theme>.yaml` (workspace root `isa/`, not the shipped
`paper2beamer/isa/`), validated against `isa/isa.schema.json`. It declares the
**extensions the theme provides** rather than re-listing every instruction:

```yaml
meta: { theme: Xxx, sty: beamerthemeXxx.sty, isa_version: 1,
        engine: xelatex, aspectratio: "169" }
provides: [Base@1, Zsem@1, ...]      # which standard extensions this theme implements
options: [ ... ]                     # \usetheme[...] options, with allowed values
capacity: { ... }                    # filled by the capacity probe (do not hand-set)
custom_instructions: [ ... ]         # theme-specific commands not in any extension
structural_idioms: [ ... ]           # checkable rules, e.g. block_requires_title
prose: |                             # advisory, judgement-only idioms
  ...
```

Standard extensions live in `isa/extensions/*.yaml` (`Base`, `Zsem`,
`SpecialFrames`, `Theorems`, `Columns`, `OverflowGuard`); reuse them, and only add
`custom_instructions` for what no extension covers.

## How

1. **Map the theme to extensions.** Read the manual (preferred) or the `.sty`:
   `\DeclareOptionBeamer` for options, `\newcommand`/`\NewDocumentCommand` for
   custom frames, `\setbeamercolor`/`\providecolor` for the semantic palette,
   `\setbeamertemplate` for structure. Decide which standard extensions the theme
   actually supports (e.g. does it provide our special frames? theorem styles?
   columns?). Anything bespoke goes in `custom_instructions` with its
   `lowering` (how to emulate it on a theme that lacks it).
2. **Overflow guard.** `overflowguard` is a paper2beamer-specific capability, NOT
   a standard Beamer feature. List `OverflowGuard` in `provides:` only if the
   theme actually implements that option. If it does not (most third-party
   themes), omit it; capacity then falls back to LaTeX's `Overfull \vbox`
   warning, which the log parser already handles.
3. **Measure capacity — do not guess.** Run the probe:
   `uv run python -m scripts.capacity_probe --theme <Theme>` and paste the printed
   `capacity:` block into the Set. The probe is ISA-options-aware: it enables the
   guard only if the theme provides `OverflowGuard`, and probes the `dense`
   density only if the theme declares a `density` option.

## Verify

- `uv run python -c "from scripts.isa_resolve import resolve; from pathlib import Path; print(resolve('<Theme>', Path('isa')).allowed_macros)"`
  resolves without a schema error.
- Smoke-compile a minimal deck with `\usetheme{<Theme>}` through `scripts/build.sh`.
- Show the resulting Set to the user and confirm it before using it for a deck.
