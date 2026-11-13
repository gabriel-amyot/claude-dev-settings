---
name: klever-demo-seed
description: Generate AND load a Canadian demo-data seed for the Measurement Map (proximity) for a demo advertiser. TWO paths — (A) DURABLE Bronze CSVs (generate_bronze_csv.py) dropped in the daily-import bucket so the Cloud Function + Dataform rebuild Gold on every run (survives the daily rebuild); (B) EPHEMERAL direct-Gold ndjson (generate_canada_demo_seed.py + load_seed.sh) wiped within ~24h by Dataform. Prefer path A for any demo that must persist. Use when the user wants to fabricate proximity demo data, seed a demo advertiser, create Canada demo data, or says "generate demo seed", "canada demo data", "seed a demo advertiser", "fabricate proximity demo data", "load the demo seed", "durable demo data", "demo data that persists". Klever org.
nav:
  bay: build
  when: "Need fabricated, believable Canadian proximity demo data for a demo advertiser so the Measurement Map renders province / census-division / FSA choropleth — generate it and load it without writing a generator from scratch each time."
  when_not: "Real customer data; US advertisers (footprint is Canadian); visitor flow lines (handled by the backend BQ adapter / KTP-699, not this seed). The loader writes to dev BQ only on an explicit, confirmed run — review the dry-run first."
  org: klever
---

# klever-demo-seed

Generate a demo seed for a Canadian Measurement-Map advertiser. Two paths — pick by whether the
demo must survive the daily Dataform rebuild.

## Path A — DURABLE Bronze CSVs (preferred) — `generate_bronze_csv.py`

The Gold proximity tables are rebuilt by Dataform on a rolling 30-day window every run, so a direct
Gold seed (Path B) is wiped within ~24h. Path A instead produces the upstream **Bronze demo-dsp
CSVs** that the `cloud-storage-to-bigquery` Cloud Function ingests; Dataform then rebuilds Gold from
them every run, so the demo persists.

```bash
# 1. Dump the CURRENT locations table (the locations CSV is OVERRIDE-all — must keep every advertiser):
bq query --project_id=prj-d-biz-report-im9q1fvvc7 --use_legacy_sql=false --format=csv \
  'SELECT DSP,DSP_PARTNER_ID,DSP_ADVERTISER_ID,KLEVER_LOCATION_ID,ADDRESS,LATITUDE,LONGITUDE,LOCATION_NAME,STATE,COUNTRY,CITY,ZIP_CODE FROM `prj-d-biz-report-im9q1fvvc7.klever_daily_data_import.demo_dsp_advertiser_locations`' > current_locations.csv

# 2. Generate the 4 Bronze CSVs:
python3 scripts/generate_bronze_csv.py \
  --advertiser-id 842 --brand "Lumberjack Pastries" \
  --dsp-advertiser-id demo842 --dsp-partner-id demo371fdcf \
  --start-date 2026-03-01 --end-date 2026-06-30 \
  --preserve-locations-csv current_locations.csv \
  --location-id-base 1000842001 --out-dir bronze

# 3. Drop them in the dev daily-import bucket (Cloud Function ingests within seconds, archives + deletes source):
gcloud storage cp bronze/*.csv gs://bkt-daily-import-im9q1fvvc7/

# 4. Trigger Dataform daily (or wait for the nightly run). The dev repo compiles from gitCommitish=dev:
#    POST .../repositories/klever-data-workflow/compilationResults {gitCommitish:dev, codeCompilationConfig:{defaultDatabase:prj-d-biz-report-im9q1fvvc7}}
#    POST .../workflowInvocations {compilationResult:<name>, invocationConfig:{includedTags:[daily], transitiveDependenciesIncluded:true}}
#    Dataform repo: project prj-d-biz-report-im9q1fvvc7, location us-central1.
```

**Hard requirements (read-proven 2026-06-16):**
- The advertiser MUST be in `klever_core_entities.dsp_account` with `DSP_PROVIDER_ID = <dsp-advertiser-id>`,
  `ADVERTISER_ID = <klever-id>`, `DSP='DEMO'` (the Bronze→Gold join is INNER — no row = data dropped).
- Bronze `ZIP` must be a 3-char FSA (`^[A-Za-z]\d[A-Za-z]$`) → COUNTRY='CA' is derived by regex; pick FSAs
  present in `third_party_data.fsa_to_cd_crosswalk.CFSAUID` so CDUID/PRUID populate (LEFT JOIN).
