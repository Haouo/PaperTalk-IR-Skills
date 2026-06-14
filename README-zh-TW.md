# papertalk-ir-skills

**把論文 PDF 編譯成 LaTeX Beamer 簡報——就像編譯器把原始碼編成執行檔。**

`paper2beamer` 是一個 [Claude Code](https://claude.com/claude-code) 技能（skill），
能將學術論文編譯成乾淨的 16:9 Beamer 投影片。它借用 LLVM 的架構：由確定性的
**frontend** 擷取結構化內容與論文的*原始圖表*，接著由一連串語意化的
**optimization passes** 改寫一份版本化的**中間表示（IR）**，最後由確定性的
**backend** 產生並編譯 `.tex`。

整個流程是 **Intent-Aware**（會先問你要做什麼樣的演講，再據此量身打造投影片）
與 **Theme-Aware**（backend 精通內建 *Simple* 主題的語彙，且絕不讓單頁溢出）。

English： [README.md](./README.md)

---

## 為什麼是「IR-inspired」？

一般的「PDF → 投影片」工具是個黑盒子。這個工具則是一條**可檢視、可編輯、可分段
重跑**的管線，就像 `clang`／`opt`：

| LLVM | paper2beamer |
|---|---|
| Frontend（原始碼 → AST → IR） | Docling：PDF → `ir.v0` ＋裁切的原始圖表 |
| `target triple`／`-O2` | **intent block**（場合、時長、受眾、重點…）驅動每個 pass |
| Optimization passes | `content` → `narrative` → `figure` → `layout` |
| Pass manager（`opt`） | 技能負責編排 passes，含審查閘門與 `-run-pass` |
| SSA（不可變值） | 版本化 IR `ir.v0 … ir.v4`；每個 pass 寫出新的、可 diff 的版本 |
| Target backend 懂 ISA | backend 懂 Simple 主題的 frames／blocks |
| 編譯＋驗證 | `latexmk -xelatex` 編出 PDF；主題的 overflow guard 就是 verifier |

```
PDF ─[frontend: Docling]→ ir.v0 ─[intent 訪談]→ ir.v0
   → content-pass → ir.v1 → narrative-pass → ir.v2
   → figure-pass → ir.v3 → layout-pass → ir.v4
   ─[backend: emit]→ deck.tex ─[build]→ deck.pdf
```

IR 是唯一的事實來源。因為每個 pass 都寫出新的 `ir.vN.json`，你可以打開任一階段、
做 diff、手動修改，再只重跑後續的 passes。

---

## 你會得到什麼

- **原圖原封不動。** Docling 裁切論文真正的圖與表；figure-pass 負責*挑選*要呈現
  哪些，backend 原樣嵌入。不重畫、不杜撰。
- **是一場演講，不是傾倒。** narrative-pass 把論文壓縮成符合你時間預算的敘事弧；
  layout-pass 將它對應到語意化的 blocks（結果 → 綠、警示 → 金）並套上 Simple 主題。
- **編得出來的投影片。** backend 是純渲染器，含嚴格驗證與 LaTeX 跳脫；build 階段
  以 XeLaTeX 編譯，若有任何溢出會明確失敗並指出是哪一頁。
- **主導權在你。** 預設三個審查閘門；或一鍵到底的「fast」模式；或只重跑單一 pass
  來迭代。

---

## 環境需求

| 工具 | 用途 | 備註 |
|---|---|---|
| [`uv`](https://docs.astral.sh/uv/) | 在隔離環境執行 Docling frontend | 建議；避免污染系統 Python |
| **Docling** ≥ 2.99 | PDF 解析＋圖表擷取 | 透過 `uv run --with docling` 即時佈建 |
| **XeLaTeX**（TeX Live） | 編譯投影片（`fontspec`、選用 `xeCJK`） | 有 `latexmk` 就用它，否則跑兩遍 `xelatex` |
| Claude Code | 執行技能 | passes 由模型驅動 |

中文（CJK）投影片另需 TeX Live `langcjk` 套件集與一套 CJK 字型（如 Noto Sans
CJK）——詳見 `paper2beamer/assets/beamerthemeSimple-manual.md`。

---

## 安裝

把技能放到 Claude Code 會探索技能的位置（例如 `~/.claude/skills/`），或留在本
儲存庫中並把技能路徑指向這裡。技能就是 `paper2beamer/` 目錄；它是自包含的（已在
`assets/` 內附主題）。

```
~/.claude/skills/paper2beamer  ->  (本儲存庫)/paper2beamer
```

---

## 快速開始（在 Claude Code 中）

直接開口：

> 「把 `attention.pdf` 做成 20 分鐘的 journal club 演講。」

技能會：

1. 執行 Docling **frontend**，產出 `build/attention/ir.v0.json` 與
   `build/attention/figures/*.png`。
2. 簡短**訪談你**（場合、時長、受眾、重點、深度、語言），並凍結進 IR 的 `intent`
   block——**閘門 ①**。
3. 跑 **content** 與 **narrative** pass，接著把敘事弧給你看——**閘門 ②**。
4. 跑 **figure** 與 **layout** pass，接著把投影片計畫給你看——**閘門 ③**。
5. 產生 `deck.tex` 並編出 `deck.pdf`，對任何溢出的頁面自動重排一次。

說「直接幫我做好」可略過閘門（**fast 模式**）；說「重做選圖」可只重跑單一 pass
（**`-run-pass`**）。

---

## 手動執行確定性階段

這些腳本也能單獨使用（方便除錯或寫腳本）：

```bash
# Frontend — PDF -> ir.v0 ＋ figures（用 uv 隔離）
uv run --with docling python paper2beamer/scripts/frontend_docling.py \
    --pdf paper.pdf --out build/paper/

# ……模型接著跑 content/narrative/figure/layout pass，寫出
#    build/paper/ir.v1.json … ir.v4.json ……

# Backend — ir.v4 -> deck.tex（純粹、確定性）
python paper2beamer/scripts/emit_beamer.py \
    --ir build/paper/ir.v4.json --out build/paper/deck.tex

# Build — deck.tex -> deck.pdf（XeLaTeX；overflow guard ＝ verifier）
bash paper2beamer/scripts/build.sh build/paper/deck.tex
```

`build.sh` 結束碼：`0` 成功 · `2` 用法／環境錯 · `3` **溢出**（對回報的頁面重跑
layout-pass）· `4` 其他 LaTeX 錯誤。

---

## IR 與 passes

完整契約放在 `paper2beamer/references/`：

- [`ir-schema.md`](./paper2beamer/references/ir-schema.md)——IR 每個欄位。
- [`ir_schema.json`](./paper2beamer/references/ir_schema.json)——可機器檢查的 JSON
  Schema（對應 `scripts/ir_common.py` 內實際執行的驗證器）。
- [`pass-contracts.md`](./paper2beamer/references/pass-contracts.md)——每個 pass 的
  輸入／輸出檢查清單。
- [`simple-theme-isa.md`](./paper2beamer/references/simple-theme-isa.md)——
  layout-pass 規劃時依據的主題「指令集」。

程式中強制的關鍵不變量：

- IR 是**累積式**的：每個 pass 只新增自己的欄位，永不刪除前一個 pass 的產物。
  `meta.source_pdf` 與 `intent` 一經寫入即凍結。
- **claims 永不刪除、只排序**（`salience`）；由 narrative-pass 從中*挑選*。
- **每個 beat 至多一張主圖**（method／overview beat 可加一張次圖）。
- 證據必須能溯源到論文——content-pass 不能杜撰數字。

---

## 目錄結構

```
papertalk-ir-skills/
├─ paper2beamer/                  # 技能本體
│  ├─ SKILL.md                    # pass-manager 編排（大腦）
│  ├─ scripts/
│  │  ├─ ir_common.py             # IR 契約：驗證、原子 IO、LaTeX 跳脫
│  │  ├─ frontend_docling.py      # PDF -> ir.v0 ＋ figures（Docling）
│  │  ├─ emit_beamer.py           # ir.v4 -> deck.tex（純渲染器）
│  │  └─ build.sh                 # deck.tex -> deck.pdf（XeLaTeX ＋ verifier）
│  ├─ references/                 # IR schema、主題 ISA、pass 契約
│  ├─ assets/                     # 內附的 Simple 主題（.sty ＋ 手冊）
│  └─ tests/                      # 單元＋golden＋schema＋整合＋e2e
├─ template/                      # workspace 主題原始檔與 domain.md
├─ docs/superpowers/specs/        # 設計規格書
├─ README.md / README-zh-TW.md
├─ CONTRIBUTING.md
└─ LICENSE.md
```

---

## 驗證

測試套件分層設計：快速檢查到處都能跑，較重的會在工具缺席時乾淨地略過。完整說明：
[`paper2beamer/tests/VERIFICATION.md`](./paper2beamer/tests/VERIFICATION.md)。

```bash
cd paper2beamer
# 快速、無外部依賴的套件（單元＋golden＋schema＋frontend helpers＋整合）：
uv run --with pytest python -m pytest tests/ -c tests/pytest.ini -q

# 選用的實機端對端（會下載 Docling 模型，需要 xelatex）：
uv run --with pytest --with docling python -m pytest tests/ -c tests/pytest.ini -m e2e -q
```

---

## 疑難排解

- **「Docling is not importable」**——請透過 `uv` 執行 frontend（錯誤訊息會給出
  確切指令）。系統的 `python` 可能看不到用 `pip` 裝的 Docling；`uv run --with
  docling` 可繞過。
- **build 以結束碼 3（溢出）結束**——某頁太滿。技能會自動重排一次；若仍存在，請
  精簡該頁或設 `density=dense`。
- **某張圖顯示「[missing figure]」框**——Docling 無法擷取該影像；build 仍會成功。
  重跑 frontend 或補上該資產。
- **掃描／純影像 PDF**——frontend 在找不到文字時會警告；OCR 結果不可靠，請優先使用
  原生數位 PDF。

---

## 授權

[MIT](./LICENSE.md)。內附的 *Simple* Beamer 主題是自包含的（無 logo 或第三方品牌）。
