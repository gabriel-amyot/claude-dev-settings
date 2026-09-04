---
name: tileset
description: "Tileset preparation pipeline for map boundary data (US+Canada by default, parameterized for other regions). Multi-mode: download-sources, merge, validate-source, prepare (tippecanoe), validate-tiles, geoid-regression. Produces .mbtiles ready to publish via mapping:mapbox. Trigger: 'prepare tilesets', 'build tiles', 'merge geojson', 'validate boundaries', 'tileset pipeline', 'refresh map boundaries'."
nav:
  bay: build
  when: "Preparing boundary/geometry data into tilesets: download sources, merge/validate GeoJSON, run tippecanoe, validate output tiles, check GEOID regression."
  when_not: "Publishing finished .mbtiles to Mapbox Studio (use mapping:mapbox). Geocoding addresses (use mapping:geocode)."
---

# mapping:tileset — Tileset Preparation Pipeline

Prepares raw boundary/geometry sources into validated `.mbtiles` tilesets — the
input to `mapping:mapbox` (publish). Ported from the proven US+Canada pipeline
(KTP-676). US+Canada is the working default; region-specific bits are
parameterized via flags so the same scripts serve other regions.

## Prerequisites

External tools (the scripts shell out to these):
- **tippecanoe** — `brew install tippecanoe` (or build from source). Produces `.mbtiles`.
- **mapshaper** — `npm install -g mapshaper`. Center-point generation + simplification.
- **GDAL / `ogr2ogr`** — `brew install gdal`. Shapefile → GeoJSON reprojection to WGS84.
- **martin** — `cargo install martin`. Local tile server used by `validate-tiles`.
- **Python 3** with `requests` and `mapbox-vector-tile` (`validate-tiles` only):
  `pip install requests mapbox-vector-tile`.

`curl` and `unzip` are assumed present.

## The `--work-dir` (geography data root)

Every mode operates on a single geography data root passed as `--work-dir`
(Python modes also accept `TILESET_WORK_DIR`). All outputs are written under it,
in committed subfolders — **never `/tmp`**:

```
<work-dir>/
  sources/      raw + reprojected GeoJSON (us_state, us_county_5m, us_zip, ca_*)
  centers/      mapshaper inner-point GeoJSON (per source)
  merged/       unified US+CA GeoJSON (boundaries + centers, COUNTRY-tagged)
  boundaries/   simplified merged polygon GeoJSON
  tiles/        *.mbtiles output  ← handed to mapping:mapbox
  pruid_to_alpha2.json   optional; falls back to the copy bundled with this skill
```

The proven instance of this root in the Klever repo is
`app-front-portal/components/map/docs/geography/`.

## Modes

Scripts live in `scripts/` under this skill. `SCRIPTS=~/.claude/plugins/local-marketplace/mapping/skills/tileset/scripts`.

| Mode | Script | Does |
|---|---|---|
| `download-sources` | `download_sources.sh` | Download zipped boundary shapefiles, reproject to WGS84 GeoJSON. |
| `merge` | `merge_geojson.py` | Merge US + CA sources into unified GeoJSON; add `COUNTRY`, normalize property names. |
| `validate-source` | `validate_geojson.py` | Assert source feature counts/properties and merged GEOID formats. |
| `prepare` | `prepare_tilesets.sh` | Full build: download → merge → centers → simplify → tippecanoe `.mbtiles`. |
| `validate-tiles` | `validate_tilesets.py` | Serve `.mbtiles` with Martin, decode tiles, assert feature coverage. |
| `geoid-regression` | `test_geoid_regression.py` | Regression-check merged GEOID format/coverage vs the normalize rule. |

### download-sources
```bash
bash "$SCRIPTS/download_sources.sh" --work-dir <work-dir>
```
- **Inputs:** none (downloads from `--base-url`). Default dataset = Statistics
  Canada 2021 Census Cartographic Boundary Files (provinces, census divisions,
  FSAs). Idempotent — skips any output that already exists.
- **Generalize:** `--base-url <url>` plus one or more
  `--dataset <zip>:<output.geojson>:<description>` triples for other regions.
  Source URLs for non-Canada regions are intentionally not hardcoded; supply
  them explicitly rather than fabricating authoritative URLs.
- **Outputs:** `<work-dir>/sources/ca_provinces.geojson`, `ca_cd.geojson`, `ca_fsa.geojson` (defaults), each WGS84. Prints SHA256 hashes for reproducibility.
- **Note:** US sources (`us_state.geojson`, `us_county_5m.geojson`, `us_zip.geojson`) are supplied separately. `us_zip.geojson` is too large for git and is downloaded manually (a Google Drive link is printed when missing).

