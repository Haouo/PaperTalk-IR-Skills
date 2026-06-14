# Pass: ingest (Docling frontend)

Deterministic extraction of structure and figures from the paper PDF. **PDF is
the only supported input.** Figures come from Docling, never from LLM guessing.

## Run

```bash
uv run --project paper2beamer --group ingest \
  paper2beamer/scripts/frontend_docling.py <paper.pdf> --out slides/<slug>
```

(The `--group ingest` flag pulls Docling on demand; it is not installed for the
fast unit-test path.)

This writes:

- `slides/<slug>/paper-content.md` — the structured Markdown rendering.
- `slides/<slug>/figures/` — extracted images (`figure-001.png`, ...).

## Rules

- `paper-content.md` and `figures/` are the **only** source for every downstream
  pass. Never re-read the PDF; never invent a figure that is not in `figures/`.
- After ingest, note the figure ids that exist. The Narrative and Slide passes
  may reference only these ids.
- Read `template/domain.md` if it exists, to calibrate background depth and
  terminology (see `domain-setup.md`). If it is absent, stay field-neutral and
  assume a general graduate-level audience in the paper's own field.

## Failure handling (defensive)

- If the PDF path is wrong or the file is not a `.pdf`, the script exits non-zero
  with a clear message — surface it and stop.
- If Docling fails to convert the PDF, **stop and report**. Do NOT fall back to
  reading the PDF yourself or guessing figures; deterministic ingest is a hard
  requirement of this skill.
