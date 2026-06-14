#!/usr/bin/env bash
# Build a deck directory containing main.tex into main.pdf with XeLaTeX.
# Usage: build.sh <deck_dir>
# Exit code is latexmk's; main.log is left in <deck_dir> for latex_log.py.
set -uo pipefail

DECK="${1:?usage: build.sh <deck_dir>}"
if [[ ! -f "$DECK/main.tex" ]]; then
  echo "build.sh: no main.tex in $DECK" >&2
  exit 2
fi

# Resolve the repo root so the Simple theme on TEXINPUTS is found regardless of
# where the deck lives. template/ holds beamerthemeSimple.sty.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Trailing // tells kpathsea to search recursively; the trailing colon keeps the
# distribution's default search paths.
export TEXINPUTS="${REPO_ROOT}/template//:${TEXINPUTS:-}"

# latexmk runs xelatex as many passes as needed for a correct frame total.
# nonstopmode + halt-on-error make a real error abort instead of prompting.
latexmk -xelatex -interaction=nonstopmode -halt-on-error -g \
  -output-directory="$DECK" "$DECK/main.tex"
exit $?
