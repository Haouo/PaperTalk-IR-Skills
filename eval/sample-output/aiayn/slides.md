# Slide IR — Attention Is All You Need

## Deck meta
- title: Attention Is All You Need
- short-title: Attention Is All You Need
- author: Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin
- institute: Google Brain · Google Research · University of Toronto
- date: NeurIPS 2017
- density: normal

### S00 — Title
- beat-ref: N00
- title: (title frame — special)
- content: \titleframe
- figure: none
- block-semantics: none

### S01 — Why you should care
- beat-ref: N01
- title: A new state of the art — without recurrence
- content: exampleblock with the headline (28.4 BLEU EN-DE, new SOTA; trained in
  a fraction of the cost); one bullet stating it uses attention only.
- figure: none
- block-semantics: example

### S02 — The bottleneck we accepted
- beat-ref: N02
- title: Recurrence forces sequential computation
- content: 3 bullets on RNN sequential dependence; alertblock naming the
  limitation (no parallelization within a sequence; long-range deps are hard).
- figure: none
- block-semantics: caveat

### S03 — The idea
- beat-ref: N03
- title: Attention is all you need
- content: block stating the claim — drop recurrence and convolution entirely;
  relate any two positions in a constant number of steps.
- figure: none
- block-semantics: claim

### S04 — The Transformer architecture
- beat-ref: N04
- title: An encoder–decoder built from attention
- content: \section{The Transformer}; figure-001 (Figure 1) + 3 bullets: N=6
  identical layers; multi-head attention + position-wise FFN per layer; residual
  + layer norm, d_model=512.
- figure: figure-001
- block-semantics: none

### S05 — Scaled dot-product attention
- beat-ref: N05
- title: Scaled dot-product attention
- content: figure-002 (Figure 2 left) + the one equation
  Attention(Q,K,V)=softmax(QK^T/√d_k)V + 1 bullet on the 1/√d_k scaling.
- figure: figure-002
- block-semantics: none

### S06 — Multi-head attention
- beat-ref: N06
- title: Many heads, many subspaces
- content: 3 bullets: h=8 parallel heads; each attends to a different
  representation subspace; cost ≈ a single full-dimension head (d_k=d_v=64).
- figure: none
- block-semantics: none

### S07 — Positional encoding
- beat-ref: N07
- title: Putting order back in
- content: 2 bullets: no recurrence ⇒ no notion of position; add sinusoidal
  positional encodings at the input so order is available.
- figure: none
- block-semantics: none

### S08 — Why self-attention
- beat-ref: N08
- title: Why self-attention
- content: condensed Table 1 (self-attention vs recurrent: complexity,
  sequential ops, path length); block stating O(1) path length eases long-range
  learning and unlocks parallelism.
- figure: none
- block-semantics: claim

### S09 — Training setup
- beat-ref: N09
- title: How it was trained
- content: 4 bullets: WMT'14 EN-DE / EN-FR; 8 P100 GPUs; Adam with warmup
  schedule; dropout + label smoothing.
- figure: none
- block-semantics: none

### S10 — Results: machine translation
- beat-ref: N10
- title: New state of the art on WMT'14
- content: \section{Results}; exampleblock with 28.4 BLEU EN-DE (+2.0 over the
  best prior, incl. ensembles) and 41.8 BLEU EN-FR; 1 bullet on training cost.
- figure: none
- block-semantics: example

### S11 — Better quality at lower cost
- beat-ref: N10
- title: Better BLEU at a fraction of the cost
- content: condensed Table 2 (a couple of strong prior models vs Transformer
  base/big: BLEU and training FLOPs).
- figure: none
- block-semantics: none

### S12 — It generalizes
- beat-ref: N11
- title: Not just translation
- content: exampleblock — 92.7 F1 on English constituency parsing with little
  tuning, beating most prior models.
- figure: none
- block-semantics: example

### S13 — Takeaways
- beat-ref: N12
- title: Attention is enough
- content: block with 3 takeaways: simpler (no recurrence/convolution), more
  parallel, stronger; a template the field can build on.
- figure: none
- block-semantics: claim

### S14 — Thanks
- beat-ref: N13
- title: (thanks frame — special)
- content: \thanksframe
- figure: none
- block-semantics: none
