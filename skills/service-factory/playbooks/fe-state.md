# Playbook: FE-state

Seeder, not a gate. Recency-weighted. Capped at 50% of seeded cards. This layer
is the one most often NEVER hypothesised — the assumption audit must seed ≥1
FE-state card at cycle 1 even when a config/data playbook ranks higher (IFM-6/11).

## Signature it matches
- UI stuck / spinner never resolves / stale render after an action.
- Symptom changes on advertiser/tab switch, or on re-mount, with no backend error.
- Intermittent + timing/interaction dependent (race) — flag intermittent, use the
  statistical exit standard (IFM-4).

## Cheapest checks first
1. `[S]` `ui-probe` the live app: read React fiber props/state + console + network
   timing at the stuck moment. Two-part anchor: symptom on the surface + the tech
   signature. (method: ui-probe — valid for an FE-state cause; its domain IS ui.)
2. `[S]` check for a stale-state guard: `useEffect` mount guard, degenerate range,
   POI stale state on advertiser switch (known Klever FE gotchas).
3. `[M]` red test: forced-interleaving / m-iteration harness for a suspected race;
   `n=1` pass is INCONCLUSIVE on an intermittent card (SFE-07).

## Source incidents
- KTP-939 (frontend-lag memory that was inflated to a "strong" hypothesis without
  a live look — seed it as a card, do not treat it as fact).
- KTP-628 (empty circles — layer never anchored before a guessed patch).
