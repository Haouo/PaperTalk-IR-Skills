# 教學：從論文到投影片，一次走完

> [English](TUTORIAL.md)

這份教學會帶你把一篇論文轉成可以編譯的 Beamer 投影片，並說明每個階段會產生什麼，包括故意
弄出一個爆頁、看它怎麼在 slide 這層被修掉，還有怎麼抽換 theme。以下指令都假設你人在
repository 根目錄，而且 `xelatex`、`latexmk`、`uv` 都在 PATH 上。

## 1. 說明你的 intent

請 skill 轉換論文，順便講清楚這場報告要做什麼：

> 把 `~/papers/attention.pdf` 做成投影片，15 分鐘的研討會報告。

Skill 會把這個 intent 記下來，估出頁數預算（15 分鐘大概 12–18 張內容投影片）和 depth/tone
profile。如果你改說「長度不限，把內容講清楚就好」，頁數檢查就會關掉。

## 2. 用 Docling 抽取

Skill 會跑 deterministic 的前端：

```bash
uv run --project paper2beamer --group ingest \
  paper2beamer/scripts/frontend_docling.py ~/papers/attention.pdf --out slides/attention
```

產物是 `slides/attention/paper-content.md` 和 `slides/attention/figures/`（`figure-001.png`
之類）。後面的階段只讀這些東西，不會再去碰原始 PDF，也不會自己生出不存在的圖。

## 3. 審查 Narrative IR（關卡）

Skill 會先擬好 `slides/attention/narrative.md`，也就是一個一個 beat 排出來的故事線，每個 beat
都有自己的 key-message、時間預算和要搭配的圖。寫完之後它會**停下來**把大綱攤給你看。這是
整個流程裡唯一需要你介入的地方。

假設 motivation 那段太長，你就跟 skill 說：

> 把兩個背景 beat 併成一個，然後 results 那段多給一點時間。

它會去改 `narrative.md` 再給你看一次。等故事順了、你點頭，剩下的 pipeline 就自己跑完。

## 4. Slide IR 和 emission

Skill 會寫出 `slides/attention/slides.md`（每張投影片都掛到某個 beat 上，block 只從 Simple
theme 的 ISA 裡挑），接著在 `slides/attention/build/` 底下寫出 build manifest（`preamble.tex`、
`order.txt`、`frames/S*.tex`），然後把投影片組起來：

```bash
python3 paper2beamer/scripts/emit_beamer.py \
  --manifest slides/attention/build --out slides/attention
```

這會產生 `slides/attention/main.tex`，每個 frame 前面都帶一行 `% slide:Sxx beat:Nyy` 的
provenance 註解，另外還有 `slides/attention/provenance.json`。

## 5. 編譯，看修復怎麼處理爆頁

```bash
bash paper2beamer/scripts/build.sh slides/attention
python3 paper2beamer/scripts/latex_log.py slides/attention/main.log
```

投影片是用 `overflowguard=on` 編的。假設 `S07` 塞太多東西，log 解析會回報：

```json
{ "compile_ok": false, "errors": [], "overflows": [7], "page_count": 16 }
```

`provenance.json` 會把內容第 7 張對到 slide `S07`，所以 repair router 把這件事丟到 **slide**
這一層。Skill 只改 `slides.md` 裡的 `S07`（把它拆成兩張），只重新 emit 那一個 fragment，再
重編一次。Narrative 完全沒動到。要是同一張又連爆兩次，router 就會升一層到 narrative，改成把
那個 beat 縮掉。

等 log 乾淨、頁數也落在預算裡，投影片就完成了：

```
slides/attention/main.pdf
```

## 6. 抽換 theme

想換 theme，就把它的 `beamerthemeMagazine.sty` 放進 `template/`，把 `template/theme.tex`
指過去，再請 skill 跑一次 **ISA setup**：

> 幫 `template/beamerthemeMagazine.sty` 建一份 ISA。

這會寫出 `isa/Magazine.md`。同一份投影片重新 emit 一次就會改打新的 theme，Narrative IR 直接
沿用，只有 Slide IR 和 emission 會照新的 ISA 調整。

## 7.（可選）Domain setup

想讓背景深度和術語貼合你的領域，每個工作區跑一次就好：

> 用 `~/papers/attention.pdf` 建一份 domain profile。

Skill 會從論文先擬一版 `template/domain.md`，再針對你的受眾問幾個問題。之後每次 Narrative
pass 都會參考它。不做也行，skill 就維持中立。
