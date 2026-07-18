# RCA — KTP-939 — POI panel intermittently stuck / 0 locations found

---

## 1. Symptom
- Reported (verbatim): "The proximity report is intermittently stuck spinning, or shows 0 locations found. Seen on prod and on the demo env." [REPORTED Rajan]
- Envs reported: {prod, demo}
- Intermittency: Two distinct manifestations. demo-dev: deterministic 500/fetch-failed (intermittency: n/a — deterministic after MR!21). prod+demo-prod: 200-empty for advertiser 842 (intermittency: not yet characterized — see Open Questions).

---

## 2. Anchor (per env)

| Env | Symptom surface | Signature | First-error time |
|---|---|---|---|
| prod | POI panel shows "0 locations found" for advertiser 842 [OBSERVED O1] | 200-empty | n/a (200, no error) |
| demo-prod | POI panel shows "0 locations found" for advertiser 842 [OBSERVED O2] | 200-empty | n/a (200, no error) |
| demo-dev | POI panel stuck spinner; network request to proxrp-cos-retired.dead returns 500 [OBSERVED O3] | 500/fetch-failed | 2026-07-15T09:12Z (after MR!21 merged) |

---

## 3. Confirmed cause(s)

### Cause A — demo-dev: retired host URL in DAC wiring

- **Claim:** demo-dev DAC config routes backend requests to `proxrp-cos-retired.dead`, a retired COS host, after MR!21 rewired the backend. Every POI panel request from demo-dev hits this dead host and returns 500. [OBSERVED O4]
- **Evidence:** O3 (ui-probe, 500/fetch-failed, network tab shows URL), O4 (live-probe, domain=infra, source=proxrp-cos-retired.dead)
- **Stamp:** [OBSERVED O4]
- **Scope:** {env: demo-dev, component: dac-gcp-back-proxrp}

---

## 4. How introduced
MR!21 rewired the demo-dev backend (new COS deployment or URL rename). The DAC config for demo-dev was not updated to point to the new host. The old `proxrp-cos-retired.dead` URL remained in the DAC wiring. [INFERRED from O4 + first-error timestamp at MR!21 merge time]

---

## 5. Eliminated hypotheses

- **H2 (demo-dev backend crashed):** SHELVED — not-refuted, skipped-for-budget. H1/Cause A explains 500 without requiring a service crash. Not in the elimination log.
- **H3 (frontend build wrong URL):** SHELVED — not-refuted, skipped-for-budget. Klever pattern: per-env backend URLs come from DAC wiring, not frontend builds. Not in the elimination log.
- **H4 (BQ missing advertiser 842 data):** UNTESTED — no world probe result available. Leading hypothesis for prod+demo-prod cluster. Remains open.
- **H5 (backend adapter mapping):** UNTESTED — no world probe result available.
- **H6 (frontend rendering bug):** UNTESTED — no world probe result available.
- **H7 (DB missing advertiser 842):** UNTESTED — no world probe result available.

**Layer coverage:**
- ui: H3 (shelved), H6 (untested)
- backend: H2 (shelved), H5 (untested)
- data: H4 (untested)
- db: H7 (untested)
- infra: H1/Cause A (CONFIRMED)

---

## 6. Open Questions / Unverified

**prod + demo-prod (200-empty):** No confirmed cause. Best surviving hypotheses (ranked):
1. H4: advertiser 842 has no BQ data (S, high-likelihood, no probe from world)
2. H5: backend adapter mapping issue for advertiser 842 (M, med-likelihood)
3. H6/H7: UI or DB layer (low likelihood)

Note: demo-prod shares prod backend + BQ [Library: dev-backend-topology.md]. If the root cause is BQ data or backend, it will affect both prod and demo-prod identically. Prior session (quick-wren) tested only one advertiser — the symptom may be specific to advertiser 842 having no data, not a systemic intermittency.

This block is `[INFERRED from O1+O2+Library]`. NOT a Verdict — open question, needs probe.

---

## 7. Fix + follow-ups + hack-debt

**Cause A (demo-dev, confirmed):**
- Disposition: quick-fix
- Fix: update DAC config for demo-dev (`dac-gcp-back-proxrp`) to point to the correct live COS host URL. Commit + redeploy DAC.
- Exit criterion: same repro red→green — ui-probe demo-dev returns 200, panel renders (not 500/fetch-failed).
- Hack-debt: none — DAC config correction is the intended mechanism.

**prod + demo-prod (open):**
- Disposition: owner-handoff / Leo-ticket (separate investigation needed)
- Probe needed: BQ query for advertiser 842 row count, then backend adapter trace
- Follow-up: tracked ticket (requires creation — pool ticket from reusable KTP pool if available)
- Exit criterion: green re-repro after fix, OR data-owner confirms advertiser 842 is intentionally empty (closes as WAI)

---

## Knowledge harvest (Phase 9)

- **Fact 1:** demo-dev uses its own DAC-wired backend separate from prod (verbatim, Library: dev-backend-topology.md). MR!21 rewirings that rename COS hosts must update the DAC config. {fact, verbatim, source: O4 + world.yaml bibliotheque, back-link: KTP-939 RCA}
- **Fact 2:** prior-session scope gaps (quick-wren: one advertiser, demo env not tested) create false negatives — the Service Factory reproduce step must probe all reported envs and all advertiser candidates before declaring "not reproduced." {fact, inferred, source: prior_session block, back-link: KTP-939 RCA}
- **Playbook:** +1 config-drift (DAC URL stale after COS host rename post-MR). New signature: `500/fetch-failed + network URL contains 'retired' or dead hostname → DAC URL stale`.
