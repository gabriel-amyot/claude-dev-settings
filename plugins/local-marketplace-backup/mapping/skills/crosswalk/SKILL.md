---
name: crosswalk
description: "Map between geographic code systems and normalize GEOIDs for tileset matching. FSA/CBG/postal <-> boundary GEOID, and DB-format <-> tileset-format GEOID normalization (e.g. '53033' <-> '0500000US53033'). Modes: normalize, lookup, build-table. Trigger: 'crosswalk FSA to', 'normalize geoid', 'map postal to boundary', 'CBG crosswalk', 'why don't my boundaries match the data'."
nav:
  bay: build
  when: "Mapping between code systems (FSA/CBG/postal/GEOID) or normalizing GEOIDs so data keys match tileset feature ids."
  when_not: "Geocoding addresses to coordinates (use mapping:geocode). Preparing the tiles themselves (use mapping:tileset)."
---

# mapping:crosswalk — Geographic Code Crosswalk & GEOID Normalization

Owns the "make the keys match" problem: mapping between geographic code systems and
normalizing GEOID formats so report data joins cleanly to tileset features. This is
the single home for GEOID normalization knowledge (see `GEOID_NORMALIZATION.md`).

## The core problem it solves
- **Format mismatch (raw Census data):** report data uses `53033`; raw Census boundary
  data carries `GEO_ID: "0500000US53033"`. Joining the two forms without reconciling
  them produces empty boundaries. **Note for Klever:** the Klever pipeline now strips
  the prefix at tileset-generation (KTP-676) and the frontend runtime normalizer was
  deleted (KTP-683 / ADR D3), so Klever tilesets are already clean and the frontend does
  no runtime normalization. This mode is for raw Census/boundary input upstream of that.
  Full detail in `GEOID_NORMALIZATION.md`.
- **System mapping:** postal/FSA <-> census CBG <-> boundary GEOID for joins and rollups.

## Modes

| Mode | Status | Does |
|---|---|---|
| `normalize` | **Real** | Canonicalize a GEOID to/from DB vs raw-Census form (strip/add the `…US` prefix). The Census-format rule; useful upstream of clean Klever tilesets (see note above). |
| `lookup` | **Real mechanism, wired to KTP-679 schema** | Resolve one code to another (FSA->CD, etc.) against a crosswalk CSV. Generic over any two columns. |
| `build-table` | **Specified** (one recipe implemented in klever-data-workflow) | Build/refresh a crosswalk table from authoritative sources. |

---

## `normalize` (solid core)

Implements the Census `…US`-prefix strip/add rule. This matches the logic the frontend
*used to* run via `normalizeCountyGeoid`, before KTP-683 (ADR D3) deleted it — Klever
tilesets are now clean end-to-end, so this mode is for raw Census input, not the live
frontend. Full knowledge in `GEOID_NORMALIZATION.md`.

```bash
# tileset form -> DB form (the production rule: split on "US", take suffix)
python3 scripts/normalize_geoid.py --to-db 0500000US53033        # -> 53033
python3 scripts/normalize_geoid.py --to-db 53033                 # -> 53033 (idempotent)

# DB form -> tileset form (inverse; level prefixes the Census GEO_ID header)
python3 scripts/normalize_geoid.py --to-tileset 53033 --level county   # -> 0500000US53033
python3 scripts/normalize_geoid.py --to-tileset 53    --level state    # -> 0400000US53

# batch from stdin (one GEOID per line)
cat geoids.txt | python3 scripts/normalize_geoid.py --to-db

# verify the rule
python3 scripts/normalize_geoid.py --self-test
```

Supported levels for `--to-tileset`: `county` (`0500000US`), `state` (`0400000US`),
`zcta` (`8600000US`).

---

## `lookup` (real mechanism — wired to the KTP-679 FSA->CD table)

`scripts/lookup_crosswalk.py` resolves one code to another against a crosswalk CSV.
It is generic over any two header columns, and is wired to the real KTP-679 schema.

```bash
# FSA -> Census Division
python3 scripts/lookup_crosswalk.py --table crosswalk_output.csv \
  --from CFSAUID --to CDUID --key M5V          # -> 3520 (Toronto)

# reverse: every FSA in a CD
python3 scripts/lookup_crosswalk.py --table crosswalk_output.csv \
  --from CDUID --to CFSAUID --key 3520

# full matched row(s) as JSON
python3 scripts/lookup_crosswalk.py --table crosswalk_output.csv \
  --from CFSAUID --key M5V --json
```

### Expected table format (FSA->CD, KTP-679 — real)

CSV with a header row matching the BigQuery table
`{project}.third_party_data.fsa_to_cd_crosswalk`:

| Column | Type | Example | Notes |
|---|---|---|---|
| `CFSAUID` | STRING | `M5V` | Forward Sortation Area (FSA), the join key |
| `CDUID` | STRING | `3520` | Census Division — population-weighted plurality CD for the FSA |
| `PRUID` | STRING | `35` | Province/territory code |
| `CDNAME` | STRING | `Toronto` | CD human-readable name |
| `PRNAME` | STRING | `Ontario` | Province human-readable name |

