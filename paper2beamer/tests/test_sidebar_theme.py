"""Smoke-compile the Sidebar theme. Heavy: needs XeLaTeX, skipped in CI by default.

Run explicitly with:  uv run pytest tests/test_sidebar_theme.py -m heavy
"""
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "paper2beamer" / "scripts" / "build.sh"

_DECK = r"""\documentclass[aspectratio=169]{beamer}
\usetheme[overflowguard=on]{Sidebar}
\title[Sidebar smoke]{Sidebar Theme Smoke Test}
\author{Tester}\date{}
\begin{document}
\section{Intro}
\begin{frame}{A content frame}
  \begin{itemize}\item one \item two\end{itemize}
  \begin{block}{Claim}A neutral block.\end{block}
  \begin{alertblock}{Caveat}A gold block.\end{alertblock}
\end{frame}
\section{Math}
\begin{frame}{Theorem and columns}
  \begin{theorem}A statement.\end{theorem}
  \begin{columns}
    \begin{column}{0.5\textwidth}Left\end{column}
    \begin{column}{0.5\textwidth}Right\end{column}
  \end{columns}
\end{frame}
\end{document}
"""


@pytest.mark.heavy
def test_sidebar_theme_compiles(tmp_path):
    (tmp_path / "main.tex").write_text(_DECK)
    result = subprocess.run([str(BUILD), str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "main.pdf").is_file()
