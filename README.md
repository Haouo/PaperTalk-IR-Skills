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

![paper2beamer overall architecture — an LLVM-style pipeline from paper PDF to Beamer deck](assets/overall-arch.png)

The pipeline reads left to right; the theme-as-ISA layer and the IR lowering chain
sit beneath it, and the evaluation harness sits off to the right. A compact text
version of the same flow:

```
[Intent]  ->  [Docling ingest]  ->  Narrative IR  ==GATE==>  Slide IR  ->  .tex  ->  [xelatex]  ->  repair
                 (figures)          (the story)    (review)   (per slide)  (assemble)   (PDF)      (right level)
```

Three Markdown intermediate representations (Narrative → Slide → `.tex`) plus a
theme-as-ISA layer. One human review gate, right after the Narrative IR, where a
wrong story is cheapest to fix. Everything after the gate runs automatically,
including the repair loop. See [docs/design-philosophy.md](docs/design-philosophy.md)
and [docs/ir-and-isa.md](docs/ir-and-isa.md) for the full rationale.

<details>
<summary>Detailed architecture — stages, artifacts, provenance, and repair routing</summary>

![paper2beamer detailed architecture — per-stage inputs and outputs, the deterministic scripts, the provenance ID chain (N-ids to S-ids to .tex line ranges), the repair loop, the ISA contract, and the evaluation harness](assets/detailed-arch.png)

</details>

## Requirements

- **XeLaTeX** and **latexmk** (TeX Live). CJK decks also need `xeCJK` + a CJK font.
- **uv** for the Python tooling (Docling is pulled on demand).
- Claude Code, with this repository as the workspace.

## Install (once)

Easiest: hand this prompt to Claude Code and let it set everything up.

> Install the paper2beamer skill: clone `git@github.com:Haouo/PaperTalk-IR-Skills.git`
> into `~/workspace/`, symlink its `paper2beamer/` directory to
> `~/.claude/skills/paper2beamer`, and check that `xelatex`, `latexmk`, and `uv`
> are installed.

By hand:

```bash
git clone git@github.com:Haouo/PaperTalk-IR-Skills.git ~/workspace/papertalk-ir-skills
ln -s ~/workspace/papertalk-ir-skills/paper2beamer ~/.claude/skills/paper2beamer
xelatex --version && latexmk --version && uv --version
```

Start a fresh Claude Code session and `paper2beamer` appears among the available
skills. See [TUTORIAL.md](TUTORIAL.md) for the full walkthrough.

## Quick start

1. In Claude Code, point the skill at a paper:

   > Turn `paper.pdf` into slides — a 15-minute conference talk.

2. The skill asks for your **intent**, ingests the PDF with Docling, drafts the
   **Narrative IR**, and pauses at the **review gate** for your approval.
3. After you approve, it plans the **Slide IR**, emits and assembles the deck,
   compiles it, and repairs any overflow or error at the right level.
4. The result is `slides/<paper-slug>/main.pdf`, with all intermediate artifacts
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
