#!/usr/bin/env python3
"""
Eval suite for the mapping:tileset skill — PURE-PYTHON modes only.

Covers, on tiny synthetic fixtures:
  - merge          (merge_geojson.py)       boundaries + centers
  - geoid-regression (test_geoid_regression.py)
  - validate-source (validate_geojson.py)   property/format logic (run as a
                    documented expected-fail: it hard-asserts REAL feature
                    counts — 56 US states, 3221 counties, 1643 FSAs — which a
                    synthetic fixture cannot satisfy. We assert it fails ONLY on
                    count mismatches, never on property/format errors, and we do
                    NOT weaken the validator.)

prepare / validate-tiles are OUT OF SCOPE (need tippecanoe/mapshaper/GDAL/martin
+ a real dataset). See EVAL.md for the manual smoke command.

Work-dir discipline: fixtures are COPIED into evals/_work/ (committed-adjacent,
git-ignorable), NEVER /tmp. The copy is wiped + rebuilt each run.

Exit 0 = all auto-eval assertions passed. Exit 1 = any failure.
"""

import json
import os
import re
import shutil
import subprocess
import sys

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(EVAL_DIR)
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
FIXTURES = os.path.join(EVAL_DIR, "fixtures")
WORK_DIR = os.path.join(EVAL_DIR, "_work")

MERGE = os.path.join(SCRIPTS, "merge_geojson.py")
VALIDATE = os.path.join(SCRIPTS, "validate_geojson.py")
GEOID = os.path.join(SCRIPTS, "test_geoid_regression.py")

PASS = "PASS"
FAIL = "FAIL"
_results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    _results.append((status, name, detail))
    marker = "[PASS]" if condition else "[FAIL]"
    line = f"{marker} {name}"
    if detail and not condition:
        line += f"  -- {detail}"
    print(line)
    return condition


def run(cmd):
    """Run a subcommand, return (returncode, combined_output)."""
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    return proc.returncode, proc.stdout


def setup_work_dir():
    """Copy fixtures into evals/_work (never /tmp). Wipe-and-rebuild."""
    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)
    os.makedirs(WORK_DIR)
    shutil.copytree(
        os.path.join(FIXTURES, "sources"), os.path.join(WORK_DIR, "sources")
    )
    # Synthesize a centers/ tree from the source fixtures so merge-centers has
    # input. Center points reuse the source identifying properties; the merge
    # transform applies the same renames as boundaries.
    centers = os.path.join(WORK_DIR, "centers")
    os.makedirs(centers)
    _make_centers(centers)


def _centroid(feature):
    ring = feature["geometry"]["coordinates"][0]
    lon = sum(p[0] for p in ring) / len(ring)
    lat = sum(p[1] for p in ring) / len(ring)
    return [round(lon, 5), round(lat, 5)]


def _to_points(src_path, keep_keys):
    with open(src_path) as f:
        data = json.load(f)
    feats = []
    for feat in data["features"]:
        props = {k: feat["properties"][k] for k in keep_keys if k in feat["properties"]}
        feats.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Point", "coordinates": _centroid(feat)},
        })
    return {"type": "FeatureCollection", "features": feats}


def _write(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f)


def _make_centers(centers):
    src = os.path.join(WORK_DIR, "sources")
    _write(_to_points(os.path.join(src, "us_state.geojson"), ["STUSPS", "NAME"]),
           os.path.join(centers, "us_state_centers.geojson"))
    _write(_to_points(os.path.join(src, "ca_provinces.geojson"), ["PRUID", "PRNAME"]),
           os.path.join(centers, "ca_province_centers.geojson"))
    _write(_to_points(os.path.join(src, "us_county_5m.geojson"), ["GEO_ID", "NAME"]),
           os.path.join(centers, "us_county_centers.geojson"))
    _write(_to_points(os.path.join(src, "ca_cd.geojson"), ["CDUID", "CDNAME"]),
           os.path.join(centers, "ca_cd_centers.geojson"))
    _write(_to_points(os.path.join(src, "us_zip.geojson"), ["ZCTA5CE20"]),
           os.path.join(centers, "us_zip_centers.geojson"))
    _write(_to_points(os.path.join(src, "ca_fsa.geojson"), ["CFSAUID"]),
           os.path.join(centers, "ca_fsa_centers.geojson"))


