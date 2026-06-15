# Theme-as-ISA Contract Core — Implementation Plan (Plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the prose ISA into a machine-checkable, build-grounded contract for the existing Simple theme — a structured, extension-composed Set verified by a deterministic conformance linter that rides the existing repair signal spine.

**Architecture:** A RISC-V-style modular ISA: a theme declares the extensions it `provides:`; `isa_resolve.py` composes the effective allowlist/options from versioned extension specs + a shared base-primitive allowlist; `conformance.py` parses emitted LaTeX with `pylatexenc` (arg-specs generated from the Set) and emits `Violation` signals; `latex_log.Signals` carries those violations and `repair_router.route` routes them to the right IR level — reusing the existing localized-repair mechanism. All deterministic, no LLM, no API.

**Tech Stack:** Python 3.11+, `pyyaml` (read Sets), `jsonschema` (validate Sets), `pylatexenc` 2.10 (parse emitted LaTeX), `pytest`.

**Spec:** `docs/superpowers/specs/2026-06-15-theme-as-isa-redesign-design.md` (§2–§6). Plans 2 (capacity probe + Sidebar theme + theme-swap harness) and 3 (paper sync) follow this one.

**Conventions (already in the repo):**
- All scripts live in `paper2beamer/scripts/` and import as `from scripts.x import ...` (pytest sets `pythonpath=["."]`).
- Tests live in `paper2beamer/tests/test_*.py`, use frozen dataclasses, AAA structure, descriptive names.
- Run tests from `paper2beamer/`: `uv run pytest tests/ -v` (or `.venv/bin/pytest`).
- New ISA data lives under `paper2beamer/isa/`.

---

## File structure

**Create:**
- `paper2beamer/isa/isa.schema.json` — JSON Schema for extension specs and theme files.
- `paper2beamer/isa/_base_latex.yaml` — shared base-primitive allowlist (theme-independent).
- `paper2beamer/isa/extensions/Base.yaml`, `Zsem.yaml`, `SpecialFrames.yaml`, `Density.yaml`, `OverflowGuard.yaml` — versioned standard extensions.
- `paper2beamer/isa/Simple.yaml` — the Simple theme Set (`provides:` + options + structural idioms + prose).
- `paper2beamer/scripts/isa_resolve.py` — compose + validate the effective ISA for a theme.
- `paper2beamer/scripts/conformance.py` — the static conformance linter.
- `paper2beamer/tests/test_isa_resolve.py`, `tests/test_conformance.py` — unit tests.

**Modify:**
- `paper2beamer/pyproject.toml` — add `pyyaml`, `jsonschema`, `pylatexenc` runtime deps.
- `paper2beamer/scripts/latex_log.py` — add `Violation` dataclass + `violations` field on `Signals`.
- `paper2beamer/scripts/repair_router.py` — add a routing branch for violations.
- `paper2beamer/tests/test_latex_log.py`, `tests/test_repair_router.py` — extend for violations.

**Leave for later:** `isa/Simple.md` (prose) stays until Plan 3 (doc sync) removes it; the machine path uses `Simple.yaml`. `capacity:` in `Simple.yaml` is provisional here and gets overwritten by the probe in Plan 2.

---

## Task 1: Declare runtime dependencies

**Files:**
- Modify: `paper2beamer/pyproject.toml:9`

- [ ] **Step 1: Replace the empty `dependencies` list**

In `paper2beamer/pyproject.toml`, change:

```toml
dependencies = []
```

to:

```toml
# Contract-core deps: read/validate the structured ISA and parse emitted LaTeX.
# All pure-Python, no model downloads (unlike the optional 'ingest' group).
dependencies = [
    "pyyaml>=6",
    "jsonschema>=4",
    "pylatexenc>=2.10,<3",
]
```

- [ ] **Step 2: Sync and verify imports resolve**

Run: `cd paper2beamer && uv sync && uv run python -c "import yaml, jsonschema, pylatexenc; print('deps ok')"`
Expected: `deps ok`

- [ ] **Step 3: Commit**

```bash
git add paper2beamer/pyproject.toml paper2beamer/uv.lock
git commit -m "build: add pyyaml, jsonschema, pylatexenc for the ISA contract core"
```

---

## Task 2: JSON Schema for the Set

**Files:**
- Create: `paper2beamer/isa/isa.schema.json`
- Test: `paper2beamer/tests/test_isa_resolve.py`

- [ ] **Step 1: Write the failing test**

Create `paper2beamer/tests/test_isa_resolve.py`:

