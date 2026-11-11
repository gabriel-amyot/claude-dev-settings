# Response reconciliation: the vendor answered

This closes the loop the escalation opened. Run it only when the user asks for it explicitly
("Nick answered, reconcile the tickets", "update the tickets with the vendor response").
It drafts. It never posts and never changes local status files without approval.

## Steps

1. **Ingest the answer.** Read the vendor reply (Jira comment, email text, or Slack message the user
   pastes). Split it into Q&A pairs. Quote the vendor's exact words for each answer. If the vendor
   answered a question that was not asked, record it as an extra pair.
2. **Load the open assumptions.** Read the spike findings, the assumptions matrix, and the list of
   child tickets that depend on the answer. Use the questions from the original escalation draft as
   the index.
3. **Map each answer to the assumptions it touches.** One row per assumption:

   | Assumption | Vendor quote | Verdict | Effect |
   |---|---|---|---|
   | ASM-n text | exact words | `CONFIRMED`, `CHALLENGED`, `PARTIAL`, or `UNANSWERED` | scope, AC, or next step that changes |

   - `CONFIRMED`: the quote says the assumption holds.
   - `CHALLENGED`: the quote contradicts it.
   - `PARTIAL`: the quote adds a condition (tier, limit, version) that changes scope.
   - `UNANSWERED`: the reply is vague or silent on it. Keep the uncertainty. Do not round a vague
     reply up to `CONFIRMED`. A follow-up question goes through Steps 1 to 6 of SKILL.md again.
   Every verdict cites its quote. A verdict with no quote is not allowed.
4. **Draft per-ticket comments.** For each affected child ticket, write a draft in that ticket's
   folder. Confirmed specs get a short validation note. Challenged or partial specs get the revised
   understanding and the next step. Route every post through `/post-comment`.
5. **Propose local state changes.** List the edits to `STATUS_SNAPSHOT.yaml`, closure roadmaps, and
   decision logs. Show the list to the user and apply it only after approval. Then add one dated
   advancement-log entry: what changed, what was cleaned, and what remains.
6. **Find stale assumptions.** Grep the ticket artifacts for the old assumption text. List each hit
   with its path. Update a hit only after approval. Flag hits in other people's files instead.

## Output

`reports/vendor/<date>-<vendor>-reconciliation.md` in the parent ticket folder, holding the Q&A
pairs, the mapping table, the list of comment drafts, the proposed state edits, and the stale hits.
