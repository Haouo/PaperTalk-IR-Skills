# Intent — AIAYN eval fixture

Fixed intent for the eval run, so the page budget is deterministic and the judge
can assess intent fit against a known target.

- intent: A 15-minute conference talk introducing the Transformer to an ML
  audience that knows sequence models but not this architecture. Lead with the
  result, keep at most one attention diagram and one equation.
- time-budget: 15 minutes
- page-budget: 12–18 content slides (1 slide/min ±20%)
- depth/tone: technical conference talk; assume seq2seq background; one proof
  sketch at most; results-first.
