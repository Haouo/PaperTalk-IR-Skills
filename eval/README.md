# Evaluation harness

Measures the **quality of an end-to-end paper2beamer conversion** on a real
paper, beyond the unit tests in `paper2beamer/tests/`. It automates most of the
manual acceptance checks in [`docs/VERIFICATION.md`](../docs/VERIFICATION.md) and
adds an LLM-judged quality score.

It runs from a committed **golden IR** — the Docling extraction of the sample
paper (text + figures) — so **no PDF ever enters the repo** and Docling is not
needed at eval time. The sample is *Attention Is All You Need* (arXiv 1706.03762).

## What it checks

**Structural (deterministic, `grade_structural.py`)** — the seven acceptance
criteria. Five are decided from the build artifacts (compiles, page budget, no
overflow, provenance consistency, Docling-only figures); two are process
properties (local repair, single human gate) read from a run manifest, reported
`unverified` if the manifest is absent.

**Quality (LLM judge, `rubric.md`)** — faithfulness to the paper, narrative
coherence, slide clarity & density, and intent fit, each scored 1–5 with
slide-cited evidence.

No hard pass/fail threshold — the report shows the structural results and the
judge scores; you read them.

## Layout

```
eval/
  README.md            this file
  EVAL.md              the run driver the agent follows
  rubric.md            the LLM judge's scoring rubric
  grade_structural.py  deterministic grader → structural.json
  tests/               grader unit tests + a clean-run fixture
  fixtures/aiayn/      golden IR: intent.md, paper-content.md, figures/, REFRESH.md
  runs/                gitignored — one dir per run
  report.md            gitignored — latest run's report
```

## Run it

Ask the agent to "run the paper2beamer eval"; it follows [`EVAL.md`](EVAL.md):
stages a run from `fixtures/aiayn/`, drives the skill from the Narrative IR stage
(gate auto-approved once), grades, judges, and writes `report.md`.

Run the grader alone against any finished deck:

```bash
python3 eval/grade_structural.py --slides <run>/slides/<slug> \
  --manifest <run>/manifest.json --out structural.json
```

## Sample output

[`sample-output/aiayn/`](sample-output/aiayn/) holds a committed reference deck
produced by one eval run: the Narrative IR (`narrative.md`), the Slide IR
(`slides.md`), and the compiled deck (`main.pdf`, 17 pages). It scored 7/7
structural and 4.75/5 on the judge. Unlike per-run artifacts under `runs/`, this
one is tracked so the repo has a concrete example of what a good run produces.

## Tests (CI-friendly)

The grader is pure Python and unit-tested; the full eval run needs the model and
is local/pre-release only (same stance as `docs/VERIFICATION.md`).

```bash
uv run --with pytest pytest eval/tests -q
```

## Refreshing the fixture

The golden IR is regenerated, not hand-edited. See
[`fixtures/aiayn/REFRESH.md`](fixtures/aiayn/REFRESH.md) — it fetches the PDF to a
gitignored location locally, runs Docling, and copies the text + figures into the
fixture. The PDF is never committed.
