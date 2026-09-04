#!/usr/bin/env python3
"""
GEOID normalization: canonicalize between DB form and tileset (Census) form.

DB form (what report data returns):                  "53033"
Census form (what raw Census boundary GEO_ID carries): "0500000US53033"

The two MUST be reconciled to a single form before matching/aggregating,
or boundaries render empty (the join silently produces no matches).

This implements the Census `…US`-prefix rule. It matches the logic the Klever
frontend USED to run via `normalizeCountyGeoid` in
app-front-portal/components/map/functions/data-processors.tsx, before KTP-683
(ADR D3) deleted it:
    export const normalizeCountyGeoid = (geoid) =>
      geoid.includes("US") ? geoid.split("US")[1] : geoid;
Klever tilesets are now clean end-to-end (KTP-676), so this script is for raw
Census input upstream of the pipeline, not the live frontend.

`to_db` reproduces that rule (split on the first "US", take the suffix).
`to_tileset` is the inverse: prefix the DB code with the Census GEO_ID
header for its geography level (county/state/zcta), so a DB code can be
matched back to raw tileset features that still carry the prefix.

Dependency-free. Run the self-test with:  python3 normalize_geoid.py --self-test

Usage:
  normalize_geoid.py --to-db    0500000US53033        -> 53033
  normalize_geoid.py --to-db    53033                 -> 53033   (idempotent)
  normalize_geoid.py --to-tileset 53033 --level county -> 0500000US53033
  normalize_geoid.py --to-tileset 53   --level state   -> 0400000US53
  echo "0500000US53033" | normalize_geoid.py --to-db   (reads stdin, one per line)
"""

import argparse
import sys

# Census GEO_ID summary-level prefixes. The portion BEFORE "US" encodes the
# geographic summary level. These are the levels the portal tilesets use.
# Source: US Census GEO_ID / AFFGEOID format (summary level + geo component "US").
LEVEL_PREFIXES = {
    "county": "0500000US",   # summary level 050 (state-county)
    "state": "0400000US",    # summary level 040 (state)
    "zcta": "8600000US",     # summary level 860 (ZIP Code Tabulation Area)
}


def to_db(geoid: str) -> str:
    """Census form -> DB form. Implements the `…US`-prefix strip rule.

    "0500000US53033" -> "53033". Already-normalized input passes through.
    Splits on the FIRST "US" occurrence (matches JS String.split semantics
    of taking element [1]).
    """
    geoid = geoid.strip()
    if "US" in geoid:
        return geoid.split("US", 1)[1]
    return geoid


def to_tileset(geoid: str, level: str) -> str:
    """DB form -> tileset form. Inverse of to_db for a known level.

    "53033" + county -> "0500000US53033". If the input already carries a
    "US" prefix it is first reduced to DB form, then re-prefixed (idempotent).
    """
    if level not in LEVEL_PREFIXES:
        raise ValueError(
            f"unknown level '{level}'; expected one of {sorted(LEVEL_PREFIXES)}"
        )
    db = to_db(geoid)
    return LEVEL_PREFIXES[level] + db


def _self_test() -> int:
    cases_to_db = [
        ("0500000US53033", "53033"),   # county tileset -> db
        ("53033", "53033"),            # already db, idempotent
        ("0400000US53", "53"),         # state tileset -> db
        ("8600000US90210", "90210"),   # zcta tileset -> db
        ("  0500000US36061  ", "36061"),  # whitespace tolerated
        ("0500000US06037", "06037"),   # leading-zero FIPS preserved
    ]
    cases_to_tileset = [
        (("53033", "county"), "0500000US53033"),
        (("53", "state"), "0400000US53"),
        (("90210", "zcta"), "8600000US90210"),
        (("0500000US53033", "county"), "0500000US53033"),  # idempotent
        (("06037", "county"), "0500000US06037"),
    ]
    failures = []
    for inp, expected in cases_to_db:
        got = to_db(inp)
        if got != expected:
            failures.append(f"to_db({inp!r}) = {got!r}, expected {expected!r}")
    for (inp, lvl), expected in cases_to_tileset:
        got = to_tileset(inp, lvl)
        if got != expected:
            failures.append(
                f"to_tileset({inp!r}, {lvl!r}) = {got!r}, expected {expected!r}"
            )
    # round-trip: db -> tileset -> db is identity
    for db, lvl in [("53033", "county"), ("53", "state"), ("90210", "zcta")]:
        rt = to_db(to_tileset(db, lvl))
        if rt != db:
            failures.append(f"round-trip {db}/{lvl} = {rt!r}, expected {db!r}")

    if failures:
        print("SELF-TEST FAILED:", file=sys.stderr)
        for f in failures:
            print("  " + f, file=sys.stderr)
        return 1
    total = len(cases_to_db) + len(cases_to_tileset) + 3
    print(f"PASS: {total} normalization cases")
    return 0


def _iter_inputs(value):
    if value is not None:
        yield value
        return
    for line in sys.stdin:
        line = line.strip()
        if line:
            yield line


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Normalize a GEOID between DB and tileset form.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--to-db", action="store_true",
                   help="convert tileset form to DB form (strip the ...US prefix)")
    g.add_argument("--to-tileset", action="store_true",
                   help="convert DB form to tileset form (add the level prefix)")
    p.add_argument("--level", choices=sorted(LEVEL_PREFIXES),
                   help="geography level (required for --to-tileset)")
    p.add_argument("--self-test", action="store_true", help="run built-in tests and exit")
    p.add_argument("geoid", nargs="?", help="GEOID to convert; if omitted, reads stdin lines")
    args = p.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not (args.to_db or args.to_tileset):
        p.error("specify --to-db, --to-tileset, or --self-test")
    if args.to_tileset and not args.level:
        p.error("--to-tileset requires --level")

    for raw in _iter_inputs(args.geoid):
        if args.to_db:
            print(to_db(raw))
        else:
            print(to_tileset(raw, args.level))
    return 0


if __name__ == "__main__":
    sys.exit(main())
