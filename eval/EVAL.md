# EVAL.md — eval run driver (for the agent)

This is the script the agent follows when asked to "run the paper2beamer eval".
It produces one deck from a committed golden-IR fixture, grades it structurally,
judges its quality, and writes `eval/report.md`. No PDF and no Docling are
needed — the fixture already contains the Docling output.

## Inputs

- A fixture under `eval/fixtures/<name>/` containing:
  - `intent.md` — the fixed intent for this run (so the page budget is known).
  - `paper-content.md` — the Docling structured extraction (golden input).
  - `figures/` — the Docling-extracted figures.
- The default fixture is `aiayn` (Attention Is All You Need).

## Steps

1. **Stamp a run dir.** Create `eval/runs/<timestamp>/slides/<name>/` and copy the
   fixture's `paper-content.md`, `figures/`, and `intent.md` into it. Create
   `eval/runs/<timestamp>/manifest.json` as `{"gate_approvals": 0, "rebuilds": []}`.

2. **Run paper2beamer from the Narrative IR stage.** Use the fixture's `intent.md`
   verbatim as the captured intent (derive the page budget per
   `references/intent.md`). **Skip the PDF + Docling ingest** — the golden
   `paper-content.md` and `figures/` already stand in for that stage. Then follow
   the skill normally: Narrative IR → review gate → Slide IR → emission → compile
   → repair.

3. **Auto-approve the gate, once.** At the review gate, do not wait for a human;
   approve immediately and set `manifest.json` `gate_approvals = 1`. The gate must
   be reached exactly once — if you ever loop back through it, that's a bug to
   record, not to hide.

4. **Record every rebuild.** Each time the repair loop rebuilds, append to
   `manifest.json` `rebuilds`:
   `{"attempt": <n>, "level": "tex|slide|narrative", "unit": "<Sxx|Nyy>", "full_regen": false}`.
   `full_regen` must be `false` — the skill never regenerates the whole deck.

5. **Grade structurally.**
   ```bash
   python3 eval/grade_structural.py \
     --slides eval/runs/<timestamp>/slides/<name> \
     --manifest eval/runs/<timestamp>/manifest.json \
     --out eval/runs/<timestamp>/structural.json
   ```

6. **Judge quality.** Read `eval/rubric.md`. Read the fixture's
   `paper-content.md` (the only allowed source of truth) and the generated
   `slides.md` + `main.tex`. Score the four dimensions 1–5 with slide-cited
   evidence. Do not use outside knowledge of the paper.

7. **Write the report.** Render `eval/report.md` (see the shape below). Report
   results and scores; do not emit an overall pass/fail verdict.

## report.md shape

```
# paper2beamer eval — <name> — <timestamp>

## Structural (from structural.json)
- [x] compiles — page_count=N
- [x] no_overflow
- [x] page_budget — K content frames; budget 12–18
- [x] provenance
- [x] figures_from_docling
- [~] local_repair — <pass | unverified | fail>
- [~] one_gate — gate_approvals=1

## Judge scores (see rubric.md)
| dimension | score | evidence (Sxx) |
| ... |
mean: X.X / 5

## Notes
<anything notable: repairs taken, slides that drifted, regressions vs a prior run>
```

`eval/runs/` and `eval/report.md` are gitignored — they are regenerated, not
source.
