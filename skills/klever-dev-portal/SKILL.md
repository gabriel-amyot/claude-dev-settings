---
name: klever-dev-portal
description: "Start, restart, or stop the Klever DEV environment (app-front-portal + its 5 backend MIGs) via start-stop-portal-in-dev.sh. Triggers on: 'start up the portal in dev', 'wake up dev', 'restart the portal for the night', 'restart the portal in dev', 'start the portal on dev for X hours', 'shut down the portal in dev'. Klever org."
user_invocable: true
nav:
  bay: ops
  when: "Starting, restarting, or stopping the Klever DEV environment (app-front-portal + backend MIGs: user-management, proximity-report, proximity-explorer, media-plan, bi-agent) for a work session."
  when_not: "Checking whether dev is currently up without changing anything (use /dev-status). Local stack work (use /klever-local-stack)."
  org: [klever]
---

# Klever Dev Portal Control

**Usage:** `/klever-dev-portal <what you want>` — e.g. "start dev", "restart the portal for the night", "start dev for 3 hours", "shut down dev".

Wraps `start-stop-portal-in-dev.sh`, the script that starts/stops the whole DEV
front-portal dependency set (6 GCP resources, all MIGs resized 1<->0):
user-management, proximity-report, proximity-explorer, media-plan, bi-agent,
then the portal itself.

**Canonical script path — never a worktree/clone copy:**
```
~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal/start-stop-portal-in-dev.sh
```
Sibling copies exist inside `app-front-portal-KTP-*` clones and `.worktrees/` —
those are stale forks for isolated feature work. Always run the one in the
main `app-front-portal` repo.

## Step 1: Parse intent

| User says | Action |
|---|---|
| "start up dev", "wake up the portal", "start dev" | **start** |
| "start dev for X hours/minutes" | **start with duration** |
| "restart the portal", "restart dev", "restart for the night" | **restart** (stop, then start) |
| "restart dev for X hours" | **restart with duration** |
| "shut down dev", "stop the portal", "tear down dev" | **stop** (guarded — see Step 3) |

Duration parsing follows the script's own format: bare number = minutes, or
`30m` / `1h` / `1h30m` / `90m`.

## Step 2: Auth preflight

`gcloud` reauth silently fails non-interactively (`Reauthentication failed.
cannot prompt during non-interactive execution.`). Before running any command,
if the last run is unknown/stale, just attempt it — if it errors with that
message, tell the user to run `! gcloud auth login` in their terminal (the `!`
prefix runs it in-session so the browser flow can complete), then retry.

## Step 3: Run the command

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal

# start (no duration) — leaves it running until manually stopped or the
# nightly 20:00 EDT auto-shutdown schedule catches it
./start-stop-portal-in-dev.sh start

# start with duration — auto-shutdown timer, survives closing the terminal
./start-stop-portal-in-dev.sh start --for 2h

# restart, no duration ("for the night") — stop, then start with no timer.
# Relies on the existing nightly scheduler for the actual teardown, so this
# is the right call whenever "restart for the night" is asked after ~20:00 —
# the day's automatic shutdown has already fired and won't fire again until
# the next 20:00, so it effectively runs until then.
./start-stop-portal-in-dev.sh stop
./start-stop-portal-in-dev.sh start

# restart with duration — same, but start takes --for
./start-stop-portal-in-dev.sh stop
./start-stop-portal-in-dev.sh start --for <duration>
```

`stop` on already-stopped resources and `start` on already-running resources
are both no-ops (idempotent gcloud resize), so don't bother checking current
state first — just run the requested sequence.

### Guard: "shut down dev" only runs in the night window

An explicit **stop** (not part of a restart) must only execute if the current
local time is **>= 20:00 or < 06:00**. Dev is a shared environment during work
hours — tearing it down before 20:00 takes it away from the rest of the team
without warning.

```bash
hhmm=$(date +%H%M)
if [ "$hhmm" -ge 2000 ] || [ "$hhmm" -lt 0600 ]; then
  # in window — proceed with stop
else
  # refuse: report current time, explain the window, do not run stop
fi
```

If refused, tell the user the current time and that explicit shutdown is
gated to 20:00–06:00 to avoid taking down dev for other engineers mid-day. If
they insist, they can run the script directly themselves.

This guard applies only to a **bare stop request**. A **restart** always runs
its `stop` half regardless of time of day (that's the whole point — restart
tears down and immediately brings back up, so there's no shared-environment
downtime window).

## Step 4: Report back

After `start --for <duration>`, the script prints an auto-shutdown timer PID,
log path, and cancel command (`kill <pid>`) — relay all three so the user can
cancel it if plans change. State the resolved shutdown time explicitly (the
script prints `~HH:MM:SS`).
