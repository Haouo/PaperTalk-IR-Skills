# Tutorial: a paper to a deck, end to end

> [繁體中文](TUTORIAL-zh-TW.md)

This walkthrough converts one paper into a compiling Beamer deck and shows what
each stage produces, including how a deliberate overflow is repaired at the slide
level and how to swap the theme.

## Install (once)

The easiest way is to hand the prompt below to Claude Code and let it do the setup:

> Install the paper2beamer skill for me:
> 1. Clone `git@github.com:Haouo/PaperTalk-IR-Skills.git` into `~/workspace/` (HTTPS is fine too).
> 2. Symlink the repo's `paper2beamer/` directory to `~/.claude/skills/paper2beamer` so Claude Code can find the skill.
> 3. Check that `xelatex`, `latexmk`, and `uv` are installed, and tell me how to add any that are missing.

Start a fresh Claude Code session afterwards and `paper2beamer` will appear among
the available skills.

To do it by hand, it is three steps:

```bash
# 1. Get the repo
git clone git@github.com:Haouo/PaperTalk-IR-Skills.git ~/workspace/papertalk-ir-skills

# 2. Symlink it into the skills folder so Claude Code discovers the skill
ln -s ~/workspace/papertalk-ir-skills/paper2beamer ~/.claude/skills/paper2beamer

# 3. Confirm the tools are present
xelatex --version && latexmk --version && uv --version
```

`xelatex` and `latexmk` come from TeX Live; `uv` runs the Python tooling (Docling
installs itself on first use). Once all three are present you are ready.

The steps below assume you are at the root of the cloned repo (the skill's
workspace) with those three tools on your PATH.

## 1. State your intent

Ask the skill to convert your paper and say what the talk is for:

> Turn `~/papers/attention.pdf` into slides — a 15-minute conference talk.

The skill captures the intent and derives a page budget (15 minutes → about
12–18 content slides) and a depth/tone profile. If you had said "length
unbounded, just convey the content", the page-count check would be disabled
instead.

## 2. Ingest with Docling

The skill runs the deterministic frontend:

```bash
uv run --project paper2beamer --group ingest \
  paper2beamer/scripts/frontend_docling.py ~/papers/attention.pdf --out slides/attention
```

Result: `slides/attention/paper-content.md` and `slides/attention/figures/`
(`figure-001.png`, …). These are the only source the later stages read — the raw
PDF is not consulted again, and no figure is ever invented.

## 3. Review the Narrative IR (the gate)

The skill drafts `slides/attention/narrative.md` — the story, one beat at a time,
with a key-message, a time budget, and supporting figures each. It then **pauses**
and presents the outline. This is the single human checkpoint.

Suppose the motivation beat is too long. Tell the skill:

> Merge the two background beats into one and give the results beat more time.

It edits `narrative.md` and re-presents. When the story is right, you approve, and
the pipeline runs the rest automatically.

## 4. Slide IR and emission

The skill writes `slides/attention/slides.md` (each slide linked to a beat,
blocks chosen only from the Simple theme's ISA), then a build manifest under
`slides/attention/build/` (`preamble.tex`, `order.txt`, `frames/S*.tex`), and
assembles the deck:

```bash
python3 paper2beamer/scripts/emit_beamer.py \
  --manifest slides/attention/build --out slides/attention
```

This produces `slides/attention/main.tex` — every frame preceded by a
`% slide:Sxx beat:Nyy` provenance comment — and `slides/attention/provenance.json`.

## 5. Compile, and watch repair fix an overflow

```bash
bash paper2beamer/scripts/build.sh slides/attention
python3 paper2beamer/scripts/latex_log.py slides/attention/main.log
```

The deck is built with `overflowguard=on`. Suppose slide `S07` is overloaded; the
log parser reports:

```json
{ "compile_ok": false, "errors": [], "overflows": [7], "page_count": 16 }
```

`provenance.json` maps content frame 7 to slide `S07`, so the repair router routes
this to the **slide** level. The skill revises only `S07` in `slides.md` (splitting
it into two slides), re-emits just that fragment, and rebuilds. The narrative is
untouched. If the same slide overflowed twice more, the router would escalate to
the narrative level and shrink the beat instead.

When the log is clean and the page count is within budget, the deck is done:

```
slides/attention/main.pdf
```

## 6. Swap the theme

To use a different theme, drop its `beamerthemeMagazine.sty` into `template/`,
point `template/theme.tex` at it, and ask the skill to run **ISA setup** once:

> Set up the ISA for `template/beamerthemeMagazine.sty`.

This writes `isa/Magazine.md`. Re-emitting the same deck now targets the new
theme — the Narrative IR is reused unchanged; only the Slide IR and emission adapt
to the new ISA.

## 7. (Optional) Domain setup

To calibrate background depth and terminology to your field, ask once per
workspace:

> Set up the domain profile from `~/papers/attention.pdf`.

The skill drafts `template/domain.md` from the paper and asks a few questions
about your audience. From then on, the Narrative pass uses it. Skip this and the
skill stays field-neutral.
