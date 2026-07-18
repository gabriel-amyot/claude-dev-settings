GATE: Phase3-coverage   CLOCK: 18m   SPEND: ~$1.50   LOOPS: 0/3
STATUS: PASS. All 5 layers carded. Two signature clusters: demo-dev (500/fetch-failed, H1/H2/H3) and prod+demo-prod (200-empty, H4/H5/H6/H7).
LAYER COVERAGE: ui=2 [H3,H6] · backend=2 [H2,H5] · data=1 [H4] · db=1 [H7] · infra=1 [H1]
OBSERVED: O1 [prod 200-empty] · O2 [demo-prod 200-empty] · O3 [demo-dev 500/fetch-failed]
RULED OUT: none yet
NEXT: Phase 4 — falsify cheapest-first. H1 (S, high, demo-dev DAC config) first; H4 (S, high, BQ data) second.
EXPRESS: declined (Phase 2b)
PARKED: 0   LINKS: board.yaml · observations.yaml
