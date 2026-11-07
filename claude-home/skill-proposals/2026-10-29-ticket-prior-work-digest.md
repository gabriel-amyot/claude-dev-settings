# Skill Proposal: ticket-prior-work-digest
Date: 2026-10-29
Source: KTP-1403 Campaign Health empty response, recovering October work from KTT-48 / KTT-54

## Trigger
"find what we have on this ticket", "we worked on this before", "add what we know to the ticket". A new Jira ticket describes a problem that older local work already investigated.

## Scope
org (Klever), portable to Supervisr

## Draft Steps
1. Fetch the ticket. Extract symptom terms, product or service name, and date.
2. Search library ALIASES/INDEX by symptom, then grep `tickets/`, `sessions/active|archive/*/reports`, and linked Jira tickets (including Won't Do ones) by product name. Do not search by the new key.
3. Build a timeline: confirmed cause (with verified_against), fix attempts and their outcome, why the work stopped, and what blocks validation.
4. Draft a "prior investigation" comment in the ticket folder. Separate confirmed facts from hypotheses. Leave out internal tooling and sessions. Ask the user for current-state facts before drafting.
5. Hand the draft to /post-comment, and add an inbox nugget if the library doc is behind.