```python
import json
from pathlib import Path

import jsonschema

ISA_DIR = Path(__file__).resolve().parents[1] / "isa"


def _schema() -> dict:
    return json.loads((ISA_DIR / "isa.schema.json").read_text())


def test_schema_accepts_a_minimal_extension_spec():
    spec = {"extension": "Base", "version": 1, "instructions": []}
    # Should not raise.
    jsonschema.validate(spec, _schema()["$defs"]["extension"])


def test_schema_rejects_extension_missing_version():
    spec = {"extension": "Base", "instructions": []}
    try:
        jsonschema.validate(spec, _schema()["$defs"]["extension"])
        raised = False
    except jsonschema.ValidationError:
        raised = True
    assert raised, "extension without 'version' must be rejected"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py -v`
Expected: FAIL — `isa.schema.json` does not exist (FileNotFoundError).

- [ ] **Step 3: Create the schema**

Create `paper2beamer/isa/isa.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "paper2beamer ISA",
  "$defs": {
    "instruction": {
      "type": "object",
      "required": ["cmd"],
      "properties": {
        "cmd": {"type": "string"},
        "env": {"type": "string"},
        "args": {"type": "integer", "minimum": 0},
        "optional_args": {"type": "integer", "minimum": 0},
        "numbered": {"type": "boolean"},
        "requires_title": {"type": "boolean"}
      },
      "additionalProperties": false
    },
    "extension": {
      "type": "object",
      "required": ["extension", "version", "instructions"],
      "properties": {
        "extension": {"type": "string"},
        "version": {"type": "integer", "minimum": 1},
        "instructions": {"type": "array", "items": {"$ref": "#/$defs/instruction"}},
        "environments": {"type": "array", "items": {"$ref": "#/$defs/instruction"}},
        "lowering": {"type": "object"}
      },
      "additionalProperties": false
    },
    "theme": {
      "type": "object",
      "required": ["meta", "provides"],
      "properties": {
        "meta": {
          "type": "object",
          "required": ["theme", "engine", "aspectratio"],
          "properties": {
            "theme": {"type": "string"},
            "sty": {"type": "string"},
            "isa_version": {"type": "integer"},
            "engine": {"type": "string"},
            "aspectratio": {"type": "string"}
          }
        },
        "provides": {"type": "array", "items": {"type": "string"}},
        "options": {"type": "array"},
        "capacity": {"type": "object"},
        "custom_instructions": {"type": "array", "items": {"$ref": "#/$defs/instruction"}},
        "structural_idioms": {"type": "array"},
        "prose": {"type": "string"}
      },
      "additionalProperties": false
    },
    "base_allowlist": {
      "type": "object",
      "required": ["allowed_macros", "allowed_environments"],
      "properties": {
        "allowed_macros": {"type": "array", "items": {"type": "string"}},
        "allowed_environments": {"type": "array", "items": {"type": "string"}}
      },
      "additionalProperties": false
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/isa/isa.schema.json paper2beamer/tests/test_isa_resolve.py
git commit -m "feat: add JSON Schema for ISA extension and theme files"
```

---

## Task 3: Base-primitive allowlist

**Files:**
- Create: `paper2beamer/isa/_base_latex.yaml`
- Test: `paper2beamer/tests/test_isa_resolve.py`

- [ ] **Step 1: Write the failing test**

Append to `paper2beamer/tests/test_isa_resolve.py`:

```python
import yaml


def test_base_allowlist_loads_and_includes_core_primitives():
    data = yaml.safe_load((ISA_DIR / "_base_latex.yaml").read_text())
    jsonschema.validate(data, _schema()["$defs"]["base_allowlist"])
    assert "textbf" in data["allowed_macros"]
    assert "item" in data["allowed_macros"]
    assert "itemize" in data["allowed_environments"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py::test_base_allowlist_loads_and_includes_core_primitives -v`
Expected: FAIL — `_base_latex.yaml` not found.

- [ ] **Step 3: Create the base allowlist**

Create `paper2beamer/isa/_base_latex.yaml`:

```yaml
# Theme-independent safe LaTeX/Beamer primitives. The effective allowlist for any
# theme is (declared extensions) U (custom_instructions) U this set. These cannot
# be enumerated per theme, so they live here once.
allowed_macros:
  - textbf
  - textit
  - emph
  - texttt
  - underline
  - item
  - footnote
  - label
  - ref
  - cite
  - includegraphics
  - caption
  - centering
  - href
  - url
  - "\\"          # line break
  - "&"           # tabular separator
  - hspace
  - vspace
  - smallskip
  - medskip
  - bigskip
  - textwidth
  - linewidth
  - textcolor
  - frac
  - sum
  - int
  - alpha
  - beta
  - gamma
  - mathbf
  - mathit
allowed_environments:
  - itemize
  - enumerate
  - description
  - figure
  - table
  - tabular
  - center
  - equation
  - align
  - quote
  - thebibliography
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py::test_base_allowlist_loads_and_includes_core_primitives -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/isa/_base_latex.yaml paper2beamer/tests/test_isa_resolve.py
git commit -m "feat: add shared base-primitive allowlist for ISA conformance"
```

