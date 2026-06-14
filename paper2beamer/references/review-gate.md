# Pass: review gate (the single human checkpoint)

This is the one place the pipeline stops for the user. The Narrative IR is the
cheapest place to fix a wrong story — before any slide exists — so spend the
gate here.

## Present

Show the Narrative IR as a readable outline, not raw file text:

- the talk's intent and derived time/page budget;
- each beat in order: its label, `key-message`, allocated time, and chosen
  figures;
- the overall arc in one or two sentences.

## Ask

Explicitly ask the user to approve or edit. Examples of what to invite:

- "Is the emphasis right — is anything over- or under-weighted?"
- "Any beat to cut, merge, reorder, or add?"
- "Are the chosen figures the ones you want to show?"

## Loop

Apply requested edits to `narrative.md` and re-present. Repeat until the user
approves.

## Proceed only after approval

Only once the user approves do you continue to `slide-ir.md`. Everything after
this gate runs automatically — Slide IR, emission, compile, and repair — so the
narrative must be right here.
