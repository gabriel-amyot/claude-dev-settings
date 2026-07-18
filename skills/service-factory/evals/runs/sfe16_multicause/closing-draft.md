# Closing comment — KTP-939

Two root causes confirmed. Each has its own disposition.

**Cause A — demo-dev stuck spinner (infra: DAC config)**

demo-dev DAC block was missing the KTP-863 host rewiring and pointed at a retired host. 500 on every API call → stuck spinner.

Fix applied to dac-gcp-back-proxrp (worktree MR to dev). demo-dev now loads, 200 OK, locations render. Green re-repro confirmed.

**Cause B — prod/demo-prod 0 locations for advertiser 842 (data: BQ onboarding gap)**

Advertiser 842 has zero rows in normalized_klever_stores_mapping — never onboarded through the BQ data pipeline. Backend returns correctly (200-empty). This is a data-owner action item.

Tracked in KTP-901. Action required: run the BQ onboarding pipeline for advertiser 842.

**Closure matrix summary**

| Env | Cause | Disposition |
|---|---|---|
| demo-dev | DAC config stale | green-rerepro (O6) |
| prod | BQ data gap adv 842 | tracked KTP-901 |
| demo-prod | BQ data gap adv 842 (shared backend) | tracked KTP-901 |

Both envs/causes resolved. KTP-901 owns the data onboarding follow-up.
