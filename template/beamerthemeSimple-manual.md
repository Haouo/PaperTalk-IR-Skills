# The Simple Beamer theme

A minimal, clean, standalone 16:9 Beamer theme for dense academic talks. It is
self-contained (no logos, images, or private branding), prefers XeLaTeX, and
degrades gracefully to pdfLaTeX for Latin-only decks.

The quiet visual system: ink-on-white frame titles with a section-name eyebrow
and a hairline rule, a blue/green/gold semantic palette, blocks marked by a thin
colored left rule (not filled headers), a restrained title-page accent, and a
compact numbered section divider.

## Install

Drop `beamerthemeSimple.sty` anywhere XeLaTeX can find it (the same directory as
your deck, or a directory on `TEXINPUTS`). In this workspace it lives at the root
and every deck under `slides/` loads it via `theme.tex`.

Requirements:

- **XeLaTeX** or **LuaLaTeX** (recommended): `fontspec` plus optional CJK. Run
  two passes, or use `latexmk -xelatex` / `latexmk -lualatex`.
- **pdfLaTeX** also works for Latin-only decks; CJK is disabled automatically.
- Optional packages, all loaded only if present (graceful fallback otherwise):
  `xeCJK` (XeLaTeX) or `luatexja` (LuaLaTeX) plus a CJK font
  (Noto Sans CJK -> Fandol), and `appendixnumberbeamer`.

### CJK decks

CJK text needs an engine-specific package: `xeCJK` under XeLaTeX or `luatexja`
under LuaLaTeX. If it is missing the theme prints a warning and CJK characters do
not render (Latin text is unaffected). For XeLaTeX, install the TeX Live `langcjk`
collection (`tlmgr install xecjk`, or add `langcjk`/`langchinese` to a nix
`texlive` set) plus a CJK font such as Noto Sans CJK. If the font fallback chain
reaches Fandol, note that FandolHei has no bold face, so bold CJK frame titles
will not look heavier.

### Math fonts and link colors

The theme deliberately does **not** load `unicode-math`, set a math font, or call
`\hypersetup`. That keeps it from fighting `bm`/`amsmath` or overriding your
hyperref setup. To opt in from your deck preamble:

```latex
% Sans-matched OpenType math (XeLaTeX/LuaLaTeX):
\usepackage{unicode-math}\setmathfont{Fira Math}
% Colored links matching the accent:
\hypersetup{colorlinks=true,linkcolor=simpleAccent,urlcolor=simpleAccent,citecolor=simpleAccent}
```

## Quick start

```latex
\documentclass[aspectratio=169]{beamer}
\usetheme{Simple}
\title[Short title]{The full, possibly long, title}
\author{Author Name}
\institute{Affiliation}
\date{2026}
\begin{document}
\titleframe
\section{Motivation}
\begin{frame}{A frame title}
  \begin{itemize}\item a point\end{itemize}
\end{frame}
\statementframe{One idea worth a whole slide.}
\thanksframe[Thank you][Questions welcome]
\end{document}
```

Always give a short title (`\title[Short]{Long}`); the footer shows the short
form, and a long title without one will clip at the footer cell edge.

## Options

Pass options to `\usetheme[...]{Simple}`:

| Option | Values | Default | Effect |
|---|---|---|---|
| `eyebrow` | `{free text}` | empty | Small label on the title page. Field-agnostic; off unless set. |
| `density` | `normal`, `dense` | `normal` | `dense` tightens margins and shrinks frame titles and blocks for result-heavy decks. |
| `divider` | `on`, `off` | `on` | Auto section-divider frame at each `\section`. |
| `overflowguard` | `on`, `off` | `off` | When `on`, the build stops with a clear error if a frame body would grow into the footer. Opt-in; skips `[plain]` and `[allowframebreaks]` frames. |

Example: `\usetheme[eyebrow={PAPER READING DECK},density=dense]{Simple}`.

## Colors

Override any of these with `\definecolor{...}` **before** `\usetheme` (all use
`\providecolor`, so your definition wins):

| Color | Role | Default (RGB) |
|---|---|---|
| `simpleAccent` | primary accent: structure, rules, links, neutral blocks | 30, 90, 160 |
| `simpleAlert` | caveats: `\alert`, alert blocks | 158, 108, 24 |
| `simpleExample` | examples / desired state: example blocks | 35, 132, 104 |
| `simpleDark` | ink / body text | 31, 36, 42 |
| `simpleGray` | muted secondary text (footer, captions, dates) | 102, 108, 116 |
| `simpleLine` | hairlines | 218, 223, 228 |
| `simplePanel` | faint block body fill | 247, 249, 251 |

The semantic colors drive both blocks and inline commands: `\alert{...}` is gold,
and the `alertblock` / `exampleblock` / `block` environments carry a matching
left rule. Captions, citations, bibliography entries, the TOC, and hyperlinks all
use `simpleAccent`.

Every default foreground color clears WCAG AA (4.5:1) for normal-size text on the
white background — `simpleAccent` 6.9:1, `simpleDark` 15.6:1, `simpleGray` 5.3:1,
`simpleAlert` 4.55:1, `simpleExample` 4.6:1 — so inline `\alert{}` and example
text stay legible on a projector. If you override these, keep that headroom in
mind: a lighter accent or gold may drop below AA for body-size text.

## Special frames

All keep the Simple aesthetic (centered text, a short accent rule, no branding).
Every special frame, and the auto section dividers, are **unnumbered**: the
frame counter in the footer reflects position among ordinary content frames, so
title, divider, statement, and closing slides do not inflate the total.

- `\titleframe` — a plain title page (equivalent to a `[plain]` frame wrapping
  `\titlepage`).
- `\statementframe{TEXT}` — one large centered statement on its own slide.
- `\thanksframe[Headline][Subtitle]` — a quiet closing slide. Both bracketed
  arguments are optional; the headline defaults to "Thank you". Examples:
  `\thanksframe`, `\thanksframe[Questions?]`, `\thanksframe[Thanks][Find me at ...]`.

Standard Beamer still works: `\maketitle` / `\titlepage`, `\section`,
`itemize` / `enumerate` / `description`, `block` / `alertblock` / `exampleblock`,
`theorem` / `definition` / `proof`, `figure` + `\caption`, and `thebibliography`.

## Engine and robustness notes

- Designed for `aspectratio=169` (16:9).
- `\appendix` frames are excluded from the total count when
  `appendixnumberbeamer` is installed.
- `overflowguard=on` hooks a beamer internal (`\beamer@autobreakframebox`,
  present in current beamer); if a future beamer release renames it, the theme
  prints a warning instead of installing a broken guard. The check compares the
  body height against the safe text height (matching beamer's own overfull-vbox
  criterion, where a box's depth falls in the bottom margin).
- Build with two passes (XeLaTeX or LuaLaTeX) so the frame total is correct.

## Demo

`demo-theme.tex` (next to the theme) exercises every feature. Build it with:

```bash
xelatex demo-theme.tex && xelatex demo-theme.tex
```