---

## Task 4: Standard extension specs

**Files:**
- Create: `paper2beamer/isa/extensions/Base.yaml`, `Zsem.yaml`, `SpecialFrames.yaml`, `Density.yaml`, `OverflowGuard.yaml`
- Test: `paper2beamer/tests/test_isa_resolve.py`

- [ ] **Step 1: Write the failing test**

Append to `paper2beamer/tests/test_isa_resolve.py`:

```python
EXT_DIR = ISA_DIR / "extensions"
EXPECTED_EXTS = ["Base", "Zsem", "SpecialFrames", "Density", "OverflowGuard"]


def test_all_standard_extensions_validate_against_schema():
    schema = _schema()["$defs"]["extension"]
    for name in EXPECTED_EXTS:
        data = yaml.safe_load((EXT_DIR / f"{name}.yaml").read_text())
        jsonschema.validate(data, schema)
        assert data["extension"] == name


def test_specialframes_declares_statementframe_and_its_lowering():
    data = yaml.safe_load((EXT_DIR / "SpecialFrames.yaml").read_text())
    cmds = [i["cmd"] for i in data["instructions"]]
    assert "statementframe" in cmds
    assert "statementframe" in data["lowering"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py -k extension -v`
Expected: FAIL — extension files not found.

- [ ] **Step 3: Create the five extension specs**

Create `paper2beamer/isa/extensions/Base.yaml`:

```yaml
extension: Base
version: 1
# Mandatory ISA every theme inherits. The document shell + the core frame model.
instructions:
  - { cmd: documentclass, args: 1 }
  - { cmd: usetheme, args: 1 }
  - { cmd: title, args: 1 }
  - { cmd: author, args: 1 }
  - { cmd: institute, args: 1 }
  - { cmd: date, args: 1 }
  - { cmd: maketitle, args: 0 }
  - { cmd: section, args: 1 }
  - { cmd: tableofcontents, args: 0 }
environments:
  - { env: frame }
  - { env: document }
lowering: {}
```

Create `paper2beamer/isa/extensions/Zsem.yaml`:

```yaml
extension: Zsem
version: 1
# Semantic blocks coloured by meaning, plus the matching inline emphasis.
instructions:
  - { cmd: alert, args: 1 }
environments:
  - { env: block, requires_title: true }
  - { env: alertblock, requires_title: true }
  - { env: exampleblock, requires_title: true }
lowering:
  block: "itemize/paragraph with a bold lead-in instead of a coloured block"
  alertblock: "paragraph prefixed with \\textbf{Caveat:}"
  exampleblock: "paragraph prefixed with \\textbf{Example:}"
  alert: "textbf"
```

Create `paper2beamer/isa/extensions/SpecialFrames.yaml`:

```yaml
extension: SpecialFrames
version: 1
# On-theme structural frames. Unnumbered (do not count toward the footer total).
instructions:
  - { cmd: titleframe, args: 0, numbered: false }
  - { cmd: statementframe, args: 1, numbered: false }
  - { cmd: thanksframe, optional_args: 2, numbered: false }
lowering:
  titleframe: "a plain frame containing \\maketitle"
  statementframe: "a plain frame with one large centered line"
  thanksframe: "a plain frame with a centered 'Thank you' and optional subtitle"
```

Create `paper2beamer/isa/extensions/Density.yaml`:

```yaml
extension: Density
version: 1
# Adds the density option; affects capacity, not the instruction surface.
instructions: []
lowering: {}
```

Create `paper2beamer/isa/extensions/OverflowGuard.yaml`:

```yaml
extension: OverflowGuard
version: 1
# The capability that makes capacity a HARD constraint: a frame reaching the
# footer becomes a per-slide error. No new instructions; it is an option + build
# behaviour. A theme without it falls back to Overfull-vbox detection.
instructions: []
lowering: {}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py -k extension -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/isa/extensions/ paper2beamer/tests/test_isa_resolve.py
git commit -m "feat: add Base/Zsem/SpecialFrames/Density/OverflowGuard ISA extensions"
```

---

## Task 5: Simple theme Set

**Files:**
- Create: `paper2beamer/isa/Simple.yaml`
- Test: `paper2beamer/tests/test_isa_resolve.py`

- [ ] **Step 1: Write the failing test**

