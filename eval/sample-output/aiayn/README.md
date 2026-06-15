# AIAYN sample deck (reference output)

A committed example of what one paper2beamer eval run produces, for the intent
"15-minute conference talk, results-first, ≤1 attention diagram + ≤1 equation".

- `narrative.md` — Narrative IR (the talk's story; theme-independent)
- `slides.md` — Slide IR (per-slide plan; Simple-theme-aware)
- `main.pdf` — the compiled 17-page deck (title + 13 content + 2 dividers + thanks)

Source paper: *Attention Is All You Need* (arXiv 1706.03762). The paper grants
reuse of its figures for scholarly works; the deck embeds Figures 1–2 on that
basis. The paper PDF itself is never committed.

## How it was produced

Following [`../../EVAL.md`](../../EVAL.md): staged from the golden IR in
[`../../fixtures/aiayn/`](../../fixtures/aiayn/), run through paper2beamer from
the Narrative IR stage (gate auto-approved once), emitted with `emit_beamer.py`,
compiled with `build.sh`. It compiled clean on the first pass — no repairs.

Result: structural 7/7, judge mean 4.75/5. To regenerate, re-run the harness;
the per-run working copy lands under the gitignored `eval/runs/`.
