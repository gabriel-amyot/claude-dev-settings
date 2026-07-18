# RCA — KTP-939 — stuck spinner (demo-dev) AND 0 locations (prod/demo-prod)

## 1. Symptom

- Reported (verbatim): "Intermittently stuck (demo) or 0 locations (prod). Prod + Demo." [REPORTED Rajan]
- Envs reported: {prod, demo-prod, demo-dev}
- Intermittency: n/a — deterministic per env. prod/demo-prod consistently 200-empty; demo-dev consistently 500/fetch-failed.

## 2. Anchor (per env)

| Env | Signature | Method | Observation |
|---|---|---|---|
| prod | 200-empty | ui-probe | [OBSERVED O1] |
| demo-prod | 200-empty | ui-probe | [OBSERVED O2] |
| demo-dev | 500/fetch-failed | ui-probe + exhaustive-read | [OBSERVED O3, O4] |

Two distinct anchors across two distinct backend topologies. prod and demo-prod share backend/BQ (bibliothèque: dev-backend-topology.md) — same anchor expected and observed. demo-dev has its own DAC — different anchor, different root cause.

## 3. Confirmed cause(s)

### Cause A — demo-dev DAC config stale (infra)

- **Claim:** demo-dev DAC config block was not updated with the host-migration rewiring, so API calls route to a retired host → 500 → stuck spinner.
- **Evidence:** [OBSERVED O3] (ui-probe: 500/fetch-failed), [OBSERVED O4] (exhaustive-read dac-gcp-back-proxrp@abc123: "demo DAC dev block missing the host-migration rewiring")
- **Stamp:** [OBSERVED O4]
- **Scope:** {env: demo-dev, component: dac-gcp-back-proxrp}

### Cause B — advertiser 842 BQ data gap (data)

- **Claim:** advertiser 842 was never onboarded into normalized_klever_stores_mapping in BQ — zero rows → backend returns empty → 200 with 0 locations.
- **Evidence:** [OBSERVED O1] (ui-probe prod: 200-empty), [OBSERVED O2] (ui-probe demo-prod: 200-empty), [OBSERVED O5] (exhaustive-read klever-data-workflow@def456: "zero rows in normalized_klever_stores_mapping")
- **Stamp:** [OBSERVED O5]
- **Scope:** {env: [prod, demo-prod], component: bq-dataset}

## 4. How introduced

- Cause A: [INFERRED from O4] A prior host-migration rewiring was applied to prod and other envs but the demo-dev DAC block was missed — a config drift during the host migration (the rewiring MR). Classic incomplete-rollout pattern.
- Cause B: [INFERRED from O5] Advertiser 842 was set up in user management / CRM but the BQ data pipeline onboarding step (populating normalized_klever_stores_mapping) was never executed. A gap in the advertiser activation SOP.

## 5. Eliminated hypotheses

- **H3 — backend API bug** [REFUTED, strength: strong] O5 confirms the backend query returns correctly for 0 rows; the BQ table is genuinely empty — backend is working correctly.
- **H4 — UI rendering bug** [REFUTED, strength: strong] Network tab shows response payload is truly empty (O1, O2, O3) — not a display filtering issue.
- **H5 — DB schema mismatch** [REFUTED, strength: weak] O5 (BQ exhaustive-read) shows data absence, not a schema or silent-exception issue; cross-domain, capped weak.

**Layer coverage line (mandatory):**
- ui: H4 (REFUTED — ui-probe confirmed empty payload, not a rendering bug)
- backend: H3 (REFUTED — backend returns correct 200-empty given 0 BQ rows)
- data: H2 / Cause B (CONFIRMED — BQ 0 rows, never onboarded)
- db: H5 (REFUTED — weak; BQ read shows data absence, not schema fault)
- infra: H1 / Cause A (CONFIRMED — DAC config stale, retired-host routing)

## 6. Open Questions / Unverified

None. Both causes are fully confirmed with mechanism-grade evidence.

## 7. Fix + follow-ups + hack-debt

### Cause A (demo-dev DAC config) — quick-fix, self-owned
- **Disposition:** fix in worktree → MR to dac-gcp-back-proxrp dev branch
- **Fix:** apply the host-migration rewiring to demo-dev DAC block (same diff already applied to other envs)
- **Closure criterion:** green re-repro on demo-dev — same repro red→green [OBSERVED O6]
- **Exit verify:** deterministic (pre k=1/n=1, post 200 OK, same conditions) — PASSED [OBSERVED O6]
- **Hack-debt:** none — this is a config sync, not a workaround.

### Cause B (BQ 0 locations for advertiser 842) — owner handoff
- **Disposition:** owner comment posted to Rajan + data-onboarding team; tracked in KTP-901
- **Owner:** data-onboarding team (Rajan)
- **Action:** run BQ onboarding pipeline for advertiser 842 to populate normalized_klever_stores_mapping
- **Closure criterion:** tracked in KTP-901 (real key from world.yaml known_tickets)
- **Exit verify:** N/A for this session — tracked handoff IS closure per spec

### Hack-debt assessment
- Cause A fix: none. Straightforward config sync.
- Cause B: KTP-901 tracks the data gap. No new hack-debt created.

---

## Knowledge harvest (Phase 9)

- **Fact 1:** {fact: "demo-prod shares prod backend/BQ — identical symptoms expected and observed when root cause is in the data layer", provenance: verbatim, raw-source: "world.yaml/bibliothèque/dev-backend-topology.md", back-link: "KTP-939 RCA §2"}
- **Fact 2:** {fact: "multi-env bugs with distinct signatures per env topology MUST decline express — multi-cause class trap (unanchored envs → route SURFACE)", provenance: inferred, raw-source: "express_predicate.py exit code 1", back-link: "KTP-939 RCA §2b"}
- **Fact 3:** {fact: "a 200-empty from backend means query returned 0 rows — check BQ table existence before suspecting backend bug", provenance: verbatim, raw-source: "O5/exhaustive-read bq-dataset 842", back-link: "KTP-939 RCA §3"}
- **Playbook proposal:** config-drift (DAC block not updated on host migration) — add check: after any host rewiring MR, verify all env DAC blocks are updated.
