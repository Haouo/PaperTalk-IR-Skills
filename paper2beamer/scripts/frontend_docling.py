#!/usr/bin/env python3
"""frontend_docling.py — the deterministic FRONTEND of the paper2beamer compiler.

Role in the pipeline (see the design spec): turn a paper PDF into ``ir.v0.json``
plus a ``figures/`` directory of *cropped original* images. This stage makes **no
semantic decisions** — it does not decide what matters, only what is there. All
selection/summarisation happens later in the LLM optimization passes.

It is meant to be invoked through ``uv`` so Docling is available without touching
the system environment::

    uv run --with docling python paper2beamer/scripts/frontend_docling.py \
        --pdf paper.pdf --out build/

Outputs, relative to ``--out``:
    ir.v0.json      the IR seeded with `paper` (sections) and `figures` (registry)
    figures/        one PNG per extracted figure/table, originals untouched

Defensive posture:
  * Docling import failure yields an actionable message (how to get it), not a
    bare ``ModuleNotFoundError``.
  * Each figure's image extraction is wrapped independently: one un-renderable
    picture cannot abort the whole run; it is logged and skipped.
  * The IR is structurally validated (stage "frontend") before it is written, so
    a downstream pass never receives a malformed v0.
  * Writes are atomic (via ir_common.save_ir).
"""

from __future__ import annotations

import argparse
import os
import re
from typing import Any

# ir_common sits next to this script; the script's directory is on sys.path[0],
# so this plain import works under both `python` and `uv run`.
import ir_common
from ir_common import die, eprint


# ---------------------------------------------------------------------------
# Docling import (isolated so the failure message is useful)
# ---------------------------------------------------------------------------

def _import_docling() -> Any:
    """Import Docling lazily and translate a missing dependency into guidance."""
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
    except ImportError as exc:  # pragma: no cover - environment-dependent
        die(
            "Docling is not importable in this interpreter.\n"
            "  Run this script through uv so the dependency is provisioned, e.g.:\n"
            "    uv run --with docling python "
            "paper2beamer/scripts/frontend_docling.py --pdf <pdf> --out <dir>\n"
            f"  (underlying import error: {exc})"
        )
    return DocumentConverter, PdfFormatOption, InputFormat, PdfPipelineOptions


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

#: Render figures at 2x so embedded images stay crisp on a projector. Higher
#: scales inflate runtime and PNG size for little visible gain at slide sizes.
IMAGE_SCALE = 2.0


def _build_converter() -> Any:
    DocumentConverter, PdfFormatOption, InputFormat, PdfPipelineOptions = _import_docling()
    options = PdfPipelineOptions()
    # We need per-figure raster images, so ask the pipeline to keep them. Page
    # images are not needed (we crop figures, not whole pages) — leaving them off
    # keeps memory down on long papers.
    options.images_scale = IMAGE_SCALE
    options.generate_picture_images = True
    try:
        # Newer Docling exposes table images behind the same flag family; set it
        # if present, but never hard-fail if the attribute name drifts.
        options.generate_table_images = True  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - attribute may not exist
        pass
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )


def _label_of(item: Any) -> str:
    """Best-effort, version-tolerant read of a Docling item's label as a string."""
    label = getattr(item, "label", None)
    if label is None:
        return ""
    # DocItemLabel is an enum; ``.value`` is the stable string ("section_header").
    return str(getattr(label, "value", label))


def _page_of(item: Any) -> int | None:
    """Extract a 1-based page number from an item's provenance, if available."""
    prov = getattr(item, "prov", None) or []
    if prov:
        page = getattr(prov[0], "page_no", None)
        if isinstance(page, int):
            return page
    return None


def _caption_text(item: Any, doc: Any) -> str:
    """Return an item's caption text, tolerating API differences across versions."""
    getter = getattr(item, "caption_text", None)
    if callable(getter):
        try:
            text = getter(doc)
            if text:
                return str(text).strip()
        except Exception:  # pragma: no cover - defensive
            pass
    return ""


# A "section_header" starts a new logical section. A "title" is the paper title
# (captured separately, not turned into a section). Caption text is owned by
# figures and must not leak into section bodies.
_HEADER_LABELS = {"section_header"}
_TITLE_LABELS = {"title"}
_SKIP_IN_BODY = {"caption", "picture", "table", "page_header", "page_footer"}


def _extract_sections(doc: Any) -> tuple[str, list[dict[str, Any]]]:
    """Reconstruct ``(title, sections)`` from the document's reading order.

    The first ``title``-labelled item becomes the paper title (papers usually
    have exactly one). Text before the first section header is collected into a
    synthetic ``Frontmatter`` section so nothing is silently dropped.
    """
    doc_title = ""
    sections: list[dict[str, Any]] = []
    current = {"id": "sec0", "title": "Frontmatter", "level": 0, "text": ""}
    body_chunks: list[str] = []
    counter = 0

    def _flush() -> None:
        current["text"] = "\n".join(body_chunks).strip()
        # Keep a section even if empty-bodied when it carries a real title, so the
        # paper's structure survives; drop a truly empty synthetic frontmatter.
        if current["text"] or current["title"] != "Frontmatter":
            sections.append(dict(current))

    for item, _level in doc.iterate_items():
        label = _label_of(item)
        text = (getattr(item, "text", "") or "").strip()
        if label in _TITLE_LABELS:
            # First title wins; it is the paper title, not a body section.
            if not doc_title and text:
                doc_title = text
            continue
        if label in _HEADER_LABELS:
            _flush()
            counter += 1
            title = text or f"Section {counter}"
            current = {"id": f"sec{counter}", "title": title, "level": 1, "text": ""}
            body_chunks = []
        elif label in _SKIP_IN_BODY:
            continue
        elif text:
            body_chunks.append(text)
    _flush()
    return doc_title, sections


