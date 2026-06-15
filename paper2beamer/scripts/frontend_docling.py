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


def relativize_image_refs(md_text: str, out_dir: Path) -> str:
    """Strip the out_dir prefix from image refs so they are relative to the md.

    Docling writes the artifacts_dir path verbatim, producing absolute refs like
    ``/tmp/run/figures/x.png``. The markdown lives in out_dir, so removing the
    out_dir prefix yields ``figures/x.png`` — portable when the folder moves.
    """
    for prefix in {f"{out_dir}/", f"{Path(out_dir).resolve()}/"}:
        md_text = md_text.replace(prefix, "")
    return md_text


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
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.types.doc import ImageRefMode

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Docling does NOT render or persist figure images by default; without this
    # the markdown export emits bare `<!-- image -->` placeholders and figures/
    # stays empty. Since "figures come ONLY from Docling" is a core invariant,
    # turn picture-image generation on and render at 2x for legible diagrams.
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_picture_images = True
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(str(pdf_path))
    document = result.document

    # Export Markdown with figures written as referenced files under figures/.
    md_path = out_dir / "paper-content.md"
    document.save_as_markdown(
        md_path,
        image_mode=ImageRefMode.REFERENCED,
        artifacts_dir=figures_dir,
    )

    # Docling writes the artifacts_dir path verbatim into the image refs, which
    # makes them absolute (e.g. /tmp/run/figures/x.png). Downstream reads
    # paper-content.md + figures/ from the slides dir, so rewrite the refs to be
    # relative to the markdown file (figures/x.png) — otherwise the deck can't
    # find its figures once the folder is moved.
    md_path.write_text(relativize_image_refs(md_path.read_text(), out_dir))
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
