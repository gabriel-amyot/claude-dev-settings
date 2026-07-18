# Env Fact Sheet — KTP-939

Library: documentation/bibliotheque/stack/dev-backend-topology.md establishes: demo-prod shares the PROD backend + BQ; demo-dev has its own DAC-wired backend.

## Environments

ENV: prod
- Backend: shared production (app-proximity-report COS)
- BQ: production dataset
- Frontend: production build

ENV: demo-prod
- Backend: SHARED with prod (same backend + BQ as production)
- Frontend: demo build (may be newer than prod)

ENV: demo-dev
- Backend: own DAC-wired backend (dac-gcp-back-proxrp, dev tier)
- Frontend: demo-dev build (newest; runs newer builds)

## Prior session note
Memory: "frontend-lag: the demo env runs newer builds and can lag prod; UI often the cause"
Prior session (quick-wren): NOT reproduced. One advertiser tested. Demo env NOT tested. No Jira action taken.

## Reported observables

OBSERVABLE: POI panel intermittently stuck spinning [REPORTED Rajan]
OBSERVABLE: 0 locations found [REPORTED Rajan]
OBSERVABLE: Envs reported: prod, demo [REPORTED Rajan]
