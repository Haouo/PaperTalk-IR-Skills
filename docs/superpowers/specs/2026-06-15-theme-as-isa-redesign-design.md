# Theme-as-ISA Redesign — Design Spec

**Date:** 2026-06-15
**Status:** Approved (design); pending implementation plan
**Motivation:** The paper now positions theme adaptability — satisfying a target
template's *contract* rather than imitating its style — as a headline payoff of
the theme-as-ISA mechanism. The current implementation does not back that claim:
the ISA is a prose Markdown manifest read only by the LLM, with no machine
verification, only one bundled theme, and no theme-swap tooling. This redesign
makes the contract real, verified, and demonstrable. Quality is prioritized over
implementation cost: this is a submission artifact.

---

## 1. Goals and non-goals

### Goals
- Turn the ISA from a *prompt that lists capabilities* into a *machine-checkable,
  build-grounded contract*, defensible against the reviewer critique "how is this
  more than constrained generation?"
- Make **theme-swap invariance (RQ4)** demonstrable with principled backing, not
  coincidence: portability defined by the extension subset a plan targets.
- Support **arbitrary themes** via a RISC-V-style modular extension model.
- Replace hand-guessed capacity ("~6–8 bullets") with **measured** per-theme
  numbers (RQ3).
- Keep the pipeline **agent-driven and zero-API-cost**: all verification is
  deterministic Python; all generation stays inside the Claude Code skill. No
  paid API key, no local-model dependency. This is both a budget constraint and a
  project-accessibility selling point.

### Non-goals (explicitly out of scope)
- **DSPy / prompt optimization.** DSPy is a program that makes its own LLM API
  calls; adopting it would require a paid key or a local-model backend, breaking
  the zero-API-cost skill model. The design is *optimization-ready* (validators
  double as metrics), so a future effort with a backend budget could wrap the
  stages in DSPy — documented as future work, not built here.
- Auto-extracting a complete ISA from a `.sty` with no human confirmation. The
  hardest parts (capacity, idioms) are not recoverable from source.
- Backward compatibility with the current prose ISA format. Pre-publication,
  single bundled theme; the format is replaced wholesale.

---

## 2. Core architectural insight: conformance rides the existing signal spine

The current repair loop is a clean spine:

```
build → latex_log.parse → Signals → repair_router.route → RepairDirective(level, target_id) → re-emit one unit
```

`Signals` carries `CompileError(tex_line)` and `Overflow(slide_number)`; the
router uses provenance to route each to the `tex` / `slide` / `narrative` level.

**Decision:** ISA conformance is a *third kind of signal* on the same spine, not a
parallel subsystem. A conformance violation natively carries frame attribution
(which frame used an illegal instruction), so it routes through the existing
provenance mechanism to localized repair — the localized-repair contribution is
inherited for free. The justification is conceptual, not cost: a compile error, an
overflow, and an illegal instruction are the same category — **violations of a
declared backend contract** — and should be one signal type routed by one
mechanism. The paper states this unification: *all backend non-conformance,
whether a compile error, an overflow, or an illegal instruction, is one kind of
signal, routed by one mechanism.*

The ISA splits into two objects with distinct roles:

| | Role | Form | Consumed by |
|---|---|---|---|
| **Contract** (Instructions / Options / Constraints / *structural* idioms) | hard, verifiable invariants | structured YAML | agent reads to generate **and** linter checks against (dual-use source of truth) |
| **Idioms** (semantic) | advisory style guidance | prose (YAML multiline field) | agent only; not machine-checked |

**Structural idioms are folded into the Contract.** Idioms mix two kinds; the
checkable ones become hard invariants, maximizing the verifiable surface:

| Subtype | Example | Deterministically checkable | Home |
|---|---|---|---|
| structural idiom | "every block must have a title", "deck needs a short title", "section name length" | yes (AST) | **Contract** (verified) |
| semantic idiom | "use color for meaning not decoration", "pick block type by meaning" | no (needs semantics) | prose (advisory) |

---

## 3. The RISC-V-style extension model

The ISA is modular, in three tiers, mirroring RISC-V (base + standard extensions
+ custom extensions, each independently versioned, composed via an "ISA string").

| RISC-V | theme-as-ISA | Content |
|---|---|---|
| Base ISA (mandatory) | **Base** — every theme inherits it | document shell, `frame`, `\section`, itemize/enumerate/description, figure+caption, `\title`/`\author`, thebibliography |
| Standard extensions (named, versioned, reusable) | capability bundles a theme may declare | `Zsem` (block/alertblock/exampleblock + semantic colors + `\alert`), `SpecialFrames` (titleframe/statementframe/thanksframe), `Theorems` (theorem/definition/proof), `Density` (density option + dense capacity), `OverflowGuard` (overflowguard option), `Columns` (columns/column) |
| Custom extensions (X-namespace) | a theme's bespoke commands | e.g. `\Xkeytakeaway` — linter supports it, but not assumed portable |
| ISA string | a theme's `provides:` list | `Simple = Base + Zsem + SpecialFrames + Density + OverflowGuard` |

