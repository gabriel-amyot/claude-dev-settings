# Skill Proposal: klever-backend-local-loadtest
Date: 2026-10-27
Source: KTP-1358 load test of app-proximity-report ZIP endpoint (branch jar vs prod BigQuery, read-only)

## Trigger
"load test this endpoint", "how slow is it at N", "measure before we pick a limit", choosing a cap/ceiling/timeout on a Klever Java backend.

## Scope
org (Klever)

## Draft Steps
1. Build the branch jar in Docker `maven:3.9-eclipse-temurin-17` (Mac has JDK 27 only). Override limits at runtime with `--property=value`, never by code change.
2. Run against real BigQuery via `klever-local-stack-real-bq`. Prefer dev data; if dev has no realistic advertiser, use prod read-only and say so. `--dry_run` every query first and report bytes.
3. Build realistic inputs from repo data (e.g. NYC ZIPs nearest a point from `us_zip_centroids.json`) with a script on disk. Pick the densest advertiser as the stress case.
4. Matrix of sizes × date spans, cold cache only (shift the window by a day or restart), 2 runs per cell. Record end-to-end latency, per-BQ-job time and rows, bytes, response size, heap (`jcmd GC.heap_info`), HTTP status.
5. Fit latency to rows and to the candidate bound; calibrate local vs prod with prod log pairs (prod was ~2× slower per row). Write `load-test-results.md` with a recommended value and caveats (single client, local network, no concurrency). Stop and remove the container.
