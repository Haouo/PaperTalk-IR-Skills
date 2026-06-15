"""Deterministic RQ4/RQ5 sweep: re-target one base deck across a theme matrix.

Given a base deck as an emit_beamer manifest (preamble.tex + order.txt +
frames/Sxx.tex) authored for a source theme, this re-targets it to every theme in
the matrix WITHOUT regenerating content: it rewrites \\usetheme, lowers any
instruction the target theme lacks to a Base equivalent (the declared
degradation), re-assembles, builds, and runs the conformance linter. It reports
RQ4 (narrative-edit rate, post-swap compile + conformance, degradation count) and
collects RQ5 data (conformance false positives: error-violations on a deck that
nonetheless compiles). Pure measurement; the only LLM cost upstream is authoring
the single base deck.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from scripts.emit_beamer import assemble
from scripts.isa_resolve import resolve
from scripts.conformance import check, instructions_used
from scripts.latex_log import parse_log

_REPO = Path(__file__).resolve().parents[2]
_BUILD = _REPO / "paper2beamer" / "scripts" / "build.sh"
_ISA_DIR = _REPO / "paper2beamer" / "isa"

# Textual lowering for the SpecialFrames instructions, applied when a target theme
# does not provide that extension (mirrors each extension's declared `lowering`).
def _lower_special_frames(text: str) -> str:
    text = re.sub(r"\\titleframe\b", r"\\maketitle", text)
    text = re.sub(r"\\statementframe\{([^}]*)\}",
                  r"\\begin{frame}[plain]\\centering\\vfill{\\Large \1}\\par\\vfill\\end{frame}",
                  text)
    text = re.sub(r"\\thanksframe(\[[^]]*\])?(\[[^]]*\])?",
                  r"\\begin{frame}[plain]\\centering\\vfill{\\Huge Thank you}\\par\\vfill\\end{frame}",
                  text)
    return text


def _retarget_preamble(preamble: str, target: str, has_guard: bool, has_density: bool) -> str:
    opts = []
    if has_density:
        opts.append("density=normal")
    if has_guard:
        opts.append("overflowguard=on")
    opt = f"[{','.join(opts)}]" if opts else ""
    return re.sub(r"\\usetheme(\[[^]]*\])?\{[^}]*\}", f"\\\\usetheme{opt}{{{target}}}", preamble)


def _caps(theme: str, isa_dir: Path):
    import yaml
    data = yaml.safe_load((isa_dir / f"{theme}.yaml").read_text())
    provides = {p.split("@")[0] for p in data["provides"]}
    optnames = {o["name"] for o in data.get("options", [])}
    return ("OverflowGuard" in provides, "density" in optnames, provides)


def swap_and_measure(manifest_dir, source_theme: str, targets, out_root, isa_dir=_ISA_DIR) -> list:
    manifest_dir = Path(manifest_dir); out_root = Path(out_root); isa_dir = Path(isa_dir)
    src_isa = resolve(source_theme, isa_dir)
    src_frames = {p.stem: p.read_text() for p in sorted((manifest_dir / "frames").glob("*.tex"))}
    used_source = instructions_used(src_isa, src_frames)
    preamble0 = (manifest_dir / "preamble.tex").read_text()

    rows = []
    for target in targets:
        has_guard, has_density, t_provides = _caps(target, isa_dir)
        t_isa = resolve(target, isa_dir)
        work = out_root / target
        (work / "frames").mkdir(parents=True, exist_ok=True)
        shutil.copy(manifest_dir / "order.txt", work / "order.txt")
        # degrade fragments if target lacks SpecialFrames
        degrade = "SpecialFrames" not in t_provides
        t_frames = {}
        for sid, txt in src_frames.items():
            new = _lower_special_frames(txt) if degrade else txt
            (work / "frames" / f"{sid}.tex").write_text(new)
            t_frames[sid] = new
        (work / "preamble.tex").write_text(
            _retarget_preamble(preamble0, target, has_guard, has_density))
        deck = out_root / f"build-{target}"
        assemble(work, deck)
        proc = subprocess.run([str(_BUILD), str(deck)], capture_output=True, text=True)
        compiles = proc.returncode == 0
        log = deck / "main.log"
        sig = parse_log(log.read_text(errors="replace") if log.is_file() else "", proc.returncode)
        violations = check(t_isa, frames=t_frames, preamble=(work / "preamble.tex").read_text())
        errs = [v for v in violations if v.severity == "error"]
        # degradation count = source instructions the target cannot express
        t_known = t_isa.allowed_macros | t_isa.allowed_environments
        degs = sorted(i for i in used_source if i not in t_known and i in src_isa.lowering)
        rows.append({
            "target": target,
            "compiles": compiles,
            "conformant": not errs,
            "n_error_violations": len(errs),
            "degradations": degs,
            "overflowed": bool(sig.overflows),
            # RQ5: a false positive is an error-violation on a deck that compiled.
            "rq5_false_positives": len(errs) if compiles else 0,
            "error_detail": [f"{v.slide_id}:{v.kind}:{v.detail}" for v in errs][:5],
        })
    return rows
