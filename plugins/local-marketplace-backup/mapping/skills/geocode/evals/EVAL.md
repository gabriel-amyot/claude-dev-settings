# proximity:geocode — Eval Suite

Evals for `scripts/geocode_locations.py` (ordered Nominatim/OSM address geocoder).

Split into a deterministic unit layer (no network, always run) and a small
opt-in live integration layer (hits real Nominatim, skippable).

## Layout

```
evals/
  _loader.py                      shared import helper (loads the script safely)
  eval_unit.py                    deterministic unit evals (NO network)
  eval_integration.py             live Nominatim check (network-dependent, skippable)
  fixtures/
    integration_addresses.tsv     3 known-good rows + 1 deliberately broken row
  EVAL.md                         this file
  _run_output/                    integration outputs land here (gitignore-able, never /tmp)
```

The script guards `main()` behind `if __name__ == "__main__"`, so importing it
is side-effect-free. `_loader.py` loads it by file path under an alias, verified
to run no network or I/O on import.

## How to run

```bash
cd evals

# Unit (fast, deterministic, no network) — the gate that must always pass:
python3 eval_unit.py

# Integration (live OSM, ~6-8s, respects the 1.1s rate limit):
python3 eval_integration.py
RUN_LIVE=0 python3 eval_integration.py    # explicit skip (exit 0)

# Syntax check everything:
python3 -m py_compile _loader.py eval_unit.py eval_integration.py
```

Both scripts exit nonzero on failure, zero on success. `eval_integration.py`
self-skips (exit 0) when OSM is unreachable, so it never blocks an offline CI.

## What is covered (automated)

### Unit — `eval_unit.py`
- **`clean_street`** — strips trailing `Unit F3`, `Suite 200`, `Ste 410`, `#5`,
  `, Apt 7`; leaves `31 Colossus Drive` / `1293 Kennedy Road` intact; idempotent;
  trims outer whitespace; never returns empty.
- **`build_tiers`** — tier ORDER contract:
  - first tier is `structured` (field-based dict, not a free-form `q`), with
    `clean_street` already applied;
  - last tier is `centroid`;
  - bare street+postal (no city/region) yields only `structured` + `centroid` —
    there is **no** q-based "street+postal" primary tier (that silently
    mis-resolves to the wrong city inside the region bbox);
  - no exact tier ever follows a centroid tier;
  - an empty row yields no tiers.
- **`in_bbox`** — QC / ON / CA / US presets exist; Montreal in QC not US;
  Toronto in ON and CA; NYC in US not QC/CA; corner-inclusive; just-outside excluded.
- **`fmt`** — 6-decimal formatting, negative padding, `None`/`""` → empty,
  numeric-string input (the resume path passes strings).

### Integration — `eval_integration.py`
- ORDER preserved (output row N ↔ input row N, by id).
- COUNT matches input exactly (failures stay as flagged rows, never dropped).
- Known-good coords within ~0.05° of expected (e.g. `1293 Kennedy Road,
  Toronto, ON M1P 2L4` ≈ 43.759, -79.278 — the proven KTP-755 Blinds To Go run).
- A deliberately broken row is flagged (`FAILED` / `APPROXIMATE` /
  `SUSPECT_OUT_OF_BBOX`) **in its original position** (slot 4).
- `latlong-paste.tsv` line count equals input row count (the top-left
  paste / fill-down alignment contract).

## What is NOT auto-tested (and why)

- **`read_rows` header/delimiter auto-detection** edge cases (CSV vs TSV sniffing,
  synonym header mapping, `--cols` override, `--has-header`). Indirectly exercised
  by the integration fixture (a headered TSV) but not unit-asserted across all
  permutations — would need its own fixture matrix. Candidate for a future
  `eval_read_rows.py`.
- **`load_resume` / `--resume`** logic (reusing a prior `verification.csv`).
  Stateful file round-trip; left manual.
- **`nominatim()` network/error handling** (timeouts, malformed JSON, empty
  results). Mocking the network is out of scope here; the integration eval covers
  the happy path against the real endpoint.
- **`main()` argument parsing / guards** (`/tmp` refusal, `--rate < 1.0` refusal,
  `--bbox` parsing, footprint summary printing). These are CLI-level; verify by
  hand or add a subprocess-based smoke test.
- **Exact coordinates / tier labels from OSM.** OSM data drifts over time, so the
  integration eval asserts a tolerance band (~0.05°) and a status class, never an
  exact lat/lon or a specific tier. If OSM materially changes how these fixture
  addresses resolve, the integration eval may need its `EXPECTED` values nudged;
  the unit eval is unaffected.
- **Rate-limit / OSM usage-policy compliance** is honored (1.1s) but not asserted;
  it is a courtesy contract with the live service, not a testable output.