def load_merged(name):
    path = os.path.join(WORK_DIR, "merged", name)
    with open(path) as f:
        return json.load(f)["features"]


def feats_by_country(features, country):
    return [f for f in features if f["properties"].get("COUNTRY") == country]


# --------------------------------------------------------------------------- #
# 1. merge — boundaries
# --------------------------------------------------------------------------- #
def eval_merge_boundaries():
    print("\n=== merge (boundaries) ===")
    rc, out = run([sys.executable, MERGE, "--work-dir", WORK_DIR])
    if not check("merge boundaries exits 0", rc == 0, out):
        return

    # --- COUNTRY tagging applied across all layers ---
    for layer in ("state_boundaries.geojson", "county_boundaries.geojson",
                  "zip_boundaries.geojson"):
        feats = load_merged(layer)
        tagged = all(f["properties"].get("COUNTRY") in ("US", "CA") for f in feats)
        check(f"COUNTRY tag on every feature in {layer}", tagged)

    # --- US county prefix stripped: 0500000US36061 -> 36061 ---
    counties = load_merged("county_boundaries.geojson")
    us_counties = feats_by_country(counties, "US")
    geoids = {f["properties"]["GEO_ID"] for f in us_counties}
    check("US county prefix stripped to clean 5-digit FIPS",
          geoids == {"36061", "06037"}, f"got {geoids}")
    check("no 0500000US remnant in any merged county GEO_ID",
          all("0500000US" not in f["properties"]["GEO_ID"] for f in counties))

    # --- CA province PRUID -> STUSPS ---
    states = load_merged("state_boundaries.geojson")
    ca_provinces = feats_by_country(states, "CA")
    stusps = {f["properties"].get("STUSPS") for f in ca_provinces}
    check("CA province PRUID->STUSPS (35->ON, 24->QC)",
          stusps == {"ON", "QC"}, f"got {stusps}")

    # --- CA census division CDUID -> GEO_ID ---
    ca_cds = feats_by_country(counties, "CA")
    cd_geoids = {f["properties"].get("GEO_ID") for f in ca_cds}
    check("CA census division CDUID->GEO_ID (clean 4-digit)",
          cd_geoids == {"3506", "2466"}, f"got {cd_geoids}")

    # --- CA FSA CFSAUID -> ZCTA5CE20 ---
    zips_ = load_merged("zip_boundaries.geojson")
    ca_fsas = feats_by_country(zips_, "CA")
    fsa_codes = {f["properties"].get("ZCTA5CE20") for f in ca_fsas}
    check("CA FSA CFSAUID->ZCTA5CE20 (K1A, H2X)",
          fsa_codes == {"K1A", "H2X"}, f"got {fsa_codes}")

    # --- US ZIP ZCTA5CE20 preserved ---
    us_zips = feats_by_country(zips_, "US")
    us_zip_codes = {f["properties"].get("ZCTA5CE20") for f in us_zips}
    check("US ZIP ZCTA5CE20 preserved (10001, 90001)",
          us_zip_codes == {"10001", "90001"}, f"got {us_zip_codes}")


