GATE: Phase2b-Express   CLOCK: 12m   SPEND: ~$1.00   LOOPS: 0/3
STATUS: DECLINED. single_cause_all_envs=false — prod/demo-prod show 200-empty (data path); demo-dev shows 500/fetch-failed (stale host URL). Two distinct signatures require separate hypotheses.
OBSERVED: O1 [OBSERVED prod, 200-empty] · O2 [OBSERVED demo-prod, 200-empty] · O3 [OBSERVED demo-dev, 500/fetch-failed]
RULED OUT: n/a
NEXT: Phase 3 SURFACE — seed board per env, all layers
EXPRESS: declined — two distinct signatures, not single_cause_all_envs
PARKED: 0   LINKS: express-input.yaml · observations.yaml
