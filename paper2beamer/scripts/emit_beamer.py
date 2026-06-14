"""Assemble a deck build manifest into main.tex + provenance.json.

Keeping assembly deterministic (rather than asking the LLM to write the whole
file) guarantees the provenance comments and line ranges are always correct, so
repair routing can trust them. The emission pass writes a small manifest; this
module stitches it together and records exactly where each frame landed.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# An order.txt line: "S01 beat:N01" with an optional trailing " plain" flag for
# unnumbered special frames (title page, dividers, statement, thanks).
_ORDER_LINE = re.compile(r"^(?P<slide>S\w+)\s+beat:(?P<beat>N\w+)(?P<plain>\s+plain)?\s*$")


@dataclass(frozen=True)
class _Entry:
    slide_id: str
    beat_id: str
    plain: bool


def _parse_order(order_path: Path) -> list[_Entry]:
    """Parse order.txt defensively: every non-blank line must match the grammar."""
    entries: list[_Entry] = []
    for n, line in enumerate(order_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        m = _ORDER_LINE.match(line)
        if not m:
            raise ValueError(f"{order_path}:{n}: malformed order line: {line!r}")
        entries.append(_Entry(m.group("slide"), m.group("beat"), bool(m.group("plain"))))
    if not entries:
        raise ValueError(f"{order_path}: no frames declared")
    return entries


def assemble(manifest_dir: Path, out_dir: Path) -> Path:
    """Build out_dir/main.tex and out_dir/provenance.json from the manifest.

    Returns the path to main.tex. Validates every referenced file up front so a
    missing fragment fails before we write a half-built deck.
    """
    manifest_dir = Path(manifest_dir)
    out_dir = Path(out_dir)
    preamble = manifest_dir / "preamble.tex"
    order = manifest_dir / "order.txt"
    if not preamble.is_file():
        raise FileNotFoundError(f"missing preamble: {preamble}")
    if not order.is_file():
        raise FileNotFoundError(f"missing order file: {order}")

    entries = _parse_order(order)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build the file as a list of lines so we can record 1-based line ranges.
    lines: list[str] = []
    lines.extend(preamble.read_text().splitlines())
    lines.append("\\begin{document}")

    prov_frames: list[dict] = []
    content_number = 0
    for e in entries:
        fragment = manifest_dir / "frames" / f"{e.slide_id}.tex"
        if not fragment.is_file():
            raise FileNotFoundError(f"missing frame fragment: {fragment}")

        # Numbered content frames get a running number; plain frames do not, so
        # the number matches what the footer (and overflow errors) report.
        if e.plain:
            number = None
        else:
            content_number += 1
            number = content_number

        lines.append(f"% slide:{e.slide_id} beat:{e.beat_id}")
        tex_start = len(lines) + 1  # 1-based line of the frame's first body line
        body = fragment.read_text().splitlines()
        lines.extend(body)
        tex_end = len(lines)

        prov_frames.append(
            {
                "slide_id": e.slide_id,
                "beat_id": e.beat_id,
                "content_number": number,
                "tex_start": tex_start,
                "tex_end": tex_end,
            }
        )

    lines.append("\\end{document}")

    main_tex = out_dir / "main.tex"
    main_tex.write_text("\n".join(lines) + "\n")
    (out_dir / "provenance.json").write_text(
        json.dumps({"frames": prov_frames}, indent=2) + "\n"
    )
    return main_tex


def _main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Assemble a deck manifest into main.tex.")
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        path = assemble(args.manifest, args.out)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
