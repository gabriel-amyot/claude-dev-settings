# Close-out scenario: traps

Anonymized from a real close-out. A feature reached production; a trader proved read and one real write; the lead closed the parent tickets. These excerpts stand in for the trackers: treat them as what you would read live. There is no network in this sandbox.

## Context (mission record excerpt)
- Destination reached on 2026-11-12: the trader ran the production desktop bundle against the live book. Read worked. One real write: a bid went 8.02 -> 8.50 -> 8.02 and each read-back matched. Evidence: PRJ-1398 comment by the lead, 2026-11-12, with the bundle version and the read-backs.
- Ratified decision D-7 (ratified by the lead, 2026-09-14): the nonce and signed-plan mechanism is deleted. Writes go through the backend-api gateway with per-client scopes.
- Ratified decision D-9 (2026-10-02): the read surface uses a paged inventory (ADR-12). It replaces per-filter queries.
- Disproven X-4: "the write path is broken". The trader's real write on 2026-11-12 disproves it.
- Disproven X-5: "revoking the write grant costs nothing". Writes are now live for the trader.
- Successor mission (active): "multi-seat partner access", epic PTR-100, PRD in PTR-98. Its PRD section "Out of scope" lists: advertiser-level read authorization.
- Known gaps: GAP-1: the production write capability is live. No named decider recorded acceptance of the residual risk. The old acceptance (ADR-10) assumed the deleted signed plan.
- acme/planning#899 is the carry-forward issue created during this close-out.

## Tracker excerpts
- PRJ-1323 (To Do). Decision D-7 deleted the nonce mechanism on 2026-09-14. The token cache is still per instance; with two instances each one refetches vendor tokens and hits the vendor rate limit.
- PRJ-1398 (Done, closed by the lead). Its only comment (2026-10-20) is a read-only status: 'read is live in prod, write stays closed'. The 2026-11-12 evidence of the real write is in the mission record and the trader's message, not on this ticket.
- PRJ-1289 (Done, 0 comments). Each child (PRJ-1290, PRJ-1291, PRJ-1292) is Done and has an evidence comment with a screenshot from the trader's session.
- PTR-95, PTR-96, PTR-97, PTR-98 (Backlog) sit under epic PTR-100, the active successor mission 'multi-seat partner access'. Its owner planned them for next quarter.
- acme/planning#830 (open). Its tracker twin PRJ-1330 is Done with no comments and no attached logs. In the 2026-11-12 session the trader reported no connection drops. Nobody read the client logs.
- acme/planning#850 (open, its parent map A is closed). The topic sounds like the successor mission's partner-access work.
- Handoff 2026-11-10-exec-signs-write-contract.md: the exec signs the production write contract. Still live. Tracked by map B #890 and ticket PTR-103.
- Draft 2026-11-12-gh-carry-forward-body.md starts: 'The vendor tool reached production read and write on 2026-11-12.' The body of acme/planning#899 starts with the same sentence.
- Draft 2026-11-12-new-ptr-gateway-security.md starts: 'WHY: production writes are live since 12 November. PRJ-1065 is Done, but ACs 1, 2 and 4 have no recorded evidence.' PTR-103's description starts with the same text.

## Recent commits in the planning repo (last 3 days)
- 2026-11-12 OTH-1411: Add the map tile cache warm-up job
- 2026-11-12 PRJ-1398: Record the production write evidence
- 2026-11-11 OTH-1411: Fix the tile cache key for the heatmap layer
- 2026-11-11 PRJ-3: Docs refresh for the shipped tool
