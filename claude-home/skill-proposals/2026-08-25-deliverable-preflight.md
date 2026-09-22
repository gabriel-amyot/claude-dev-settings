# Skill Proposal: deliverable-preflight
Date: 2026-08-25
Source: KTP-920 Chevron DOOH deliverable rebuild (session `lucid-pike`)

## Trigger

Before handing any generated data file to the human who owns it — a client report, a crosswalk, a
seeded table export, a QA sample. Phrases: "send this to {SME}", "ready for QA", "hand this to the
client", "is this file right".

Not for code review and not for a schema check. This is: **run the reviewer's own checks before the
reviewer does.**

## Why it is worth a skill

On KTP-920 the rebuilt report matched the SME's file on header, column order, date format, campaign
names, venue types and totals (within 0.07%). It looked ready. Running her checks first surfaced the
finding that mattered: the **screen-identified impressions were byte-identical to the file she had
already rejected** — every impression of improvement came from one unattributed lump row. She would
have found it in a single filter, and a handover framed as "rebuilt, ready for QA" would have been
rejected on sight.

Separately, a draft comment to her quoted a figure measured on a *different export* of the same
vendor report. It was coherent, real, and about the wrong file. Caught by self-audit minutes before
posting. A preflight that forces every number to name its artifact would have caught it earlier.

The cost of being subtly wrong to a domain owner is not a correction. It is that they stop reading.

## Scope

Org (Klever). Generalises to Supervisr — any human-owned data deliverable.

## Draft Steps

1. **Identify the reviewer and their reference file.** Who owns this report, and what do they compare
   against? If they produce a version by hand, get it. Without a reference, say so and stop claiming
   parity.
2. **Run the composition checks a reviewer runs**, and report counts only, never rows:
   - row-type composition (identified vs aggregate vs other) with each one's share of the metric
   - blank rate per enrichment column, split by whether the blank is expected for that row type
   - apparent duplicates: keys carrying more than one row, and whether they are legitimate splits
   - coverage: date span, missing days, distinct entities, entity count vs the reference
   - value sanity: zeros, negatives, per-unit-cost min/median/max and outlier count
3. **Diff against the reference on the natural key**, and report keys-only-in-each-side separately
   from keys-present-but-differing. Never quote a total-to-total delta alone: it hides offsetting
   errors. This is the step that catches "totals agree, composition does not".
4. **Stamp every figure with the artifact it was measured on.** File name, run id, and which export
   if the vendor has more than one. Two exports of one report are not the same file.
5. **Write the anticipated objections, in the order the reviewer will find them**, with the
   measurement behind each. Then draft the handover to lead with what is fixed AND what is unchanged.
6. Route any external message through `/post-comment`. Never post a data claim without step 4.

## Existing implementation to build from

`project-management/tickets/KTP/no-epic/KTP-920/scripts/anticipate_sme_review.py` already does steps
2 and part of 3 for a CSV with a configurable key. It prints counts only, so nothing sensitive
reaches a transcript. Generalise the column names rather than rewriting it.

## Notes

Do not merge this with `/klever-test` (that is UI/runtime validation) or `/sprint-close` (that is
AC evidence). This is narrower and earlier: one artifact, one reviewer, before it is sent.
