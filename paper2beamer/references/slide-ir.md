# Pass: Slide IR

Turn the approved narrative into a per-slide plan. This level is **ISA-aware**:
every choice must be something the active theme actually supports.

## Inputs

- the approved `slides/<slug>/narrative.md`
- the active ISA: the theme's resolved effective contract (composed by
  `scripts/isa_resolve.py` from `paper2beamer/isa/Simple.yaml`, or
  `isa/<Theme>.yaml` if the
  workspace selected another theme (see `isa-setup.md`)

## Output

`slides/<slug>/slides.md`, following the Slide IR schema in `ir-format.md`: a
`## Deck meta` block, then one `### S<NN> — title` section per slide.

## Rules

- Assign `S` ids in final deck order. Every slide carries a `beat-ref` to the
  `N..` beat it serves.
- Choose `block-semantics` ONLY from the blocks the ISA lists (for Simple:
  `claim`→`block`, `caveat`→`alertblock`, `example`→`exampleblock`, or `none`).
- Respect ISA **capacity**: do not plan a slide the ISA says will not fit (for
  Simple at `density=normal`, ~6–8 bullets, or a figure + 2–3 bullets, or two
  small blocks). Split dense beats across slides up front rather than relying on
  repair.
- Assign each figure to exactly one slide.
- Plan structural slides with the ISA's special frames: a title frame, automatic
  section dividers (via `\section`), and a closing/thanks frame. Mark these so
  emission knows they are unnumbered.
- Keep `content` at the bullet/structure level — describe what goes on the slide,
  not final LaTeX. LaTeX is the emission pass's job.

## Handoff

When `slides.md` is complete and every slide maps to a beat and respects the
ISA, go to `emission.md`.
