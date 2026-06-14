"""Parse a LaTeX/latexmk run into normalized, immutable build signals.

The rest of the pipeline never reads a raw .log. It reads the Signals object
produced here, so all the brittle string-matching lives in exactly one place.
That keeps the repair router and the orchestrator decoupled from TeX's wording.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Optional

# --- immutable signal records ------------------------------------------------


@dataclass(frozen=True)
class CompileError:
    """One TeX-level error. tex_line is the line in main.tex TeX blamed, if any."""

    message: str
    tex_line: Optional[int]
    raw: str


@dataclass(frozen=True)
class Overflow:
    """One frame whose body overflowed. slide_number is TeX's content frame number."""

    slide_number: Optional[int]
    detail: str


@dataclass(frozen=True)
class Signals:
    """Everything the repair router needs to know about one build."""

    compile_ok: bool
    errors: tuple[CompileError, ...] = ()
    overflows: tuple[Overflow, ...] = ()
    page_count: Optional[int] = None


# --- regexes (compiled once) -------------------------------------------------

# A TeX error line starts with "! ". Multiline so we scan the whole log.
_ERR_LINE = re.compile(r"^! (.+)$", re.MULTILINE)
# TeX reports the offending source line as "l.<n> ...".
_TEX_LINE = re.compile(r"^l\.(\d+)", re.MULTILINE)
# The Simple theme's overflowguard error names the slide precisely.
_OVERFLOW_GUARD = re.compile(r"Frame body overflows the safe area on slide (\d+)")
# Generic fallback when the theme has no overflowguard option.
_OVERFULL_VBOX = re.compile(r"Overfull \\vbox \(([\d.]+pt) too high\)")
# Final page count, written once per pdf output ("... (N pages, ...").
_PAGE_COUNT = re.compile(r"Output written on .*?\((\d+) pages?")


def parse_log(log_text: str, exit_code: int) -> Signals:
    """Turn raw log text + the process exit code into Signals.

    Defensive: rejects a non-string log or non-int exit code so a caller that
    passes the wrong thing fails loudly here, not three layers down.
    """
    if not isinstance(log_text, str):
        raise TypeError(f"log_text must be str, got {type(log_text).__name__}")
    if not isinstance(exit_code, int):
        raise TypeError(f"exit_code must be int, got {type(exit_code).__name__}")

    errors = _extract_errors(log_text)
    overflows = _extract_overflows(log_text)
    page_count = _extract_page_count(log_text)

    # The build is OK only if the process succeeded AND we saw no hard errors.
    compile_ok = exit_code == 0 and not errors

    return Signals(
        compile_ok=compile_ok,
        errors=tuple(errors),
        overflows=tuple(overflows),
        page_count=page_count,
    )


def _extract_errors(text: str) -> list[CompileError]:
    """Pair each `! ...` error with the nearest following `l.<n>` line, if any."""
    errors: list[CompileError] = []
    for match in _ERR_LINE.finditer(text):
        message = match.group(1).strip()
        # Search only the slice AFTER this error for its line marker, so two
        # errors never steal each other's line numbers.
        tail = text[match.end():]
        line_match = _TEX_LINE.search(tail)
        tex_line = int(line_match.group(1)) if line_match else None
        errors.append(
            CompileError(message=message, tex_line=tex_line, raw=match.group(0))
        )
    return errors


def _extract_overflows(text: str) -> list[Overflow]:
    """Prefer the theme's precise per-slide error; fall back to Overfull vbox."""
    overflows = [
        Overflow(slide_number=int(m.group(1)), detail=m.group(0))
        for m in _OVERFLOW_GUARD.finditer(text)
    ]
    if not overflows:
        overflows = [
            Overflow(slide_number=None, detail=m.group(0))
            for m in _OVERFULL_VBOX.finditer(text)
        ]
    return overflows


def _extract_page_count(text: str) -> Optional[int]:
    matches = _PAGE_COUNT.findall(text)
    # A two-pass build writes the count twice; the last write is authoritative.
    return int(matches[-1]) if matches else None


def _main(argv: list[str]) -> int:
    """CLI: `latex_log.py <main.log> [--assert-clean]`. Prints a JSON summary."""
    import argparse
    import json
    from pathlib import Path

    ap = argparse.ArgumentParser(description="Summarize a LaTeX log into signals.")
    ap.add_argument("log", type=Path)
    ap.add_argument(
        "--assert-clean",
        action="store_true",
        help="exit non-zero if any error or overflow is present",
    )
    args = ap.parse_args(argv)

    if not args.log.is_file():
        print(f"error: log file not found: {args.log}", file=sys.stderr)
        return 2

    sig = parse_log(args.log.read_text(errors="replace"), exit_code=0)
    print(
        json.dumps(
            {
                "compile_ok": sig.compile_ok,
                "errors": [e.message for e in sig.errors],
                "overflows": [o.slide_number for o in sig.overflows],
                "page_count": sig.page_count,
            },
            indent=2,
        )
    )

    if args.assert_clean and (sig.errors or sig.overflows):
        print("assert-clean failed: build has errors or overflows", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