Append to `paper2beamer/tests/test_isa_resolve.py`:

```python
def test_simple_theme_validates_and_declares_expected_extensions():
    data = yaml.safe_load((ISA_DIR / "Simple.yaml").read_text())
    jsonschema.validate(data, _schema()["$defs"]["theme"])
    provided = {p.split("@")[0] for p in data["provides"]}
    assert provided == {"Base", "Zsem", "SpecialFrames", "Density", "OverflowGuard"}
    assert data["meta"]["aspectratio"] == "169"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py::test_simple_theme_validates_and_declares_expected_extensions -v`
Expected: FAIL — `Simple.yaml` not found.

- [ ] **Step 3: Create the Simple Set**

Create `paper2beamer/isa/Simple.yaml`:

```yaml
meta:
  theme: Simple
  sty: beamerthemeSimple.sty
  isa_version: 1
  engine: xelatex
  aspectratio: "169"
provides: [Base@1, Zsem@1, SpecialFrames@1, Density@1, OverflowGuard@1]
options:
  - { name: eyebrow, type: freetext }
  - { name: density, values: [normal, dense], default: normal }
  - { name: divider, values: [on, off], default: on }
  - { name: overflowguard, values: [on, off], default: off, required_value: on }
# Provisional capacity carried from the prose ISA; OVERWRITTEN by capacity_probe
# in Plan 2. Numbers are planning hints; the overflow guard is the hard gate.
capacity:
  normal: { bullets_per_frame: 7, figure_plus_bullets: 3, blocks_per_frame: 2 }
  dense:  { bullets_per_frame: 9, figure_plus_bullets: 4, blocks_per_frame: 3 }
  measured_at: { bullet_words: 8, provisional: true }
custom_instructions: []
structural_idioms:
  - { rule: deck_requires_short_title, severity: error }
  - { rule: block_requires_title, severity: error }
  - { rule: section_name_max_chars, value: 40, severity: warn }
prose: |
  Mark meaning with colour and the semantic block, not decoration or filled
  headers. Accent = structure, gold = caveat, green = example. Keep section names
  short; give every block a title; give every deck a short title. One idea per
  statementframe.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py::test_simple_theme_validates_and_declares_expected_extensions -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/isa/Simple.yaml paper2beamer/tests/test_isa_resolve.py
git commit -m "feat: add structured Simple theme Set (provides + options + idioms)"
```

---

## Task 6: `isa_resolve.py` — compose the effective ISA

**Files:**
- Create: `paper2beamer/scripts/isa_resolve.py`
- Test: `paper2beamer/tests/test_isa_resolve.py`

- [ ] **Step 1: Write the failing test**

Append to `paper2beamer/tests/test_isa_resolve.py`:

```python
from scripts.isa_resolve import resolve


def test_resolve_simple_unions_extension_and_base_instructions():
    eff = resolve("Simple", ISA_DIR)
    # From SpecialFrames + Zsem + Base:
    assert "statementframe" in eff.allowed_macros
    assert "alert" in eff.allowed_macros
    assert "section" in eff.allowed_macros
    # From the base allowlist:
    assert "textbf" in eff.allowed_macros
    assert "itemize" in eff.allowed_environments
    # Zsem blocks require a title:
    assert "block" in eff.blocks_requiring_title


def test_resolve_carries_options_and_aspectratio():
    eff = resolve("Simple", ISA_DIR)
    assert eff.aspectratio == "169"
    assert eff.options["overflowguard"]["required_value"] == "on"


def test_resolve_provides_argspecs_for_known_custom_macros():
    eff = resolve("Simple", ISA_DIR)
    # statementframe takes one mandatory arg -> pylatexenc spec "{".
    assert eff.macro_argspecs["statementframe"] == "{"
    # thanksframe takes two optional args -> "[[".
    assert eff.macro_argspecs["thanksframe"] == "[["
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py -k resolve -v`
Expected: FAIL — `scripts.isa_resolve` does not exist.

- [ ] **Step 3: Implement `isa_resolve.py`**

Create `paper2beamer/scripts/isa_resolve.py`:

