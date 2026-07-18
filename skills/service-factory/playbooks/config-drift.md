# Playbook: config-drift / wiring

Seeder, not a gate. Seeds board cards; every card still gets a falsify-test and
must be eliminated on evidence. Recency-weighted (recently-changed config first).
Capped: no single playbook may exceed 50% of seeded cards (IFM-6).

## Signature it matches
- One env works, a sibling env does not, SAME code.
- `500`/`fetch-failed`/`connection refused` to a host or project that a recent
  MR/config diff touched.
- A migration/rewiring MR merged recently; a demo/dev DAC block not updated with it.

## Cheapest checks first (rank: likelihood × 1/cost)
1. `[S]` diff the failing env's DAC/config block vs the working env's and vs the
   recent MR. Component = the DAC repo git-ref. (method: exhaustive-read)
2. `[S]` read the resolved runtime config / env vars on the failing instance;
   confirm which backend/project/host it actually points at. (method: live-probe,
   source component must match the claim — do not scope a cause to a library-asserted
   topology without this, IFM-3.)
3. `[M]` curl/log-trace the failing request end to end; find first error + host.
   (method: log-trace)

## Source incidents
- KTP-939 Cause B (demo DAC dev block missing KTP-863 rewiring).