This does **real technical work** (not decoration), which the paper must
demonstrate operationally:

1. **Theme-swap invariance becomes a theorem, not luck.** A plan whose Slide IR
   uses only instructions in extension subset *E* is guaranteed re-emittable to
   any theme providing ⊇ *E* with zero narrative edits — exactly as an RV64I
   program runs on any RV64I-superset core. RQ4 portability = the extension subset
   the plan targets.
2. **Graceful degradation (capability negotiation).** Swapping to a theme lacking
   an extension the deck used has a *defined* fallback: lower the instruction to
   its Base equivalent (`\statementframe` → plain centered `frame`) — the RISC-V
   "emulate the missing extension" analogue. Makes theme-swap robust even across
   capability-divergent themes.
3. **`OverflowGuard` as an extension** precisely defines Table 1's "hard backend"
   column: a theme with it yields hard per-slide errors; without it, detection
   falls back to `Overfull \vbox` warnings (already handled by `latex_log.py`).

**Discipline:** the analogy must do work. We implement portability-by-subset and
missing-extension degradation as real mechanisms, so the paper can state "the
extension model is not an analogy; it defines portability and degradation
operationally."

---

## 4. The Set: structured, typed, dual-use contract

One file per theme — `isa/<Theme>.yaml` — replaces the prose `Simple.md`. YAML so
agent, human, and parser all read it. Semantic idioms live as a multiline `prose`
field in the same file (single source of truth, no two-file drift). The whole Set
is validated by `isa.schema.json` (JSON Schema) — the contract is itself typed; a
malformed ISA fails loudly.

Extensions are first-class spec files: `isa/extensions/{Base,Zsem,SpecialFrames,
Theorems,Density,OverflowGuard,Columns}.yaml`, versioned. A theme file is thin:
`provides:` + `custom_instructions:` + measured `capacity:` (capacity is per-theme
even for inherited instructions, since rendering geometry differs by theme).

Effective allowlist for a theme = **⋃(instruction sets of declared extensions) ∪
custom_instructions ∪ shared base-primitive allowlist**. The base-primitive
allowlist (`isa/_base_latex.yaml`, theme-independent, versioned) covers safe
text/math/list/spacing primitives (`\item`, `\textbf`, `\emph`, `\\`, math) that
can't be enumerated per theme.

### Example extension spec (`isa/extensions/SpecialFrames.yaml`)
```yaml
extension: SpecialFrames
version: 1
instructions:
  - { cmd: titleframe,     args: 0,          numbered: false }
  - { cmd: statementframe, args: 1,          numbered: false }
  - { cmd: thanksframe,    optional_args: 2, numbered: false }
lowering:                          # Base equivalent when this extension is absent
  titleframe:     "frame with \\maketitle"
  statementframe: "plain frame, centered large text"
  thanksframe:    "plain frame, centered 'Thank you' + optional subtitle"
```

### Example theme file (`isa/Simple.yaml`)
```yaml
meta: { theme: Simple, sty: beamerthemeSimple.sty, isa_version: 1,
        engine: xelatex, aspectratio: "169" }
provides: [Base@1, Zsem@1, SpecialFrames@1, Density@1, OverflowGuard@1]
options:                           # validated: deck's \usetheme[...] ⊆ declared
  - { name: density,       values: [normal, dense], default: normal }
  - { name: overflowguard, values: [on, off], default: off, required_value: on }
  - { name: divider,       values: [on, off], default: on }
  - { name: eyebrow,       type: freetext }
capacity:                          # MEASURED by capacity_probe, not guessed
  normal: { bullets_per_frame: 7, figure_plus_bullets: 3, blocks_per_frame: 2 }
  dense:  { bullets_per_frame: 9, figure_plus_bullets: 4, blocks_per_frame: 3 }
  measured_at: { bullet_words: 8 }   # honesty: capacity is for representative content
custom_instructions: []
structural_idioms:
  - { rule: deck_requires_short_title, severity: error }
  - { rule: block_requires_title,      severity: error }
  - { rule: section_name_max_chars, value: 40, severity: warn }
prose: |
  Mark meaning with colour and the semantic block, not decoration.
  Accent = structure, gold = caveat, green = example. One idea per statementframe.
```

---

## 5. Components

