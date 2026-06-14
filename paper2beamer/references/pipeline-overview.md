# Pipeline overview

Single pipeline, multi-stage generation. Three Markdown IR levels (Narrative →
Slide → `.tex`) plus a pluggable theme-as-ISA layer. One human review gate after
the Narrative IR; everything after runs automatically including the repair loop.

```
[Intent capture]   required every run; shapes the whole pipeline
      |
[Frontend: Docling]  PDF -> structure + figures   (deterministic, no LLM)
      |   paper-content.md, figures/
      v
[Narrative IR]   the talk's story (theme/domain-independent; shaped by intent)  -- LLM
      |   narrative.md
      v  ===== GATE: user reviews the story outline =====
      v
[Slide IR]       per-slide plan (ISA-aware)                                      -- LLM
      |   slides.md            ^ reads ISA
      v                        |
[Emission]       build manifest -> main.tex (only ISA-provided instructions)    -- LLM + emit_beamer.py
      |   main.tex, provenance.json
      v
[Compile/Verify] latexmk -xelatex -> main.pdf + signals   (deterministic)
      |   errors / overflow / page-count vs intent
      v
[Repair-at-the-right-level]  route each signal along provenance to the right
                             IR level; surgically fix only that unit; recompile.
```

## Layer rules

- **Narrative IR is target- and domain-independent.** It never reads the ISA.
  Only the Slide IR and emission passes consult the ISA.
- **The ISA is per theme.** Swapping a theme = swapping `isa/<Theme>.md` and the
  workspace `theme.tex`; the Narrative IR is reused unchanged.
- **Figures are deterministic.** They come only from Docling's output; never
  invent or hallucinate a figure.

## Artifact map (one folder per paper)

```
slides/<slug>/
  source.pdf            the input
  figures/              Docling-extracted images
  paper-content.md      Docling structured extraction (the only paper source downstream)
  narrative.md          Narrative IR
  slides.md             Slide IR
  build/                emission manifest: preamble.tex, order.txt, frames/<Sxx>.tex
  main.tex              assembled deck with provenance comments
  provenance.json       frame -> IR unit map (from emit_beamer.py)
  main.pdf              the output
  repair-report.md      only if the repair budget is exhausted with signals left
```

See `ir-format.md` for the exact schema of each IR level and the provenance
invariants.
