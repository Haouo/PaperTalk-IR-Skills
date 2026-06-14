"""Opt-in live end-to-end test of the Docling frontend on a REAL generated PDF.

Marked ``e2e`` and excluded from the default run (see pytest.ini) because it
downloads Docling models on first use and needs xelatex to synthesise the PDF.

Run with:
    uv run --with pytest --with docling python -m pytest tests/ -m e2e
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

import ir_common

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
FIG = os.path.join(HERE, "fixtures", "sample_build", "figures", "fig1.png")

pytestmark = pytest.mark.e2e

_have_docling = importlib.util.find_spec("docling") is not None
_have_xelatex = shutil.which("xelatex") is not None
requires_tools = pytest.mark.skipif(
    not (_have_docling and _have_xelatex),
    reason="needs both docling and xelatex",
)


def _make_pdf(work: str) -> str:
    """Compile a tiny but realistic paper PDF (title, sections, a figure)."""
    shutil.copy(FIG, os.path.join(work, "fig1.png"))
    tex = textwrap.dedent(r"""
        \documentclass{article}
        \usepackage{graphicx}
        \begin{document}
        \title{A Tiny Test Paper on Sparse Routing}
        \author{T. Ester}
        \maketitle
        \section{Introduction}
        Decoding is slow. We propose sparse attention routing.
        As shown in Figure 1, the router selects k heads per token.
        \section{Method}
        The router scores heads and keeps the top k.
        \begin{figure}[h]\centering
        \includegraphics[width=0.4\textwidth]{fig1.png}
        \caption{Sparse attention routing selects k heads per token.}
        \end{figure}
        \section{Results}
        We improve BLEU by 3.2 and decode two times faster.
        \end{document}
    """)
    tex_path = os.path.join(work, "mini.tex")
    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write(tex)
    subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "mini.tex"],
        cwd=work, capture_output=True, text=True, check=True,
    )
    return os.path.join(work, "mini.pdf")


@requires_tools
def test_frontend_extracts_sections_and_figure(tmp_path):
    work = str(tmp_path)
    pdf = _make_pdf(work)
    out = os.path.join(work, "out")
    subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "frontend_docling.py"),
         "--pdf", pdf, "--out", out],
        check=True,
    )
    ir = ir_common.load_ir(os.path.join(out, "ir.v0.json"))
    # The produced IR must be a valid v0.
    ir_common.validate_ir(ir, "frontend")
    # Real extraction expectations.
    assert len(ir["paper"]["sections"]) >= 3
    assert len(ir["figures"]) >= 1
    fig = ir["figures"][0]
    assert os.path.isfile(os.path.join(out, fig["path"]))   # image was cropped to disk
