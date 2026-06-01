---
name: dev-status
description: "Quick-check Klever dev environment status. Checks nightly schedule, pings Cloud Run services, reports up/down. Triggers on: 'is dev up', 'dev status', 'check dev', 'dev returning 000', 'can I use dev', 'dev environment'. Klever org."
user_invocable: true
nav:
  bay: ops
  when: "Quick-check if Klever dev environment is up. Pings Cloud Run services."
  when_not: "Full infrastructure audit. Local stack issues (use /klever-local-stack)."
  org: [klever]
---

# Klever Dev Environment Status Check

**Usage:** `/dev-status`

Quick check whether the Klever dev environment is available. Handles the nightly shutdown schedule that causes recurring confusion.

## Step 1: Check Schedule

The dev environment (COS instances on GCP) shuts down nightly. Load the schedule:

```
Read: documentation/bibliotheque/sops/dev-environment-nightly-schedule.md
```

Compare current time (EDT) against the schedule:
- **Before 20:00 EDT**: Should be up. Proceed to Step 2.
- **After 20:00 EDT / before ~08:00 EDT**: Down by design. Report: "Dev is in nightly shutdown window. Use local mode (`/klever-local-stack`)."

## Step 2: Ping Services

If within uptime window, check each service:

```bash
# Frontend portal (Cloud Run)
curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://portal.dev.beklever.com/ 2>/dev/null

# Proximity Report backend
curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://proximity-report.dev.beklever.com/actuator/health 2>/dev/null

# User Management backend
curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://user-management.dev.beklever.com/actuator/health 2>/dev/null
```

**Note:** These URLs require IAP authentication. If you get 302 or 401, IAP cookie may be expired. Refresh via `git fetch` on any Klever repo (see memory: `feedback_iap_refresh_via_git_fetch.md`).

## Step 3: Report

Format:

```
Dev Environment Status (YYYY-MM-DD HH:MM EDT)
---------------------------------------------
Schedule:  [IN UPTIME WINDOW / NIGHTLY SHUTDOWN]
Frontend:  [UP (200) / DOWN (XXX) / TIMEOUT]
Proximity: [UP (200) / DOWN (XXX) / TIMEOUT]
User Mgmt: [UP (200) / DOWN (XXX) / TIMEOUT]

Recommendation: [Use dev / Use local (/klever-local-stack)]
```

## Common Patterns

| Symptom | Cause | Action |
|---------|-------|--------|
| All services return 000/timeout | Nightly shutdown | Use local |
| 302 on all services | IAP cookie expired | `git fetch` on any Klever repo |
| Frontend up, backend down | Backend COS not started | Wait 5 min (cold start) or use local |
| All up but data stale | Dataform runs at 06:00 UTC | Data refreshes daily, not real-time |