### 5.1 `isa_resolve.py` — compose the effective ISA
Given a theme name, deterministically composes the full effective ISA (allowlist =
⋃ extensions ∪ custom ∪ base; options; measured capacity; structural idioms; prose)
into a single **resolved artifact**. That one artifact feeds both the agent (reads
to generate) and the linter (checks against) — dual-use preserved at the resolved
level. `slide-ir.md` / `emission.md` instruct the agent to read the resolved ISA.

### 5.2 `conformance.py` — pre-build static gate
Runs after assembly, **before** `build.sh`: catches illegal instructions and
missing block titles without wasting a compile, and separates contract violations
from compile/overflow in time (clean for the paper).

- **Parser:** `pylatexenc` (a real LaTeX walker), **not regex**. The parser's
  macro/environment arg-specs are **generated from the Set** (which declares arg
  counts) so custom commands parse correctly — the Set feeds both generation and
  verification.
- **Allowlist rule:** any used macro/environment not in (declared extensions ∪
  custom ∪ base-primitive allowlist) → Violation.
- **Checks and level mapping** (mirrors compile→tex / overflow→slide):

  | Check | Severity | Routed level | target |
  |---|---|---|---|
  | undeclared instruction/environment | error | `tex` (re-emit fragment) | slide_id |
  | block without title (folded structural idiom) | error | `slide` (plan should carry title; semantic) | slide_id |
  | `\usetheme` option out of range / `overflowguard≠on` / wrong aspectratio | error | `tex` (preamble, deck-global) | preamble |
  | section name too long | warn | reported, non-blocking | slide_id |
  | statically unresolvable (`\csname`, deep nesting) | warn | "needs manual check" | slide_id |

- **Honesty discipline:** the linter is conservative — uncertain constructs are
  `warn` ("needs manual check"), **never silently allowed**, so the
  machine-checkable claim is not undermined by silent gaps. Coverage limits are
  stated in the paper's Limitations.
- **Spine integration:** `latex_log.Signals` gains `violations: tuple[Violation,
  ...]`; `repair_router.route()` gains one branch. Orchestrator flow:
  ```
  emit → conformance(static) → errors? → route → re-emit one fragment → re-conformance
                             → clean   → build → latex_log → route(overflow/compile) → ...
  ```

### 5.3 `capacity_probe.py` — render-and-measure
Replaces guessed capacity with measured per-theme, per-block-type, per-density
numbers (feeds RQ3).

- **Method (deterministic, no LLM):** for each content shape (`bullets_per_frame`,
  `figure_plus_bullets`, `blocks_per_frame`) × density, emit test frames of
  monotonically increasing fill, compile with `overflowguard=on` (reusing
  `build.sh` + `latex_log.py`), binary/linear-search the largest non-overflowing
  N. Write N into the theme's `capacity:`.
- **Extension-aware:** only probe block types the theme's `provides:` actually
  includes.
- **Honesty:** capacity depends on bullet length; measured at a fixed
  representative length (recorded in `measured_at`). Capacity numbers are
  **planning hints** (used by Slide IR to avoid predictable overflow up front);
  the overflow guard is the **hard enforcement** for real content. RQ3's
  ISA-unaware ablation = strip `capacity:` from the Set.

### 5.4 Degradation: declarative lowering
Each standard extension spec declares `lowering:` — how each instruction maps to a
Base equivalent when the extension is absent (see §4 example). When the target
theme lacks an extension but the plan used its instruction, emission consults that
extension's `lowering:` and emits the Base equivalent. Degradation semantics are a
property of the extension spec (RISC-V "defined emulation"), not ad-hoc code.

### 5.5 Second theme — `Sidebar` (capability-divergent, for a hard RQ4)
A second bundled theme with a deliberately divergent extension profile and a
distinct visual identity, so one swap exercises **both** RQ4 cases:

- `Simple   = Base + Zsem + SpecialFrames + Density + OverflowGuard`
- `Sidebar  = Base + Zsem + Theorems + Columns + OverflowGuard`
  - **shared subset** `Base + Zsem + OverflowGuard` → plans targeting it are
    guaranteed portable (portability case);
  - `Sidebar` lacks `SpecialFrames` → decks using `\statementframe` must degrade
    (degradation case); it adds `Theorems`/`Columns` and has a different measured
    `capacity:`.

Exact aesthetics decided at implementation; the design commitment is "divergent
extension profile + divergent measured capacity." Requires
`beamerthemeSidebar.sty` + `isa/Sidebar.yaml`.

### 5.6 `theme_swap.py` — RQ4 invariance harness
- **Input:** an accepted deck (`narrative.md` + `slides.md`) + a target theme.
- **Process:** keep `narrative.md` **fixed**; swap the ISA to the target theme;
  re-run Slide IR + emission from the same narrative (missing instructions lowered
  per §5.4); build; conformance-check.