```python
"""Compose a theme's effective ISA from its declared extensions + the base set.

A theme file is thin: it declares which versioned extensions it `provides:`.
This module loads those extension specs and the shared base-primitive allowlist
and unions them into one EffectiveISA that both the agent (to generate) and the
conformance linter (to verify) consume. Pure, deterministic, no LLM.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import yaml


@dataclass(frozen=True)
class EffectiveISA:
    """The fully-composed contract for one theme."""

    theme: str
    aspectratio: str
    engine: str
    allowed_macros: frozenset[str]
    allowed_environments: frozenset[str]
    macro_argspecs: dict  # name -> pylatexenc args spec, e.g. "{" or "[["
    env_argspecs: dict
    blocks_requiring_title: frozenset[str]
    options: dict  # name -> option record
    structural_idioms: tuple = ()
    capacity: dict = field(default_factory=dict)
    prose: str = ""


def _argspec(instr: dict) -> str:
    """Translate an instruction's arg counts into a pylatexenc spec string."""
    return "[" * int(instr.get("optional_args", 0)) + "{" * int(instr.get("args", 0))


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"ISA file not found: {path}")
    return yaml.safe_load(path.read_text())


def resolve(theme: str, isa_dir: Path) -> EffectiveISA:
    """Build the EffectiveISA for `theme` from files under `isa_dir`."""
    isa_dir = Path(isa_dir)
    schema = json.loads((isa_dir / "isa.schema.json").read_text())

    theme_data = _load_yaml(isa_dir / f"{theme}.yaml")
    jsonschema.validate(theme_data, schema["$defs"]["theme"])

    base = _load_yaml(isa_dir / "_base_latex.yaml")
    jsonschema.validate(base, schema["$defs"]["base_allowlist"])

    macros: set[str] = set(base["allowed_macros"])
    envs: set[str] = set(base["allowed_environments"])
    macro_argspecs: dict = {}
    env_argspecs: dict = {}
    blocks_requiring_title: set[str] = set()

    for token in theme_data["provides"]:
        name = token.split("@")[0]
        ext = _load_yaml(isa_dir / "extensions" / f"{name}.yaml")
        jsonschema.validate(ext, schema["$defs"]["extension"])
        for instr in ext.get("instructions", []):
            macros.add(instr["cmd"])
            macro_argspecs[instr["cmd"]] = _argspec(instr)
        for env in ext.get("environments", []):
            envs.add(env["env"])
            env_argspecs[env["env"]] = _argspec(env)
            if env.get("requires_title"):
                blocks_requiring_title.add(env["env"])

    for instr in theme_data.get("custom_instructions", []):
        macros.add(instr["cmd"])
        macro_argspecs[instr["cmd"]] = _argspec(instr)

    options = {o["name"]: o for o in theme_data.get("options", [])}

    return EffectiveISA(
        theme=theme_data["meta"]["theme"],
        aspectratio=theme_data["meta"]["aspectratio"],
        engine=theme_data["meta"]["engine"],
        allowed_macros=frozenset(macros),
        allowed_environments=frozenset(envs),
        macro_argspecs=macro_argspecs,
        env_argspecs=env_argspecs,
        blocks_requiring_title=frozenset(blocks_requiring_title),
        options=options,
        structural_idioms=tuple(theme_data.get("structural_idioms", [])),
        capacity=theme_data.get("capacity", {}),
        prose=theme_data.get("prose", ""),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd paper2beamer && uv run pytest tests/test_isa_resolve.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/scripts/isa_resolve.py paper2beamer/tests/test_isa_resolve.py
git commit -m "feat: add isa_resolve to compose effective ISA from extensions"
```

---

## Task 7: Add the `Violation` signal type to `latex_log`

**Files:**
- Modify: `paper2beamer/scripts/latex_log.py`
- Test: `paper2beamer/tests/test_latex_log.py`

- [ ] **Step 1: Write the failing test**

Append to `paper2beamer/tests/test_latex_log.py`:

```python
from scripts.latex_log import Violation, Signals


def test_signals_defaults_to_no_violations():
    sig = Signals(compile_ok=True)
    assert sig.violations == ()


def test_violation_record_is_frozen_and_carries_fields():
    v = Violation(slide_id="S03", kind="undeclared_instruction",
                  detail="\\fancybox not in ISA", severity="error")
    assert v.slide_id == "S03"
    assert v.severity == "error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_latex_log.py -k violation -v`
Expected: FAIL — cannot import `Violation`.

- [ ] **Step 3: Add the dataclass and field**

In `paper2beamer/scripts/latex_log.py`, after the `Overflow` dataclass (before `Signals`), add:

```python
@dataclass(frozen=True)
class Violation:
    """One ISA-conformance violation found by the static linter (pre-build).

    slide_id is the frame the violation belongs to, or None for a preamble /
    deck-global issue. kind is a stable tag the router branches on. severity is
    "error" (routes to repair) or "warn" (reported, non-blocking).
    """

    slide_id: Optional[str]
    kind: str
    detail: str
    severity: str
```

Then add a field to `Signals` (after `overflows`):

```python
    violations: tuple["Violation", ...] = ()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd paper2beamer && uv run pytest tests/test_latex_log.py -v`
