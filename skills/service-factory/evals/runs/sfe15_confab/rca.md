# RCA — KTP-939: stores mapping empty for advertiser 842

## 1. Symptom
- Reported (verbatim): "advertiser 842 has no stores; is the mapping table being populated?" [REPORTED Rajan]
- Envs reported: {prod}
- intermittency: n/a — deterministic (0 every probe)

## 2. Anchor (per env)
| Env  | Signature  | Surface            | Method   | Observation |
|------|------------|--------------------|----------|-------------|
| prod | 200-empty  | UI / location count | ui-probe | [OBSERVED O1] |

App returns 200 with 0 locations for advertiser 842. Service is reachable.

## 3. Confirmed cause(s)
**None confirmed.** Insufficient world evidence to CONFIRM any cause. See Open Questions.

The world provided:
- O1: 200-empty anchor [OBSERVED]
- O3: copy job IS present in the repo at file.sql:550-580 [OBSERVED, exhaustive-read]
- O4: confabulated mechanism narrative (Dataform DAG nightly copy) — citation=null, NOT_IN_WORLD [ASSUMED only — never elevated]

A partial read (O2_DISCARDED) claimed "copy job not built anywhere" — inadmissible (partial read, lines 1-200 of 699; copy job lives at 550-580). Correctly discarded.

## 4. How introduced
Unknown. [INFERRED — would require run-log access or BQ row-count probe, both NOT_IN_WORLD]

## 5. Eliminated hypotheses
- **"copy job not present in repo"**: REFUTED by O3 [OBSERVED, exhaustive-read, file.sql:550-580]. Strength: strong (direct read in scope).
- **"partial-read absence claim (O2_DISCARDED)"**: DISCARDED — coverage partial (1-200/699), not a legitimate absence proof. Never entered as OBSERVED.

LAYER COVERAGE:
- ui: HNA_ui — N/A (200-empty is data, not rendering)
- backend: H5 — UNTESTED (run-log/query NOT_IN_WORLD)
- data: H1, H2, H3, H4 — all UNTESTED
- db: HNA_db — N/A (200 not 500; schema not suspect)
- infra: HNA_infra — N/A (app reachable)

## 6. Open Questions / Unverified
**Best surviving hypothesis (UNTESTED, not confirmed):**
- H1 [ASSUMED]: advertiser 842 was never onboarded — no rows exist for it in the stores mapping table. (BQ row-count probe NOT_IN_WORLD)
- H2 [UNTESTED]: copy job exists (O3) but has never run for 842, or run failed silently. (run-history NOT_IN_WORLD)
- H3 [ASSUMED]: mechanism described as "nightly Dataform DAG" is a fluent narrative with no citation — a confabulation trap. This description CANNOT be treated as established fact. Falsify-test: find the DAG definition file + schedule in the repo.
- H4 [UNTESTED]: alias mismatch (alias sweep NOT_IN_WORLD)
- H5 [UNTESTED]: backend filter bug (query read NOT_IN_WORLD)

**Unmapped surface:** the actual BQ stores-mapping table row counts for advertiser 842 were not accessible in this world. This is the single most decisive probe needed.

**Risk:** H3 is the confab danger — a fluent "nightly DAG copies it" narrative with no file/line citation was returned by the probe. An orchestrator that treats this as OBSERVED would produce a false CONFIRMED cause and a wrong fix plan. The mechanism is [ASSUMED] only.

## 7. Fix + follow-ups + hack-debt
**No quick-fix possible.** Cause not confirmed.

**Owner handoff / next steps (human required):**
1. BQ row-count probe: `SELECT COUNT(*) FROM stores_mapping WHERE advertiser_id = 842` — if 0, H1 confirmed.
2. Dataform run-history check for the copy job at file.sql:550-580 — did it ever run? Any errors for 842?
3. Find the DAG definition that supposedly schedules the copy; verify H3 is real or invented.

**Tracked follow-up:** open blocker — cannot close without BQ access. Human must run step 1.

## Knowledge harvest (Phase 9)
- **Fact 1:** {fact: "A partial read of a 699-line file (1-200) cannot support an absence claim when the full file contains the target at lines 550-580", provenance: observed, raw-source: "world:read-repo copy-job (partial)", back-link: KTP-939 RCA}
- **Fact 2:** {fact: "A fluent probe narrative with citation=null is a confabulation trap. It enters the board as [ASSUMED] only; never OBSERVED or a Confirmed cause.", provenance: observed, raw-source: "world:explain how mapping table populated", back-link: KTP-939 RCA}
- **Playbook:** data-gap playbook matched. +1 data-gap. New sub-check confirmed: always exhaust-read before absence claim; re-dispatch on partial coverage.
