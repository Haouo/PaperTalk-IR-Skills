# Pass: emission

Turn the Slide IR into a build manifest, then let `emit_beamer.py` assemble the
deck deterministically. **Never hand-write `main.tex`** — the assembler owns the
provenance comments and line ranges that repair depends on.

## Write the build manifest

Under `slides/<slug>/build/`:

### `preamble.tex`

Everything before `\begin{document}`:

```latex
\documentclass[aspectratio=169]{beamer}
\usetheme[overflowguard=on, density=<normal|dense>, eyebrow={<optional>}]{Simple}
\title[<short>]{<full>}
\author{<author>}
\institute{<institute, or omit>}
\date{<date>}
```

- ALWAYS include `overflowguard=on` for the build, so overflow is a hard,
  per-slide signal.
- Set `density` to match the Deck meta. Add `eyebrow` only if the user wants a
  title-page label.
- Emit ONLY instructions the ISA lists. Do not add `unicode-math` or
  `\hypersetup` unless the paper genuinely needs them (the Simple theme leaves
  those to the deck on purpose).

### `order.txt`

One line per frame, in deck order. Mark unnumbered special frames with `plain`:

```
S00 beat:N00 plain
S01 beat:N01
S02 beat:N01
```

### `frames/<Sxx>.tex`

The actual LaTeX for each frame — a full `\begin{frame}...\end{frame}`, or a
special-frame macro like `\titleframe` / `\statementframe{...}` /
`\thanksframe[...]`. Use the figure files under `figures/` by name. Use semantic
blocks per the slide's `block-semantics`.

> Section dividers are automatic at each `\section{...}`. Put the `\section{...}`
> at the top of the first content frame fragment of that section (it is not a
> separate frame in `order.txt`).

## Assemble

```bash
python3 paper2beamer/scripts/emit_beamer.py \
  --manifest slides/<slug>/build --out slides/<slug>
```

This writes `slides/<slug>/main.tex` (with `% slide:Sxx beat:Nyy` comments) and
`slides/<slug>/provenance.json`. If a fragment named in `order.txt` is missing,
the assembler fails loudly — fix the manifest, do not improvise.

## Handoff

Go to `compile-verify.md`.
