# Optional setup: build a theme's ISA

**Optional, once per theme.** This is "building a backend for a new target": read
a user-supplied Beamer theme and distil its public API into an ISA manifest the
Slide IR and emission passes can obey. The bundled Simple theme already ships
with `paper2beamer/isa/Simple.md`, so you only run this for OTHER themes.

## Input

- a theme package `beamerthemeXxx.sty` (required), and its manual if one exists.

## Produce

Write `isa/<Theme>.md` (workspace root `isa/`, not the shipped
`paper2beamer/isa/`) in the SAME four-section structure as
`paper2beamer/isa/Simple.md`:

1. **Instructions** — special frames, semantic block environments, inline
   emphasis, semantic colors, the document shell, and which standard Beamer
   constructs work.
2. **Options** — what `\usetheme[...]` accepts, and how to override colors.
3. **Constraints** — aspect ratio, engine/font requirements, rough per-frame
   capacity, frame-numbering behaviour, and forbidden zones (packages the theme
   deliberately leaves to the deck).
4. **Idioms** — the theme's style contract.

## How

- If a manual exists, prefer it; it is the human-readable ISA already.
- Otherwise, read the `.sty` source: `\DeclareOption*`/`\DeclareOptionBeamer` for
  options, `\newcommand`/`\NewDocumentCommand` for special frames,
  `\setbeamercolor`/`\providecolor` for the semantic palette,
  `\setbeamertemplate` for structure.
- **Overflow detection**: note whether the theme has an `overflowguard`-style
  option. If it does, the build should enable it. If it does NOT, overflow
  detection falls back to generic `Overfull \vbox` warnings (the log parser
  already handles both) — record this in the ISA's Constraints section so the
  Slide IR budgets capacity more conservatively.

## Confirm

Show the resulting ISA to the user and confirm it before using it for a deck.
