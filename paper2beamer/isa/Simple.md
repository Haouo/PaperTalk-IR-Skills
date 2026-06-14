# ISA: Simple (beamerthemeSimple v3.2)

> Capability manifest for the bundled Simple theme. This is the contract the
> Slide IR and emission passes MUST obey: emit only the instructions listed
> here, respect the constraints, follow the idioms. Builds run with
> `overflowguard=on` so any overflow becomes a hard, per-slide error.

## 1. Instructions (what you may emit)

**Document shell**

- `\documentclass[aspectratio=169]{beamer}` — 16:9 is the only supported ratio.
- `\usetheme[<options>]{Simple}` — see options in section 2.
- Title metadata: `\title[<short>]{<full>}`, `\author{}`, `\institute{}`,
  `\date{}`. ALWAYS give a short title; the footer clips a long one.

**Special frames (unnumbered, on-theme; prefer these for structural slides)**

- `\titleframe` — title page.
- `\statementframe{TEXT}` — one big centered statement on its own slide.
- `\thanksframe[Headline][Subtitle]` — closing slide; both args optional, the
  headline defaults to "Thank you".
- Section dividers are AUTOMATIC at each `\section{...}` (unless `divider=off`).

**Content frames**

- `\begin{frame}{Title}{Optional subtitle} ... \end{frame}` — numbered content.
- `\section{...}` sets the frame-title eyebrow and triggers the auto divider.
  Keep section names SHORT (a long one wraps above the frame title).

**Semantic blocks (carry meaning by color; pick by what the content means)**

- `block` → neutral claim / definition (accent left rule).
- `alertblock` → caveat / warning / limitation (gold left rule).
- `exampleblock` → example / desired state / positive result (green left rule).
- An EMPTY block title prints no rule and no gap — always give a block a title.

**Inline semantics**

- `\alert{...}` → gold emphasis, matches `alertblock`.
- example text color matches `exampleblock`.

**Standard Beamer that also works**: `itemize` / `enumerate` / `description`,
`theorem` / `definition` / `proof`, `figure` + `\caption` (captions are
numbered, label separated by a colon), `thebibliography`.

## 2. Options (`\usetheme[...]{Simple}`)

| Option | Values | Default | Effect |
|---|---|---|---|
| `eyebrow` | free text | empty | Small title-page label. Field-agnostic. |
| `density` | `normal`, `dense` | `normal` | `dense` tightens margins and shrinks titles/blocks for result-heavy slides. |
| `divider` | `on`, `off` | `on` | Auto section-divider frame at each `\section`. |
| `overflowguard` | `on`, `off` | `off` | **Builds MUST set `on`**: a frame body reaching the footer becomes a hard error naming the slide number. Skips `[plain]` and `[allowframebreaks]` frames. |

Color overrides: `\definecolor{<name>}{RGB}{r,g,b}` BEFORE `\usetheme` (every
color uses `\providecolor`, so your definition wins).

## 3. Constraints (calling conventions, capacity, forbidden zones)

- **Aspect ratio**: 16:9 only.
- **Engine**: XeLaTeX (or LuaLaTeX). CJK needs `xeCJK` (XeLaTeX) or `luatexja`
  (LuaLaTeX) plus a CJK font; if absent, CJK silently does not render and Latin
  text is unaffected.
- **Capacity** (rough, for overflow budgeting): at `density=normal` a content
  frame comfortably holds ~6–8 short bullets, OR one figure plus 2–3 bullets, OR
  two small blocks. `density=dense` adds roughly 25% headroom. When
  `overflowguard=on` fires, the slide is over — split it, trim it, or switch that
  build to `density=dense`.
- **Frame numbering**: title, dividers, statement, and thanks frames are
  unnumbered and do NOT count toward the footer total. Page-count budgeting
  should count content frames.
- **Forbidden zones**: the theme deliberately does NOT load `unicode-math`, does
  NOT set a math font, and does NOT call `\hypersetup`, so it never fights
  `bm`/`amsmath` or your hyperref setup. You MAY opt into these at the deck
  preamble if a paper truly needs them, but that is the deck's choice, not the
  theme's — do not assume they are present.

## 4. Idioms (style contract)

- Mark meaning with COLOR and the semantic block, not with decoration or filled
  headers. Choose `block` / `alertblock` / `exampleblock` by what the content
  *means* (claim / caveat / example).
- Use color semantically: accent = structure, gold = caveat, green = example.
- Keep section names short; give every block a title; give every deck a short
  title.
- One idea per `\statementframe`. Prefer the special frames for title and
  closing slides over hand-rolled layouts.
- Keep the default colors unless the field demands otherwise — the defaults all
  clear WCAG AA contrast on the white background.
