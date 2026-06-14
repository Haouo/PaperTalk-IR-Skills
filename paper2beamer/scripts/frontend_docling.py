"""Deterministic PDF ingest via Docling.

Figures and structure are extracted by Docling, never guessed by an LLM. The
output is a Markdown rendering of the paper plus an images directory; the
Narrative pass reads these, it never reads the raw PDF. Keeping ingest
deterministic means the same paper always yields the same figures.
"""
from __future__ import annotations

import sys
from pathlib import Path


def figure_filename(index: int, ext: str) -> str:
    """Stable, sortable figure name: figure-001.png. index is 1-based."""
    if index < 1:
        raise ValueError("figure index is 1-based")
    return f"figure-{index:03d}.{ext}"


def ingest(pdf_path: Path, out_dir: Path) -> Path:
    """Extract ``pdf_path`` into out_dir/{paper-content.md, figures/}.

    Validates the input is an existing .pdf BEFORE importing Docling, so a bad
    path fails instantly instead of after a slow model import. Returns the path
    to paper-content.md.
    """
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"expected a .pdf, got {pdf_path.suffix!r}")

    # Imported lazily: Docling pulls heavy models; keep it out of the fast path
    # and out of CI's unit tests (which never call ingest()).
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import ImageRefMode

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    document = result.document

    # Export Markdown with figures written as referenced files under figures/.
    md_path = out_dir / "paper-content.md"
    document.save_as_markdown(
        md_path,
        image_mode=ImageRefMode.REFERENCED,
        artifacts_dir=figures_dir,
    )
    return md_path


def _main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Ingest a paper PDF with Docling.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        md = ingest(args.pdf, args.out)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
