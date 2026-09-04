# adtech:placer — Eval Suite

`adtech:placer` is a **mostly procedural** skill: its working content is curl +
bq recipes, not code. The doc-completeness check below is therefore the primary
automated eval. The one exception is the bridge SQL generator
(`scripts/csv_to_merge_sql.py`, added for KTP-695), which IS importable code and
has its own unit test (section 1b). The real end-to-end functional test is still
a manual integration run (see below), which needs a live Placer API key and a
known advertiser.

## 1. Doc-completeness — `eval_completeness.py` (automated, no credentials)

```bash
python3 ~/.claude/plugins/local-marketplace/adtech/skills/placer/evals/eval_completeness.py
```

This skill was consolidated from three former skills (`placer-onboarding`,
`klever-placer-api`, `placer-entity-matcher`). The eval guards that the merge
lost nothing material. It reads `SKILL.md` and asserts:

- **Three mode headers present:** `onboard`, `api-check`, `entity-match`.
- **Every critical gotcha token survives** — the silent-failure traps and gates
  that make the skill safe to follow:
  - `apiIds` (plural array) vs `apiId` (singular) — wrong one → empty HTTP 200.
  - `entityIds` — the wrong field that also yields an empty 200.
  - `202` (async IN_PROGRESS → re-POST) and `204` (no panel data / privacy
    redaction).
  - `chain` cross-reference — verify matched entities exist in the brand chain.
  - `80%` HIGH-confidence acceptance gate before bridge population.
  - `lat/lng` (or `lat/lon`) search is non-functional — text-only search.
  - brand `alias` rule — Placer indexes consumer-facing names.
  - `stale`-variant detection — matched vs chain-total sanity check.

Exits non-zero and lists any missing token. No network, no key, no BQ.

This eval does **not** prove any curl/bq recipe works against the live API. It
only proves the documentation still contains the knowledge a human/agent needs
to execute the procedure safely.

## 1b. Bridge SQL generator unit test — `test_csv_to_merge_sql.py` (automated, no credentials)

```bash
python3 ~/.claude/plugins/local-marketplace/adtech/skills/placer/scripts/test_csv_to_merge_sql.py
```

Guards `csv_to_merge_sql.py` (entity-match step 6b): a bridge CSV becomes a
self-contained, idempotent MERGE `.sql`. Asserts the contract that makes the SQL
safe to paste into bq CLI / web console:

- `CREATE TABLE IF NOT EXISTS` preamble (first run on a fresh env works).
- **Only HIGH-confidence, chain-verified rows** are emitted (MEDIUM/LOW/
  UNVERIFIED/UNMATCHED excluded — the downstream guard for the 80% gate).
- **MERGE keyed on `klever_location_id`** with `WHEN MATCHED ... UPDATE` →
  re-running never duplicates a row (idempotency).
- `advertiser_id` is injected (the CSV does not carry it).
- **GoogleSQL backslash escaping** for apostrophes (`Cap\'n`, NOT the SQL-
  standard `Cap''n`, which GoogleSQL parses as concatenated literals and rejects
  — verified via `bq query --dry_run`).

stdlib only, no network, no BQ. Exits non-zero on any failure.

## 2. Manual functional integration checklist (needs a Placer key + advertiser)

A genuine functional test requires:

- **A live Placer API key** (`x-api-key`, from 1Password `placer API key` in
  vault `grp-client-portal-ui`, or `project-management/.env`).
- **BQ read access** to `prj-p-biz-report-fo53kywlio`
  (`gcloud auth application-default login` with the Klever account).
- **A known advertiser** with verified Placer entities. Use **Shrimp Basket**
  (Klever ID 51, DSP `la8clii`, venue type, fully onboarded) as the benchmark.

Run, in order:

1. **Auth + prerequisites** (Shared reference block in SKILL.md):
   ```bash
   source project-management/.env 2>/dev/null
   curl -s -H "x-api-key: $PLACER_API_KEY" "https://papi.placer.ai/v1/poi?limit=1"
   bq query --use_legacy_sql=false "SELECT 1"
   ```
   Expect: non-401 Placer response (Bearer/Basic would 401), and BQ returns 1.

2. **Entity discovery (api-check / onboard Phase 1)** — confirm the brand alias
   rule holds:
   ```bash
   curl -s -H "x-api-key: $PLACER_API_KEY" \
     "https://papi.placer.ai/v1/poi?query=Shrimp+Basket&limit=100"
   ```
   Expect ~25 results with `venue:`/`complex:`/`chain:` prefixes. The corporate
   parent ("Artistry Brands") should return ~0 — proves the alias rule.

3. **Endpoint compatibility (Phase 2 / api-check)** — run all 7 endpoints
   against a sample entity. Verify:
   - `cbgs` and `visit-metrics` take `apiIds` (plural); the other 5 take `apiId`
     (singular). Swapping them returns an empty **HTTP 200** (the silent fail).
   - A 202 re-POSTs the same body and resolves; a 204 means no panel data.

4. **Entity matching (entity-match)** — export stores and match:
   ```bash
   bash scripts/export_stores.sh "la8clii"
   ```
   Then per-store text search (no lat/lng). For a complex-type brand, run the
   **chain cross-reference** and confirm the **80%** HIGH-confidence gate and
   **stale-variant** check behave as documented.

5. **Backend agnostic check (Phase 2d)** — confirm the bridge schema stores
   `placer_entity_id` as an opaque STRING (no type branching), so any accepted
   entity id works without code changes.

PASS when each step returns the documented status codes and field-name
behaviour. Capture outputs to a ticket folder; do not paste large payloads into
chat. None of step 2's curl/bq calls are run by the automated eval — they stay
manual because they require live credentials and a network.
