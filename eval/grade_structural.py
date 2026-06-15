"""Deterministic grader for a paper2beamer eval run.

Takes one finished `slides/<slug>/` output directory (and an optional run
manifest) and judges it against the seven acceptance criteria from
`docs/VERIFICATION.md`. Five criteria are decidable purely from the build
artifacts; two are process properties (local repair, single human gate) that can
only be observed from a manifest the eval driver writes. When the manifest is
absent those two are reported as `unverified` rather than silently passed —
honesty over a green checkmark.

The LaTeX log is parsed by the pipeline's own `latex_log.py`, so the grader and
the repair loop agree on what "compiles" and "overflow" mean.

CLI:
    python grade_structural.py --slides <run>/slides/<slug> \
        [--manifest <run>/manifest.json] [--out structural.json]
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

# Reuse the pipeline's single source of truth for LaTeX-log parsing. The eval
# harness lives beside the skill package; add its scripts dir to the path so the
# grader never reimplements brittle TeX string-matching.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "paper2beamer" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
import latex_log  # noqa: E402  (path injected above)

# Status vocabulary, kept small and explicit.
PASS = "pass"
FAIL = "fail"
SKIP = "skip"  # criterion does not apply to this run (e.g. unbounded intent)
UNVERIFIED = "unverified"  # could not be checked (e.g. manifest missing)

_INCLUDEGRAPHICS = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}")
_PROV_COMMENT = "% slide:{slide} beat:{beat}"
# Image extensions emit_beamer / Docling can legitimately produce.
_FIGURE_EXTS = (".png", ".pdf", ".jpg", ".jpeg")


@dataclass(frozen=True)
class Criterion:
    """One graded acceptance criterion."""

    id: str
    title: str
    status: str
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


# --- individual criteria (pure where possible, file I/O in grade()) ----------


def check_compiles(signals: "latex_log.Signals") -> Criterion:
    if signals.compile_ok:
        return Criterion(
            "compiles", "Deck compiles to a PDF", PASS,
            f"compile_ok; page_count={signals.page_count}",
        )
    msgs = "; ".join(e.message for e in signals.errors) or "non-zero build"
    return Criterion("compiles", "Deck compiles to a PDF", FAIL, msgs)


def check_overflow(signals: "latex_log.Signals") -> Criterion:
    if not signals.overflows:
        return Criterion("no_overflow", "No frame overflows", PASS, "no overflows")
    slides = ", ".join(
        str(o.slide_number) if o.slide_number is not None else "?"
        for o in signals.overflows
    )
    return Criterion(
        "no_overflow", "No frame overflows", FAIL, f"overflow on slide(s): {slides}"
    )


def parse_page_budget(narrative_text: str) -> Optional[tuple[int, int]]:
    """Read the `page-budget:` line from a Narrative IR `## Talk meta` block.

    Returns (min, max) for a bounded budget, None for an unbounded one. Raises
    ValueError when the line is present but unparseable, so a malformed budget is
    a loud failure rather than a silent skip.
    """
    line = None
    for raw in narrative_text.splitlines():
        stripped = raw.strip().lstrip("-").strip()
        if stripped.lower().startswith("page-budget:"):
            line = stripped.split(":", 1)[1].strip()
            break
    if line is None:
        raise ValueError("no page-budget line in Talk meta")
    low = line.lower()
    if "none" in low or "unbounded" in low:
        return None
    nums = [int(n) for n in re.findall(r"\d+", line)]
    if len(nums) >= 2:
        return nums[0], nums[1]
    raise ValueError(f"unparseable page-budget: {line!r}")


def count_content_frames(provenance: dict) -> int:
    """Frames carrying a footer number are the content slides the budget governs."""
    return sum(
        1 for f in provenance.get("frames", []) if f.get("content_number") is not None
    )


def check_page_budget(narrative_text: str, provenance: dict) -> Criterion:
    cid, title = "page_budget", "Content frame count within intent budget"
    try:
        budget = parse_page_budget(narrative_text)
    except ValueError as exc:
        return Criterion(cid, title, UNVERIFIED, str(exc))
    count = count_content_frames(provenance)
    if budget is None:
        return Criterion(cid, title, SKIP, f"unbounded intent; {count} content frames")
    lo, hi = budget
    status = PASS if lo <= count <= hi else FAIL
    return Criterion(cid, title, status, f"{count} content frames; budget {lo}-{hi}")


def check_provenance(main_tex_text: str, provenance: dict) -> Criterion:
    """Every frame's provenance comment must sit at tex_start-1, ranges must be
    well-formed, non-overlapping, and slide ids unique."""
    cid, title = "provenance", "Provenance comments present and consistent"
    frames = provenance.get("frames")
    if not frames:
        return Criterion(cid, title, FAIL, "provenance.json has no frames")
    lines = main_tex_text.splitlines()
    seen_ids: set[str] = set()
    spans: list[tuple[int, int]] = []
    for f in frames:
        sid, bid = f.get("slide_id"), f.get("beat_id")
        start, end = f.get("tex_start"), f.get("tex_end")
        if sid in seen_ids:
            return Criterion(cid, title, FAIL, f"duplicate slide_id {sid}")
        seen_ids.add(sid)
        if not (isinstance(start, int) and isinstance(end, int) and start <= end):
            return Criterion(cid, title, FAIL, f"{sid}: bad tex range {start}-{end}")
        if start < 2 or end > len(lines):
            return Criterion(cid, title, FAIL, f"{sid}: range outside main.tex")
        comment = lines[start - 2]  # comment line precedes the first body line
        want = _PROV_COMMENT.format(slide=sid, beat=bid)
        if comment.strip() != want:
            return Criterion(
                cid, title, FAIL, f"{sid}: expected {want!r}, found {comment.strip()!r}"
            )
        spans.append((start, end))
    spans.sort()
    for (a_start, a_end), (b_start, _) in zip(spans, spans[1:]):
        if b_start <= a_end:
            return Criterion(cid, title, FAIL, f"overlapping frame ranges near {a_end}")
    return Criterion(cid, title, PASS, f"{len(frames)} frames consistent")


def check_figures(main_tex_text: str, figures_dir: Path) -> Criterion:
    """Every \\includegraphics must resolve to a file under figures/ (Docling's
    output). Anything outside figures/ or missing means an invented figure."""
    cid, title = "figures_from_docling", "Figures originate only from Docling"
    refs = _INCLUDEGRAPHICS.findall(main_tex_text)
    if not refs:
        return Criterion(cid, title, PASS, "no figures referenced")
    available = {p.stem for p in figures_dir.glob("*") if p.is_file()}
    for ref in refs:
        ref_path = ref.strip()
        head = ref_path.split("/", 1)[0] if "/" in ref_path else ""
        if head != "figures":
            return Criterion(cid, title, FAIL, f"figure not under figures/: {ref_path}")
        stem = Path(ref_path).name
        stem_noext = Path(stem).stem if Path(stem).suffix in _FIGURE_EXTS else stem
        if stem_noext not in available and stem not in available:
            return Criterion(cid, title, FAIL, f"missing figure: {ref_path}")
    return Criterion(cid, title, PASS, f"{len(refs)} figure(s), all from Docling")


def check_local_repair(manifest: Optional[dict]) -> Criterion:
    """Process property: each rebuild must touch one IR level and never regen."""
    cid, title = "local_repair", "Repair stays local (no full regen)"
    if manifest is None:
        return Criterion(cid, title, UNVERIFIED, "no run manifest")
    rebuilds = manifest.get("rebuilds")
    if rebuilds is None:
        return Criterion(cid, title, UNVERIFIED, "manifest has no rebuilds field")
    if not rebuilds:
        return Criterion(cid, title, PASS, "no repairs needed")
    allowed = {"tex", "slide", "narrative"}
    for r in rebuilds:
        if r.get("full_regen"):
            return Criterion(cid, title, FAIL, f"full regen at attempt {r.get('attempt')}")
        if r.get("level") not in allowed:
            return Criterion(cid, title, FAIL, f"bad repair level {r.get('level')!r}")
    return Criterion(cid, title, PASS, f"{len(rebuilds)} local repair(s)")


def check_one_gate(manifest: Optional[dict]) -> Criterion:
    """Process property: exactly one human review gate, after the Narrative IR."""
    cid, title = "one_gate", "Exactly one human review gate"
    if manifest is None:
        return Criterion(cid, title, UNVERIFIED, "no run manifest")
    approvals = manifest.get("gate_approvals")
    if approvals is None:
        return Criterion(cid, title, UNVERIFIED, "manifest has no gate_approvals field")
    status = PASS if approvals == 1 else FAIL
    return Criterion(cid, title, status, f"gate_approvals={approvals}")


# --- orchestration -----------------------------------------------------------


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def grade(slides_dir: Path, manifest_path: Optional[Path] = None) -> list[Criterion]:
    """Grade one finished slides/<slug>/ directory. Missing artifacts surface as
    FAIL/UNVERIFIED criteria rather than exceptions, so a partial run still
    produces a readable report."""
    slides_dir = Path(slides_dir)
    results: list[Criterion] = []

    log_path = slides_dir / "main.log"
    if log_path.is_file():
        signals = latex_log.parse_log(log_path.read_text(errors="replace"), exit_code=0)
        results.append(check_compiles(signals))
        results.append(check_overflow(signals))
    else:
        results.append(Criterion("compiles", "Deck compiles to a PDF", FAIL, "no main.log"))
        results.append(Criterion("no_overflow", "No frame overflows", UNVERIFIED, "no main.log"))

    prov_path = slides_dir / "provenance.json"
    narrative_path = slides_dir / "narrative.md"
    main_tex_path = slides_dir / "main.tex"
    provenance = _read_json(prov_path) if prov_path.is_file() else {"frames": []}

    if narrative_path.is_file():
        results.append(check_page_budget(narrative_path.read_text(), provenance))
    else:
        results.append(Criterion("page_budget", "Content frame count within intent budget", UNVERIFIED, "no narrative.md"))

    if main_tex_path.is_file() and prov_path.is_file():
        main_tex = main_tex_path.read_text()
        results.append(check_provenance(main_tex, provenance))
        results.append(check_figures(main_tex, slides_dir / "figures"))
    else:
        results.append(Criterion("provenance", "Provenance comments present and consistent", FAIL, "missing main.tex or provenance.json"))
        results.append(Criterion("figures_from_docling", "Figures originate only from Docling", UNVERIFIED, "no main.tex"))

    manifest = _read_json(manifest_path) if manifest_path and Path(manifest_path).is_file() else None
    results.append(check_local_repair(manifest))
    results.append(check_one_gate(manifest))
    return results


def _main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Grade a paper2beamer eval run.")
    ap.add_argument("--slides", required=True, type=Path, help="slides/<slug> dir")
    ap.add_argument("--manifest", type=Path, default=None, help="run manifest.json")
    ap.add_argument("--out", type=Path, default=None, help="write structural.json here")
    args = ap.parse_args(argv)

    if not args.slides.is_dir():
        print(f"error: slides dir not found: {args.slides}", file=sys.stderr)
        return 2

    results = grade(args.slides, args.manifest)
    payload = [c.to_dict() for c in results]
    text = json.dumps(payload, indent=2) + "\n"
    if args.out:
        args.out.write_text(text)
    print(text, end="")
    # Exit non-zero if any hard FAIL, so the eval driver can branch on it.
    return 1 if any(c.status == FAIL for c in results) else 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
