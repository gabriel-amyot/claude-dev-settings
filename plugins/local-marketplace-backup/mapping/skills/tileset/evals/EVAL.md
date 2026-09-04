# mapping:tileset — Eval Suite

Auto-eval for the **pure-Python** modes of the `tileset` skill, on tiny
synthetic fixtures. No external tools, no network, no real dataset.

## Run

```bash
python3 evals/eval_pipeline.py
# exit 0 = all checks passed, exit 1 = failure
```

The pipeline copies `fixtures/sources/` into `evals/_work/` (a committed-adjacent,
git-ignored work-dir — **never `/tmp`**), synthesizes a `centers/` tree from the
sources, then runs the real skill scripts against it. `_work/` is wiped and
rebuilt on every run.

## What's covered (auto-eval on synthetic data)

| Mode | Script | Coverage |
|---|---|---|
| `merge` (boundaries) | `merge_geojson.py` | `COUNTRY` tagging on every feature; US county prefix strip `0500000US36061 → 36061`; CA province `PRUID → STUSPS` (35→ON, 24→QC); CA census division `CDUID → GEO_ID`; CA FSA `CFSAUID → ZCTA5CE20`; US ZIP `ZCTA5CE20` preserved. |
| `merge` (centers) | `merge_geojson.py merge-centers` | Same renames applied to point features. |
| `geoid-regression` | `test_geoid_regression.py` | Clean 5-digit US FIPS, no `0500000US` remnants, CA 4-digit CDUID, `normalizeCountyGeoid` round-trip unchanged, US count preserved through merge. **Count-agnostic — passes cleanly on synthetic data.** |

### `validate-source` — run as a *documented expected-fail*

`validate_geojson.py` hard-asserts **real-world feature counts**: 13 provinces,
293 census divisions, 1643 FSAs (sources) and 56 US states, 3221 US counties,
1643 CA FSAs (merged). A 2-feature-per-source synthetic fixture cannot satisfy
these, and **we do not weaken the validator** to fake them.

Instead the eval runs `validate-source --merged` and asserts:
1. it exits **nonzero** on synthetic data (expected), and
2. every `FAIL` line is a **real-count mismatch only** — never a property or
   format error.

This proves the rename/format logic the validator enforces is satisfied by our
merged fixtures, while honestly surfacing that the count assertions require the
real dataset. The property/format correctness itself is positively asserted by
the eval's own direct checks on the merged output (see the `merge` rows above)
and by `geoid-regression`.

To run `validate-source` for real (full pass), point it at the real work-dir
with the complete US+CA dataset:

```bash
python3 scripts/validate_geojson.py \
  --work-dir app-front-portal/components/map/docs/geography
```

## Out of scope — MANUAL SMOKE ONLY

`prepare` and `validate-tiles` shell out to external tooling and need a real,
full-size dataset. They are **not** auto-eval'd. Smoke them manually against the
real work-dir:

**Requires:** `tippecanoe`, `mapshaper` (`npm i -g mapshaper`), GDAL / `ogr2ogr`,
`martin` (`cargo install martin`), and Python `requests` + `mapbox-vector-tile`.
Plus `us_zip.geojson` (downloaded manually — too large for git).

```bash
WORK=app-front-portal/components/map/docs/geography

# prepare: download → merge → centers → simplify → tippecanoe .mbtiles
bash scripts/prepare_tilesets.sh --work-dir "$WORK"

# validate-tiles: serve via Martin, decode, assert 100% feature coverage
python3 scripts/validate_tilesets.py --work-dir "$WORK" --yes
```

These exercise the parts the auto-eval cannot: shapefile reprojection, mapshaper
simplification/inner-points, tippecanoe zoom/feature-limit settings, and the
Martin tile-decode coverage check.

## Fixtures

`fixtures/sources/` — 2 features per source, crafted to exercise every rename:

| File | Features | Exercises |
|---|---|---|
| `us_county_5m.geojson` | NY `0500000US36061`, LA `0500000US06037` | US county prefix strip + source-prefix baseline |
| `us_state.geojson` | NY (NY), CA (CA) | US state `STUSPS` passthrough |
| `us_zip.geojson` | 10001, 90001 | US `ZCTA5CE20` passthrough |
| `ca_provinces.geojson` | ON `PRUID 35`, QC `PRUID 24` | `PRUID → STUSPS` |
| `ca_cd.geojson` | `CDUID 3506`, `2466` | `CDUID → GEO_ID` |
| `ca_fsa.geojson` | `CFSAUID K1A`, `H2X` | `CFSAUID → ZCTA5CE20` |

All geometries are small WGS84-valid polygons in the correct hemisphere.
PRUID values 35/24 map via the skill-bundled `pruid_to_alpha2.json` (ON/QC).
