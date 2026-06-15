# Narrative IR — Attention Is All You Need

## Talk meta
- intent: A 15-minute conference talk introducing the Transformer to an ML
  audience that knows sequence models but not this architecture. Lead with the
  result, keep at most one attention diagram and one equation.
- time-budget: 15 minutes
- page-budget: 12–18 content slides (1 slide/min ±20%)
- depth/tone: technical conference talk; assume seq2seq background; one proof
  sketch / one equation at most; results-first.

### N00 — Title
- goal: title frame
- key-message: n/a
- time-budget: 0 min
- supporting-figures: none

### N01 — Result-first hook
- goal: open with the payoff so the audience knows why this matters
- key-message: A model built only from attention — no recurrence, no convolution
  — sets a new WMT'14 state of the art while training far faster.
- time-budget: 1 min
- supporting-figures: none

### N02 — The bottleneck in recurrent models
- goal: name the limitation the field had accepted
- key-message: Recurrence forces sequential computation along the sequence, which
  blocks parallelization and makes long-range dependencies hard to learn.
- time-budget: 2 min
- supporting-figures: none

### N03 — The idea: attention is all you need
- goal: state the core proposal in one sentence
- key-message: Replace recurrence entirely with attention to relate any two
  positions in a constant number of steps.
- time-budget: 1 min
- supporting-figures: none

### N04 — Architecture overview
- goal: orient the audience to the encoder–decoder stack
- key-message: An encoder and decoder of N=6 identical layers, each built from
  multi-head attention + a position-wise feed-forward net, with residual
  connections and layer norm.
- time-budget: 2 min
- supporting-figures: figure-001  (Figure 1: the Transformer architecture)

### N05 — Scaled dot-product attention
- goal: give the one mechanism (and the one equation) the talk needs
- key-message: Attention is a softmax over query–key dot products, scaled by
  1/√d_k, used to take a weighted sum of values.
- time-budget: 2 min
- supporting-figures: figure-002  (Figure 2 left: scaled dot-product attention)

### N06 — Multi-head attention
- goal: explain why one attention is not enough
- key-message: h=8 parallel heads attend to different representation subspaces at
  once, at a compute cost similar to a single full-dimension head.
- time-budget: 1 min
- supporting-figures: none

### N07 — Positional encoding
- goal: close the obvious gap — no recurrence means no order
- key-message: Sinusoidal positional encodings injected at the input let the
  model use sequence order without any recurrence.
- time-budget: 1 min
- supporting-figures: none

### N08 — Why self-attention wins
- goal: justify the design with the complexity/path-length argument
- key-message: Self-attention connects all positions with O(1) sequential
  operations and O(1) path length, versus O(n) for recurrence — easier
  long-range learning and far more parallelism.
- time-budget: 2 min
- supporting-figures: none

### N09 — Training setup
- goal: make the result reproducible and credible in one breath
- key-message: WMT'14 EN-DE/EN-FR, 8 P100 GPUs, Adam with a warmup schedule,
  dropout and label smoothing.
- time-budget: 1 min
- supporting-figures: none

### N10 — Results: machine translation
- goal: deliver the headline numbers against prior SOTA
- key-message: 28.4 BLEU EN-DE (+2.0 over the best prior, including ensembles)
  and 41.8 BLEU EN-FR, at a fraction of the training cost.
- time-budget: 2 min
- supporting-figures: none

### N11 — It generalizes
- goal: show the architecture is not translation-specific
- key-message: With little tuning the Transformer reaches 92.7 F1 on English
  constituency parsing, beating most prior models.
- time-budget: 1 min
- supporting-figures: none

### N12 — Takeaways
- goal: leave the audience with the lasting message
- key-message: Attention alone is enough — simpler, more parallel, and stronger;
  a template the field can build on.
- time-budget: 1 min
- supporting-figures: none

### N13 — Thanks
- goal: closing frame
- key-message: n/a
- time-budget: 0 min
- supporting-figures: none
