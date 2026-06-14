# Pass: compile & verify

Build the deck and read the signals. This is deterministic — trust the scripts,
not your reading of the `.tex`.

## Build

```bash
bash paper2beamer/scripts/build.sh slides/<slug>
```

`build.sh` runs `latexmk -xelatex` (as many passes as needed for a correct frame
total), puts the theme on `TEXINPUTS`, and leaves `main.log` in the deck dir.

## Read the signals

```bash
python3 paper2beamer/scripts/latex_log.py slides/<slug>/main.log
```

This prints `compile_ok`, `errors`, `overflows` (slide numbers), and
`page_count`.

## Decide

The deck is **done** when ALL hold:

- `compile_ok` is true,
- `overflows` is empty,
- the intent page budget is `none` (unbounded) OR `page_count` is within
  `[min_pages, max_pages]`.

If done, report the path to `slides/<slug>/main.pdf` and stop.

Otherwise, go to `repair.md` with the signals, `provenance.json`, the intent
budget, and the per-slide attempt counts so far.
