# Contributing

Thanks for helping improve paper2beamer. This guide covers the repository layout,
how to run the tests, and the standards every change is held to.

## Repository layout

```
paper2beamer/            the skill package
  SKILL.md               orchestrator (the pipeline, the gate, the repair loop)
  references/            one guide per pass (LLM-read)
  isa/Simple.md          pre-built ISA for the bundled Simple theme
  scripts/               deterministic Python + shell (unit-tested)
  tests/                 pytest suite + fixtures (incl. the golden deck)
  pyproject.toml         uv project; docling is an optional 'ingest' group
template/                workspace theme scaffolding (.sty, manual, theme.tex, domain.md)
docs/                    design philosophy, IR/ISA deep-dive, verification plan, specs/plans
.github/workflows/ci.yml CI: unit tests + LaTeX golden-deck smoke build
```

## Running the tests

The deterministic tooling is unit-tested and must stay green.

```bash
cd paper2beamer
uv sync --group dev      # installs pytest only; NOT docling
uv run pytest -q
```

- Tests import modules as `from scripts.x import ...`; `pythonpath = ["."]` in
  `pyproject.toml` makes this work when run from `paper2beamer/`.
- The `heavy` marker tags tests that run the full Docling model pipeline. They are
  **skipped by default** (and in CI). Run them locally with a real sample PDF:

  ```bash
  uv sync --group ingest
  uv run pytest -m heavy
  ```

- The LaTeX golden-deck smoke build (assemble → `build.sh` → `latex_log.py
  --assert-clean`) needs a TeX Live install with `xelatex` and `latexmk`; CI runs
  it on every push.

## Coding standards

These apply to all deterministic code under `paper2beamer/scripts/`:

- **Defensive programming.** Validate inputs at the boundary (existence, type,
  value). Fail fast with a clear, actionable message. Never trust external data
  (PDF, LaTeX log, IR files); never swallow an error silently.
- **Full comments in clear, simple English.** Explain *why*, especially for the
  brittle parts (log regexes, line-range bookkeeping).
- **Immutability.** Prefer pure functions; return new values rather than mutating
  inputs. The signal records and the router are frozen dataclasses for this reason.
- **Small, focused files.** Target under 400 lines; 800 is a hard ceiling. One
  clear responsibility per module.
- **TDD for deterministic code.** Write the failing test first, watch it fail,
  implement the minimum to pass, then commit. Fixtures live in `tests/fixtures/`.

LLM-read files (`SKILL.md`, `references/*.md`, `isa/*.md`) are not unit-tested;
review them for accuracy against the actual theme API and the IR schema in
`references/ir-format.md`.

## Adding a new theme ISA

1. Place `beamerthemeXxx.sty` in `template/` and point `template/theme.tex` at it.
2. Follow `paper2beamer/references/isa-setup.md` to author `isa/<Theme>.md` in the
   same four-section structure as `paper2beamer/isa/Simple.md`.
3. If the theme has no `overflowguard`-style option, say so in the ISA's
   Constraints section — overflow detection then falls back to `Overfull \vbox`
   warnings, which the log parser already handles.

## Commit and review

- Conventional commit messages: `feat:`, `fix:`, `docs:`, `test:`, `chore:`,
  `refactor:`, `perf:`, `ci:`.
- Keep commits scoped; a change to deterministic code should come with its test.
- CI (unit tests + the LaTeX smoke build) must be green before review.

See [docs/VERIFICATION.md](docs/VERIFICATION.md) for the full verification plan.
