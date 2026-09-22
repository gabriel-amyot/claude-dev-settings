# Skill Proposal: klever-emulator-stack-verify

Date: 2026-06-10
Source: KTP-796 — emulator-backed local stack, backend verification

## Trigger
"verify the local stack", "check the emulator", "is the map backend serving advertiser X", after bringing up the emulator-backed local stack, or as a headless pre-check before the frontend visual render.

## Scope
org (Klever)

## Why
KTP-796 proved the local BigQuery emulator path by hand-curling the map endpoints for advertiser 842 and reading the boot log for "EMULATOR mode active". That probe sequence is repeatable and catches integration gaps (param-binding 500s, empty array filters, crosswalk errors) without needing a browser. It's the headless half of Phase 5 — fast, deterministic, no Chrome.

## Draft Steps
1. Confirm emulator up (`:9050`) + fixtures loaded (`load_fixtures.py` validation), and proximity-report booted with `PROXIMITYREPORT_BIGQUERY_EMULATORHOST` set — assert the log shows "EMULATOR mode active".
2. For a given advertiserId + country (CA/US) + date window, POST the core map endpoints: `/map/data/locations`, `/reports/states`, `/map/data/county` (with real CDUIDs pulled from the emulator → exercises the array shim), `/reports/conversions`. Assert 200 + non-empty `data`.
3. Scan the report log for `Failed to execute BigQuery` / `failed to analyze` / crosswalk errors; classify graceful-fallback (insights/crosswalk) vs real 500.
4. Report a per-endpoint pass/fail table. Gate the frontend render on all-green.

## Notes
Lighter than a full skill if the orchestrator already brings the stack up — could be a sub-file of `klever-test` (a new "emulator backend probe" mode) rather than a standalone skill.
