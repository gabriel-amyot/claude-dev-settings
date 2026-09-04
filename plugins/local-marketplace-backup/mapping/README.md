# mapping

Generic, **portable** map-data tooling — the reusable layer shared across *every*
map project (advertising / proximity, hiking, travel). One living source of truth in
the local marketplace: each project installs it, update once → reinstall everywhere,
no divergence.

The spine: **geocode → crosswalk/normalize → tileset prep → mapbox publish → verify.**

## Layering (see `project-management/documentation/architecture/mapping-ecosystem-design.md`)

- **This plugin (mapping)** holds only *generic* map jobs — nothing advertising-specific,
  nothing Klever-specific.
- **`adtech` plugin** holds advertising vendors (Placer, Goldfish) that feed map data.
  Composes WITH mapping for advertising use cases; never ships to hiking/travel.
- **`klever-data`** (loose Klever skills, not a plugin) is the BigQuery infra layer.
  `geocode-bq-locations` composes `mapping:geocode`.
- **"proximity" is a use case, not a plugin** = mapping + adtech + klever-data.

## Skills

| Skill | Invocation | Status | What it does |
|---|---|---|---|
| `geocode` | `mapping:geocode` | ✅ built + validated | Ordered address list → coordinates, order-preserved, OSM-only, bbox-validated. Output formats: sheet-tsv (default), geojson, csv. |
| `tileset` | `mapping:tileset` | ✅ built (ported from KTP-676) | Tileset prep pipeline (6 modes): download-sources, merge, validate-source, prepare (tippecanoe), validate-tiles, geoid-regression. Needs tippecanoe/mapshaper/GDAL/martin. |
| `mapbox` | `mapping:mapbox` | ✅ built | Mapbox Studio API: upload (proven), list, status, replace. list/status/replace want a live-token smoke test. |
| `crosswalk` | `mapping:crosswalk` | ✅ built | GEOID `normalize` (real, mirrors frontend rule), `lookup` (FSA→CD wired to KTP-679), `build-table` (specified). Owns `GEOID_NORMALIZATION.md`. |
| `location-scrape` | `mapping:location-scrape` | ✅ migrated | Scrape store/POI locations from the web → feeds `geocode`. Per-site template + helper. |

**Referenced by name, NOT forked** (live in `app-front-portal/.agents/skills/`):
`mapbox-cartography`, `mapbox-style-patterns`, `mapbox-style-quality`,
`mapbox-data-visualization-patterns`, `mapbox-search-integration`,
`mapbox-search-patterns`, `mapbox-store-locator-patterns`, `mapbox-token-security`,
`mapbox-web-integration-patterns`, `mapbox-web-performance-patterns`.

## Hard rules baked into the plugin

- **OSM/Nominatim is the only automated geocoder.** Never persist Mapbox or Google
  geocoding output (licensing). Attribution `(c) OpenStreetMap contributors`.
- **Outputs to committed folders, never `/tmp`.**
- **Order is sacred** — failures stay flagged in position; one top-left paste fills down.
- **Identity audit** before geocoding — confirm the footprint matches the brand.
