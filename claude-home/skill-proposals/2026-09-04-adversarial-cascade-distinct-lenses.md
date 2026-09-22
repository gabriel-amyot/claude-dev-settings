# Skill Proposal: adversarial-cascade-distinct-lenses
Date: 2026-09-04
Source: KTP-571 Planning Map decision record (session deft-kestrel)

## Trigger

A design document, decision record, or plan is about to be acted on, and being wrong is
expensive. Distinct from `adversarial-cascade`, which reviews *implemented code* in two passes.
This reviews a *document before anyone builds from it*.

## The finding it is built on

Three reviewers ran over the same two documents. **Each found what the previous ones missed, and
the value came from the lenses being different, not from there being more of them.**

- **Codex (correctness/adversarial):** refuted 6 of 8 recommendations, caught the document
  contradicting itself (calling a change "behaviour-preserving" while demanding a regression
  before shipping it), and refuted a claim the *architect* had made.
- **Winston (BMAD architect):** found two blockers nobody else saw — the tile-to-API seam was
  keyed on an id that does not exist, and half the architecture had no ticket, owner or gate.
  Also found the finding that moved the delivery date.
- **Fable (usability / decision-readiness):** took the reader's lens rather than the reviewer's.
  Found the blocker both others missed: the change silently shipped an unrelated product decision.
  Also caught cross-document drift left by the earlier fixes.

A repeated pass with the same lens would have found none of the second and third rounds.

## Scope

Global. Any org, any document.

## Draft Steps

1. **Correctness pass.** Adversarial, external if possible (Codex CLI read-only). Prompt to
   REFUTE, not to review. Require a verdict per claim.
2. **Apply findings**, and record where the reviewer overruled the author rather than presenting a
   clean consensus. The disagreement is signal for the human.
3. **Architecture pass.** A domain architect persona. Hunt for what is implied by the decisions and
   appears in no section — the gap hunt is the highest-value question.
4. **Apply**, then re-verify any factual claim the two reviewers disagree on. In this run the
   architect over-claimed and the correctness reviewer was right; a third check settled it.
5. **Reader pass.** Different lens entirely: can the named human act on this tomorrow, and where
   would a competent engineer executing it go wrong? Also sweep for stale sentences left by rounds
   1 to 4 — revision churn is the reliable defect source.
6. **Sweep for self-contradiction before delivery.** Grep the document for phrases the revisions
   should have removed. Every round of this cascade left at least one behind.

## Notes

- Each reviewer must be told what the previous ones already applied, or round 3 re-litigates round 1.
- Give each pass a *different question*, not a different model. The lens is the mechanism.
- Expect to be overruled. In this run, 6 of 8 initial recommendations did not survive, and the
  final recommendation reversed the author's opening position.
