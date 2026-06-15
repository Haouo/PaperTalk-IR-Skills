# Verification plan

How paper2beamer is verified, at three levels: automated unit tests, an automated
LaTeX smoke build, and manual end-to-end checks that exercise the LLM passes. The
acceptance criteria at the end map directly to the design.

## 1. Automated — Python unit tests (CI)

Run:

```bash
cd paper2beamer && uv run pytest -q
```

Expected: **17 passed, 1 deselected** (the `heavy` Docling test). Coverage of the
deterministic core:

| Module | Test file | What it proves |
|---|---|---|
| `latex_log.py` | `test_latex_log.py` | clean/error/overflow logs parse to the right signals; page count read; non-string input rejected |
| `repair_router.py` | `test_repair_router.py` | each signal routes to the right level; escalation after 2 attempts; unbounded budget skips page routing; clean+in-budget yields no directive |
| `emit_beamer.py` | `test_emit_beamer.py` | main.tex carries provenance comments and frame order; content numbers skip plain frames; line ranges recorded; missing fragment rejected |
| `frontend_docling.py` | `test_frontend_docling.py` | figure naming; missing-PDF and non-PDF inputs rejected (pure/defensive helpers; Docling itself is `heavy`) |

## 2. Automated — LaTeX golden-deck smoke build (CI)

Proves the deterministic deck path compiles with the real Simple theme:

```bash
python3 paper2beamer/scripts/emit_beamer.py \
  --manifest paper2beamer/tests/fixtures/golden-deck --out /tmp/golden
bash paper2beamer/scripts/build.sh /tmp/golden
python3 paper2beamer/scripts/latex_log.py /tmp/golden/main.log --assert-clean
```

Expected: `/tmp/golden/main.pdf` exists; `latex_log.py` reports `compile_ok: true`,
`page_count: 3` (title + 2 content), no errors, no overflows; exit code 0.

## 3. Manual / local — exercises the LLM passes (needs LaTeX + Docling)

These cannot run in CI because they require the model and the Docling models.
Run them locally before a release.

1. **Heavy Docling ingest.** Place a real paper at
   `paper2beamer/tests/fixtures/sample.pdf`, then:
   ```bash
   cd paper2beamer && uv sync --group ingest && uv run pytest -m heavy
   ```
   Expected: `paper-content.md` and `figures/` are produced.

2. **Full pipeline dry-run.** Convert one real paper with a bounded intent
   (e.g. "15-minute talk") through the skill. Expected: a compiling
   `slides/<slug>/main.pdf` whose content frame count is within the intent's page
   budget; the review gate paused once after the Narrative IR.

3. **Deliberate-overflow repair.** Force one slide to overflow (e.g. an intent
   that crams a dense beat). Expected: `latex_log.py` reports the overflow with a
   slide number; the skill edits only that slide in `slides.md`, re-emits only its
   fragment, and the deck recompiles. Confirm the narrative was not rewritten for
   a layout fault.

4. **Theme swap.** Add a second theme + its ISA via ISA setup, re-emit the same
   deck, and confirm it targets the new theme with the Narrative IR unchanged.

## 4. Quality — eval harness (local / pre-release)

The acceptance criteria below are also automated by the **eval harness**
(`eval/`), which runs paper2beamer end-to-end on a committed golden-IR fixture
(the Docling extraction of *Attention Is All You Need*; no PDF in the repo),
grades the structural criteria with `eval/grade_structural.py`, and adds an
LLM-judged quality score (faithfulness, narrative, clarity, intent fit). See
[`eval/README.md`](../eval/README.md). The grader is unit-tested in CI; a full
run needs the model and is local-only, like the manual checks above.

## Acceptance criteria (mapped to the design)

- [ ] The deck **compiles** to a PDF with XeLaTeX.
- [ ] When the intent is bounded, the **content frame count is within the page
      budget**; when unbounded, page count is not enforced.
- [ ] **No overflow** under `overflowguard=on`.
- [ ] `main.tex` carries `% slide:Sxx beat:Nyy` **provenance comments**, and
      `provenance.json` is present and consistent.
- [ ] Repair is **local**: between rebuilds, only the targeted fragment (tex),
      slide section (slide), or beat (narrative) changed — never a full regen.
- [ ] Figures originate **only from Docling** output.
- [ ] Exactly **one human gate**, after the Narrative IR.

## Pre-merge checklist

- [ ] `uv run pytest -q` green (17 passed, 1 deselected).
- [ ] Golden-deck smoke build green (locally or in CI).
- [ ] New deterministic code has a failing-first test and defensive input checks.
- [ ] LLM-read guides still match the theme API and `references/ir-format.md`.
- [ ] CI green on the PR.