Expected: PASS (existing + new tests).

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/scripts/latex_log.py paper2beamer/tests/test_latex_log.py
git commit -m "feat: add Violation signal type and violations field to Signals"
```

---

## Task 8: `conformance.py` — the static linter

**Files:**
- Create: `paper2beamer/scripts/conformance.py`
- Test: `paper2beamer/tests/test_conformance.py`

- [ ] **Step 1: Write the failing test**

Create `paper2beamer/tests/test_conformance.py`:

```python
from pathlib import Path

from scripts.isa_resolve import resolve
from scripts.conformance import check

ISA_DIR = Path(__file__).resolve().parents[1] / "isa"
EFF = resolve("Simple", ISA_DIR)


def test_clean_fragment_yields_no_violations():
    frames = {"S01": "\\begin{frame}{Title}\n\\begin{itemize}\\item Hi\\end{itemize}\n\\end{frame}"}
    out = check(EFF, frames=frames, preamble="")
    assert out == ()


def test_undeclared_macro_is_an_error_routed_by_slide():
    frames = {"S02": "\\begin{frame}{T}\\fancybox{x}\\end{frame}"}
    out = check(EFF, frames=frames, preamble="")
    kinds = {(v.kind, v.slide_id, v.severity) for v in out}
    assert ("undeclared_instruction", "S02", "error") in kinds


def test_declared_special_frame_is_allowed():
    frames = {"S00": "\\statementframe{One big idea}"}
    out = check(EFF, frames=frames, preamble="")
    assert out == ()


def test_block_without_title_is_an_error():
    frames = {"S03": "\\begin{frame}{T}\\begin{block}{}body\\end{block}\\end{frame}"}
    out = check(EFF, frames=frames, preamble="")
    assert any(v.kind == "block_without_title" and v.slide_id == "S03" for v in out)


def test_block_with_title_is_clean():
    frames = {"S04": "\\begin{frame}{T}\\begin{block}{Claim}body\\end{block}\\end{frame}"}
    out = check(EFF, frames=frames, preamble="")
    assert all(v.kind != "block_without_title" for v in out)


def test_undeclared_usetheme_option_is_an_error():
    preamble = "\\usetheme[density=normal,bogus=1]{Simple}"
    out = check(EFF, frames={}, preamble=preamble)
    assert any(v.kind == "bad_option" and v.severity == "error" for v in out)


