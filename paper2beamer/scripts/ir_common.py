"""ir_common.py — shared foundation for the paper2beamer pass pipeline.

This module is imported by every Python helper in the skill (the Docling
frontend and the Beamer backend). It deliberately depends on the **standard
library only** so that it can run under either the system interpreter or an
ephemeral ``uv run`` environment without pulling extra wheels.

It provides four things, each defensive by design:

1. Constants describing the IR contract (versions, the figure kinds, the legal
   Simple-theme frame/block vocabulary). Centralising them keeps the frontend,
   backend and the reference docs from drifting apart.
2. ``escape_latex`` — a conservative LaTeX escaper. The backend must never emit
   raw user/paper text into a ``.tex`` file without escaping, or a stray ``&``
   or ``_`` will break the build (or worse, silently change meaning).
3. Atomic, validated IR file IO (``load_ir`` / ``save_ir``). Writes go through a
   temp file + ``os.replace`` so a crash mid-write can never leave a truncated
   ``ir.vN.json`` that a later pass would happily misparse.
4. ``validate_ir`` — a focused, stage-aware structural validator. It fails fast
   with a precise, human-readable path to the offending field, which is the
   single most useful thing when a semantic (LLM) pass writes a slightly wrong
   shape.

Design rule mirrored from the spec: passes are *accumulative*. ``validate_ir``
checks that the fields a given stage is supposed to have produced are present
and well-formed; it never requires fields a later stage owns.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from typing import Any, Iterable, NoReturn

# ---------------------------------------------------------------------------
# IR contract constants
# ---------------------------------------------------------------------------

#: Bump only on breaking changes to the IR shape. Stored in ``meta.schema`` so a
#: stale IR from an older skill version can be detected and rejected.
SCHEMA_VERSION = "1.0"

#: Ordered pipeline stages. The index doubles as the numeric IR version, i.e.
#: ``STAGES.index("content-pass")`` -> the ``vN`` that pass produces.
#: ``frontend`` and ``intent-intake`` both land in ``v0`` (intake augments the
#: frontend's output in place, as decided in the design), so they share index 0.
STAGES: tuple[str, ...] = (
    "frontend",        # v0: paper + figures
    "intent-intake",   # v0: + intent block (augments v0)
    "content-pass",    # v1: + claims
    "narrative-pass",  # v2: + story
    "figure-pass",     # v3: + story[].figures
    "layout-pass",     # v4: + slides
)

#: Figure kinds the frontend is allowed to register. Anything else is a bug in
#: the extractor and should surface loudly rather than reach a slide.
FIGURE_KINDS: frozenset[str] = frozenset({"figure", "table", "equation"})

#: Claim types the content-pass may assign.
CLAIM_TYPES: frozenset[str] = frozenset(
    {"problem", "method", "result", "contribution", "limitation", "background"}
)

#: Narrative beat roles the narrative-pass may assign.
STORY_ROLES: frozenset[str] = frozenset(
    {"hook", "problem", "gap", "idea", "method", "result", "takeaway", "closing"}
)

#: The Simple theme's "instruction set": the frame types the layout-pass may
#: emit. Kept in lock-step with references/simple-theme-isa.md and the backend's
#: dispatch table; the backend rejects anything outside this set.
FRAME_TYPES: frozenset[str] = frozenset(
    {"titleframe", "frame", "statementframe", "thanksframe"}
)

#: Legal block environments inside a content ``frame``.
BLOCK_TYPES: frozenset[str] = frozenset(
    {"block", "alertblock", "exampleblock", "itemize", "enumerate"}
)

#: Recognised intent languages.
LANGUAGES: frozenset[str] = frozenset({"en", "zh", "bilingual"})


class IRValidationError(ValueError):
    """Raised when an IR document violates the structural contract.

    Carries a ``path`` (dotted/indexed location of the offending field) so the
    caller — and the human reading the error — can jump straight to it.
    """

    def __init__(self, message: str, path: str = "<root>") -> None:
        self.path = path
        super().__init__(f"{path}: {message}")


# ---------------------------------------------------------------------------
# LaTeX escaping
# ---------------------------------------------------------------------------

# The ten TeX specials and their escaped forms. We replace them in a SINGLE
# regex pass (each match substituted exactly once) rather than sequentially —
# sequential replacement is subtly broken because the braces introduced by, e.g.,
# ``\textbackslash{}`` would be re-escaped by a later ``{`` -> ``\{`` rule.
_LATEX_REPLACEMENTS: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# A character class matching any single special. Order inside the class is
# irrelevant since each position is matched once and mapped via the dict.
_LATEX_SPECIAL_RE = re.compile("|".join(re.escape(ch) for ch in _LATEX_REPLACEMENTS))


def escape_latex(text: Any) -> str:
    """Return ``text`` safe to drop into a LaTeX document body.

    Defensive on input type: anything non-``str`` is coerced via ``str`` so a
    stray number or ``None`` in the IR cannot crash the renderer (it becomes
    visible text, which is easy to spot in the PDF and fix in the IR).

    This is intentionally conservative — it escapes the ten TeX specials and
    nothing else, each exactly once. The backend uses it for *all* paper-derived
    text. Verbatim LaTeX that a pass intends literally (e.g. a math snippet) must
    travel through a field the backend treats as raw, never through this function.
    """
    if text is None:
        return ""
    s = text if isinstance(text, str) else str(text)
    return _LATEX_SPECIAL_RE.sub(lambda m: _LATEX_REPLACEMENTS[m.group()], s)


# ---------------------------------------------------------------------------
# Atomic, validated IR file IO
# ---------------------------------------------------------------------------

def load_ir(path: str) -> dict[str, Any]:
    """Load an IR JSON file, failing loudly on the common breakages.

    Distinguishes "file missing" from "file present but not valid JSON" from
    "valid JSON but not an object", because each points at a different mistake
    upstream and a generic ``KeyError`` three passes later would hide all three.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"IR file not found: {path!r}. Did the previous pass run and write it?"
        )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:  # narrow: corrupt/partial JSON
        raise IRValidationError(
            f"not valid JSON ({exc.msg} at line {exc.lineno} col {exc.colno})",
            path=path,
        ) from exc
    if not isinstance(data, dict):
        raise IRValidationError(
            f"top-level IR must be a JSON object, got {type(data).__name__}",
            path=path,
        )
    return data


