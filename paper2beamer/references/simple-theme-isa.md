# Simple theme "instruction set" (ISA)

This is the cheat-sheet the **layout-pass** plans against and the **backend**
emits. It is a distilled, layout-oriented view of `assets/beamerthemeSimple.sty`;
the full prose manual is `assets/beamerthemeSimple-manual.md`. The backend
(`emit_beamer.py`) only knows how to spell the constructs listed here — planning
outside this set will fail validation, by design (keeps the deck buildable).

## Document shell (emitted automatically by the backend)

```latex
\documentclass[aspectratio=169]{beamer}
\usetheme[eyebrow={...},density=normal|dense,overflowguard=on]{Simple}
\title[Short]{Long}\author{...}\institute{...}\date{}
\begin{document} ... \end{document}
```

The layout-pass does **not** write the shell — it only produces the `slides`
array. The backend derives `\usetheme` options from `intent` (occasion → eyebrow,
short duration → `density=dense`, always `overflowguard=on`).

## Frame types (`slides[].frame_type`)

| `frame_type` | Emits | When the layout-pass should use it |
|---|---|---|
| `titleframe` | `\titleframe` | Exactly once, first slide. |
| `frame` | `\begin{frame}{title} … \end{frame}` | Every ordinary content slide. |
| `statementframe` | `\statementframe{TEXT}` | One big idea that deserves a whole slide (a `takeaway`/`hook` beat). No bullets. |
| `thanksframe` | `\thanksframe[Head][Sub]` | Exactly once, last slide (the `closing` beat). |

Section dividers are produced **automatically** by the theme at each `\section`
(the backend currently emits a linear deck without explicit `\section` calls; see
"Future work" in the spec). Do not plan divider frames by hand.

## Content-frame body (`slides[].body[]`)

A body is an ordered list; each item is **either** a block **or** a figure.

### Blocks (`{"block": ...}`)

| `block` value | Emits | Semantic color | Use for |
|---|---|---|---|
| `block` | `block` env | accent (blue) | neutral claims, setup |
| `alertblock` | `alertblock` env | gold | caveats, limitations, warnings |
| `exampleblock` | `exampleblock` env | green | results, desired behaviour, examples |
| `itemize` | `itemize` list | — | a plain bullet list (no box) |
| `enumerate` | `enumerate` list | — | an ordered list (no box) |

Block fields:
- `title` — the block heading (ignored for `itemize`/`enumerate`).
- `text` — an optional leading paragraph.
- `items` — an optional list of bullet strings (rendered as an inner `itemize`).

```jsonc
{ "block": "exampleblock", "title": "Result",
  "text": "On the held-out set:", "items": ["+3.2 BLEU", "2x faster decoding"] }
```

### Figures (`{"figure": ...}`)

```jsonc
{ "figure": "fig3", "caption": "...", "width": "0.7\\textwidth" }
```

- `figure` — a figure **id that exists in `figures[]`** (referential integrity is
  validated). The original image is embedded untouched.
- `caption` — optional; if omitted the backend falls back to the paper's original
  caption for that figure.
- `width` — optional; must match a safe LaTeX width
  (`0.7\textwidth`, `\linewidth`, `5cm`, …) or it is replaced by `0.8\textwidth`.
  Height is auto-capped at `0.7\textheight` with `keepaspectratio`, so figures
  never overflow vertically.

A missing image file degrades to a labelled placeholder box (the build still
succeeds), so a deck is never blocked by one un-extractable asset.

## Inline emphasis

`\alert{...}` (gold) is available inside any text the backend escapes — but the
layout-pass should prefer **semantic blocks** over inline alerts for talk clarity.

## Hard constraints the layout-pass must respect

1. **One primary figure per content frame** (an optional secondary supporting
   figure is allowed for `method`/overview beats; it stacks below).
2. **No overflow.** `overflowguard=on` will *fail the build* if a frame's body
   reaches the footer. Keep bullets short (≤ ~6 per frame, ≤ ~12 words each) and
   move overflow to a second frame. A big single sentence belongs on a
   `statementframe`, not a crowded `frame`.
3. **Title + closing exactly once.** First slide `titleframe`, last `thanksframe`.
4. Plan **frame count to the time budget**: a rule of thumb is ~1 content slide
   per minute for `balanced` depth; fewer for `overview`, more for `deep-dive`.

## Colors (override only if asked)

`simpleAccent` (blue), `simpleAlert` (gold), `simpleExample` (green),
`simpleDark` (ink), `simpleGray` (muted). All defaults clear WCAG AA on white.
The layout-pass should not invent colors; it selects semantics via block type.
