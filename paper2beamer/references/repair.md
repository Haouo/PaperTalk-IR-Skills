# Pass: repair-at-the-right-level

The core idea: a build signal is fixed at the **lowest IR level that can resolve
it**, editing only the one unit it traces to — never by regenerating the deck.

## Get the directives

Feed the signals + provenance + intent budget + attempt counts to the router:

```bash
# Conceptually: route(signals, provenance.json, budget, attempts) -> directives
```

You may call `paper2beamer/scripts/repair_router.py` for the directives, or apply
the routing table directly:

| Signal | Repair level | What to edit |
|---|---|---|
| compile error (undefined cmd / syntax) | `tex` | only `build/frames/<Sxx>.tex` for the frame whose line range covers the error (from `provenance.json`) |
| frame overflow on `S07` | `slide` | revise slide `S07` in `slides.md` (split / trim / move detail to a later slide), then re-emit only `S07`'s fragment |
| total pages over/under the budget | `narrative` | revise beats in `narrative.md` (cut/merge to shrink, or expand), re-plan affected slides, re-emit |

## Apply, then rebuild

1. Make the surgical edit at the directed level only.
2. If you edited a fragment, re-run `emit_beamer.py` to reassemble `main.tex` +
   `provenance.json`.
3. Re-run `build.sh` and `latex_log.py` (back to `compile-verify.md`).

## Escalation and stop-loss (defensive)

- Track a per-slide attempt count. After **2** failed trims of the same slide,
  the router escalates that overflow to the `narrative` level (cut/shrink the
  beat) instead of trimming a fourth time.
- Enforce a **total repair budget of 6 rebuilds** per deck. If signals remain
  when the budget is spent, STOP: write `slides/<slug>/repair-report.md` listing
  the unresolved signals and the path to the best-effort `main.pdf`, and tell the
  user. Do not loop forever.

## Never

- Never regenerate the whole deck from scratch.
- Never edit a higher level than the signal requires (e.g. do not rewrite the
  narrative for a single LaTeX typo).
