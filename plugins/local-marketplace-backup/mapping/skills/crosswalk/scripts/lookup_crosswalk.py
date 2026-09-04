#!/usr/bin/env python3
"""
Crosswalk lookup: resolve one geographic code to another against a crosswalk table.

WIRED to the KTP-679 FSA -> Census Division crosswalk (real table, real schema):

  Table:  {project}.third_party_data.fsa_to_cd_crosswalk
  Schema: CFSAUID:STRING, CDUID:STRING, PRUID:STRING, CDNAME:STRING, PRNAME:STRING
  Rows:   1,643 (one per Canadian FSA), population-weighted plurality CD per FSA
  Built by: klever-data-workflow scripts/canada/build_fsa_to_cd_crosswalk.py

This script reads the crosswalk from a LOCAL CSV (the portable, dependency-free
path that also matches the KTP-679 CSV fallback for `bq load`). The CSV must have
a header row matching the schema column names above.

Reasoning for CSV-first: BQ write access for the table was blocked at KTP-679 ship
time (gamyot@beklever.com lacked bigquery.tables.create on third_party_data).
The authoritative table is loaded from this same CSV via:
  bq load --source_format=CSV --replace --skip_leading_rows=1 \\
    {project}:third_party_data.fsa_to_cd_crosswalk crosswalk_output.csv \\
    CFSAUID:STRING,CDUID:STRING,PRUID:STRING,CDNAME:STRING,PRNAME:STRING

Usage:
  # FSA -> CD (default direction for the fsa_to_cd table)
  lookup_crosswalk.py --table crosswalk_output.csv --from CFSAUID --to CDUID --key M5V
  # reverse: all FSAs in a CD
  lookup_crosswalk.py --table crosswalk_output.csv --from CDUID --to CFSAUID --key 3520
  # emit the whole matched row as JSON
  lookup_crosswalk.py --table crosswalk_output.csv --from CFSAUID --key M5V --json
  # batch from stdin (one key per line)
  cat fsas.txt | lookup_crosswalk.py --table crosswalk_output.csv --from CFSAUID --to CDUID

Generic: this works for ANY crosswalk CSV, not just FSA->CD. Point --from / --to at
any two header columns. See EXPECTED TABLE FORMAT in the skill GEOID_NORMALIZATION.md
and SKILL.md for other crosswalk schemas (postal->CBG, CBG->ZIP, etc.).
"""

import argparse
import csv
import json
import sys


def load_table(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: empty file or missing header row")
        return reader.fieldnames, list(reader)


def lookup(rows, from_col, key, to_col=None):
    """Return matching rows (to_col=None) or distinct values of to_col."""
    matched = [r for r in rows if r.get(from_col) == key]
    if to_col is None:
        return matched
    seen, out = set(), []
    for r in matched:
        v = r.get(to_col)
        if v is not None and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _iter_keys(value):
    if value is not None:
        yield value
        return
    for line in sys.stdin:
        line = line.strip()
        if line:
            yield line


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Resolve one geographic code to another via a crosswalk CSV.")
    p.add_argument("--table", required=True, help="path to crosswalk CSV (header row required)")
    p.add_argument("--from", dest="from_col", required=True, help="source column name (e.g. CFSAUID)")
    p.add_argument("--to", dest="to_col", help="target column name (e.g. CDUID); omit with --json for full row")
    p.add_argument("--key", help="value to look up; if omitted, reads keys from stdin (one per line)")
    p.add_argument("--json", action="store_true", help="emit full matched row(s) as JSON")
    args = p.parse_args(argv)

    fields, rows = load_table(args.table)
    for col in (args.from_col, args.to_col):
        if col and col not in fields:
            p.error(f"column '{col}' not in table; available: {', '.join(fields)}")

    exit_code = 0
    for key in _iter_keys(args.key):
        if args.json or not args.to_col:
            matched = lookup(rows, args.from_col, key)
            if not matched:
                print(f"# no match for {args.from_col}={key}", file=sys.stderr)
                exit_code = 2
            print(json.dumps(matched))
        else:
            values = lookup(rows, args.from_col, key, args.to_col)
            if not values:
                print(f"# no match for {args.from_col}={key}", file=sys.stderr)
                exit_code = 2
            for v in values:
                print(v)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
