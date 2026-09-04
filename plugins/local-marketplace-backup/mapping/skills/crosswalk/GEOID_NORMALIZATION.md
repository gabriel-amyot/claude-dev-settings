# GEOID Normalization — Canonical Reference

> Canonical home for the GEOID-format knowledge behind `mapping:crosswalk`.
> **Authority: ADR D3 (KTP-683) + KTP-676.** The Klever frontend no longer normalizes
> GEOIDs at runtime — keep this doc in sync with those decisions; if they change, this
> doc changes. (Originally extracted from `app-front-portal/CLAUDE.md`, whose GEOID
> section KTP-683 has since rewritten to match the state described here.)

## The problem (the raw-data fact this skill exists for)

The US Census publishes the same geography under **two GEOID formats**. Raw tileset/
boundary source data uses the long Census form; report/database data uses the short
FIPS/ZCTA form. Joining the two forms without reconciling them silently produces zero
rows and **boundaries render empty / uncolored**.

| Source | County example | State example | ZCTA example |
|---|---|---|---|
| Report / database data (**DB form**) | `53033` | `53` | `90210` |
| Raw Census tileset feature `GEO_ID` (**Census form**) | `0500000US53033` | `0400000US53` | `8600000US90210` |

The Census form is the **GEO_ID / AFFGEOID** format: a summary-level header, the literal
`US`, then the FIPS/ZCTA code.

| Geography | Census summary level | Census-form prefix |
|---|---|---|
| State | 040 | `0400000US` |
| County | 050 | `0500000US` |
| ZCTA (ZIP) | 860 | `8600000US` |

## Current state in Klever (ADR D3 / KTP-683 / KTP-676)

**The Klever frontend does NO runtime GEOID normalization, and `normalizeCountyGeoid`
no longer exists.**

- **KTP-676** strips the Census prefix **at tileset-generation time**, so the published
  tilesets Klever consumes already carry clean codes: tileset `GEO_ID` is `53033`
  (US 5-digit FIPS) or `3506` (CA 4-digit CDUID), not `0500000US53033`.
- **KTP-683 (ADR D3)** then **deleted** the runtime `normalizeCountyGeoid` helper from
  `app-front-portal/components/map/functions/data-processors.tsx`. Both backend and
  tilesets now emit clean GEO_IDs, so the frontend uses `GEO_ID` **directly** for
  matching, lookups, and Mapbox expressions — no prefix stripping, no reconstruction.
- **Do NOT re-add `normalizeCountyGeoid`.** A regression test guards the clean-code
  invariant: `app-front-portal/components/map/docs/geography/test_geoid_regression.py`
  asserts every US county `GEO_ID` is exactly 5 digits with no `0500000US` remnant.

Historical note: before KTP-676/683 the frontend defined `normalizeCountyGeoid` and
every tileset-`GEO_ID` read had to call it. That era is over; references to the function
now live only in test/merge-pipeline comments as provenance.

## What this skill still does

The **raw-data fact** above has not changed: Census source data still ships in the long
form. So `mapping:crosswalk`'s `scripts/normalize_geoid.py` remains useful **upstream of
the Klever pipeline** — for reconciling raw Census/boundary input before it becomes a
clean tileset:

```bash
# Census form -> DB form (split on US, take the suffix; idempotent on clean input)
python3 scripts/normalize_geoid.py --to-db 0500000US53033       # -> 53033

# DB form -> Census form (inverse, needs level)
python3 scripts/normalize_geoid.py --to-tileset 53033 --level county   # -> 0500000US53033

# verify the rule
python3 scripts/normalize_geoid.py --self-test
```

`--to-db` is idempotent: an already-clean code (`53033`) has no `US`, so it passes
through unchanged — safe to run on mixed input.

## Frontend data storage convention

All county data is keyed by the **clean** GEOID (`"53033"` for US, `"3506"` for CA;
never `"0500000US53033"`):

```typescript
{
  [advertiserId]: {
    [date]: {
      CLICKS: { "53033": { Video: 1000, DOOH: 500 } },
      CONVERSIONS: { "53033": { Online: { Video: 100 } } }
    }
  }
}
```

`countyCenters` is keyed the same way. If a popup or color expression "can't find"
data, the first suspect is a key mismatch — but since the pipeline now emits clean codes
end-to-end, that should not occur for correctly-generated tilesets.

## Canada note

Canadian boundaries use a different code system entirely (FSA `CFSAUID`, Census Division
`CDUID`, Province `PRUID`) and do **not** carry the `…US` Census header, so the US
strip-prefix rule does not apply. Canadian PRUID -> alpha-2 province mapping lives at
`app-front-portal/components/map/docs/geography/pruid_to_alpha2.json`. Mapping between
Canadian code systems (FSA -> CD) is the job of the **`lookup`** mode against the KTP-679
crosswalk table, not the `normalize` mode.
