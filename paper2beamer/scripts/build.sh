#!/usr/bin/env bash
# build.sh — compile a generated deck.tex into deck.pdf with XeLaTeX.
#
# This is the final, deterministic stage of the paper2beamer pipeline. It runs
# the *real* compiler over the backend's output; a non-zero exit means the deck
# does not build and the pipeline must not claim success.
#
# It doubles as the pipeline's VERIFIER: the Simple theme is loaded with
# overflowguard=on, so a frame whose body would spill into the footer aborts the
# build with a recognisable error. build.sh detects that specific failure and
# reports the offending slide numbers on a dedicated exit code (3), which the
# SKILL.md verifier loop uses to trigger a localised layout-pass re-run.
#
# Usage:
#   paper2beamer/scripts/build.sh <path/to/deck.tex>
#
# Exit codes:
#   0  success: deck.pdf produced
#   2  usage / environment error (bad args, missing engine, missing file)
#   3  overflow: a frame exceeded the safe area (verifier signal)
#   4  other LaTeX compilation failure
#
# Defensive choices:
#   * `set -euo pipefail` so any unexpected command failure stops the script.
#   * Engine and input existence are checked up front with clear messages.
#   * TEXINPUTS is extended (not overwritten) so the bundled theme .sty resolves
#     without polluting the user's TeX tree, and the trailing ':' keeps the
#     default search path intact.

set -euo pipefail

# --- locate ourselves and the bundled theme assets -------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ASSETS_DIR="$(cd "${SCRIPT_DIR}/../assets" >/dev/null 2>&1 && pwd)"

usage() {
  echo "usage: build.sh <deck.tex>" >&2
  exit 2
}

# --- argument validation ---------------------------------------------------
[ "$#" -eq 1 ] || usage
DECK_TEX="$1"
[ -f "${DECK_TEX}" ] || { echo "error: deck not found: ${DECK_TEX}" >&2; exit 2; }

# --- engine checks ---------------------------------------------------------
command -v xelatex  >/dev/null 2>&1 || { echo "error: xelatex not found on PATH" >&2; exit 2; }
HAVE_LATEXMK=0
command -v latexmk >/dev/null 2>&1 && HAVE_LATEXMK=1

DECK_DIR="$(cd "$(dirname "${DECK_TEX}")" >/dev/null 2>&1 && pwd)"
DECK_BASE="$(basename "${DECK_TEX}" .tex)"

# Make the bundled theme and the deck's own directory discoverable. The leading
# entries are searched first; the trailing ':' preserves the system default.
export TEXINPUTS="${ASSETS_DIR}:${DECK_DIR}:${TEXINPUTS:-}"

cd "${DECK_DIR}"

echo "build: compiling ${DECK_BASE}.tex with XeLaTeX (two passes for frame totals) ..."

set +e
if [ "${HAVE_LATEXMK}" -eq 1 ]; then
  # latexmk runs as many passes as needed (and only as many as needed).
  latexmk -xelatex -interaction=nonstopmode -halt-on-error "${DECK_BASE}.tex" \
    >"${DECK_BASE}.build.out" 2>&1
  STATUS=$?
else
  # Fallback: two explicit passes so the footer frame total is correct.
  xelatex -interaction=nonstopmode -halt-on-error "${DECK_BASE}.tex" \
    >"${DECK_BASE}.build.out" 2>&1 \
    && xelatex -interaction=nonstopmode -halt-on-error "${DECK_BASE}.tex" \
    >>"${DECK_BASE}.build.out" 2>&1
  STATUS=$?
fi
set -e

LOG="${DECK_DIR}/${DECK_BASE}.log"

# --- success ---------------------------------------------------------------
if [ "${STATUS}" -eq 0 ] && [ -f "${DECK_DIR}/${DECK_BASE}.pdf" ]; then
  echo "build: ok -> ${DECK_DIR}/${DECK_BASE}.pdf"
  exit 0
fi

# --- failure triage --------------------------------------------------------
# The overflow guard is the verifier signal; surface the exact slides so the
# layout-pass can re-run on just those.
if [ -f "${LOG}" ] && grep -q "Frame body overflows the safe area" "${LOG}"; then
  echo "build: OVERFLOW — one or more frames exceed the safe area:" >&2
  grep -A2 "Frame body overflows the safe area" "${LOG}" | sed 's/^/  /' >&2
  echo "build: re-run the layout-pass for these slides (or set density=dense)." >&2
  exit 3
fi

# Generic LaTeX failure: show the first real error lines to orient the user.
echo "build: FAILED — XeLaTeX did not produce a PDF (status ${STATUS})." >&2
if [ -f "${LOG}" ]; then
  echo "build: first errors from ${DECK_BASE}.log:" >&2
  grep -n -m5 "^!" "${LOG}" | sed 's/^/  /' >&2 || true
fi
exit 4
