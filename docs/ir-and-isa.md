# The IR levels, the ISA, and provenance

This document specifies the three intermediate representations, the theme-as-ISA
layer, and the provenance mechanism that enables repair at the right level. It is
the reference companion to [design-philosophy.md](design-philosophy.md); the
operational schemas the model follows live in
`paper2beamer/references/ir-format.md`.

## The three IR levels

### Narrative IR

The Narrative IR records the talk as a sequence of *beats*. It is independent of
both the target theme and the rendering mechanism; the only inputs that shape it
are the paper's content, the captured intent, and (optionally) the workspace
domain profile. Each beat carries a goal, a single key-message, an allocated time
budget, and the identifiers of any figures that support it. A meta block at the
head records the intent verbatim alongside its derived page budget and depth/tone
profile, so the authorial assumptions are explicit and auditable.

Because it is theme-independent, the Narrative IR is the unit of reuse across
themes: re-targeting a deck to a different theme does not touch it.

### Slide IR

The Slide IR records the deck as a sequence of slides, each linked by a
`beat-ref` to the narrative beat it serves. A slide carries its title, its
content at the bullet/structure level (not final LaTeX), an optional figure, and
a block semantic drawn only from those the active theme provides. This level is
ISA-aware: it may not plan a slide the theme cannot express or accommodate.
Slide identifiers are assigned in final deck order.

### The `.tex` deck

The lowest level is the Beamer source itself. It is never authored as a monolith.
The emission step writes a build manifest — a preamble, an ordered frame list,
and one LaTeX fragment per frame — and a deterministic assembler stitches these
into `main.tex`. The assembler, not the model, is responsible for the structural
metadata that the repair policy depends on.

## The ISA

A theme's ISA is its capability contract, expressed as a machine-readable Set
(`isa/<Theme>.yaml`) that both the model (to generate) and a deterministic
conformance linter (to verify) consume — a single source of truth, not a prompt.
It has two parts: a **verifiable contract** (the instructions the theme provides,
the `\usetheme` options it accepts, its measured capacity, and its
structurally-checkable idioms such as "every block carries a title") that the
linter enforces, and a few **advisory idioms** (use colour semantically, keep
section names short) that stay prose because they need judgement, not a syntactic
test.

### A modular, extensible instruction set (RISC-V style)

An ISA is composed, not monolithic. A theme declares the **extensions** it
`provides:` — a mandatory **Base** (document shell, `frame`, `\section`, lists,
figures, `\title`) plus standard, versioned extensions and any theme-specific
custom instructions. Standard extensions in the repo:

- `Zsem` — semantic blocks (`block`/`alertblock`/`exampleblock`) + `\alert`;
- `SpecialFrames` — `\titleframe`/`\statementframe`/`\thanksframe`;
- `Theorems` — `theorem`/`definition`/`proof`;
- `Columns` — `columns`/`column`;
- `OverflowGuard` — the hard per-slide overflow guard (see below).

`scripts/isa_resolve.py` composes a theme's **effective ISA** = the union of its
declared extensions' instructions ∪ its custom instructions ∪ a shared
base-primitive allowlist (`isa/_base_latex.yaml`). The Set and every extension are
validated against `isa/isa.schema.json`.

Two properties follow. **Portability:** a deck whose Slide IR uses only
instructions in an extension subset *E* re-targets to any theme providing ⊇ *E*
with no narrative edits. **Graceful degradation:** when a target theme lacks an
extension a deck used, each missing instruction is *lowered* to its declared Base
equivalent (each extension's `lowering:` block), so a swap to a less capable theme
still builds, at a reported degradation cost rather than a failure.

### Capacity is measured; the overflow guard is one extension

Per-theme, per-density capacity is **measured** by `scripts/capacity_probe.py`
(render frames of increasing fill, find where they overflow), not guessed. The
hard `overflowguard` is a paper2beamer-specific capability modelled as the optional
`OverflowGuard` extension — **not** a standard Beamer feature. A theme that
provides it turns overflow into a per-slide build error; a theme without it (e.g.
the stock third-party Madrid theme) is held only to LaTeX's softer `Overfull
\vbox` warning, and the probe measures capacity via that fallback.

### Conformance

`scripts/conformance.py` parses each emitted fragment with `pylatexenc` (arg-specs
generated from the Set) and emits a `Violation` for any undeclared instruction or
option, any block missing its required title, etc. It runs **before** the build,
so a contract breach is caught without spending a compile. Violations ride the
same signal spine as compile errors and overflows (next section).

The ISA is the contract between the Slide IR and emission; the Narrative IR never
consults it. Authoring an ISA for a new theme means declaring the extensions it
provides (plus any custom instructions) and running the capacity probe — the
analogue of standing up a compiler backend. The bundled Simple theme and the stock
Madrid theme each ship with a resolved ISA.

## Provenance: the analogue of debug information

A compiler attaches source locations to its IR so that a diagnostic at the back
end can be reported against the responsible line of source. paper2beamer attaches
the same kind of metadata across its IR levels, and this is precisely what makes
local repair possible.

- **Stable identifiers.** Beats are `N01`, `N02`, …; slides are `S00`, `S01`, ….
  Identifiers are assigned once and never reused, even after a beat or slide is
  cut, so a reference is never silently rebound.
- **Cross-level links.** Each Slide IR section names the beat it serves
  (`beat-ref`). The assembler writes a provenance comment above each frame,
  `% slide:Sxx beat:Nyy`, and emits `provenance.json`, recording for every frame
  its slide and beat identifiers, its footer content number (or null for
  unnumbered special frames), and its line range in `main.tex`.

With this metadata, every build signal resolves to exactly one unit:

- a compile error at a line is located within the frame whose recorded line range
  contains it, yielding a slide identifier;
- an overflow reported against a content-frame number is matched to the frame
  with that number, yielding a slide identifier and, on escalation, the beat it
  serves.

## The routing table and stop-loss

The repair router is a pure function of the build signals, the provenance map,
the intent's page budget, and the per-target attempt counts. It encodes the
following policy:

| Signal | Resolved level | Action |
|---|---|---|
| Conformance violation (pre-build) | `tex` / `slide` / preamble | Re-emit the implicated fragment (undeclared instruction → `tex`; missing block title → `slide`; bad option → preamble). |
| Compile error | `tex` | Re-emit only the implicated frame's fragment. |
| Frame overflow | `slide` | Revise the implicated slide; re-emit its fragment. |
| Page count outside budget | `narrative` | Cut/merge (over) or expand (under) beats; re-plan affected slides. |

Two safeguards bound the loop. First, **escalation**: after a fixed number of
unsuccessful trims of the same slide, an overflow is re-routed upward to the
narrative level, on the principle that a slide which cannot be made to fit is
evidence the beat is overloaded. Second, **stop-loss**: a deck has a fixed total
rebuild budget; when it is exhausted with signals still outstanding, the pipeline
stops, emits a best-effort PDF, and writes a report enumerating what remains
unresolved. The page-count rule is disabled entirely when the intent leaves the
talk length unbounded.

This policy is implemented in `paper2beamer/scripts/repair_router.py` and is unit
tested; the operational instructions the model follows are in
`paper2beamer/references/repair.md`.
