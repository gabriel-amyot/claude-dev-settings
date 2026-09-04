#!/usr/bin/env python3
"""Deterministic UNIT evals for proximity:geocode pure functions. NO network.

Covers the pure, side-effect-free functions in scripts/geocode_locations.py:
  - clean_street      strip trailing unit/suite/apt/#, leave plain streets intact
  - build_tiers       tier ORDER contract (structured first, centroid last,
                      bare street+postal is NOT a q-based primary tier)
  - in_bbox           QC / ON / CA / US presets + known in/out points
  - fmt               output formatter (6-decimal, blanks for None/"")

Run:
  python3 eval_unit.py
Exit code is nonzero on any failure; each failure prints a clear message.
"""

import sys

from _loader import load_geocoder

G = load_geocoder()

_failures = []
_passed = 0


def check(cond, msg):
    global _passed
    if cond:
        _passed += 1
    else:
        _failures.append(msg)
        print(f"FAIL: {msg}", file=sys.stderr)


# --------------------------------------------------------------------------
# clean_street
# --------------------------------------------------------------------------
def test_clean_street():
    cs = G.clean_street

    # Strips trailing unit/suite/apt/#/room designators.
    check(cs("501 Earl Grey Drive Unit F3") == "501 Earl Grey Drive",
          f"clean_street: 'Unit F3' not stripped -> {cs('501 Earl Grey Drive Unit F3')!r}")
    check(cs("100 Main St Suite 200") == "100 Main St",
          f"clean_street: 'Suite 200' not stripped -> {cs('100 Main St Suite 200')!r}")
    check(cs("45 King St #5") == "45 King St",
          f"clean_street: '#5' not stripped -> {cs('45 King St #5')!r}")
    check(cs("12 Yonge St, Apt 7") == "12 Yonge St",
          f"clean_street: ', Apt 7' not stripped -> {cs('12 Yonge St, Apt 7')!r}")
    check(cs("8 Bay St Ste 410") == "8 Bay St",
          f"clean_street: 'Ste 410' not stripped -> {cs('8 Bay St Ste 410')!r}")

    # Plain street with a trailing number-as-name must be left INTACT.
    check(cs("31 Colossus Drive") == "31 Colossus Drive",
          f"clean_street: plain street altered -> {cs('31 Colossus Drive')!r}")
    check(cs("1293 Kennedy Road") == "1293 Kennedy Road",
          f"clean_street: plain street altered -> {cs('1293 Kennedy Road')!r}")

    # Idempotent: cleaning a clean street is a no-op.
    once = cs("501 Earl Grey Drive Unit F3")
    check(cs(once) == once, "clean_street: not idempotent on already-clean input")

    # Whitespace is normalized but a never-empty guarantee holds.
    check(cs("   77 Spadina Ave   ") == "77 Spadina Ave",
          f"clean_street: outer whitespace not trimmed -> {cs('   77 Spadina Ave   ')!r}")


# --------------------------------------------------------------------------
# build_tiers
# --------------------------------------------------------------------------
def test_build_tiers():
    bt = G.build_tiers

    full = {"id": "1", "street": "1293 Kennedy Road Unit 4",
            "city": "Toronto", "region": "ON", "postal": "M1P 2L4"}
    tiers = bt(full, "ca")
    labels = [t[0] for t in tiers]

    # Contract 1: the FIRST tier is the structured query (a dict, no 'q').
    check(labels[0] == "structured",
          f"build_tiers: first tier should be 'structured', got {labels[0]!r} ({labels})")
    first_params = tiers[0][1]
    check("q" not in first_params and "street" in first_params,
          f"build_tiers: structured tier must be field-based, got {first_params!r}")
    # clean_street is applied inside build_tiers (unit stripped for the query).
    check(first_params.get("street") == "1293 Kennedy Road",
          f"build_tiers: structured street not cleaned -> {first_params.get('street')!r}")

    # Contract 2: the LAST tier is a centroid (approximate) fallback.
    check(labels[-1] == "centroid",
          f"build_tiers: last tier should be 'centroid', got {labels[-1]!r} ({labels})")

    # Contract 3: bare street+postal is NOT offered as a q-based primary tier.
    # With only street+postal (no city, no region), the tiers must be exactly
    # structured then centroid(s) — never a free-form 'street, postal' q query
    # (that silently mis-resolves to the wrong city within the region bbox).
    spo = {"id": "2", "street": "1293 Kennedy Road",
           "city": "", "region": "", "postal": "M1P 2L4"}
    spo_tiers = bt(spo, "ca")
    spo_labels = [t[0] for t in spo_tiers]
    check(spo_labels[0] == "structured",
          f"build_tiers(street+postal): first tier should be structured, got {spo_labels}")
    check(all(l in ("structured", "centroid") for l in spo_labels),
          f"build_tiers(street+postal): unexpected primary tier present -> {spo_labels}")
    # No q-tier should contain ONLY the street and the postal of an unknown city.
    for label, params in spo_tiers:
        if "q" in params:
            check(label == "centroid",
                  f"build_tiers(street+postal): q-tier {label!r} present "
                  f"(only centroid q-tiers allowed) -> {params!r}")

    # Contract 4: centroid tiers always come AFTER any exact tiers.
    first_centroid = next((i for i, l in enumerate(labels) if l == "centroid"), len(labels))
    exact_after = [l for l in labels[first_centroid:] if l != "centroid"]
    check(not exact_after,
          f"build_tiers: exact tier appears after a centroid tier -> {labels}")

    # Contract 5: a row with no street and no locality yields no tiers.
    empty = {"id": "3", "street": "", "city": "", "region": "", "postal": ""}
    check(bt(empty, "ca") == [],
          f"build_tiers: empty row should yield no tiers, got {bt(empty, 'ca')!r}")