- 1,643 rows (one per Canadian FSA), unique `CFSAUID`, no NULLs.
- Fixtures: `M5V->3520`, `H2X->2466`, `V6B->5915`. Absent: `E2R`, `J5N`, `M7A`.

### Other crosswalk schemas (mechanism is generic; supply the CSV)

These tables exist in the Klever world but are not bundled here. Point `--from`/`--to`
at their columns:

| Crosswalk | Likely columns | Source |
|---|---|---|
| CBG -> ZIP (US) | `CBG_GEOID`, `ZIP` (+ weight) | KTP-130 / KTP-532 `build_cbg_zip_crosswalk.py`, loaded to BQ `851430.cen…` |
| ZCTA -> County (US) | `ZCTA`, `COUNTY_GEOID` | klever-data-workflow `zcta_to_county_crosswalk` (third_party_data) |

> Do not fabricate rows. If a table is needed and no authoritative CSV is on disk,
> build/refresh it (see `build-table`) or pull it from BigQuery.

---

## `build-table` (specified; one concrete recipe shipped)

The authoritative builders live in **klever-data-workflow** (not in this skill), so the
data and credentials stay in the data repo. This mode documents how to build/refresh.

### FSA -> CD crosswalk (KTP-679 — concrete, implemented)

Script: `klever-data-workflow/scripts/canada/build_fsa_to_cd_crosswalk.py`
(PR https://github.com/adminbeklever/klever-data-workflow/pull/249).

Recipe (population-weighted plurality):
1. Download Stats Canada 2021 Census sources:
   - DGRF (Dissemination Geography Relationship File): DA -> (CFSAUID, CDUID, PRUID).
     `https://www12.statcan.gc.ca/census-recensement/2021/geo/aip-pia/attribute-attribs/files-fichiers/2021_92-151-X_eng.zip`
   - DA population (Table 98-10-0002-01):
     `https://www150.statcan.gc.ca/n1/tbl/csv/98100002-eng.zip`
   - Geographic Attribute File (GAF) for `CDNAME` / `PRNAME` (may be embedded in DGRF).
2. Join DA rows to DA population on `DAUID`.
3. `GROUP BY CFSAUID, CDUID -> SUM(population)`.
4. For each `CFSAUID`, pick the `CDUID` with the max summed population (plurality).
5. Enrich with `CDNAME`, `PRNAME`.
6. Validate: exactly 1,643 rows, unique `CFSAUID`, no NULLs, ~260 distinct CDs;
   pin fixtures `M5V->3520`, `H2X->2466`, `V6B->5915`.
7. Load to BQ (idempotent `WRITE_TRUNCATE`), CSV fallback if write access is denied:
   ```bash
   bq load --source_format=CSV --replace --skip_leading_rows=1 \
     {project}:third_party_data.fsa_to_cd_crosswalk crosswalk_output.csv \
     CFSAUID:STRING,CDUID:STRING,PRUID:STRING,CDNAME:STRING,PRNAME:STRING
   ```

> **Known caveats (carried from KTP-679 handoff):**
> - **BQ write was blocked** at ship time (no `bigquery.tables.create` on
>   `third_party_data` in dev `prj-rnd-n-gimel-y0lz5vkrny` or prod
>   `prj-d-biz-report-im9q1fvvc7`). Until granted, the CSV + manual `bq load` above is
>   the path, and `lookup` runs against the CSV directly.
> - **T0J rural pin:** AC-1 expected `T0J->4803` (Foothills); the 2021 data yields
>   `T0J->4805` (Taber). The script uses the data-driven `4805`. Open spec question.

### Other tables (recipe pattern)

For CBG->ZIP and ZCTA->County, follow the same shape: download the authoritative
source (Census relationship/population files), aggregate to the target grain, validate
against fixtures, load idempotently. Builders live in `klever-data-workflow` /
ticket-data folders (KTP-130, KTP-532). This skill does not re-implement them.

---

## Consumers
- `mapping:tileset` (geoid-regression) enforces the clean-GEOID invariant documented in
  `GEOID_NORMALIZATION.md`. The Klever frontend no longer normalizes at runtime
  (KTP-683 / ADR D3) — it consumes clean codes directly.
- Use-case pages in the Bibliothèque reference this skill for the GEOID bridge.

## Notes
- Outputs to committed folders, never `/tmp`.
- `GEOID_NORMALIZATION.md` is the canonical home for this skill's GEOID-format knowledge.
  The `app-front-portal/CLAUDE.md` GEOID section was already rewritten by KTP-683 to
  match (clean codes, no runtime normalization), so it is NOT a one-line pointer — it
  stands on its own. Keep this skill's doc aligned with ADR D3 if that decision evolves.