### merge
```bash
python3 "$SCRIPTS/merge_geojson.py" --work-dir <work-dir>                # boundaries
python3 "$SCRIPTS/merge_geojson.py" --work-dir <work-dir> merge-centers  # center points
```
- **Inputs:** `<work-dir>/sources/*` (boundaries) or `<work-dir>/centers/*` (centers).
- **Property normalization (CA → US conventions):** `PRUID → STUSPS` (via `pruid_to_alpha2.json`), `CDUID → GEO_ID`, `CFSAUID → ZCTA5CE20`. US county `GEO_ID` prefix stripped (`0500000US36061 → 36061`). All features tagged `COUNTRY: US|CA`.
- **Outputs:** `<work-dir>/merged/{state,county,zip}_boundaries.geojson` and `{state,county,zip}_centers.geojson`.

### validate-source
```bash
python3 "$SCRIPTS/validate_geojson.py" --work-dir <work-dir>             # all
python3 "$SCRIPTS/validate_geojson.py" --work-dir <work-dir> --sources   # raw sources only
python3 "$SCRIPTS/validate_geojson.py" --work-dir <work-dir> --merged    # merged output only
```
- **Inputs:** `sources/` and/or `merged/` GeoJSON.
- **Checks:** feature counts (13 provinces, 293 CDs, 1643 FSAs; 56 US states, 3221 US counties), required IDs, WGS84 bounds, US county source prefix baseline, merged GEOID format per country. Missing files are skipped (not failed). Exit 1 on any assertion failure.

### prepare
```bash
bash "$SCRIPTS/prepare_tilesets.sh" --work-dir <work-dir>
```
- **Inputs:** `<work-dir>/sources/*` (auto-runs `download-sources` if CA sources missing; errors if `us_zip.geojson` missing).
- **Steps:** download (if needed) → `merge` → mapshaper inner-point centers → `merge-centers` → mapshaper simplify (states 10%, counties 7%, ZIPs 5%) → tippecanoe centers (`--drop-rate=0 --no-feature-limit --no-tile-size-limit`) → tippecanoe boundaries (`--use-attribute-for-id`, `--no-feature-limit`). Zoom strategy: states Z2–5, counties Z4–6, ZIPs Z6–8.
- **Outputs:** `<work-dir>/tiles/{state,county,zip}_{boundaries,centers}.mbtiles`.

### validate-tiles
```bash
python3 "$SCRIPTS/validate_tilesets.py" --work-dir <work-dir> [--yes]
```
- **Inputs:** `<work-dir>/tiles/*.mbtiles` (plus `sources/` and `centers/` for the boundary-vs-center cross-check).
- **Does:** boundary↔center correspondence check, then starts Martin, decodes tiles at known locations, validates CA feature properties, and scans every tile at each center tileset's min zoom to confirm 100% feature coverage (validates the `--no-feature-limit` setting). `--yes` skips the interactive prompt on a boundary/center mismatch.
- **Note:** known null-geometry FSAs (`E2R`, `J5N`, `M7A`) are excluded from "missing center" failures.

### geoid-regression
```bash
python3 "$SCRIPTS/test_geoid_regression.py" --work-dir <work-dir>
```
- **Inputs:** `<work-dir>/merged/county_boundaries.geojson` and `sources/us_county_5m.geojson`.
- **Checks:** US `GEO_ID` is clean 5-digit FIPS, CA is clean 4-digit, no `0500000US` remnants, the frontend `normalizeCountyGeoid` round-trips unchanged, and US feature count survives the merge. Exit 1 on failure.

## Pipeline order

```
download-sources → merge → validate-source → prepare → validate-tiles → geoid-regression
```
`prepare` internally re-runs download + merge, so the typical flow is:
`prepare` (build everything) → `validate-source --merged` → `validate-tiles` →
`geoid-regression`. Then hand the `.mbtiles` in `<work-dir>/tiles/` to
**`mapping:mapbox` (mode `upload`)** to publish to Mapbox Studio.

## Notes
- GEOID format normalization is owned by `mapping:crosswalk`; `geoid-regression`
  consumes that rule and checks the merged output against it.
- Outputs always go to committed folders under `--work-dir`, never `/tmp`.
- `pruid_to_alpha2.json` is bundled with this skill as a fallback; a copy in
  `<work-dir>` takes precedence if present.
