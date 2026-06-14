# Pass: intent capture

**This is the FIRST action of every conversion run.** Do not ingest, plan, or
generate anything before you have the user's intent.

## Ask

Ask the user, in their own words, what this talk is for. Offer examples so they
can anchor:

- "Length unbounded — the goal is to convey the paper's content faithfully."
- "A 15-minute conference talk."
- "A seminar for my advisor and lab group."

## Translate intent into two profiles

Record both in the Narrative IR `## Talk meta` block.

### 1. Page budget (drives page-count repair)

- A **stated duration** → a target content-slide range using roughly
  **1 content slide per minute, ±20%**. Examples:
  - 15 minutes → `min_pages 12`, `max_pages 18`
  - 30 minutes → `min_pages 24`, `max_pages 36`
- **"Unbounded" / "length-free" / "just convey the content"** → page budget is
  **none**, and the page-count repair trigger is DISABLED (the deck may be any
  length; only compile errors and overflow are repaired).

### 2. Depth / tone

Read the intent for who the audience is and how deep to go:

- "technical conference talk" → tight, assume field background, keep one proof
  sketch at most, lead with results.
- "seminar for my advisor" → more depth, keep methodological detail, room for
  derivations.
- "convey the content" → faithful coverage over time pressure.

## Defensive rule

If the intent is **ambiguous about length** (no duration, no "unbounded"), ask
ONE clarifying question rather than guessing — the page budget changes the whole
plan. Once clear, proceed to ingest.