- **Metrics:**

  | Metric | Expected | Computation |
  |---|---|---|
  | narrative-edit rate | **0 (by construction)** | diff `narrative.md` before/after; the harness never touches it, so what it actually tests is whether a fixed narrative can be re-emitted to another theme and still compile/conform |
  | post-swap compile+conform rate | high | build succeeds ∧ no violations ∧ no overflow |
  | degradation events | reported (non-zero is honest) | count of instructions lowered to Base — portability is "portable with K degradations," not binary |

- **Clarification:** the Slide IR is *expected* to change on swap (different
  special frames/layout) — that is decoupling working (story fixed, realization
  re-binds), not an "edit." The metric tracks only narrative beats unchanged (0)
  plus compile/conform of the new realization. If re-emission ever required
  touching the narrative, the harness surfaces it as a design bug.
- **Determinism:** narrative-diff / build / conformance / degradation counting /
  metric computation are deterministic; only Slide IR re-gen is one agent pass per
  (deck × target theme), so RQ4 stays cheap, early, judge-free, baseline-free.

### 5.7 Generation/verification split
Agent *generates* (reads resolved ISA, writes tex); deterministic tools *verify*
(conformance linter, capacity probe, overflow guard, theme-swap harness). The
contract is expressed as the signature the agent targets; the guarantee comes from
the checker — never from agent self-report.

---

## 6. Component inventory and migration

**New artifacts**
- `isa.schema.json` — JSON Schema validating every theme Set + extension spec.
- `isa/_base_latex.yaml` — shared base-primitive allowlist (theme-independent).
- `isa/extensions/*.yaml` — Base + standard extensions (versioned, with `lowering`).
- `isa/Simple.yaml`, `isa/Sidebar.yaml` — thin theme files.
- `beamerthemeSidebar.sty` — second theme.
- `scripts/isa_resolve.py`, `scripts/conformance.py`, `scripts/capacity_probe.py`,
  `scripts/theme_swap.py`.

**Minimal extensions to existing scripts**
- `latex_log.py`: add `violations` to `Signals`.
- `repair_router.py`: add a routing branch for violations.
- `emit_beamer.py`: consult `lowering:` for missing-extension degradation.

**Migration**
- `isa/Simple.md` (prose) → extension specs + `isa/Simple.yaml` (capacity filled by
  the probe).
- `isa-setup.md` rewritten: a new theme = declare `provides:` + custom + run the
  capacity probe; confirm with the user.
- No backward-compat shim (pre-publication, single bundled theme).

**Tests**
- New: `conformance.py`, `isa_resolve.py`, capacity-probe logic, `theme_swap.py`.
- Extend: `latex_log` / `repair_router` for the violations path.

---

## 7. Paper synchronization (submission artifact — all must align)

| Manuscript element | Change |
|---|---|
| §3.5 (Slide IR & theme-as-ISA) | rewrite: Contract+Idioms split, extension model, conformance verification, measured capacity |
| New §3.x (extension model) | extension tiers + portability-by-subset statement + degradation — now a real contribution, needs prose |
| §3.1 (layered abstraction) | add "all backend non-conformance is one signal" unification |
| §3.7 + Fig 2 (repair routing) | add the conformance-violation route alongside compile-error / overflow |
| §4 + Table 2 (pipeline) | add conformance / capacity-probe / isa_resolve stages; mark ≥2 themes |
| §5 (eval) | RQ3 (measured-capacity ablation); RQ4 (portability-by-subset + degradation metric + second theme) |
| Fig 1 (overview) | theme-as-ISA band shows extension composition |
| Abstract / Table 1 / §1 contributions + delta | "machine-checkable / verified" + "extension-modular" wording; theme-as-ISA stays ONE mechanism contribution (richer description, not inflated) |
| repo docs | `ir-and-isa.md`, `isa-setup.md`, `slide-ir.md`, `emission.md`, `pipeline-overview.md`, `SKILL.md` |

**Portability statement for the paper:** *A deck whose Slide IR uses only
instructions in extension subset E is re-emittable to any theme providing ⊇ E with
zero narrative edits; for a theme providing ⊉ E, the missing instructions are
lowered to Base and the harness reports the degradation count.*

---

## 8. What would falsify the redesign's thesis
- If theme-swap forces narrative edits even for plans within the shared subset →
  the layers are not actually decoupled; reframe RQ4.
- If degradation fires so often that swapped decks are visually unacceptable →
  report it honestly; portability is weaker than claimed.
- If measured capacity makes no difference to overflow vs. the ISA-unaware
  ablation → soften the capacity-contract (RQ3) claim.