# --------------------------------------------------------------------------
# in_bbox  (REGION_BBOX presets + a known in/out point)
# --------------------------------------------------------------------------
def test_in_bbox():
    ib = G.in_bbox
    bb = G.REGION_BBOX

    for preset in ("QC", "ON", "CA", "US"):
        check(preset in bb, f"REGION_BBOX missing preset {preset!r}")

    # Montreal (~45.50, -73.57) is inside QC.
    check(ib(45.5017, -73.5673, bb["QC"]), "in_bbox: Montreal not inside QC bbox")
    # NOTE: the coarse US bbox (24-50 lat) overlaps southern Canada, so Montreal
    # also falls inside US — that's expected and fine, the US preset is a rough
    # contiguous-US box, not a precise border. Use a far-northern QC point to
    # confirm the US preset excludes the high latitudes.
    check(not ib(58.0, -70.0, bb["US"]),
          "in_bbox: northern QC point wrongly inside US bbox")
    check(ib(58.0, -70.0, bb["QC"]),
          "in_bbox: northern QC point not inside QC bbox")

    # Toronto (~43.65, -79.38) inside ON and CA.
    check(ib(43.6532, -79.3832, bb["ON"]), "in_bbox: Toronto not inside ON bbox")
    check(ib(43.6532, -79.3832, bb["CA"]), "in_bbox: Toronto not inside CA bbox")

    # Manhattan (~40.71, -74.00) inside US, not inside QC/ON/CA.
    check(ib(40.7128, -74.0060, bb["US"]), "in_bbox: NYC not inside US bbox")
    check(not ib(40.7128, -74.0060, bb["QC"]), "in_bbox: NYC wrongly inside QC bbox")
    check(not ib(40.7128, -74.0060, bb["CA"]), "in_bbox: NYC wrongly inside CA bbox")

    # Boundary inclusivity: corners are inside (<=, >=).
    lat_min, lat_max, lon_min, lon_max = bb["QC"]
    check(ib(lat_min, lon_min, bb["QC"]), "in_bbox: lower corner should be inclusive")
    check(ib(lat_max, lon_max, bb["QC"]), "in_bbox: upper corner should be inclusive")
    # Just outside the corner is excluded.
    check(not ib(lat_min - 0.001, lon_min, bb["QC"]),
          "in_bbox: point below lat_min should be excluded")


# --------------------------------------------------------------------------
# fmt  (output formatter)
# --------------------------------------------------------------------------
def test_fmt():
    fmt = G.fmt
    check(fmt(43.7591234) == "43.759123",
          f"fmt: 6-decimal formatting wrong -> {fmt(43.7591234)!r}")
    check(fmt(-79.2783) == "-79.278300",
          f"fmt: negative/pad wrong -> {fmt(-79.2783)!r}")
    check(fmt(None) == "", f"fmt(None) should be empty, got {fmt(None)!r}")
    check(fmt("") == "", f"fmt('') should be empty, got {fmt('')!r}")
    # Accepts numeric strings (verification.csv resume path passes strings).
    check(fmt("43.5") == "43.500000", f"fmt('43.5') wrong -> {fmt('43.5')!r}")


def main():
    test_clean_street()
    test_build_tiers()
    test_in_bbox()
    test_fmt()

    total = _passed + len(_failures)
    print(f"\n=== UNIT EVAL: {_passed}/{total} assertions passed ===")
    if _failures:
        print(f"{len(_failures)} FAILED:")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("All unit assertions passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
