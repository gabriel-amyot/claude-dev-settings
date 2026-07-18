# RCA — KTP-130 — Artistry Brand flow lines missing

## 1. Symptom
- Reported (verbatim): "Vendor returns nothing for 'Artistry Brand'." [REPORTED by Amal]
- Envs reported: {prod}
- Intermittency: n/a — deterministic (0 results every query under corporate name)

## 2. Anchor (per env)
| Env | Signature | Observation | Method |
|-----|-----------|-------------|--------|
| prod | 0-rows from vendor API | [OBSERVED O1] | live-probe |

Reproduced: vendor returns 0 results for query "Artistry Brand". Two-part anchor: symptom (0 flow lines in UI per reporter) + tech signature (0-rows from vendor API O1).

## 3. Confirmed cause(s)

**Claim:** Vendor API queried with corporate parent name "Artistry Brand"; the vendor indexes entities by consumer storefront name. Correct query key is "Shrimp Basket" (214 POIs, flow-line data available). [OBSERVED O2]
- **Evidence:** [O1, O2, O4] — O1 confirms 0-rows on "Artistry Brand"; O2 confirms rich results on "Shrimp Basket"; O4 is the Jira comment that names the alias.
- **Stamp:** [OBSERVED O2] (method: exhaustive-read — alias sweep per data-gap playbook)
- **Scope:** {env: prod, component: vendor-api-adapter}

## 4. How introduced
The entity was onboarded or first queried using the corporate parent name "Artistry Brand" without a consumer-name alias sweep. [INFERRED from O1, O2, O4 — no explicit change commit in world]

## 5. Eliminated hypotheses
- H2: Entity absent from vendor entirely — REFUTED [OBSERVED O3]. Vendor UI shows Shrimp Basket with full coverage. Strength: strong. Verdict scope covers prod.
- H3: Backend adapter hardcodes corporate name — SHELVED (not-refuted, skipped-for-budget; H1 CONFIRMED explains the anchor completely).

Layer coverage line: ui=N/A (app renders) · backend=1 card SHELVED (H3) · data=2 cards (H1 CONFIRMED, H2 REFUTED) · db=N/A · infra=N/A

## 6. Open Questions / Unverified
- H3 (backend hardcodes name) is shelved not refuted. If the fix (querying by "Shrimp Basket") must be made in the backend adapter, the exact file/line is unverified — NOT_IN_WORLD. This does not block the diagnosis but the fix scope may be wider.

## 7. Fix + follow-ups + hack-debt
- **H1 disposition: quick-fix.** Change the vendor query from "Artistry Brand" to "Shrimp Basket" (or parameterize via config/alias map). Closure criterion: same repro red→green (vendor-search "Shrimp Basket" returns rows and flow lines render in UI on prod).
- **H3 follow-up:** If the name is hardcoded in the adapter, a Leo-gated ticket to add an alias-map config layer (so future corporate→consumer name mismatches are handled without code changes). Track as a parking-lot item.
- Exit verification: re-run vendor-search "Shrimp Basket" repro; confirm flow lines render. (No flaky exit needed — deterministic symptom.)
- Hack-debt: none beyond the shelved H3 follow-up.
