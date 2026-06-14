# Design philosophy

paper2beamer treats slide generation as a *compilation* problem. A research paper
is the source program; a Beamer deck is the target artifact; the user's intent is
a set of compiler flags. Rather than asking a language model to map source to
target in a single leap, the skill borrows the architecture that has made
production compilers tractable for forty years — the multi-stage pipeline with
multiple intermediate representations, exemplified by LLVM — and adapts it to an
LLM workflow.

## The LLVM analogy

| LLVM stage | paper2beamer stage | Determinism |
|---|---|---|
| Source + frontend (lex, parse) | Paper PDF + Docling extraction | Deterministic |
| LLVM IR (target-independent) | **Narrative IR** — the talk's story | LLM |
| Machine IR (target-aware) | **Slide IR** — the per-slide plan | LLM, ISA-constrained |
| Machine code (MC) | Beamer `.tex` | LLM + deterministic assembler |
| Assembler / linker | `latexmk -xelatex` → PDF | Deterministic |
| Target ISA / backend | **Theme-as-ISA** (`isa/<Theme>.md`) | Authored once per theme |

The value of the analogy is not aesthetic. Each property that makes LLVM's design
worthwhile transfers to this setting.

## Why multiple IR levels in an LLM workflow

A single-shot "PDF to LaTeX" prompt conflates three decisions that have different
owners and different failure modes: *what story to tell* (an authorial decision,
shaped by intent), *how to lay that story across slides* (a design decision,
constrained by the theme), and *how to render each slide in LaTeX* (a mechanical
decision). Collapsing them means a fault in any one forces regeneration of all
three. Separating them gives each a place to be inspected and a place to be
repaired. The Narrative IR can be reviewed by a human before a single slide
exists; the Slide IR can be checked against the theme's capabilities before a
single line of LaTeX is written.

## Why the IR is structured Markdown, not JSON

The intermediate representations are produced and consumed by a language model,
and the Narrative IR is additionally read by a human at the review gate. Rigid
JSON optimizes for a machine parser that this pipeline does not have: the
"parser" is an LLM, which handles labelled Markdown sections more reliably than
deeply nested JSON, and surgical edits to one Markdown section are cleaner than
edits to a serialized object. The representation is therefore *structured* — each
beat or slide is a section with a fixed set of labelled fields — without being
*rigid*. This keeps the IR simultaneously human-reviewable, machine-locatable,
and cheap to edit in place.

## Intent as a frontend-shaping force

In a compiler, flags such as the optimization level reshape the IR the frontend
emits. Here, the user's intent plays the same role. A fifteen-minute conference
talk and an unbounded content-faithful walkthrough of the same paper are not the
same program compiled differently at the back end; they are different Narrative
IRs from the start. Capturing intent before ingestion, and translating it into a
page budget and a depth/tone profile, lets that force act where it belongs — at
the top of the pipeline — rather than as a post-hoc trim.

## The theme as a pluggable ISA

A compiler backend targets an instruction set: it may emit only the operations
the target actually provides. A Beamer theme is exactly such a contract. It
defines the available "instructions" (special frames, semantic block
environments, inline emphasis, a semantic palette), the legal configuration (its
`\usetheme` options), and the constraints (aspect ratio, engine requirements,
per-frame capacity, and the packages it deliberately leaves to the deck). The
skill captures this as an ISA manifest, one per theme. The Narrative IR is
ISA-blind, so swapping a theme — swapping the backend — never disturbs the story;
only the Slide IR and the emission step consult the ISA. Authoring an ISA for a
new theme is the analogue of bringing up a new backend, and it is done once.

## The contribution: repair at the right level

The element this design adds beyond the standard compiler picture is the repair
policy. When a build fails, the naive LLM response is to regenerate — to recompile
the whole program from the source on every diagnostic. paper2beamer instead routes
each diagnostic to the lowest IR level that can resolve it, and edits only the one
unit it implicates. A LaTeX syntax error is a code-generation fault: fix the
offending frame's `.tex`. A frame that overflows its safe area is a layout fault:
revise that slide in the Slide IR. A deck that runs far past its time budget is an
authorial fault: cut or merge beats in the Narrative IR. Each diagnostic carries,
through provenance metadata, the identity of the single unit responsible, so the
fix is local. This is the analogue of a compiler attaching source locations to
diagnostics rather than discarding a translation unit whenever any instruction is
malformed. The mechanism that makes it possible — stable IDs and cross-level
provenance links — is detailed in [ir-and-isa.md](ir-and-isa.md).

The full pipeline and the decisions behind it are recorded in the design
specification under `docs/superpowers/specs/`.
