# disk-management eval report (2026-11-06)

Suite: `evals/run_scan_evals.py` (Layer A, hermetic). HOME is a temp fixture. Stub `df`, `brew`
and `docker` lead PATH. The stub `df` reports `/` at 73% and the Data volume at 100%, the
2026-09-21 incident.

| Case | New scripts | 2026-09-21 scan.sh |
|---|---|---|
| verdict names the full Data volume | PASS | FAIL (no verdict, only `df -h /`) |
| full scan verdict, no real brew cleanup | PASS | FAIL |
| `--df-only` after-shot skips location sections | PASS | FAIL |
| non-APFS host falls back to `/` | PASS | FAIL |
| brew `--prune=all` dry-run summary surfaced | PASS | FAIL |
| `size_items.sh --children` splits 3.0M / 1.0M | PASS | n/a (script did not exist) |
| `size_items.sh` named paths skip missing items | PASS | n/a |

Result: 7/7 on the new scripts. 2/7 on the old scan.sh (the two passes are the new
`size_items.sh` cases, which do not depend on scan.sh). Reproduce the red arm with
`SCAN_SH=<old scan.sh> python3 evals/run_scan_evals.py`.

Live check on this Mac: `/` reports 6%, `/System/Volumes/Data` reports 67%. The verdict line
names the Data volume.
