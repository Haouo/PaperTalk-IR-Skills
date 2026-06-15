# LLM judge rubric

The structural grader (`grade_structural.py`) covers everything decidable by
machine. This rubric covers the quality that only judgement can assess. The judge
is an LLM (the agent running `EVAL.md`) that reads the **golden IR**
(`paper-content.md`) and the **generated deck** (`slides.md` + `main.tex`), then
scores four dimensions 1–5.

## Hard rules for the judge

- **Evidence only.** Score from the actual fixture and the actual deck. Do NOT
  use outside knowledge of the paper to fill gaps — if a claim isn't in
  `paper-content.md`, the judge cannot treat it as faithful or as missing.
- **Cite a slide.** Every score must reference at least one concrete slide id
  (`Sxx`) as justification.
- **No verdict.** Report scores and evidence. Do not compute a pass/fail; the
  reader decides.

## Dimensions (1–5 each)

### Faithfulness to paper
Do the slides accurately reflect the paper's claims, method, and results, with no
hallucinated or distorted content?

- **1** — invents claims or contradicts the paper.
- **3** — mostly accurate; a few imprecise or overreaching statements.
- **5** — every assertion traces to `paper-content.md`; no distortion.

### Narrative coherence
Does the talk tell a logical story matched to the stated intent (audience +
length), with sound beat-to-beat flow?

- **1** — disjoint slides, no through-line.
- **3** — a story exists but has gaps or abrupt jumps.
- **5** — clear arc; each beat sets up the next; matches the intent's shape.

### Slide clarity & density
Are individual slides focused and readable, not overstuffed; is figure use
purposeful?

- **1** — walls of text or dumped figures.
- **3** — readable but some slides crowded or a figure underused.
- **5** — one idea per slide; figures earn their place.

### Intent fit
Does the deck match the captured intent (purpose, depth, length/budget) rather
than reading as a generic summary?

- **1** — generic; ignores the intent's depth/length.
- **3** — broadly on-target but tone or depth drifts.
- **5** — visibly shaped by the intent (e.g. a tight 15-min conference cut).

## Output shape (the judge writes this into report.md)

```
| dimension            | score | evidence                                  |
|----------------------|-------|-------------------------------------------|
| Faithfulness         | 4     | S05 states the attention eqn as in §3.2   |
| Narrative coherence  | 5     | S02→S06 build problem→method→result       |
| Slide clarity        | 4     | S07 a touch dense; rest focused           |
| Intent fit           | 4     | depth fits a 15-min conference talk        |
mean: 4.25 / 5
```
