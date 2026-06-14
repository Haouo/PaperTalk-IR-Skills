# Pass: Narrative IR

Produce the talk's story. This level is **theme-independent and ISA-blind** — do
not think about slides, blocks, or LaTeX yet. The only forces shaping it are the
paper's content and the user's intent.

## Inputs

- `slides/<slug>/paper-content.md` and the figure ids in `slides/<slug>/figures/`
- the intent profiles from `intent.md` (page budget + depth/tone)
- `template/domain.md` if present (calibration)

## Output

`slides/<slug>/narrative.md`, following the Narrative IR schema in
`ir-format.md`. Write the `## Talk meta` block first (intent verbatim, derived
time-budget, derived page-budget, depth/tone), then one `### N<NN> — label`
section per beat.

## Rules

- Tell ONE coherent story. Each beat has a single `key-message` — the sentence
  the audience must retain.
- Allocate `time-budget` across beats so the total fits the intent's duration.
  For an unbounded intent, allocate by importance instead of a fixed total.
- Attach `supporting-figures` only from real Docling figure ids (or `none`).
- Calibrate depth to the domain and tone: skip what the audience already knows;
  teach what `template/domain.md` says must always be taught.
- Do NOT plan slide counts or layouts here. That is the Slide IR's job, after the
  gate.

## Handoff

When `narrative.md` is written, go to `review-gate.md`. Do not start the Slide IR
until the user approves the narrative.