# --------------------------------------------------------------------------- #
# 2. merge — centers (same renames applied to point features)
# --------------------------------------------------------------------------- #
def eval_merge_centers():
    print("\n=== merge-centers ===")
    rc, out = run([sys.executable, MERGE, "--work-dir", WORK_DIR, "merge-centers"])
    if not check("merge-centers exits 0", rc == 0, out):
        return

    state_centers = load_merged("state_centers.geojson")
    ca_state_centers = feats_by_country(state_centers, "CA")
    check("center: CA province PRUID->STUSPS",
          {f["properties"].get("STUSPS") for f in ca_state_centers} == {"ON", "QC"})

    county_centers = load_merged("county_centers.geojson")
    us_cc = feats_by_country(county_centers, "US")
    check("center: US county prefix stripped",
          {f["properties"].get("GEO_ID") for f in us_cc} == {"36061", "06037"})
    ca_cc = feats_by_country(county_centers, "CA")
    check("center: CA CDUID->GEO_ID",
          {f["properties"].get("GEO_ID") for f in ca_cc} == {"3506", "2466"})

    zip_centers = load_merged("zip_centers.geojson")
    ca_zc = feats_by_country(zip_centers, "CA")
    check("center: CA FSA CFSAUID->ZCTA5CE20",
          {f["properties"].get("ZCTA5CE20") for f in ca_zc} == {"K1A", "H2X"})


# --------------------------------------------------------------------------- #
# 3. geoid-regression — fully count-agnostic, must PASS on synthetic data
# --------------------------------------------------------------------------- #
def eval_geoid_regression():
    print("\n=== geoid-regression ===")
    rc, out = run([sys.executable, GEOID, "--work-dir", WORK_DIR])
    print(out.rstrip())
    check("geoid-regression exits 0 (all checks pass)", rc == 0, out)
    # Surface the individual checks for evidence.
    check("geoid-regression: clean 5-digit FIPS check passed",
          "PASS:" in out and "5-digit FIPS" in out)
    check("geoid-regression: no prefix remnants check passed",
          "No prefix remnants" in out)
    check("geoid-regression: CA 4-digit CDUID check passed",
          "4-digit CDUID" in out)
    check("geoid-regression: normalizeCountyGeoid round-trip passed",
          "normalizeCountyGeoid produces correct results" in out)
    check("geoid-regression: US count preserved through merge",
          "US county count preserved" in out)


# --------------------------------------------------------------------------- #
# 4. validate-source — documented expected-fail on REAL counts
# --------------------------------------------------------------------------- #
def eval_validate_source_documented():
    print("\n=== validate-source (documented count mismatch) ===")
    rc, out = run([sys.executable, VALIDATE, "--work-dir", WORK_DIR, "--merged"])
    print(out.rstrip())

    # It MUST exit nonzero on synthetic data: the validator hard-asserts real
    # feature counts. This is expected and correct — we do not weaken it.
    check("validate-source --merged exits nonzero on synthetic data (expected)",
          rc != 0, f"rc={rc}")

    # Every FAIL line must be a COUNT mismatch, never a property/format error.
    # This proves the rename/format logic is satisfied by our merged fixtures
    # while honestly surfacing that real counts cannot be met synthetically.
    fail_lines = [ln for ln in out.splitlines() if "FAIL:" in ln]
    count_pat = re.compile(r"Expected \d+ .*got \d+|count mismatch", re.IGNORECASE)
    only_count_fails = all(count_pat.search(ln) for ln in fail_lines)
    check("validate-source failures are ONLY real-count mismatches (no format/property errors)",
          bool(fail_lines) and only_count_fails,
          "fails: " + " | ".join(fail_lines))


def main():
    print("=" * 60)
    print("mapping:tileset eval — pure-python modes on synthetic fixtures")
    print("work-dir:", WORK_DIR)
    print("=" * 60)

    setup_work_dir()
    eval_merge_boundaries()
    eval_merge_centers()
    eval_geoid_regression()
    eval_validate_source_documented()

    print("\n" + "=" * 60)
    failed = [r for r in _results if r[0] == FAIL]
    passed = len(_results) - len(failed)
    print(f"RESULT: {passed}/{len(_results)} checks passed")
    if failed:
        print("FAILED checks:")
        for _, name, detail in failed:
            print(f"  - {name}: {detail}")
        sys.exit(1)
    print("ALL EVAL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
