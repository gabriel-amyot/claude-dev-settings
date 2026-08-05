---
name: um-local-grant
description: >
  Grant local User Management super-admins the "ALL" component so the frontend's
  server-side component gates (KTP-688 requireComponent) pass locally. Fixes a 403
  from a gated media-plan / agent API route when running the portal against the local
  stack. LOCAL DEV ONLY — never a Liquibase changeset, never deployed. Idempotent;
  re-run after every `reseed` (reseed wipes the grant). Trigger: "media plan agent
  403 locally", "component gate 403", "requireComponent forbidden local", "local
  MediaPlanAgent forbidden", "grant local components", "fix local permission gate",
  "um local grant". Klever org.
nav:
  bay: ops
  when: "Running the portal locally and a gated API route (media-plan/agent, KTP-688 requireComponent) returns 403 because the local UM seed doesn't grant the super-admin the component."
  when_not: "You need to START the local stack (use /klever-local-stack) or seed users/advertisers (use /um-local-seed). This only grants component access on an already-running, already-seeded local UM."
  personas: [amelia]
  org: [klever]
---

# um-local-grant — local component-gate fix

## What it does

Grants the sentinel **`ALL`** component to every ALL-scope (super administrator) permission in the
local `user_management_local` MySQL. That makes the frontend's fail-closed server-side component gate
(`app-front-portal/lib/permissions/require-component.ts`, KTP-688 `requireComponent`) pass for any gated
API route when you drive the local portal as a demo super-admin.

**Why it's needed:** the committed local seed (`012-insert-local-test-data.sql`) does not grant
super-admins the `ALL` component, and newer gated routes (e.g. `MediaPlanAgent` for the media-plan
agent) have no component grant in local data. So those routes 403 locally out of the box. Every
`start-stop-portal-in-local.sh reseed` wipes `user_component`, so the grant must be re-applied.

**This is local test data only.** It is NOT a Liquibase changeset, is never committed to a deploy path,
and only touches the native local MySQL. Do not add this to `db/changelog/`.

## Usage

Prereq: the local backend stack is up (`start-stop-portal-in-local.sh start --profile backend` or
`/klever-local-stack`), so MySQL + the UM schema exist.

```bash
~/.claude/skills/um-local-grant/grant-local-components.sh            # apply the grant (idempotent)
~/.claude/skills/um-local-grant/grant-local-components.sh --status   # show current grants, change nothing
~/.claude/skills/um-local-grant/grant-local-components.sh --revert   # remove the ALL grant this script added
```

Run `--apply` (the default) once after each `reseed`. It reports which super-admin permissions it
granted and prints the resulting component list per super-admin.

## How to run it (agent)

1. Confirm the local stack is up. If MySQL isn't running, tell the user to start it (`/klever-local-stack`
   or `start-stop-portal-in-local.sh start --profile backend`) — do not start it silently as part of a grant.
2. Run `grant-local-components.sh` (default `--apply`).
3. To verify the fix end to end, POST the gated route and expect a 200 SSE stream, e.g.
   `curl -s -X POST http://localhost:3000/api/media-plan?mediaPlanFixture=tiered` (needs the frontend
   dev server running with `.env.local` pointing `KLEVER_DEMO_AUTH0_USER_ID` at a seeded super-admin,
   e.g. `auth0|plat-001`).

## Connection

Mirrors `start-stop-portal-in-local.sh`: native MySQL over the unix socket
`~/.klever-local-mysql/data/mysql.sock`, user `root`, database `user_management_local`. Override with
`MYSQL_PREFIX`, `MYSQL_DATADIR`, `DB_NAME` env vars if your local layout differs.

## Related

- `/klever-local-stack` — start/stop the local portal stack (must run first).
- `/um-local-seed` — seed users/advertisers into local UM.
- The proper long-term fix (team-wide) is to add the `MediaPlanAgent` component grant to the committed
  local seed; until then this local-only script covers Gabriel's machine.