def save_ir(path: str, ir: dict[str, Any]) -> None:
    """Write ``ir`` to ``path`` atomically (temp file + ``os.replace``).

    A half-written ``ir.vN.json`` is worse than no file at all, because the next
    pass might parse a truncated-but-syntactically-plausible prefix. Writing to
    a sibling temp file in the same directory (so ``os.replace`` is atomic on the
    same filesystem) and renaming over the target guarantees readers see either
    the old file or the complete new one, never a torn write.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".ir-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(ir, fh, ensure_ascii=False, indent=2, sort_keys=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())  # durability: survive a crash right after rename
        os.replace(tmp_path, path)  # atomic on POSIX within one filesystem
    except BaseException:
        # Clean up the temp file on any failure (including KeyboardInterrupt) so
        # we never litter the working directory with .ir-*.tmp droppings.
        with _suppress_errors():
            os.unlink(tmp_path)
        raise


class _suppress_errors:
    """Tiny context manager: swallow exceptions during best-effort cleanup."""

    def __enter__(self) -> "_suppress_errors":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return True  # suppress whatever was raised inside the block


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _require(cond: bool, message: str, path: str) -> None:
    """Raise ``IRValidationError`` unless ``cond`` holds."""
    if not cond:
        raise IRValidationError(message, path=path)


def _require_type(value: Any, types: type | tuple[type, ...], path: str) -> None:
    names = (
        types.__name__
        if isinstance(types, type)
        else " or ".join(t.__name__ for t in types)
    )
    _require(isinstance(value, types), f"expected {names}, got {type(value).__name__}", path)


def _require_keys(obj: Any, keys: Iterable[str], path: str) -> None:
    _require_type(obj, dict, path)
    for key in keys:
        _require(key in obj, f"missing required key {key!r}", path)


def _require_in(value: Any, allowed: Iterable[Any], path: str) -> None:
    allowed = set(allowed)
    _require(value in allowed, f"{value!r} not in {sorted(allowed)}", path)


def _stage_index(stage: str) -> int:
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {list(STAGES)}")
    return STAGES.index(stage)


def validate_ir(ir: dict[str, Any], stage: str) -> None:
    """Validate ``ir`` against the contract *up to and including* ``stage``.

    ``stage`` is the pass that just produced this IR. We check that every field
    owned by ``stage`` and all earlier stages is present and well-typed, and we
    do **not** demand fields a later stage owns (the IR is accumulative).

    Raises ``IRValidationError`` with a precise path on the first problem.
    """
    idx = _stage_index(stage)

    # meta is mandatory from v0 onward -------------------------------------
    _require_keys(ir, ("meta",), "<root>")
    meta = ir["meta"]
    _require_keys(meta, ("schema", "ir_version", "source_pdf", "produced_by_pass"), "meta")
    _require(
        meta["schema"] == SCHEMA_VERSION,
        f"schema {meta['schema']!r} != supported {SCHEMA_VERSION!r}",
        "meta.schema",
    )

    # v0: paper + figures ---------------------------------------------------
    _validate_paper(ir)
    _validate_figures(ir)

    # intent block: present once the intake stage has run -------------------
    if idx >= _stage_index("intent-intake"):
        _validate_intent(ir)

    # v1: claims ------------------------------------------------------------
    if idx >= _stage_index("content-pass"):
        _validate_claims(ir)

    # v2: story -------------------------------------------------------------
    if idx >= _stage_index("narrative-pass"):
        _validate_story(ir, require_figures=idx >= _stage_index("figure-pass"))

    # v4: slides ------------------------------------------------------------
    if idx >= _stage_index("layout-pass"):
        _validate_slides(ir)


def _validate_paper(ir: dict[str, Any]) -> None:
    _require_keys(ir, ("paper",), "<root>")
    paper = ir["paper"]
    _require_keys(paper, ("title", "sections"), "paper")
    _require_type(paper["title"], str, "paper.title")
    _require_type(paper["sections"], list, "paper.sections")
    seen_ids: set[str] = set()
    for i, sec in enumerate(paper["sections"]):
        p = f"paper.sections[{i}]"
        _require_keys(sec, ("id", "title", "text"), p)
        _require_type(sec["id"], str, f"{p}.id")
        _require(sec["id"] not in seen_ids, f"duplicate section id {sec['id']!r}", f"{p}.id")
        seen_ids.add(sec["id"])
        _require_type(sec["title"], str, f"{p}.title")
        _require_type(sec["text"], str, f"{p}.text")


def _validate_figures(ir: dict[str, Any]) -> None:
    _require_keys(ir, ("figures",), "<root>")
    figures = ir["figures"]
    _require_type(figures, list, "figures")
    seen_ids: set[str] = set()
    for i, fig in enumerate(figures):
        p = f"figures[{i}]"
        _require_keys(fig, ("id", "kind", "path"), p)
        _require_type(fig["id"], str, f"{p}.id")
        _require(fig["id"] not in seen_ids, f"duplicate figure id {fig['id']!r}", f"{p}.id")
        seen_ids.add(fig["id"])
        _require_in(fig["kind"], FIGURE_KINDS, f"{p}.kind")
        _require_type(fig["path"], str, f"{p}.path")


def _validate_intent(ir: dict[str, Any]) -> None:
    _require_keys(ir, ("intent",), "<root>")
    intent = ir["intent"]
    _require_keys(intent, ("occasion", "duration_min", "language"), "intent")
    _require_type(intent["occasion"], str, "intent.occasion")
    _require_type(intent["duration_min"], (int, float), "intent.duration_min")
    _require(intent["duration_min"] > 0, "duration_min must be positive", "intent.duration_min")
    _require_in(intent["language"], LANGUAGES, "intent.language")


def _validate_claims(ir: dict[str, Any]) -> None:
    _require_keys(ir, ("claims",), "<root>")
    claims = ir["claims"]
    _require_type(claims, list, "claims")
    section_ids = {s["id"] for s in ir["paper"]["sections"]}
    figure_ids = {f["id"] for f in ir["figures"]}
    seen_ids: set[str] = set()
    for i, claim in enumerate(claims):
        p = f"claims[{i}]"
        _require_keys(claim, ("id", "type", "statement", "salience"), p)
        _require(claim["id"] not in seen_ids, f"duplicate claim id {claim['id']!r}", f"{p}.id")
        seen_ids.add(claim["id"])
        _require_in(claim["type"], CLAIM_TYPES, f"{p}.type")
        _require_type(claim["statement"], str, f"{p}.statement")
        _require_type(claim["salience"], (int, float), f"{p}.salience")
        _require(0.0 <= claim["salience"] <= 1.0, "salience must be in [0,1]", f"{p}.salience")
        # Referential integrity: a claim may only cite sections/figures that exist.
        if "section" in claim and claim["section"] is not None:
            _require_in(claim["section"], section_ids, f"{p}.section")
        for j, fid in enumerate(claim.get("figure_refs", []) or []):
            _require_in(fid, figure_ids, f"{p}.figure_refs[{j}]")


def _validate_story(ir: dict[str, Any], *, require_figures: bool) -> None:
    _require_keys(ir, ("story",), "<root>")
    story = ir["story"]
    _require_type(story, list, "story")
    claim_ids = {c["id"] for c in ir["claims"]}
    figure_ids = {f["id"] for f in ir["figures"]}
    seen_ids: set[str] = set()
    for i, beat in enumerate(story):
        p = f"story[{i}]"
        _require_keys(beat, ("id", "role", "headline"), p)
        _require(beat["id"] not in seen_ids, f"duplicate story id {beat['id']!r}", f"{p}.id")
        seen_ids.add(beat["id"])
        _require_in(beat["role"], STORY_ROLES, f"{p}.role")
        _require_type(beat["headline"], str, f"{p}.headline")
        for j, cid in enumerate(beat.get("claim_refs", []) or []):
            _require_in(cid, claim_ids, f"{p}.claim_refs[{j}]")
        figs = beat.get("figures", []) or []
        if require_figures:
            # The figure-pass invariant: at most one PRIMARY figure per beat.
            # A secondary (role != "primary"-excluded) figure is allowed for
            # method/overview beats, so we only cap the primaries.
            primaries = [g for g in figs if (g.get("role") or "evidence") == "primary"]
            _require(len(primaries) <= 1, "more than one primary figure on a beat", f"{p}.figures")
        for j, g in enumerate(figs):
            gp = f"{p}.figures[{j}]"
            _require_keys(g, ("figure_id",), gp)
            _require_in(g["figure_id"], figure_ids, f"{gp}.figure_id")


def _validate_slides(ir: dict[str, Any]) -> None:
    _require_keys(ir, ("slides",), "<root>")
    slides = ir["slides"]
    _require_type(slides, list, "slides")
    _require(len(slides) > 0, "deck has no slides", "slides")
    figure_ids = {f["id"] for f in ir["figures"]}
    for i, slide in enumerate(slides):
        p = f"slides[{i}]"
        _require_keys(slide, ("frame_type",), p)
        _require_in(slide["frame_type"], FRAME_TYPES, f"{p}.frame_type")
        ftype = slide["frame_type"]
        if ftype == "frame":
            _require_keys(slide, ("title",), p)
            _require_type(slide["title"], str, f"{p}.title")
            _validate_frame_body(slide.get("body", []), figure_ids, f"{p}.body")
        elif ftype == "statementframe":
            _require_keys(slide, ("text",), p)
            _require_type(slide["text"], str, f"{p}.text")
        # titleframe / thanksframe carry only optional decorative fields.


def _validate_frame_body(body: Any, figure_ids: set[str], path: str) -> None:
    _require_type(body, list, path)
    for i, item in enumerate(body):
        p = f"{path}[{i}]"
        _require_type(item, dict, p)
        # A body item is exactly one of: a block, or a figure embed.
        if "figure" in item:
            _require_in(item["figure"], figure_ids, f"{p}.figure")
        elif "block" in item:
            _require_in(item["block"], BLOCK_TYPES, f"{p}.block")
        else:
            raise IRValidationError("body item must have a 'block' or 'figure' key", path=p)


# ---------------------------------------------------------------------------
# Small CLI utilities shared by the scripts
# ---------------------------------------------------------------------------

def eprint(*args: Any) -> None:
    """Print to stderr so machine-readable stdout (if any) stays clean."""
    print(*args, file=sys.stderr, flush=True)


def die(message: str, code: int = 1) -> NoReturn:
    """Print an error to stderr and exit with a non-zero status."""
    eprint(f"error: {message}")
    raise SystemExit(code)
