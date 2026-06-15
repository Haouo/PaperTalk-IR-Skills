"""Measure a theme's per-frame capacity by rendering and building, not guessing.

For each content shape and density, emit frames with monotonically increasing
fill, build, and binary-search the largest fill that does NOT overflow. The
result replaces the prose "~6-8 bullets" with a measured number per theme.
Deterministic, no LLM; it just drives the existing build + log parser.

OverflowGuard awareness: overflowguard is a paper2beamer-specific capability (an
ISA extension), NOT a standard Beamer feature and NOT present in every theme.
When a theme provides the OverflowGuard extension, the probe enables it and reads
the hard per-slide error. When a theme lacks it, the probe omits the (nonexistent)
option and falls back to LaTeX's own "Overfull \\vbox" warning, which the log
parser already recognizes. Capacity numbers are PLANNING HINTS; the hard gate at
build time is the guard where present, the vbox warning where not.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import yaml

from scripts.latex_log import parse_log

_REPO = Path(__file__).resolve().parents[2]
_BUILD = _REPO / "paper2beamer" / "scripts" / "build.sh"
_ISA_DIR = _REPO / "paper2beamer" / "isa"

_BULLET = r"\item Representative bullet of roughly eight words here."


def _theme_caps(theme: str, isa_dir) -> tuple:
    """Return (has_density_option, provides_overflowguard) from the theme's Set."""
    data = yaml.safe_load((Path(isa_dir) / f"{theme}.yaml").read_text())
    provides = {p.split("@")[0] for p in data["provides"]}
    optnames = {o["name"] for o in data.get("options", [])}
    return ("density" in optnames, "OverflowGuard" in provides)


def _deck(theme: str, density: str, body: str, has_density: bool, has_guard: bool) -> str:
    parts = []
    if has_density:
        parts.append(f"density={density}")
    if has_guard:
        parts.append("overflowguard=on")
    opt = f"[{','.join(parts)}]" if parts else ""
    return (
        "\\documentclass[aspectratio=169]{beamer}\n"
        f"\\usetheme{opt}{{{theme}}}\n"
        "\\title[Probe]{Probe}\\author{}\\date{}\n"
        "\\begin{document}\n"
        "\\begin{frame}{Capacity probe}\n"
        f"{body}\n"
        "\\end{frame}\n"
        "\\end{document}\n"
    )


def _bullets(n: int) -> str:
    return "\\begin{itemize}\n" + "\n".join([_BULLET] * n) + "\n\\end{itemize}"


def _figure_bullets(n: int) -> str:
    fig = "\\begin{center}\\rule{0.6\\textwidth}{0.42\\textheight}\\end{center}"
    return fig + "\n" + _bullets(n)


def _blocks(n: int) -> str:
    one = "\\begin{block}{Point}Representative block body of about eight words.\\end{block}"
    return "\n".join([one] * n)


_SHAPES = {
    "bullets_per_frame": _bullets,
    "figure_plus_bullets": _figure_bullets,
    "blocks_per_frame": _blocks,
}


def _fits(theme: str, density: str, body: str, isa_dir=_ISA_DIR) -> bool:
    """True if a frame with this body does not overflow under the theme's gate.

    With the OverflowGuard extension: a guard error (non-zero exit) means overflow.
    Without it: the build succeeds and overflow shows up as an Overfull vbox.
    """
    has_density, has_guard = _theme_caps(theme, isa_dir)
    with tempfile.TemporaryDirectory() as d:
        deck = Path(d)
        (deck / "main.tex").write_text(_deck(theme, density, body, has_density, has_guard))
        proc = subprocess.run([str(_BUILD), str(deck)], capture_output=True, text=True)
        log = deck / "main.log"
        sig = parse_log(log.read_text(errors="replace") if log.is_file() else "", proc.returncode)
        if has_guard:
            if proc.returncode == 0:
                return True
            if sig.overflows:
                return False
            raise RuntimeError(
                f"guarded probe build failed for {theme}/{density} for a non-overflow "
                f"reason:\n{(proc.stdout + proc.stderr)[-800:]}"
            )
        # No guard: a build error is a real failure, not an overflow signal.
        if proc.returncode != 0:
            raise RuntimeError(
                f"unguarded probe build failed for {theme}/{density}:\n"
                f"{(proc.stdout + proc.stderr)[-800:]}"
            )
        return not sig.overflows  # Overfull \vbox => overflow


def measure(theme: str, shape: str, density: str, lo: int = 1, hi: int = 16,
            isa_dir=_ISA_DIR) -> int:
    """Binary-search the largest fill in [lo, hi] that does not overflow."""
    build = _SHAPES[shape]
    if not _fits(theme, density, build(lo), isa_dir):
        return 0
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        if _fits(theme, density, build(mid), isa_dir):
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def probe_all(theme: str, isa_dir=_ISA_DIR) -> dict:
    """Measure every shape at every density the theme supports; return a capacity dict."""
    has_density, _ = _theme_caps(theme, isa_dir)
    densities = ("normal", "dense") if has_density else ("normal",)
    out: dict = {}
    for density in densities:
        out[density] = {shape: measure(theme, shape, density, isa_dir=isa_dir)
                        for shape in _SHAPES}
    out["measured_at"] = {"bullet_words": 8}
    return out


def _main(argv: list) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Measure a theme's per-frame capacity.")
    ap.add_argument("--theme", required=True)
    args = ap.parse_args(argv)
    capacity = probe_all(args.theme)
    print(yaml.safe_dump({"capacity": capacity}, sort_keys=False, default_flow_style=False))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
