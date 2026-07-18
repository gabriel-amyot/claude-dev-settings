GATE: Phase5-WALL   CLOCK: 28m   SPEND: ~$2.50   LOOPS: 0/3
STATUS: stamp_check PASS (1 confirmed cause). WALL package ready.

CONFIRMED CAUSE A: demo-dev DAC config routes requests to retired host proxrp-cos-retired.dead after MR!21. [OBSERVED O4]
OPEN (no confirmed cause): prod+demo-prod 200-empty for advertiser 842 — H4/H5/H6/H7 all UNTESTED (no world probe results).

OBSERVED: O1 [prod 200-empty] · O2 [demo-prod 200-empty] · O3 [demo-dev 500/fetch-failed] · O4 [demo-dev live-probe infra: proxrp-cos-retired.dead]
RULED OUT: H2 (SHELVED not-refuted) · H3 (SHELVED not-refuted)

ENV-COVERAGE CHECKLIST:
  demo-dev: Cause A CONFIRMED. green re-repro criterion: 200 panel renders.
  prod: NO confirmed cause. Open Questions block. Needs BQ probe.
  demo-prod: NO confirmed cause. Shares prod backend+BQ. Same open question.

WALL QUESTION (H gate): RCA presented. Do you approve Cause A fix? Prod/demo-prod: approve open-question package (tracked investigation) or dig with new budget?
OPTIONS:
  1. approve (fix demo-dev Cause A + create tracked ticket for prod/demo-prod investigation)
  2. reject (send back to board)
  3. dig-with-new-budget (run BQ probe for advertiser 842)
  4. park

NEED FROM YOU: choice above + confirm fix plan: update dac-gcp-back-proxrp config to live COS host URL.
EXPRESS: declined (Phase 2b — multi-cause)
PARKED: 0   LINKS: rca.md · board.yaml · observations.yaml
