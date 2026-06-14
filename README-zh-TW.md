# paper2beamer

> [English](README.md)

一個受 LLVM IR 啟發的 Claude Code skill，把學術論文（PDF）轉成 Beamer 投影片。它是
**intent-aware**——每次轉換都先詢問這場 talk 的目的與時長——也是 **theme-aware**——
Beamer theme 是一個可抽換的 backend。

圖片用 **Docling 做 deterministic 抽取**（不讓模型憑感覺抓），投影片用 **XeLaTeX 編譯**，
編譯失敗時**在對的層級修復**，而不是從頭重生整份投影片。領域無關：各個領域的研究人員都能用。

## 運作方式

```
[Intent]  ->  [Docling 抽取]  ->  Narrative IR  ==關卡==>  Slide IR  ->  .tex  ->  [xelatex]  ->  修復
                  (圖片)          (故事線)      (人工審查)  (逐張規劃)  (組裝)     (PDF)      (對的層級)
```

三層 Markdown 中介表示（Narrative → Slide → `.tex`）外加一層 theme-as-ISA。唯一的人工審查
關卡就在 Narrative IR 之後——故事線錯了，在這裡修最便宜。關卡之後全部自動化，包含修復迴圈。
完整理念見 [docs/design-philosophy.md](docs/design-philosophy.md) 與
[docs/ir-and-isa.md](docs/ir-and-isa.md)。

## 需求

- **XeLaTeX** 與 **latexmk**（TeX Live）。CJK 投影片另需 `xeCJK` 與 CJK 字型。
- **uv**（執行 Python 工具；Docling 會按需安裝）。
- Claude Code，並以本 repository 作為工作區。

## 快速開始

1. 確認 `xelatex`、`latexmk`、`uv` 都在 PATH 上。
2. 在 Claude Code 裡把 skill 指向一篇論文：

   > 把 `paper.pdf` 轉成投影片——15 分鐘的研討會報告。

3. Skill 會先問你的 **intent**，用 Docling 抽取 PDF，草擬 **Narrative IR**，並在
   **審查關卡**停下來等你確認。
4. 你確認後，它規劃 **Slide IR**、產生並組裝投影片、編譯，並在對的層級修復任何爆頁或錯誤。
5. 成果是 `slides/<paper-slug>/main.pdf`，所有中間產物都在旁邊供檢視。

## Theme

內建的 **Simple** theme（`template/beamerthemeSimple.sty`）已附上預建的 ISA，位於
`paper2beamer/isa/Simple.md`。要用別的 theme，把它的 `beamerthemeXxx.sty` 放進
`template/`，讓 `template/theme.tex` 指向它，再跑一次 **ISA setup** 產生
`isa/<Theme>.md`。Narrative IR 在不同 theme 間原封重用。

## 可選的 setup

- **ISA setup**——教 skill 認識一個新 theme（每個 theme 一次）。
- **Domain setup**——產生 `template/domain.md`，讓 skill 依你的領域校準背景深度與術語
  （每個工作區一次）。略過則維持領域中立。

## 文件

- [TUTORIAL-zh-TW.md](TUTORIAL-zh-TW.md)——端到端教學。
- [docs/design-philosophy.md](docs/design-philosophy.md)——LLVM 類比與設計理念。
- [docs/ir-and-isa.md](docs/ir-and-isa.md)——IR 層級、ISA、provenance 深入說明。
- [docs/VERIFICATION.md](docs/VERIFICATION.md)——驗證方式。
- [CONTRIBUTING.md](CONTRIBUTING.md)——開發流程與規範。

## 授權

MIT——見 [LICENSE.md](LICENSE.md)。
