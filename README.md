# paper2beamer

> [繁體中文](README-zh-TW.md)

An LLVM-IR-inspired Claude Code skill that turns an academic paper (PDF) into a
Beamer slide deck. It is **intent-aware** — every run starts by capturing what the
talk is for and how long it should be — and **theme-aware** — the Beamer theme is
a pluggable backend you can swap.

Figures are extracted **deterministically with Docling** (never guessed by the
model), the deck is **compiled with XeLaTeX**, and build failures are **repaired
at the right level** instead of regenerating the whole deck from scratch.
Domain-agnostic: researchers in any field can use it.

## How it works

```
[Intent]  ->  [Docling ingest]  ->  Narrative IR  ==GATE==>  Slide IR  ->  .tex  ->  [xelatex]  ->  repair
                 (figures)          (the story)    (review)   (per slide)  (assemble)   (PDF)      (right level)
```

Three Markdown intermediate representations (Narrative → Slide → `.tex`) plus a
theme-as-ISA layer. One human review gate, right after the Narrative IR, where a
wrong story is cheapest to fix. Everything after the gate runs automatically,
including the repair loop. See [docs/design-philosophy.md](docs/design-philosophy.md)
and [docs/ir-and-isa.md](docs/ir-and-isa.md) for the full rationale.

## Requirements

- **XeLaTeX** and **latexmk** (TeX Live). CJK decks also need `xeCJK` + a CJK font.
- **uv** for the Python tooling (Docling is pulled on demand).
- Claude Code, with this repository as the workspace.

## Quick start

1. Make sure `xelatex`, `latexmk`, and `uv` are on your PATH.
2. In Claude Code, point the skill at a paper:

   > Turn `paper.pdf` into slides — a 15-minute conference talk.

3. The skill asks for your **intent**, ingests the PDF with Docling, drafts the
   **Narrative IR**, and pauses at the **review gate** for your approval.
4. After you approve, it plans the **Slide IR**, emits and assembles the deck,
   compiles it, and repairs any overflow or error at the right level.
5. The result is `slides/<paper-slug>/main.pdf`, with all intermediate artifacts
   beside it for inspection.

## Themes

The bundled **Simple** theme (`template/beamerthemeSimple.sty`) ships with a
pre-built ISA at `paper2beamer/isa/Simple.md`. To use another theme, drop its
`beamerthemeXxx.sty` in `template/`, point `template/theme.tex` at it, and run the
**ISA setup** once to generate `isa/<Theme>.md`. The Narrative IR is reused
unchanged across themes.

## Optional setups

- **ISA setup** — teach the skill a new theme (once per theme).
- **Domain setup** — generate `template/domain.md` so the skill calibrates
  background depth and terminology to your field (once per workspace). Skip it and
  the skill stays field-neutral.

## Documentation

- [TUTORIAL.md](TUTORIAL.md) — an end-to-end walkthrough.
- [docs/design-philosophy.md](docs/design-philosophy.md) — the LLVM analogy and rationale.
- [docs/ir-and-isa.md](docs/ir-and-isa.md) — IR levels, ISA, and provenance in depth.
- [docs/VERIFICATION.md](docs/VERIFICATION.md) — how the skill is verified.
- [CONTRIBUTING.md](CONTRIBUTING.md) — development workflow and standards.

## License

MIT — see [LICENSE.md](LICENSE.md).
