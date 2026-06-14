# Pass contracts

Each pass is a function `IR(vN-1) → IR(vN)` (or a script that seeds/renders the
IR). This file is the authoritative checklist every pass must satisfy. The
Python validator `scripts/ir_common.py::validate_ir` enforces the *structural*
half of each contract; the *semantic* half is the responsibility of the LLM pass
and is listed here so it can self-check before writing the IR.

Global invariants (all passes):

- **Accumulative & immutable-prior:** a pass only adds/refines the fields it
  owns. It never deletes fields an earlier pass produced.
- **`meta.source_pdf` and `intent` are frozen** after they are first written.
- **Original figures are never re-rendered or edited** — passes reference them by
  id only.
- After writing `ir.vN.json`, the pass must pass `validate_ir(ir, "<pass>")`.
- Each pass bumps `meta.ir_version` and sets `meta.produced_by_pass`.

---

## frontend — `frontend_docling.py` → `ir.v0`

- **Reads:** `paper.pdf`
- **Writes:** `paper` (title, sections[]), `figures` (cropped originals registry)
- **Structural:** every section has a unique `id`, `title`, `text`; every figure
  has a unique `id`, a `kind` ∈ {figure, table, equation}, and a `path`.
- **Semantic:** none — purely mechanical extraction. No selection, no summary.
- **Failure:** Docling error → abort, no half-written IR.

## intent-intake (LLM, interactive) → augments `ir.v0`

- **Reads:** `ir.v0`, `assets/domain.example.md` (or the workspace `domain.md`)
- **Writes:** `intent` block (written **once**, then frozen)
- **Structural:** `occasion`, `duration_min > 0`, `language` ∈ {en, zh, bilingual}.
- **Semantic:** capture occasion, duration, audience, emphasis, depth, language
  from a short interview. Unanswered fields fall back to occasion defaults.
- **Gate ①:** in staged mode, stop here for user review.

## P1 content-pass (LLM) → `ir.v1`

- **Reads:** `ir.v0` (+ `intent`)
- **Writes:** `claims[]`
- **Structural:** each claim has a unique `id`, `type` ∈ the claim types,
  `statement`, and `salience` ∈ [0,1]; `section`/`figure_refs` must reference
  existing ids.
- **Semantic:**
  - One atomic, checkable assertion per claim. **Do not fabricate** numbers —
    `evidence` must be quotable from `paper.sections[].text`.
  - `salience` is **intent-aware**: weight by `intent.emphasis` and audience.
  - An assertion you cannot trace to the text stays in the IR with `salience: 0`
    (recorded, not deleted).

## P2 narrative-pass (LLM) → `ir.v2`

- **Reads:** `ir.v1` + `intent`
- **Writes:** `story[]` (ordered beats)
- **Structural:** each beat has a unique `id`, `role` ∈ the story roles, a
  `headline`; `claim_refs` must reference existing claims.
- **Semantic:**
  - **Compression is the point.** Select high-salience claims and arrange them
    into an arc (hook → problem → gap → idea → method → result → takeaway →
    closing — not all roles are mandatory).
  - Keep Σ`est_minutes` ≈ `intent.duration_min`. Over budget → drop the
    lowest-salience beats or lower depth. Dropped claims **stay** in `claims[]`.
  - Each beat's `headline` is the one sentence the audience should remember.
- **Gate ②:** in staged mode, stop here for user review of the arc.

## P3 figure-pass (LLM) → `ir.v3`

- **Reads:** `ir.v2`
- **Writes:** `story[].figures[]` (selection only)
- **Structural:** every `figure_id` must exist in `figures[]`; **≤ 1 primary**
  figure per beat.
- **Semantic:**
  - Choose original figures that *carry evidence the words cannot*. A beat with
    no such figure stays text-only.
  - Mark the main figure `role: "primary"`; a method/overview beat may add one
    `role: "evidence"`/`"context"` secondary.
  - Carry the original caption along (the backend can reuse or the layout-pass
    can shorten it).

## P4 layout-pass (LLM) → `ir.v4`

- **Reads:** `ir.v3` + `references/simple-theme-isa.md`
- **Writes:** `slides[]`
- **Structural:** valid `frame_type`s; content frames have a `title` and a body
  of blocks/figures; figure ids exist. First slide `titleframe`, last
  `thanksframe`.
- **Semantic:**
  - Map each beat to one (or, if dense, two) frames using the theme ISA.
  - Pick block semantics by meaning (result → `exampleblock`, caveat →
    `alertblock`, neutral → `block`); a single big message → `statementframe`.
  - **Respect the overflow budget** (short bullets, split crowded frames).
- **Gate ③:** in staged mode, stop here for user review of the slide plan.

## backend — `emit_beamer.py` → `deck.tex`

- **Reads:** `ir.v4`
- **Writes:** `deck.tex`
- **Pure rendering**, zero semantic decisions. Validates the IR first; a schema
  mismatch is reported as a named IR field, never as raw TeX.

## build — `build.sh` → `deck.pdf`

- **Reads:** `deck.tex`
- **Writes:** `deck.pdf`
- Runs `latexmk -xelatex` (two passes). `overflowguard=on` is the verifier:
  exit code `3` + offending slide numbers on overflow → the SKILL.md loop
  re-runs the layout-pass for those slides (**at most once** automatically).
