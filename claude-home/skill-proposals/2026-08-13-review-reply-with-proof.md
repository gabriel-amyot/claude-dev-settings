# Skill Proposal: review-reply-with-proof
Date: 2026-08-13
Source: KTP-1065 / MR !24 — replying to 130 crit comments after implementing the review outcomes

## Why this is worth a skill

Implementing a review and *closing* a review are different jobs, and the second one catches things the first misses.

On KTP-1065 the implementation pass ran eight batches, kept the suite green after every one, and reported done. Writing a proof-carrying reply per comment then found **three defects the build and test cycle could not have caught**:

1. A handoff had recorded a finding as "superseded by a later change". It was half true — the guard-order NPE it named was still live behind a nullable record component. Nothing failed; the claim was simply wrong.
2. A javadoc cut had gone **backwards** in 5 of 12 files, because later batches added comments. Every batch's local claim was true; the aggregate claim was false.
3. Several explanatory comments described code that had since been deleted, so replying "fixed" would have been nonsense — the honest reply is "this is now false".

None of these are test failures. They are all mismatches between *what was claimed* and *what is in the tree*, and the only thing that surfaces them is being forced to produce an anchor per claim.

## Trigger

- "reply to the review comments", "close the review loop", "address all the comments"
- after a `/crit` round whose outcomes have been implemented
- before marking a review-driven ticket as done
- when a definition of done includes "every comment has a reply"

Not for: writing the review itself (`/crit`), or a review with a handful of comments where inline is cheaper.

## Scope

Global. The verification discipline is tool-agnostic; the crit mechanics are one adapter.

## Draft steps

1. **Inventory to disk, not to context.** Load every comment (id, path, line, author, body) into a working file. Detect ids that appear in more than one review store — those cannot be replied to via the crit CLI.
2. **Lock a fact base once.** Run the suite, the lint gate, and the greps that prove the deletions and the exit criteria. Record the numbers. Every later reply cites this, so it is measured once rather than asserted 130 times.
3. **Classify each comment before writing.** Actionable finding / still-true design note / **now-false** note / not done. The third and fourth categories are the ones that carry the value.
4. **Per reply: verdict, how, proof.** Proof is a commit sha plus a checkable anchor — `file:line` in the current tree, a test name, or a command and its output. Never the solution document; the doc is what was planned, not what shipped.
5. **When the proof does not verify, fix it and say so.** The reply records that the earlier claim was wrong. Do not quietly repair and claim it always worked.
6. **Post atomically, never resolve.** Bulk JSON via a file (multi-paragraph bodies break shell quoting). Back up the review store first. Resolving is the reviewer's call.
7. **Verify the write.** Re-read the store, assert every target id has a reply and the resolved count is unchanged.

## Guardrails learned the hard way

- Aggregate metrics get measured at the end, never per batch.
- A "superseded" claim from a handoff is a hypothesis; verify against the tree.
- A reply that says "not done, and here is why" is worth more than a vague "addressed".
- Report the real number even when it misses the target (278 → 167 against a target of 48), with the reason for the gap.

## Open questions

- Should it read a ticket's AC and cross-check that no comment contradicts a status marked MET?
- Is there a cheap way to detect stale comments automatically — e.g. flag any comment whose quoted symbol no longer exists in the tree?
