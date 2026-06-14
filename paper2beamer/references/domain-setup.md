# Optional setup: investigate the domain

**Optional, once per workspace.** Produce a `template/domain.md` that calibrates
how much background to give, which terminology to normalize, and what counts as
good evidence in this field. If skipped, the pipeline stays field-neutral and
assumes a general graduate-level audience.

This uses **approach C: infer from a paper, then confirm with a few questions.**

## Step 1 — draft from a representative paper

Ask the user for one representative paper (PDF) from their field. Read it (you
may reuse Docling ingest) and DRAFT `template/domain.md` by inference, filling
the existing template fields:

- Field / area
- Audience (best guess)
- Assume the audience already knows
- Always explain (do not assume)
- Key terminology to define / normalize
- What "good evidence" looks like here

## Step 2 — confirm what a paper cannot reveal

Ask a few targeted questions for the things inference cannot settle:

- "Who exactly is the audience for these talks — lab group, journal club, a
  thesis committee, cross-disciplinary reviewers?"
- "Which concepts must ALWAYS be taught, even to specialists, for your talks to
  land?"
- "Any terms your subfield uses differently from neighbours?"

Fold the answers in.

## Step 3 — save

Write the result to `template/domain.md`. The Narrative pass reads it on every
run. The user can edit it by hand any time.