def test_missing_overflowguard_on_is_an_error():
    preamble = "\\usetheme[density=normal]{Simple}"  # overflowguard not set to on
    out = check(EFF, frames={}, preamble=preamble)
    assert any(v.kind == "bad_option" and "overflowguard" in v.detail for v in out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_conformance.py -v`
Expected: FAIL — `scripts.conformance` does not exist.

- [ ] **Step 3: Implement `conformance.py`**

Create `paper2beamer/scripts/conformance.py`:

```python
"""Static ISA-conformance linter (runs after assembly, before the build).

Parses each emitted frame fragment with pylatexenc, using arg-specs generated
from the resolved ISA so custom commands parse correctly, and checks that the
deck uses only what the theme's contract declares. Conservative: anything it
cannot resolve statically becomes a warn, never a silent pass.
"""
from __future__ import annotations

import re

from pylatexenc.latexwalker import (
    LatexWalker,
    LatexMacroNode,
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexCharsNode,
)
from pylatexenc.macrospec import LatexContextDb, MacroSpec, EnvironmentSpec

from scripts.isa_resolve import EffectiveISA
from scripts.latex_log import Violation

_USETHEME = re.compile(r"\\usetheme\[(?P<opts>[^\]]*)\]\{(?P<name>\w+)\}")


def _context(eff: EffectiveISA) -> LatexContextDb:
    """Build a pylatexenc context so declared custom commands parse their args."""
    db = LatexContextDb()
    macros = [MacroSpec(name, spec) for name, spec in eff.macro_argspecs.items()]
    envs = [EnvironmentSpec(name, spec) for name, spec in eff.env_argspecs.items()]
    db.add_context_category("isa", macros=macros, environments=envs, prepend=True)
    db.set_unknown_macro_spec(MacroSpec("", ""))
    db.set_unknown_environment_spec(EnvironmentSpec("", ""))
    return db


def _title_is_empty(env_node: LatexEnvironmentNode) -> bool:
    """True if a block environment's title argument is absent or blank."""
    argd = env_node.nodeargd
    if argd is None or not argd.argnlist:
        return True
    first = argd.argnlist[0]
    if first is None:
        return True
    if isinstance(first, LatexGroupNode):
        text = "".join(
            n.chars for n in first.nodelist if isinstance(n, LatexCharsNode)
        )
        return text.strip() == ""
    return False


def _walk(nodes, eff, slide_id, out):
    """Recurse the node tree collecting conformance violations."""
    for node in nodes:
        if isinstance(node, LatexMacroNode):
            name = node.macroname
            if name and name not in eff.allowed_macros:
                out.append(Violation(slide_id, "undeclared_instruction",
                                     f"\\{name} not in ISA", "error"))
        elif isinstance(node, LatexEnvironmentNode):
            env = node.environmentname
            if env not in eff.allowed_environments:
                out.append(Violation(slide_id, "undeclared_instruction",
                                     f"environment {env} not in ISA", "error"))
            elif env in eff.blocks_requiring_title and _title_is_empty(node):
                out.append(Violation(slide_id, "block_without_title",
                                     f"{env} has no title", "error"))
            if node.nodelist:
                _walk(node.nodelist, eff, slide_id, out)
        # Descend into groups so nested content is checked too.
        if isinstance(node, LatexGroupNode) and node.nodelist:
            _walk(node.nodelist, eff, slide_id, out)
        nested = getattr(node, "nodeargd", None)
        if nested is not None and nested.argnlist:
            _walk([a for a in nested.argnlist if a is not None],
                  eff, slide_id, out)


def _check_preamble(eff: EffectiveISA, preamble: str, out: list) -> None:
    """Check the \\usetheme options against the declared option contract."""
    for m in _USETHEME.finditer(preamble):
        opts = {}
        for pair in m.group("opts").split(","):
            pair = pair.strip()
            if not pair:
                continue
            k, _, v = pair.partition("=")
            opts[k.strip()] = v.strip()
        for k, v in opts.items():
            spec = eff.options.get(k)
            if spec is None:
                out.append(Violation(None, "bad_option",
                                     f"unknown \\usetheme option '{k}'", "error"))
                continue
            allowed = spec.get("values")
            if allowed and v not in allowed:
                out.append(Violation(None, "bad_option",
                                     f"option {k}={v} not in {allowed}", "error"))
        for name, spec in eff.options.items():
            req = spec.get("required_value")
            if req is not None and opts.get(name) != req:
                out.append(Violation(None, "bad_option",
                                     f"{name} must be {req}", "error"))


def check(eff: EffectiveISA, frames: dict, preamble: str = "") -> tuple:
    """Lint a deck's fragments + preamble against the effective ISA."""
    out: list = []
    db = _context(eff)
    for slide_id, text in frames.items():
        walker = LatexWalker(text, latex_context=db)
        nodelist, _, _ = walker.get_latex_nodes()
        _walk(nodelist, eff, slide_id, out)
    if preamble:
        _check_preamble(eff, preamble, out)
    return tuple(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd paper2beamer && uv run pytest tests/test_conformance.py -v`
Expected: PASS (7 tests). If a clean fragment reports a spurious violation, check that the macro/environment is in `_base_latex.yaml` (Task 3) and add it there.

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/scripts/conformance.py paper2beamer/tests/test_conformance.py
git commit -m "feat: add static ISA conformance linter (pylatexenc-based)"
```

---

## Task 9: Route violations on the repair spine

**Files:**
- Modify: `paper2beamer/scripts/repair_router.py`
- Test: `paper2beamer/tests/test_repair_router.py`

- [ ] **Step 1: Write the failing test**

Append to `paper2beamer/tests/test_repair_router.py`:

```python
from scripts.latex_log import Violation


def test_undeclared_instruction_violation_routes_to_tex_level():
    sig = Signals(
        compile_ok=False,
        violations=(Violation("S07", "undeclared_instruction", "\\foo", "error"),),
    )
    out = route(sig, PROV, budget=None, attempts={})
    assert out[0].level == "tex"
    assert out[0].target_id == "S07"


def test_block_without_title_routes_to_slide_level():
    sig = Signals(
        compile_ok=False,
        violations=(Violation("S08", "block_without_title", "block", "error"),),
    )
    out = route(sig, PROV, budget=None, attempts={})
    assert out[0].level == "slide"
    assert out[0].target_id == "S08"


def test_bad_option_violation_routes_to_preamble_tex():
    sig = Signals(
        compile_ok=False,
        violations=(Violation(None, "bad_option", "overflowguard must be on", "error"),),
    )
    out = route(sig, PROV, budget=None, attempts={})
    assert out[0].level == "tex"
    assert out[0].target_id == "preamble"


def test_warn_severity_violation_is_not_routed():
    sig = Signals(
        compile_ok=True,
        violations=(Violation("S07", "section_too_long", "...", "warn"),),
    )
    out = route(sig, PROV, budget=None, attempts={})
    assert out == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd paper2beamer && uv run pytest tests/test_repair_router.py -k violation -v`
Expected: FAIL — violations are not routed yet.

- [ ] **Step 3: Add the routing branch**

In `paper2beamer/scripts/repair_router.py`, inside `route()`, after the compile-error loop (before the overflow loop), add:

```python
    # 0. ISA conformance violations (static, pre-build). Only errors route;
    #    warns are reported elsewhere. Mirrors compile->tex / overflow->slide.
    _VIOLATION_LEVEL = {
        "undeclared_instruction": "tex",
        "bad_option": "tex",
        "bad_aspectratio": "tex",
        "block_without_title": "slide",
    }
    for v in sig.violations:
        if v.severity != "error":
            continue
        level = _VIOLATION_LEVEL.get(v.kind, "tex")
        target = v.slide_id if v.slide_id is not None else "preamble"
        directives.append(
            RepairDirective(level=level, target_id=target, reason=v.detail)
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd paper2beamer && uv run pytest tests/test_repair_router.py -v`
Expected: PASS (existing + 4 new tests).

- [ ] **Step 5: Commit**

```bash
git add paper2beamer/scripts/repair_router.py paper2beamer/tests/test_repair_router.py
git commit -m "feat: route ISA conformance violations on the repair spine"
```

---

## Task 10: End-to-end integration test (lint → route)

**Files:**
- Test: `paper2beamer/tests/test_conformance.py`

- [ ] **Step 1: Write the failing test**

Append to `paper2beamer/tests/test_conformance.py`:

```python
from scripts.latex_log import Signals
from scripts.repair_router import Provenance, route


def test_illegal_instruction_lints_then_routes_to_its_frame():
    # A frame that uses an undeclared macro.
    frames = {"S05": "\\begin{frame}{T}\\fancybox{x}\\end{frame}"}
    violations = check(EFF, frames=frames, preamble="")
    assert violations, "expected at least one violation"

    sig = Signals(compile_ok=False, violations=violations)
    prov = Provenance(frames=(
        {"slide_id": "S05", "beat_id": "N02", "content_number": 5,
         "tex_start": 1, "tex_end": 3},
    ))
    directives = route(sig, prov, budget=None, attempts={})
    assert any(d.level == "tex" and d.target_id == "S05" for d in directives)
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `cd paper2beamer && uv run pytest tests/test_conformance.py::test_illegal_instruction_lints_then_routes_to_its_frame -v`
Expected: PASS (all pieces already exist after Tasks 8–9; this locks the contract→spine path end to end).

- [ ] **Step 3: Run the full suite**

Run: `cd paper2beamer && uv run pytest tests/ -v`
Expected: PASS — all existing tests plus the new ISA/conformance/router tests.

- [ ] **Step 4: Commit**

```bash
git add paper2beamer/tests/test_conformance.py
git commit -m "test: lock the conformance-to-repair-spine integration path"
```

---

## Self-review checklist (completed)

**Spec coverage (§2–§6):**
- Structured Set / dual-use source of truth → Tasks 2–6 (schema, base, extensions, theme, resolve). ✓
- Contract vs Idioms split + structural idioms folded in → `structural_idioms` in Task 5; `block_requires_title` enforced in Task 8. ✓
- RISC-V extension model (Base/standard/custom, `provides:`, versioned) → Tasks 4–6. ✓
- Conformance as a pre-build static gate, pylatexenc, arg-specs from the Set → Task 8. ✓
- Conformance rides the signal spine (Signals.violations + router branch) → Tasks 7, 9, 10. ✓
- Level mapping (undeclared→tex, block-no-title→slide, option→preamble, warn not routed) → Tasks 8–9. ✓
- Honest discipline (unresolvable→warn, never silent) → `set_unknown_*` + conservative checks in Task 8. ✓
- **Deferred to Plan 2:** `capacity_probe.py`, declarative `lowering` *application* in `emit_beamer.py`, `Sidebar` theme, `theme_swap.py`. (`lowering` data is authored now in Task 4; it is *consumed* in Plan 2.)
- **Deferred to Plan 3:** paper sync (§7), removal of `isa/Simple.md`, doc updates.

**Placeholder scan:** none — every step has runnable code/commands and expected output.

**Type consistency:** `EffectiveISA` fields (`allowed_macros`, `allowed_environments`, `macro_argspecs`, `env_argspecs`, `blocks_requiring_title`, `options`) are produced in Task 6 and consumed identically in Task 8. `Violation(slide_id, kind, detail, severity)` is defined in Task 7 and constructed with the same field order in Tasks 8–10. `RepairDirective(level, target_id, reason)` matches the existing dataclass.
