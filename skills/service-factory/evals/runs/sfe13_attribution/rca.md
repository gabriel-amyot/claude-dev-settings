# RCA — KTP-939 / 0 locations for agency 133

## 1. Symptom
- Reported (verbatim): "Advertisers under agency 133 show 0 locations. Prod." [REPORTED by Rajan]
- Envs reported: {prod}
- intermittency: n/a — deterministic (reported as consistent 0 locations)

## 2. Anchor (per env)

| Env | Surface | Signature | O-id | Method |
|-----|---------|-----------|------|--------|
| prod | POI panel | 200-empty | O1 | ui-probe |

Backend log trace O2: method=log-trace, but source={env: prod, instance: proxrp-cos, traffic: "prod+demo mixed (unattributable)"}. CAVEAT: logs do not carry agency or env discriminator. Cannot confirm any log line belongs to agency 133 or to prod-only traffic. O2 establishes that proxrp-cos returns empty results on some requests, but cannot be attributed to the claimed scope.

## 3. Confirmed cause(s)

**NONE.** No cause reached CONFIRMED status.

All probes for H1–H6 returned NOT_IN_WORLD (world.yaml provides no additional missions). The log-trace O2 is unattributable to agency 133 / prod — it cannot back a mechanism-class cause whose scope is agency 133 in prod. Promoting any hypothesis to CONFIRMED without attributable evidence would be confabulation (see: confabulation trap, IFM).

## 4. How introduced

Unknown — no cause confirmed.

## 5. Eliminated hypotheses

LAYER COVERAGE: ui=H5 (UNTESTED) · backend=H3 (UNTESTED) · data=H1,H2 (UNTESTED) · db=H4 (UNTESTED) · infra=H6 (UNTESTED)

All 6 cards remain UNTESTED. No card was REFUTED (no falsifying evidence obtained). No card was SHELVED (budget not exhausted on any specific card; the world simply provided no probe results for them).

## 6. Open Questions / Unverified

**Best surviving hypothesis (unverified):** H1 — agency 133 advertisers absent from BQ source data. Matches the data-gap playbook signature (200-empty, one agency missing, possibly never onboarded). NOT CONFIRMED — no BQ read in world.yaml.

**Attribution gap:** The only backend evidence (O2, log-trace proxrp-cos) carries an explicit CAVEAT: traffic is prod+demo mixed and logs carry no agency/env discriminator. O2 cannot be used to attribute empty-result requests to agency 133 specifically. This is the load-bearing epistemic gap blocking any mechanism-class CONFIRMED cause.

**Probes needed (not in world):**
- BQ exhaustive-read: SELECT COUNT(*) for agency 133 in location table
- BQ exhaustive-read: advertiser-agency mapping table for agency 133
- UM DB read: agency 133 presence
- proxrp-cos env-var read: BQ project + agency-filter config

## 7. Fix + follow-ups + hack-debt

Disposition: **owner-handoff** — no confirmed cause, probes not available in this session.

Action: Post Jira comment flagging the attribution gap in O2 (unattributable logs), request that the data team run BQ reads for agency 133, and surface H1 as the cheapest first probe.

Exit verification: cannot exit — no green re-repro possible without a confirmed cause.

Hack-debt: none (no code change made).

---

## Knowledge harvest (Phase 9)

- **Knowledge-fact:** `proxrp-cos` serves prod AND demo-prod traffic on the same request path; backend logs carry no agency or env discriminator. Any log-trace from this instance produces unattributable evidence — cannot scope to a specific agency or env. [OBSERVED O2, verbatim from world.yaml caveat]
  - back-link: this RCA, O2
- **Playbook:** data-gap +1 (signature matched: 200-empty, one agency missing). Attribution-gap sub-pattern is new — propose adding "shared-instance log unattributable" note to data-gap.md.
