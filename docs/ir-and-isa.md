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

A theme's ISA is its capability manifest, expressed in four sections:

1. **Instructions** — the special frames, semantic block environments, inline
   emphasis commands, semantic colours, and the document shell the theme
   provides, together with the standard Beamer constructs known to work with it.
2. **Options** — the values the theme's `\usetheme[...]` accepts and the
   sanctioned way to override its colours.
3. **Constraints** — aspect ratio, engine and font requirements, an approximate
   per-frame capacity used for layout budgeting, frame-numbering behaviour, and
   the *forbidden zones*: packages the theme deliberately leaves to the deck.
4. **Idioms** — the theme's style contract, so emitted slides read as intended
   rather than merely valid.

The ISA is the contract between the Slide IR and emission. The Narrative IR never
consults it. One ISA is authored per theme — the analogue of standing up a
compiler backend — and the bundled Simple theme ships with its ISA pre-built.

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
