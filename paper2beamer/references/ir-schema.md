# IR schema (human reference)

The IR is a **single accumulative JSON document**, versioned per pass
(`ir.v0.json` … `ir.v4.json`). Each pass writes a new version (SSA spirit) so any
stage can be diffed or re-run. The **authoritative, enforced** contract is
`scripts/ir_common.py::validate_ir`; `ir_schema.json` is a JSON-Schema mirror for
editors and external tooling; this file is the readable overview.

A test (`tests/test_schema_consistency.py`) asserts the three sources agree.

## Top level

| Field | Owned by | Notes |
|---|---|---|
| `meta` | every pass | `schema`, `ir_version`, `source_pdf` (frozen), `produced_by_pass` |
| `intent` | intent-intake | frozen after first write; read by every later pass |
| `paper` | frontend | `title`, `authors[]`, `venue`, `abstract`, `sections[]`, `references[]` |
| `figures` | frontend | registry of cropped originals |
| `claims` | content-pass | atomic assertions with salience |
| `story` | narrative-pass | ordered beats; `story[].figures` added by figure-pass |
| `slides` | layout-pass | concrete Simple-theme frame sequence |

## `meta`

```jsonc
{ "schema": "1.0", "ir_version": "v2",
  "source_pdf": "/abs/path/paper.pdf", "produced_by_pass": "narrative-pass" }
```

## `intent` (frozen once written)

```jsonc
{ "occasion": "journal-club",   // conference | journal-club | defense | lab-meeting
  "duration_min": 30,           // > 0
  "audience": "NLP graduate students",
  "emphasis": ["method", "results"],
  "language": "en",             // en | zh | bilingual
  "depth": "balanced",          // overview | balanced | deep-dive
  "domain_ref": "template/domain.md" }
```

## `paper.sections[]`

```jsonc
{ "id": "sec4", "title": "Method", "level": 1, "text": "full section text ..." }
```
`id` is unique. `text` is the verbatim section body (the content-pass quotes from
it; it must never invent evidence absent here).

## `figures[]`

```jsonc
{ "id": "fig3", "kind": "figure",       // figure | table | equation
  "page": 5, "path": "figures/fig3.png", // relative to the IR file
  "caption": "Figure 3: ...",            // original caption (may be empty)
  "referenced_in": ["sec4"] }            // best-effort back-links
```

## `claims[]`

```jsonc
{ "id": "c1", "section": "sec4",
  "type": "result",   // problem|method|result|contribution|limitation|background
  "statement": "Method X improves BLEU by 3.2 over the baseline.",
  "evidence": ["+3.2 BLEU (Table 2)"],
  "figure_refs": ["fig3"],   // must exist in figures[]
  "salience": 0.9 }          // [0,1]; intent-aware importance
```

## `story[]`

```jsonc
{ "id": "u3", "role": "result",  // hook|problem|gap|idea|method|result|takeaway|closing
  "headline": "The decoder change is what buys the speedup.",
  "claim_refs": ["c1", "c2"],    // must exist in claims[]
  "figures": [                    // added by figure-pass
    { "figure_id": "fig3", "role": "primary" } ],  // <= 1 primary per beat
  "est_minutes": 2.0,
  "notes": "speaker-note seed" }
```

## `slides[]`

```jsonc
[
  { "frame_type": "titleframe" },
  { "frame_type": "frame", "title": "Result", "story_ref": "u3",
    "body": [
      { "block": "exampleblock", "title": "Headline number",
        "items": ["+3.2 BLEU", "2x faster decoding"] },
      { "figure": "fig3", "caption": "...", "width": "0.7\\textwidth" }
    ],
    "density_hint": "normal", "notes": "..." },
  { "frame_type": "statementframe", "text": "One idea worth a whole slide." },
  { "frame_type": "thanksframe", "headline": "Thanks", "subtitle": "Questions welcome" }
]
```

Body items are **either** a `block` (`block`/`alertblock`/`exampleblock`/`itemize`/
`enumerate`) **or** a `figure` (id must exist). See
[`simple-theme-isa.md`](./simple-theme-isa.md) for the full rendering rules.
