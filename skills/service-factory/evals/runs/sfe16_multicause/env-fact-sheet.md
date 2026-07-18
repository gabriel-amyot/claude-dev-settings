# Env Fact Sheet — KTP-939

Library: documentation/bibliotheque/stack/dev-backend-topology.md
  — establishes: "demo-prod shares PROD backend/BQ; demo-dev has its own DAC backend"

ENV: prod
  BACKEND: shared prod backend
  BQ: shared prod BQ dataset
  OBSERVABLE: 0 locations for advertiser 842 [REPORTED Rajan]

ENV: demo-prod
  BACKEND: shared prod backend (same as prod)
  BQ: shared prod BQ dataset (same as prod)
  OBSERVABLE: 0 locations for advertiser 842 [REPORTED Rajan]

ENV: demo-dev
  BACKEND: own DAC backend (dac-gcp-back-proxrp)
  BQ: own dev BQ dataset
  OBSERVABLE: stuck spinner [REPORTED Rajan]

TOPOLOGY NOTE: prod and demo-prod share backend/BQ — a data-layer root cause in prod
  will produce the same symptom in demo-prod. demo-dev is isolated; its symptoms
  must have a separate root cause from its own DAC config.
