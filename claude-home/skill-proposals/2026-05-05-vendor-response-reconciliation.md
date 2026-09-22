# Skill Proposal: vendor-response-reconciliation

Date: 2026-05-05
Source: KTP-607 Placer vendor response session

## Trigger

"vendor responded", "Nick answered", "got the answer from [vendor]", "update tickets with vendor response", or when a vendor comment appears on a spike/blocker ticket.

## Scope

org (Klever). Could generalize to global if Supervisr has similar vendor dependency patterns.

## Draft Steps

1. **Ingest vendor answer.** Pull the Jira comment or message containing the vendor response. Parse into discrete Q&A pairs.
2. **Load spike context.** Read the original spike findings, assumptions matrix, and child ticket list.
3. **Cross-reference.** For each Q&A pair, classify against spike assumptions: CONFIRMED (assumption holds), CHALLENGED (assumption invalidated), or PARTIAL (nuance changes scope).
4. **Draft Jira comments.** For every affected child ticket, draft a comment: confirmed specs get a short validation note, challenged specs get the revised understanding and next steps. Route through /post-comment.
5. **Update local state.** Update STATUS_SNAPSHOT.yaml, closure roadmaps, and decisions logs. Create an advancement log entry documenting what changed, what was cleaned, and what actions remain.
6. **Clean stale assumptions.** Grep local ticket artifacts for references to the old assumption. Flag or update each occurrence.
