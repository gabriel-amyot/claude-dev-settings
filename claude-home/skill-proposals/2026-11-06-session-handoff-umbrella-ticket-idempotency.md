# Skill Proposal: session:handoff idempotency for umbrella tickets
Date: 2026-11-06
Source: session watchful-lynx (KTP-853). The handoff skill matches existing handoffs by exact `ticket`; KTP-853 had 6+ `awaiting_initiation` handoffs on unrelated scopes (LangSmith, prod-finish close, overnight closeout). "Update in place" would have overwritten another session's handoff and dropped its intents.

## Trigger
`/session:handoff` when the ticket already has awaiting handoffs from a different `source_session` or theme.

## Scope
global (session plugin, `skills/handoff/SKILL.md`).

## Draft Steps
1. Match on (`ticket`, `source_session`) or (`ticket`, `theme`), not ticket alone.
2. If only the ticket matches, create a new handoff and list the sibling handoffs in its Context.
3. Never update in place a handoff written by another session.
