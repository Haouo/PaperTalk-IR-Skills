# Tutorial — from zero to a Beamer talk

A hand-holding walkthrough: install `paper2beamer`, then turn a real paper PDF
into a slide deck. No prior knowledge of the skill assumed.

If you'd rather have **Claude Code do the install for you**, jump to
[§2a — Let Claude Code install it](#2a-let-claude-code-install-it-easiest) and
paste the prompt.

繁體中文使用者：指令與流程相同；每一步都附有可直接複製的 prompt。

---

## 0. What you'll end up with

```
build/yourpaper/
├─ ir.v0.json … ir.v4.json   # the intermediate representation, one file per stage
├─ figures/*.png             # your paper's ORIGINAL figures, cropped by Docling
├─ deck.tex                  # the generated LaTeX
└─ deck.pdf                  # the finished 16:9 Beamer talk
```

You drive the whole thing from a conversation with Claude Code. The skill asks
what talk you're giving, then builds a deck tailored to it.

---

## 1. Prerequisites (and how to check each)

You need three things. Run these checks first — copy the whole block into a
terminal:

```bash
# 1) uv — runs Docling in an isolated environment
uv --version            || echo "MISSING: uv"

# 2) XeLaTeX — compiles the deck (part of TeX Live)
xelatex --version | head -1   || echo "MISSING: xelatex"

# 3) Claude Code — the agent that runs the skill
claude --version        || echo "MISSING: claude code"
```

You do **not** need to install Docling yourself — `uv` fetches it on demand the
first time the frontend runs (≈ a few hundred MB of models, one time).

### If something is missing

| Missing | Fastest fix |
|---|---|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (see <https://docs.astral.sh/uv/>) |
| `xelatex` | Install TeX Live. macOS: `brew install --cask mactex-no-gui`. Debian/Ubuntu: `sudo apt install texlive-xetex texlive-latex-extra`. For Chinese decks also add `texlive-lang-cjk` + a CJK font (e.g. Noto Sans CJK). |
| `claude` | <https://claude.com/claude-code> |

> **Prefer to let Claude Code sort dependencies out?** Paste this prompt into a
> Claude Code session opened in any directory:
>
> > Check whether `uv`, `xelatex`, and `latexmk` are installed and on my PATH.
> > For anything missing, detect my OS and tell me the exact install command (and
> > run it if it's safe and non-interactive). Don't install a full TeX Live if a
> > smaller XeLaTeX subset will do. Finish by re-running the checks and showing me
> > the versions.

---

## 2. Install the skill

The skill is the `paper2beamer/` directory in this repository. Claude Code
discovers personal skills in `~/.claude/skills/<name>/`, so "installing" means
making `~/.claude/skills/paper2beamer` point at this repo's `paper2beamer/`.

### 2a. Let Claude Code install it (easiest)

Open Claude Code **inside this repository** and paste:

> Install the `paper2beamer` skill from this repo for me:
> 1. Symlink `~/.claude/skills/paper2beamer` to `./paper2beamer` (create
>    `~/.claude/skills` if needed; if a `paper2beamer` already exists there, show
>    me what it is before replacing it).
> 2. Verify `uv`, `xelatex`, and `latexmk` are available.
> 3. Run the skill's fast test suite and paste the summary:
>    `cd paper2beamer && uv run --with pytest python -m pytest tests/ -c tests/pytest.ini -q`
> 4. Tell me to start a new Claude Code session so the skill is picked up.

That's it — skip to [§3](#3-your-first-deck).

### 2b. Manual install

A **symlink** keeps the skill in sync with the repo (recommended):

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/paper2beamer" ~/.claude/skills/paper2beamer
```

Prefer a **copy** if you want it frozen and independent of the repo:

```bash
mkdir -p ~/.claude/skills
cp -r "$(pwd)/paper2beamer" ~/.claude/skills/paper2beamer
```

Or install it **per-project** instead of globally — put it under a project's
`.claude/skills/` the same way.

### Verify the install

```bash
ls ~/.claude/skills/paper2beamer/SKILL.md        # should exist
cd ~/.claude/skills/paper2beamer
uv run --with pytest python -m pytest tests/ -c tests/pytest.ini -q   # expect: passed
```

Then **start a new Claude Code session** — skills are discovered at session
start. In the new session you can confirm it's available by asking:
*"Do you have a paper2beamer skill? What does it do?"*

---

## 3. Your first deck

Have a paper PDF ready (born-digital, not a scan). Open Claude Code in a working
directory where you want the `build/` folder to appear, with the PDF accessible.

### Step 1 — kick it off

Paste a prompt like:

> Use the paper2beamer skill to turn `attention.pdf` into a **20-minute
> journal-club talk** for NLP grad students. Emphasise the method and the
> results.

The skill recognises the request and starts the pipeline.

### Step 2 — the frontend runs (Docling)

You'll see it run the Docling frontend:

```
uv run --with docling python .../frontend_docling.py --pdf attention.pdf --out build/attention/
frontend: wrote build/attention/ir.v0.json  (8 sections, 5 figures)
```

The first run downloads models (one time, a few minutes). After that it's fast.
Your paper's original figures are now in `build/attention/figures/`.

### Step 3 — Gate ① : intent

The skill interviews you briefly — occasion, duration, audience, emphasis,
depth, language — and writes that into the IR's `intent` block. You already
answered most of it in your opening prompt, so this is usually a quick confirm:

> Looks right — go ahead. (Make it **English**, **balanced** depth.)

### Step 4 — Gate ② : the story arc

After the content and narrative passes, the skill shows you the **story arc** —
the beats, their one-line headlines, and the time budget. This is where you
shape the talk. Example responses:

> Drop the related-work beat, and make the "speedup" the climax. Otherwise good.

It rewrites `ir.v2.json` and re-checks the timing.

### Step 5 — Gate ③ : the slide plan

After the figure and layout passes, you get the **slide plan** — which figures
land where, which blocks, how many slides. For example:

> Slide 6 is too busy — split the method figure onto its own slide.

### Step 6 — build

The skill emits `deck.tex` and compiles it. If a slide overflows, it
re-lays-out that slide automatically (once) and rebuilds. You end with:

```
build: ok -> build/attention/deck.pdf
```

### Step 7 — look at it

```bash
# macOS
open build/attention/deck.pdf
# Linux
xdg-open build/attention/deck.pdf
```

---

## 4. Going faster, and iterating

You're not locked into the three gates.

**Fast mode — one shot, no stops:**

> Just build the deck end-to-end, don't stop to ask me.

**Re-run a single stage** (like `opt -run-pass`) when you want to change one
thing without redoing everything:

> Redo only the figure choices — prefer the architecture diagram over the loss
> curves.

> Re-run the layout pass with denser slides; the deck is one slide too long.

**Hand-edit the IR** — it's just JSON. Open `build/attention/ir.v2.json`, tweak
a headline, then:

> I edited ir.v2.json by hand. Continue from the figure pass.

Because every stage is a versioned file, nothing downstream is lost — the skill
picks up from where you changed things.

---

## 5. Chinese / bilingual decks

Ask for the language up front:

> 把 `論文.pdf` 做成 30 分鐘的 lab meeting 簡報，**用中文**。

For CJK you need TeX Live's `langcjk` collection and a CJK font (e.g. Noto Sans
CJK). The Simple theme auto-loads `xeCJK` under XeLaTeX when present; if it's
missing, Latin text still renders and the build warns about CJK. See
`paper2beamer/assets/beamerthemeSimple-manual.md` for the details.

---

## 6. When something goes wrong

| Symptom | What it means / fix |
|---|---|
| *"Docling is not importable"* | Run the frontend through `uv` (the skill already does). Your system `python` may not see Docling; `uv run --with docling` fixes it. |
| Build stops with **exit code 3** | A slide overflows. The skill re-lays-out once automatically; if it persists, tell it to trim that slide or use `density=dense`. |
| A figure shows a **"[missing figure]"** box | Docling couldn't extract that one image; the deck still builds. Re-run the frontend, or drop a replacement PNG into `build/<paper>/figures/`. |
| *"no text sections extracted"* warning | The PDF is probably scanned/image-only. OCR is unreliable — use a born-digital PDF. |
| The title slide shows the **filename** | The paper had no clear title heading; tell the skill the real title and it'll set it in the IR. |

Deeper diagnostics, exit codes, and the test layers are in
[`paper2beamer/tests/VERIFICATION.md`](./paper2beamer/tests/VERIFICATION.md).

---

## 7. Prompt cheat-sheet

Copy-paste starting points:

| Goal | Prompt |
|---|---|
| Install via Claude Code | *"Install the paper2beamer skill from this repo: symlink it into `~/.claude/skills/`, verify uv/xelatex/latexmk, run the fast tests, and tell me to restart."* |
| Standard talk | *"Use paper2beamer to make a 15-minute conference talk from `paper.pdf`, emphasis on results."* |
| Fast, no gates | *"paper2beamer `paper.pdf` → deck, one-shot, don't stop to ask."* |
| Thesis defense | *"Make a 45-minute thesis-defense deck from `paper.pdf`, deep-dive depth, for my committee."* |
| Re-pick figures | *"Re-run only the figure pass; show the system diagram, not the tables."* |
| Shorten | *"Re-run the layout pass denser — cut it to 18 slides."* |
| Chinese | *"把 `paper.pdf` 做成 20 分鐘的 journal club 簡報，用中文。"* |

---

## What's next

- Read the [README](./README.md) for the LLVM analogy and architecture.
- Read [`paper2beamer/references/`](./paper2beamer/references/) to understand the
  IR and each pass — handy if you want to hand-edit the IR.
- Want to change how decks look or add a pass? See [CONTRIBUTING](./CONTRIBUTING.md).