def _extract_figures(doc: Any, figures_dir: str, out_dir: str) -> list[dict[str, Any]]:
    """Save each picture/table image and return the figure registry.

    The stored ``path`` is *relative to the IR file* so the backend can resolve
    it regardless of where the build runs.
    """
    os.makedirs(figures_dir, exist_ok=True)
    registry: list[dict[str, Any]] = []

    def _harvest(items: Any, kind: str, prefix: str) -> None:
        for index, item in enumerate(items or [], start=1):
            fid = f"{prefix}{index}"
            rel_path = os.path.join("figures", f"{fid}.png")
            abs_path = os.path.join(figures_dir, f"{fid}.png")
            try:
                image = item.get_image(doc)  # PIL.Image or None
            except Exception as exc:  # pragma: no cover - defensive
                eprint(f"  warn: {fid}: could not obtain image ({exc}); skipping")
                continue
            if image is None:
                eprint(f"  warn: {fid}: no raster image available; skipping")
                continue
            try:
                image.save(abs_path)
            except Exception as exc:  # pragma: no cover - defensive
                eprint(f"  warn: {fid}: failed to save PNG ({exc}); skipping")
                continue
            registry.append(
                {
                    "id": fid,
                    "kind": kind,
                    "page": _page_of(item),
                    "path": rel_path,
                    "caption": _caption_text(item, doc),
                    "referenced_in": [],  # filled by _link_references below
                }
            )

    _harvest(getattr(doc, "pictures", None), "figure", "fig")
    _harvest(getattr(doc, "tables", None), "table", "tab")
    return registry


# Match "Figure 3", "Fig. 3", "Table 1", "Fig 2a" etc. in body text.
_REF_RE = re.compile(r"\b(?:fig(?:ure)?|tab(?:le)?)\.?\s*([0-9]+)", re.IGNORECASE)
_CAP_NUM_RE = re.compile(r"\b(?:figure|fig|table|tab)\.?\s*([0-9]+)", re.IGNORECASE)


def _link_references(sections: list[dict[str, Any]], figures: list[dict[str, Any]]) -> None:
    """Best-effort: record which sections mention each figure by its number.

    Purely advisory metadata for the figure-pass; failure to match is harmless.
    """
    # Map a figure to the number stated in its caption ("Figure 3" -> "3").
    fig_number: dict[str, str] = {}
    for fig in figures:
        m = _CAP_NUM_RE.search(fig.get("caption") or "")
        if m:
            fig_number[fig["id"]] = m.group(1)

    for sec in sections:
        nums_in_section = {m.group(1) for m in _REF_RE.finditer(sec["text"])}
        for fig in figures:
            num = fig_number.get(fig["id"])
            if num and num in nums_in_section:
                fig["referenced_in"].append(sec["id"])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run(pdf_path: str, out_dir: str) -> str:
    """Convert ``pdf_path`` into ``out_dir/ir.v0.json`` + figures. Return IR path."""
    if not os.path.isfile(pdf_path):
        die(f"input PDF not found: {pdf_path!r}")
    os.makedirs(out_dir, exist_ok=True)
    figures_dir = os.path.join(out_dir, "figures")

    eprint(f"frontend: converting {pdf_path} with Docling (scale={IMAGE_SCALE}x) ...")
    converter = _build_converter()
    try:
        result = converter.convert(pdf_path)
    except Exception as exc:
        die(f"Docling conversion failed: {exc}")
    doc = getattr(result, "document", None)
    if doc is None:
        die("Docling returned no document (conversion produced an empty result)")

    # Prefer the title Docling labelled; fall back to the document/file name.
    fallback_title = getattr(doc, "name", None) or os.path.splitext(os.path.basename(pdf_path))[0]
    extracted_title, sections = _extract_sections(doc)
    title = extracted_title or fallback_title
    figures = _extract_figures(doc, figures_dir, out_dir)
    _link_references(sections, figures)

    if not sections:
        # Not fatal, but a paper with zero sections almost certainly means the
        # PDF was scanned/image-only; warn so the user can pick a better source.
        eprint("  warn: no text sections extracted — is this a scanned/image PDF?")

    ir: dict[str, Any] = {
        "meta": {
            "schema": ir_common.SCHEMA_VERSION,
            "ir_version": "v0",
            "source_pdf": os.path.abspath(pdf_path),
            "produced_by_pass": "frontend",
        },
        "paper": {
            "title": str(title),
            "authors": [],            # Docling rarely separates authors reliably
            "venue": "",
            "abstract": "",
            "sections": sections,
            "references": [],
        },
        "figures": figures,
    }

    # Fail fast if we somehow produced a malformed v0.
    ir_common.validate_ir(ir, stage="frontend")

    ir_path = os.path.join(out_dir, "ir.v0.json")
    ir_common.save_ir(ir_path, ir)
    eprint(
        f"frontend: wrote {ir_path}  "
        f"({len(sections)} sections, {len(figures)} figures)"
    )
    return ir_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Docling frontend: PDF -> ir.v0.json + cropped figures."
    )
    parser.add_argument("--pdf", required=True, help="path to the input paper PDF")
    parser.add_argument(
        "--out", required=True, help="output directory for ir.v0.json and figures/"
    )
    args = parser.parse_args(argv)
    run(args.pdf, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
