---
name: klever-local-stack
description: "Start/stop the Klever portal stack locally via the start-stop-portal-in-local.sh orchestrator. Profiles (map/full/backend), native MySQL, curated seed. Trigger: 'start the local stack', 'run the portal locally', 'spin up the backend', 'local stack', 'start user-management locally'. Klever org."
nav:
  bay: build
  when: "Start/stop the Klever portal locally (frontend + UM + proximity-report, optionally explorer + chatbot)."
  when_not: "Need real BQ data wiring nuance (see /klever-local-stack-real-bq). Just checking dev status (use /dev-status). Waking the DEV environment (use start-stop-portal-in-dev.sh)."
  org: [klever]
---

# Klever Local Stack

Single entry point for the local portal stack:
`grp-app/grp-frontend/app-front-portal/start-stop-portal-in-local.sh`
(the local counterpart to `start-stop-portal-in-dev.sh`, which wakes the dev COS
instances). This skill drives that script; behavior lives in the script, not here.

Design + rationale: `doc/local-stack-orchestrator-design.md`.

## Commands

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal

./start-stop-portal-in-local.sh setup-db          # one-time: provision native MySQL 8.0
./start-stop-portal-in-local.sh start             # default profile: map
./start-stop-portal-in-local.sh start --profile full      # + explorer + chatbot
./start-stop-portal-in-local.sh start --profile backend   # no frontend
./start-stop-portal-in-local.sh start --with-explorer     # add one agent to a profile
./start-stop-portal-in-local.sh status
./start-stop-portal-in-local.sh stop
./start-stop-portal-in-local.sh reseed            # re-apply the curated UM seed (idempotent)
```

## Profiles

| Profile | Services | Use |
|---|---|---|
| `map` (default) | UM + proximity-report (8097) + frontend (3000) | daily map work |
| `full` | map + explorer (8096) + chatbot (8000) | full portal incl. agents |
| `backend` | UM + proximity-report | API work, no UI |

## Key facts

- **Ports come from `.env.local`.** The script parses `KLEVER_USER_MANAGEMENT_URL`,
  `KLEVER_PROXIMITY_REPORT_URL`, `KLEVER_PROXIMITY_PLANNING_URL`. Currently UM
  resolves to **8098**, which is also the `gcp-connect.sh` tunnel port — so the
  local stack and the dev tunnel are **mutually exclusive** (run one or the other).
  `.env.local` is read-only; never edit it.
- **Health endpoints have context paths:** UM `/user/actuator/health`,
  proximity-report `/proximity-report/actuator/health`.
- **Database is Homebrew native MySQL 8.0** (not Docker), provisioned once by
  `setup-db` into `~/.klever-local-mysql/` with `lower_case_table_names=1` to match
  dev. No Docker daemon required. Socket: `~/.klever-local-mysql/data/mysql.sock`.
- **UM boots with a sentinel Liquibase context** (`local-stack`, not `local`), which
  builds the schema + all components (including Feedback id 9) but skips the
  local-context seed changeset 012. The curated seed is applied by `reseed`
  afterward. This avoids a fresh-DB FK ordering trap between changesets 012 and 013.
- **First `start` auto-seeds** if the user table is empty; otherwise it leaves data
  alone. `reseed` is idempotent (truncates seed tables, then re-applies). Expected
  seed: ~21 users, 12 advertisers, 12 DSP accounts, agency 133 (Klever).
- **Repo paths resolve from `KLEVER_ROOT`** (default `~/Developer/grp-beklever-com`),
  so the script runs correctly from a worktree too.

## Preflight (handled by the script, surfaced in `status`)

- Java 17 for the JVM services (UM, proximity-report).
- ADC = `gamyot@beklever.com` for BQ/Vertex services (proximity-report, explorer, chatbot).
- Placer key (1Password `op` or `PLACER_API_KEY`) for proximity-report visitor
  origins; absence degrades gracefully (origins 401, rest of stack still runs).
- `uv` for the Python agents (explorer, chatbot).

A red preflight prints the exact fix command and skips that service; the rest of
the stack still comes up. `status` shows green/red per service.

## Does NOT

- Touch `start-stop-portal-in-dev.sh` or `gcp-connect.sh` (separate, still used
  standalone for dev tunnels).
- Pull live data from dev. The seed is a committed curated snapshot; refreshing its
  contents to match dev is a separate maintenance step.
