# 教學：從論文到投影片，端到端

> [English](TUTORIAL.md)

本教學把一篇論文轉成可編譯的 Beamer 投影片，並說明每個階段的產物，包含一個刻意製造的爆頁
如何在 slide 層級被修復，以及如何抽換 theme。指令假設你在 repository 根目錄，且
`xelatex`、`latexmk`、`uv` 都在 PATH 上。

## 1. 說明你的 intent

請 skill 轉換論文，並說明這場 talk 的用途：

> 把 `~/papers/attention.pdf` 轉成投影片——15 分鐘的研討會報告。

Skill 會擷取 intent 並推導頁數預算（15 分鐘 → 約 12–18 張內容投影片）與 depth/tone profile。
如果你說「長度不限，只要表達內容」，頁數檢查就會改為停用。

## 2. 用 Docling 抽取

Skill 執行 deterministic 前端：

```bash
uv run --project paper2beamer --group ingest \
  paper2beamer/scripts/frontend_docling.py ~/papers/attention.pdf --out slides/attention
```

產物：`slides/attention/paper-content.md` 與 `slides/attention/figures/`
（`figure-001.png`…）。後續階段只讀這些——不再讀原始 PDF，也絕不憑空生出圖。

## 3. 審查 Narrative IR（關卡）

Skill 草擬 `slides/attention/narrative.md`——逐個 beat 的故事線，每個 beat 都有 key-message、
時間預算與支撐圖。接著它會**停下來**呈現大綱。這就是唯一的人工關卡。

假設 motivation 這段太長，告訴 skill：

> 把兩個背景 beat 合併成一個，並給 results 那段多一點時間。

它會修改 `narrative.md` 並重新呈現。故事對了，你就核可，pipeline 其餘部分自動執行。

## 4. Slide IR 與 emission

Skill 寫出 `slides/attention/slides.md`（每張投影片連到一個 beat，block 只從 Simple theme 的
ISA 挑選），接著在 `slides/attention/build/` 下寫出 build manifest
（`preamble.tex`、`order.txt`、`frames/S*.tex`），然後組裝投影片：

```bash
python3 paper2beamer/scripts/emit_beamer.py \
  --manifest slides/attention/build --out slides/attention
```

這會產生 `slides/attention/main.tex`——每個 frame 前都有 `% slide:Sxx beat:Nyy` provenance
註解——以及 `slides/attention/provenance.json`。

## 5. 編譯，並看修復如何處理爆頁

```bash
bash paper2beamer/scripts/build.sh slides/attention
python3 paper2beamer/scripts/latex_log.py slides/attention/main.log
```

投影片以 `overflowguard=on` 編譯。假設 `S07` 內容過多，log 解析回報：

```json
{ "compile_ok": false, "errors": [], "overflows": [7], "page_count": 16 }
```

`provenance.json` 把內容第 7 張對應到 slide `S07`，於是 repair router 把它路由到 **slide**
層級。Skill 只修改 `slides.md` 裡的 `S07`（拆成兩張），只重新 emit 那個 fragment，再重建。
Narrative 原封不動。若同一張再爆頁兩次，router 會升級到 narrative 層級、改為縮減該 beat。

當 log 乾淨且頁數落在預算內，投影片完成：

```
slides/attention/main.pdf
```

## 6. 抽換 theme

要用別的 theme，把它的 `beamerthemeMagazine.sty` 放進 `template/`，讓 `template/theme.tex`
指向它，再請 skill 跑一次 **ISA setup**：

> 為 `template/beamerthemeMagazine.sty` 建立 ISA。

這會寫出 `isa/Magazine.md`。重新 emit 同一份投影片就會以新 theme 為目標——Narrative IR 原封
重用，只有 Slide IR 與 emission 依新 ISA 調整。

## 7.（可選）Domain setup

要依你的領域校準背景深度與術語，每個工作區跑一次：

> 用 `~/papers/attention.pdf` 建立 domain profile。

Skill 會從論文草擬 `template/domain.md`，並針對你的受眾問幾個問題。此後 Narrative pass 都會
使用它。略過則 skill 維持領域中立。
