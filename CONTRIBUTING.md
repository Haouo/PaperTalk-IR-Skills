# Contributing to papertalk-ir-skills

Thanks for helping improve `paper2beamer`. This guide covers how to set up, the
conventions that keep the pipeline coherent, and the one rule that matters most:
**the IR contract is sacred — change it in all four places at once.**

## Mental model

`paper2beamer` is a compiler. Keep stages honest about their role:

- **Scripts are deterministic** (`frontend_docling.py`, `emit_beamer.py`,
  `build.sh`). They make *no* semantic decisions. Same input → same output.
- **Passes are semantic** (driven by the model via `SKILL.md`). They never touch
  LaTeX syntax; they only read/write the IR.
- **`ir_common.py` is the contract** between them, and the single source of
  truth for what a valid IR is.

If you find yourself wanting an LLM pass to emit LaTeX, or the backend to "decide
what's important", stop — that's a layering violation.

## Setup

```bash
# uv provisions everything without touching system Python.
uv run --with pytest python -m pytest paper2beamer/tests/ -c paper2beamer/tests/pytest.ini -q
```

Requirements for the full suite: `uv`, and `xelatex` for the integration tests
(they skip if it is absent). The opt-in `e2e` tests additionally need `docling`.

## Running tests

```bash
cd paper2beamer

# Fast, hermetic suite (run this before every commit):
uv run --with pytest python -m pytest tests/ -c tests/pytest.ini -q

# Live end-to-end (downloads Docling models; slow):
uv run --with pytest --with docling python -m pytest tests/ -c tests/pytest.ini -m e2e -q
```

See [`paper2beamer/tests/VERIFICATION.md`](./paper2beamer/tests/VERIFICATION.md)
for what each layer covers.

## The IR-change protocol (read before editing the schema)

The IR shape is described in **four** places that must stay in lock-step:

1. `paper2beamer/scripts/ir_common.py` — the **enforced** validator + constants.
2. `paper2beamer/references/ir_schema.json` — the JSON-Schema mirror.
3. `paper2beamer/references/ir-schema.md` — the human reference.
4. `paper2beamer/references/pass-contracts.md` — the per-pass checklist.

When you add/rename/remove a field or an enum value:

- Update all four. `tests/test_schema_consistency.py` will fail if (1) and (2)
  disagree on any enum — that's your safety net, not a substitute for updating
  the docs.
- If the change affects rendering, regenerate and re-inspect the golden fixture
  `tests/fixtures/deck.expected.tex`, and confirm it still compiles.
- Bump `SCHEMA_VERSION` in `ir_common.py` (and the `const` in the JSON Schema)
  only for **breaking** changes.

## Code conventions

- **Python:** standard library only in `ir_common.py` and `emit_beamer.py` (they
  must run under a bare interpreter). Docling-specific code stays in
  `frontend_docling.py`. Type hints throughout; functions small and focused.
- **Defensive by default:** validate at boundaries, fail fast with a precise
  message (include the IR path), never let one bad figure abort a whole run, and
  write files atomically.
- **Comments explain *why*,** not *what*. Match the density of the existing code.
- **No mutation of caller data** where a fresh value is cheap; prefer returning
  new structures.
- **Escaping:** all paper-derived text rendered by the backend must go through
  `escape_latex`. Never interpolate raw text into the `.tex`.

## Adding a test

Mirror the existing layout in `paper2beamer/tests/`:

- pure logic → unit test (no subprocess, no LaTeX);
- backend output → extend the golden assertions or add a focused behaviour test;
- anything touching `xelatex` → guard with the `needs_xelatex` skip;
- anything touching `docling` → mark `@pytest.mark.e2e`.

## Commits & PRs

- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`,
  `chore:`, `perf:`.
- Keep PRs focused. Describe what changed and how you verified it; paste the
  `pytest` summary.
- Green fast suite is required. If you changed the IR, say which of the four
  sources you updated.

## Scope / philosophy

- **YAGNI:** the project deliberately supports **one** theme (Simple) deeply.
  Theme pluggability is a future seam (`simple-theme-isa.md`), not a current
  feature — don't add it speculatively.
- **No fabrication:** features that would let the deck state things not in the
  paper are out of scope.