- REPORT files use entity `advertiser_<dsp-advertiser-id>` in the filename so the delete-before-append is
  scoped to THIS advertiser only (using the shared partner would wipe other demo advertisers' rows).
- Bronze DATE must stay within the last ~30 days to surface in Gold; re-upload with shifted dates to refresh.

This path persists across Dataform runs but Gold only shows the rolling-30-day window of the Bronze dates;
a long-lived demo still needs periodic date-shifted re-upload (the unbuilt "demo dsp" refresh job, KTP-769).

## Path B — EPHEMERAL direct-Gold seed — `generate_canada_demo_seed.py` + `load_seed.sh`

Stdlib-only scripts that stage Gold-table ndjson and load it **directly** into `klever_proximity_data.*`.
Fast for a throwaway/local check, but **Dataform wipes it within ~24h.** Details below.

## Quick start

```bash
python3 scripts/generate_canada_demo_seed.py \
  --advertiser-id <KLEVER_ADVERTISER_ID> \
  --brand "Lumberjack Pastries" \
  --seed 42 --start-date 2026-05-06 --end-date 2026-06-01 \
  --out-dir staged
```

Outputs in `staged/`: `zip_performance_<id>.ndjson`, `country_performance_<id>.ndjson`,
`locations_<id>.csv`, `load_<id>.sql`, `README.md` (the runbook).

## Prereqs

- The advertiser must already exist in **user-management** (Klever demo agency 133) so it is
  portal-selectable; UM assigns the `KLEVER_ADVERTISER_ID`. Pass that id. **Never reuse an existing
  advertiser ID** (e.g. 826 Taco Chain, 827 FitConnect, 835 Blinds To Go) for a new fabricated brand.
- Python 3 (stdlib only — no install).

## What it generates (and what actually renders)

- **zip table** rows: `STATE`=full province name, `ZIP`=FSA, `COUNTRY`=CA → feeds the **province
  (state-zoom) + FSA** layers.
- **country table** rows: `PRUID` + bare 4-digit `CDUID`, FIPS columns NULL → feeds the
  **census-division** layer.
- **locations CSV**: for the Google-Sheet import path — do NOT load directly
  (`proximity_advertiser_locations` is Dataform-rebuilt from a Sheet).

## Load (manual — run the loader script)

Use the bundled **`scripts/load_seed.sh`** — it backs up first, deletes the advertiser's rows
(scoped), loads the two ndjson, and verifies ≥5 provinces. Run it from the staged dir:

```bash
cd <staged-dir>                                  # where the *_<id>.ndjson files are
bash load_seed.sh --advertiser-id <id>           # backup -> confirm -> delete -> load -> verify
bash load_seed.sh --advertiser-id <id> --dry-run # rehearse, runs nothing
bash load_seed.sh --advertiser-id <id> --yes     # skip the confirm prompt
```

Safety brakes: refuses unless the matching `*_<id>.ndjson` exist (can't target a random advertiser);
backs up BOTH tables to `backups/` before any delete (aborts if backup fails, `set -e`); DELETE is
advertiser-scoped; idempotent (re-run safe); confirm gate; `--dry-run`. The script writes to BQ only
on a real (non-dry, confirmed) run. **Not in the script's control:** if Dataform rebuilds the tables it
may wipe seeded rows — check rows persist a day later; if not, seed at the Sheet/Dataform source.

Store locations (`locations_<id>.csv`) still go via the Google Sheet (that table is Dataform-rebuilt).
The older `load_<id>.sql` is the raw runbook; `load_seed.sh` supersedes it.

## Customizing brand / footprint

- `--brand` sets the advertiser/location display name (and the location-id slug).
- Geography lives in `scripts/geography.py` `FOOTPRINT`. Edit it to add provinces / urban clusters.
  Rules: `STATE` = full StatCan province name; `PRUID` = 2-digit; `CDUID` = **bare 4-digit** with
  first 2 digits == `PRUID`; `FSA` matches `^[A-Z]\d[A-Z]$`.

## Constraints / gotchas

- **CDUID must be bare 4-digit** (e.g. `3506`) — it must equal the `county_boundaries` tileset
  `GEO_ID`.
- **Census-division coloring needs a backend change** (the county adapter must read `CDUID` for
  `country=CA`). Until it lands, provinces + FSAs render but CDs do NOT. Contract:
  `project-management/tickets/KTP/KTP-559/KTP-728/reports/architecture/cd-layer-canada-contract.md`.
- **Mixed US/CA HTTP-400**: the backend rejects a request mixing US + CA region codes. Verify with
  CA-only `/api/v1/map/data/*` calls; cross-border viewport rendering is a separate ticket.
- Province choropleth filters by `STATE` full-name (verified live against advertiser 835 / Blinds To
  Go, which colors Ontario + Quebec from the base tables — no view needed).

This is fabricated demo data: believable, not real. Origin: KTP-728 (Lumberjack Pastries).
