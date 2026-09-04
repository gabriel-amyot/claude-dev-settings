# Eval Suite — `mapping:crosswalk` skill

Deterministic, stdlib-only eval suite for the two crosswalk scripts. Each eval
drives its target **via the CLI (subprocess)** rather than importing functions,
so the full path is exercised: argparse wiring, `--level`/`--to`/`--from`
handling, stdin batch mode, and process exit codes. This matches how callers
actually invoke the scripts and catches CLI regressions that an import-only test
would miss.

## How to run

```bash
cd <skill>/evals
python3 eval_normalize.py   # exit 0 = pass; nonzero = number of failed checks
python3 eval_lookup.py      # exit 0 = pass; nonzero = number of failed checks
```

Both print `PASS: N checks` on success and exit `0`. On failure they print each
failing check to stderr and exit with the failure count (assert-style, nonzero).

No arguments, no env, no network, no `/tmp`. The lookup eval reads only
`fixtures/fsa_to_cd_sample.csv` (relative to the eval file).

Last run: `eval_normalize.py` → PASS 35 checks; `eval_lookup.py` → PASS 27 checks.

## Coverage

### `eval_normalize.py` (target: `scripts/normalize_geoid.py`) — 35 checks

| Area | Cases |
|------|-------|
| `to_db` (tileset → DB) | `0500000US53033`→`53033`; idempotent `53033`→`53033`; state `0400000US53`→`53`; zcta `8600000US90210`→`90210`; whitespace `  0500000US36061  `→`36061`; leading-zero FIPS `0500000US06037`→`06037` |
| `to_tileset` (DB → tileset) | county `53033`→`0500000US53033`; state `53`→`0400000US53`; zcta `90210`→`8600000US90210`; idempotent `0500000US53033`+county→same; leading-zero `06037`→`0500000US06037` |
| Round-trip stability | `db → to_tileset → to_db == db` for county/state/zcta/leading-zero |
| stdin batch | multi-line `--to-db` over mixed tileset/DB inputs |
| Error paths | `--to-tileset` without `--level` → nonzero; unknown level `tract` → nonzero (argparse `choices`) |
| Built-in self-test | script's own `--self-test` exits 0 |

Every positive case also asserts a zero exit code alongside the value.

### `eval_lookup.py` (target: `scripts/lookup_crosswalk.py`) — 27 checks

| Area | Cases |
|------|-------|
| Forward (`CFSAUID`→`CDUID`) | Known anchors M5V→3520, H2X→2466, V6B→5915, plus T2P→4806, K1P→3506 |
| Reverse (`CDUID`→`CFSAUID`) | CD `3520` → `M5V`,`M5H` (multiple, **distinct/deduped**, fixture order preserved) |
| JSON output | `--json` for M5V: single-row list; CDUID/PRUID/CDNAME/PRNAME values; exact 5-field schema set |
| stdin batch | `M5V\nH2X\nV6B` → `3520\n2466\n5915` |
| No-match (value mode) | `Z9Z` → nonzero exit, empty stdout, `no match` on stderr |
| No-match (JSON mode) | `Z9Z --json` → nonzero exit, `[]` on stdout |
| Column validation | unknown `--from NOPE` → nonzero exit |

### Fixture: `fixtures/fsa_to_cd_sample.csv`

KTP-679 schema header `CFSAUID,CDUID,PRUID,CDNAME,PRNAME`, 6 rows. Includes the
three documented anchors (M5V/H2X/V6B) plus T2P, K1P, and a second Toronto FSA
(M5H→3520) specifically so reverse lookup returns a multi-value deduped result.

## Not auto-tested (gaps / out of scope)

- **Real BigQuery table.** `lookup_crosswalk.py` is CSV-first by design (BQ write
  was blocked at KTP-679 ship). The eval validates CSV behavior only; the
  authoritative `third_party_data.fsa_to_cd_crosswalk` table is not queried.
- **Full 1,643-row crosswalk correctness.** Fixture is a 6-row sample. It proves
  lookup mechanics and the known anchors, not data completeness of the real table.
- **CSV edge cases** not exercised: missing header / empty file (`load_table`
  raises `ValueError`), duplicate header columns, embedded newlines/quoting,
  non-UTF-8 encodings, trailing whitespace inside cells.
- **Performance / large inputs.** No scale or timing assertions.
- **Mapbox / production parity.** `to_db` mirrors the frontend `normalizeCountyGeoid`
  rule by inspection; there is no live cross-check against the running portal.
- **Non-Census GEO_ID forms.** Only county/state/zcta level prefixes exist in the
  script; tract, block-group, place, etc. are intentionally unsupported and untested.
