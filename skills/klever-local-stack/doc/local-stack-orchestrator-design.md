# Design: `start-stop-portal-in-local.sh` — Resilient Klever local full stack

Status: Approved 2026-06-04. Author: Gabriel (with Claude).
Lives in: `grp-app/grp-frontend/app-front-portal/start-stop-portal-in-local.sh` (committed to the frontend repo, beside `start-stop-portal-in-dev.sh`).

## Purpose

One script to bring up (or tear down) the full Klever portal stack on the local
machine, the local counterpart to Marc-André's `start-stop-portal-in-dev.sh`
(which wakes the dev COS instances). Where the dev script starts cloud VMs, this
one starts local processes. It gives a single, resilient entry point so any part
of the portal can be exercised end-to-end locally.

## Scope guards (what this does NOT do)

- Does **not** modify `start-stop-portal-in-dev.sh` (Marc-André's) or
  `gcp-connect.sh` (shared; still used standalone for dev tunnels).
- Does **not** pull live data from dev's database. Local data comes from a
  committed, curated seed.
- Does **not** containerize the agents or introduce docker-compose.
- Replaces (retires) the earlier `scripts/start-local-stack.sh`, whose proven
  logic is carried forward.

## CLI

```
start-stop-portal-in-local.sh start  [--profile map|full|backend] [--with-chatbot] [--with-explorer]
start-stop-portal-in-local.sh stop   [--profile ...]
start-stop-portal-in-local.sh status
start-stop-portal-in-local.sh reseed          # re-apply the committed UM seed
start-stop-portal-in-local.sh setup-db         # one-time native MySQL provisioning
```

- No args → print status, then an interactive `start/stop` prompt (mirrors the
  dev script's UX) for discoverability.
- With args → fully non-interactive, so the e2e / proof runners can call it.

## Path resolution

The script resolves repo locations from `KLEVER_ROOT`
(default `$HOME/Developer/grp-beklever-com`), **not** relative to its own path.
This keeps it correct whether run from the committed location, a git worktree, or
elsewhere.

## Service registry & profiles

A single declarative table is the source of truth. Each service row carries:
port, repo path (relative to `KLEVER_ROOT`), build command, run command, health
URL, log file, and required secrets/credentials. Start, stop, status, and health
all iterate over this table, so there is no duplicated port list or health logic.

| Service | Default port | Profiles | Data plane |
|---|---|---|---|
| Frontend (Next.js) | 3000 | map, full | local |
| User Management (Java) | 8090 | map, full, backend | local code + local MySQL |
| Proximity Report (Java) | 8097 | map, full, backend | local code + real BigQuery + Placer |
| Proximity Explorer / Planning (Python, FastAPI) | 8096 | full | local code + real BigQuery + Vertex AI |
| Chatbot / agent-hub (Python, Chainlit) | 8000 | full | local code + real BigQuery + Vertex AI |

- `map` (default): frontend + UM + proximity-report. The daily map-work stack.
- `full`: adds explorer + chatbot.
- `backend`: backends only, no frontend.
- `--with-chatbot` / `--with-explorer`: add a single agent to any profile.

**Ports come from `.env.local`, not hardcoded.** The script parses
`KLEVER_USER_MANAGEMENT_URL`, `KLEVER_PROXIMITY_REPORT_URL`, and
`KLEVER_PROXIMITY_PLANNING_URL` from the frontend's `.env.local` to derive UM,
report, and planning ports (falling back to 8090 / 8097 / 8096). This removes the
8090-vs-8098 drift between the env sample and the runtime convention, and keeps
`.env.local` the single source of truth. `.env.local` is read-only, never written.

Explorer runs the same FastAPI app dev runs (`uvicorn app:app`), bound to the
local planning port instead of dev's internal 8080. Chatbot runs
`chainlit run src/agent_hub/ui/app.py` and is standalone (not wired into portal
env in this iteration).

## Database — Homebrew native MySQL 8.0

Chosen over Docker for a lighter footprint. The one fidelity risk is table-name
casing, so provisioning is explicit:

- `setup-db` (one-time): `brew install mysql@8.0`, write a dedicated `my.cnf`
  with `lower_case_table_names=1` and dev-matching collation
  (`utf8mb4` / `utf8mb4_0900_ai_ci`), initialize the datadir, `brew services start`.
  `lower_case_table_names` must be set at datadir-init time on macOS; it cannot be
  changed afterward, hence a dedicated datadir provisioned by this script.
- `start`: verifies MySQL is listening; if not, starts the brew service. If MySQL
  was never provisioned, it points the user to `setup-db`.
- Schema: created by UM's own Liquibase (`local` context) on first boot, unchanged.
- DB / user / password follow `application-local.properties` defaults
  (`user_management_local` / `user_management` / `password`), overridable by env.

## Data sync model — curated seed, refreshed on demand

- `reseed` re-applies the committed seed
  (`app-user-management/.../release.1.0.0/012-insert-local-test-data.sql`):
  demo agency 133, demo user, advertisers, DSP accounts (incl. Shrimp Basket
  `efbuw`).
- Keeping local "in sync with dev" means **refreshing the seed contents** to match
  dev's current demo state. That is a separate, occasional maintenance step
  (read dev once via the running dev UM API or a dump, regenerate the seed SQL,
  commit it), documented but not run on every boot. No live dev DB access and no
  PII at runtime.

## Resilience

Per-service start sequence:

1. **Port-squatter check** — warn on a stale listener; never auto-kill an SSH
   tunnel or anything unexpected.
2. **Preflight** — verify required credentials before launch: ADC identity is
   `gamyot@beklever.com` (BQ/Vertex services), Placer key present (proximity
   report), Java 17 (Java services). A red preflight reports the **exact fix
   command** and skips that service; the rest of the stack still comes up.
3. **Build** → 4. **Launch** (nohup, logged to `/tmp/klever-local-<svc>.log`)
   → 5. **Health poll** of the service's health URL with a timeout.

`status` shows green/red per service in one view. This folds the preflight
discipline that currently lives only in the `klever-local-stack` skill into the
script itself.

## Skill integration

- `klever-local-stack` skill becomes a thin pointer that drives
  `start --profile`.
- `um-local-seed` skill maps onto `reseed`.

No behavior lives in two places.

## Open items resolved during implementation

- Chatbot local port confirmed as Chainlit default (8000); standalone for now.
- Explorer confirmed to expose a FastAPI server (`app:app`), so it mirrors dev
  rather than running the CLI `main.py`.
