# Skill Proposal: proxi-health-check
Date: 2026-11-05
Source: Proxi support study (session steady-osprey, GitHub #596)

## Trigger
"how is Proxi doing", "check Proxi", "Proxi health", "is Proxi working", before a Proxi rollout, or after a Proxi alert in #ai-proxi-home.

## Scope
org (Klever, Proxi only)

## Draft Steps
1. One read-only IAP SSH batch to the prod VM: `docker inspect` versions of all 4 containers, `cron/jobs.json` status table, MEMORY.md and USER.md sizes vs the config.yaml limits, codex bridge token issue/expiry timestamps (never tokens), the latest monitoring/daily JSON, disk use, the latest READY snapshot age.
2. Read-only LangSmith `proxi-prod` aggregates for the last 7 days: turns per day, failed turns, fallbacks, p50/p95 latency, tokens by job and tier.
3. state.db usage per user (counts only) and the amops.db feedback rows.
4. Compare each result with the claims on the runbook and fleet library pages. Flag every mismatch as a doc defect.
5. Emit a stamped health table (`verified_against:` per row), and post it as a status comment on #596 or the matching child issue.
