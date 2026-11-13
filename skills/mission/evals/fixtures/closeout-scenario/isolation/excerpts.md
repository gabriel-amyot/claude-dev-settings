# Close-out scenario: isolation

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
- PRJ-1321 (In review/testing since 2026-10-14). The 2026-11-12 production evidence on PRJ-1398 shows env, seat and spend on each result, and a refused call that named its cause and said no bid moved.
- PRJ-1324 (Backlog). The plan-signing secret was retired with D-7. No code reads it.
- acme/planning#841, #842, #843 (open, under the closed map A). No tracker ticket and no successor issue covers any of them.
- OTH-1415 (In Progress, another product: the map heatmap) matched the alias 'vendor' in its summary. Its handoff 2026-11-11-heatmap-vendor-colours.md matched on the same word. Neither belongs to the vendor trading tool.

## Recent commits in the planning repo (last 3 days)
- 2026-11-12 OTH-1411: Add the map tile cache warm-up job
- 2026-11-12 PRJ-1398: Record the production write evidence
- 2026-11-11 OTH-1411: Fix the tile cache key for the heatmap layer
- 2026-11-11 PRJ-3: Docs refresh for the shipped tool
