# IR format — structured Markdown + provenance

All three IR levels are **structured Markdown**, not JSON/YAML: they are produced
and consumed by an LLM, and the Narrative IR is read by a human at the review
gate. The structure is light but fixed — each unit is a Markdown section with a
small set of labelled fields, so it is both readable and machine-locatable.

The non-negotiable rule that makes repair-at-the-right-level work: **stable IDs
and cross-level provenance**. IDs are assigned once and never reused.

---

## Narrative IR — `slides/<slug>/narrative.md`

Target- and domain-independent. The only thing that shapes it is the user's
**intent**. One section per beat.

```markdown
# Narrative IR — <paper short title>

## Talk meta
- intent: <the user's intent, verbatim>
- time-budget: <e.g. 15 minutes | unbounded>
- page-budget: <e.g. 12–18 content slides | none (unbounded)>
- depth/tone: <e.g. technical conference talk; keep one proof sketch>

### N01 — Motivation
- goal: orient the audience and state why the problem matters
- key-message: <the one sentence the audience must retain>
- time-budget: 2 min
- supporting-figures: figure-001  (id from paper-content.md, or "none")

### N02 — ...
```

Fields per beat: `goal`, `key-message`, `time-budget`, `supporting-figures`
(real Docling figure ids only, or `none`).

---

## Slide IR — `slides/<slug>/slides.md`

ISA-aware. One section per slide. `S` ids are assigned in final deck order.

```markdown
# Slide IR — <paper short title>

## Deck meta
- title: <full title>
- short-title: <short title for the footer>
- author: <author>
- institute: <affiliation, or omit>
- date: <date>
- density: normal   (or dense)

### S00 — Title
- beat-ref: N00
- title: (title frame — special)
- content: \titleframe
- figure: none
- block-semantics: none

### S01 — Why this problem matters
- beat-ref: N01
- title: Why this problem matters
- content: 3 bullets framing the gap; lead with the running example
- figure: figure-001
- block-semantics: none

### S02 — The core limitation
- beat-ref: N01
- title: The core limitation
- content: one alertblock stating the caveat in today's approaches
- figure: none
- block-semantics: caveat
```

Fields per slide: `beat-ref` (the `N..` it serves — provenance UP), `title`,
`content` (bullet/structure prose, NOT final LaTeX), `figure` (id or `none`),
`block-semantics` (`claim` / `caveat` / `example` / `none` — only values the
active ISA supports).

---

## `.tex` provenance — `slides/<slug>/main.tex`

The emission pass never hand-writes `main.tex`. It writes a build manifest and
runs `emit_beamer.py`, which inserts a provenance comment above every frame:

```latex
% slide:S01 beat:N01
\begin{frame}{Why this problem matters}
  ...
\end{frame}
```

`emit_beamer.py` also writes `provenance.json`, recording each frame's
`slide_id`, `beat_id`, `content_number` (the footer number for content frames,
`null` for plain frames), and `tex_start`/`tex_end` line range. The repair
router uses this to map any build signal back to one IR unit:

- a compile error at tex line L → the frame whose `[tex_start, tex_end]` covers L
  → its `slide_id`;
- an overflow on "slide N" → the frame whose `content_number == N` → its
  `slide_id` (and, on escalation, its `beat_id`).

---

## Provenance invariants (do not break these)

1. IDs (`N01`, `S07`) are stable and never reused, even after a beat or slide is
   cut.
2. Every Slide IR section MUST carry a `beat-ref`.
3. The build manifest `order.txt` lists frames in final deck order, marking
   unnumbered special frames with the `plain` flag so content numbering matches
   the footer and overflow errors.
