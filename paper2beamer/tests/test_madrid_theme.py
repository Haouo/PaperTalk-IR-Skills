"""Smoke-compile the real stock Madrid theme through our build wrapper.

Heavy: needs XeLaTeX, skipped in CI by default.
Run with:  uv run pytest tests/test_madrid_theme.py -m heavy
"""
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "paper2beamer" / "scripts" / "build.sh"

_DECK = r"""\documentclass[aspectratio=169]{beamer}
\usetheme{Madrid}
\title[Madrid]{Madrid Theme Test}\author{T}\date{}
\begin{document}
\frame{\titlepage}
\section{Intro}
\begin{frame}{Content}
  \begin{itemize}\item a\item b\end{itemize}
  \begin{block}{Claim}body\end{block}
\end{frame}
\begin{frame}{Math and columns}
  \begin{theorem}A statement.\end{theorem}
  \begin{columns}
    \begin{column}{0.5\textwidth}Left\end{column}
    \begin{column}{0.5\textwidth}Right\end{column}
  \end{columns}
\end{frame}
\end{document}
"""


@pytest.mark.heavy
def test_madrid_theme_compiles(tmp_path):
    (tmp_path / "main.tex").write_text(_DECK)
    result = subprocess.run([str(BUILD), str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "main.pdf").is_file()
