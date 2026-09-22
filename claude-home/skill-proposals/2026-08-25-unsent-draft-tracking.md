# Skill Proposal: unsent-draft-tracking

Date: 2026-08-25
Source: patient-osprey — KTP-920, where an unsent draft cost six days

## The failure it prevents

`/post-comment` writes a draft to disk, previews it, and waits for approval. If approval never
comes, the draft has **no tracked state and no owner**. The session closes and the draft becomes
invisible.

Measured cost, 2026-08-19 to 2026-08-25: a colleague answered a question the same day it was asked.
A correct reply was drafted that morning and never sent. Six days later a fresh session re-derived
the same answer from BigQuery, spent hours on it, and produced a *worse* reply that would have sent
the colleague to change the wrong setting. The right answer was in the Jira thread the whole time.

This is the same failure class as a deferred AC with no Jira comment, which already has an SOP. The
external-draft case does not.

## Trigger

- `/post-comment` renders a preview and the human does not approve in that turn
- `/session:check --close` runs while any draft under `reports/drafts/` has no matching entry in
  the post log
- Any agent writes a draft intended for an external platform and does not post it

## Scope

Global. The gap is in the harness, not in one org — `/post-comment` is used across Klever,
Supervisr and personal work.

## Draft steps

1. **Detect the unsent draft.** On `/post-comment` exit without a post, and on session close, list
   drafts in the ticket's `reports/drafts/` (or the session's draft folder) with no corresponding
   entry in `reports/ship/post-log.yaml`.
2. **Require an expiry trigger, not a good intention.** Prompt for one of: a date, or a condition
   ("send if X has not confirmed by Y"). Refuse "hold until we decide" — that is the failure mode.
3. **Write a `pending/` inbox item** in the org's inbox with the draft path, the target, the reason
   it is held, and the trigger. Add the index line.
4. **Surface it on session start.** `/session:init` and `/pickup` already read the ledger; extend
   them to report held drafts whose trigger has fired or expired.
5. **Close the loop on post.** When the draft is eventually posted, move the inbox item to
   `resolved/`.

## Notes

- Step 2 is the load-bearing one. A tracked item with no expiry is only marginally better than an
  untracked one — it still waits for someone to remember.
- Consider a mechanical backstop rather than a skill: a `Stop` hook that refuses to close a session
  with an unsent draft and no pending item, mirroring
  `session-close-operationalize-guard.sh`. That would make it un-skippable, which the discipline
  alone has already proven not to be.
- Related existing rule: "A Deferred AC Is an Open Question" in the Klever project CLAUDE.md. This
  proposal is the external-communication sibling of it.
