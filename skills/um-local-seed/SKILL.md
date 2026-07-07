---
name: um-local-seed
description: "Seed (or reset) the local User Management database with curated test data. Now backed by the start-stop-portal-in-local.sh orchestrator's idempotent reseed against native MySQL. Trigger: 'seed UM data', 'populate local database', 'fresh UM data', 'reset local users'. Klever org. Input: none. Returns: seeded record counts."
nav:
  bay: build
  when: "Seed/reset local User Management with curated test data (idempotent)."
  when_not: "Full local stack startup (use /klever-local-stack). Production data."
  org: [klever]
---

# UM Local Seed

Seeds (or resets) the local User Management database with the curated test data.

> **This is now a thin wrapper around the orchestrator.** Seeding lives in
> `start-stop-portal-in-local.sh reseed`. The old Docker container
> (`klever-mysql-local`) is superseded by Homebrew native MySQL provisioned by
> the orchestrator's `setup-db`.

## Primary path

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal
./start-stop-portal-in-local.sh reseed
```

`reseed` is idempotent: it truncates the seed tables (FK-safe order) and re-applies
`app-user-management/.../release.1.0.0/012-insert-local-test-data.sql`. It requires
the schema to exist, so start User Management once first (the orchestrator's first
`start` auto-seeds an empty DB). Source of seed: changeset 012.

## Direct DB access (native MySQL)

```bash
MYSQL="$(brew --prefix mysql@8.0)/bin/mysql"
SOCK="$HOME/.klever-local-mysql/data/mysql.sock"
"$MYSQL" --socket="$SOCK" -uroot user_management_local -e "<query>"
```

## Verify counts

```sql
SELECT 'users' e, COUNT(*) c FROM user
UNION ALL SELECT 'advertisers', COUNT(*) FROM advertiser
UNION ALL SELECT 'dsp_accounts', COUNT(*) FROM dsp_account;
```

Expected: ~21 users, ~12 advertisers, ~12 DSP accounts, agency 133 (Klever).

## Notes

- Never modify `.env.local`.
- The `@Profile("local")` mock prevents creating real Auth0 users.
- **Liquibase checksum risk:** never edit an already-applied changeset (e.g. `012`).
  The orchestrator avoids running `012` via Liquibase at all (sentinel context),
  applying it through `reseed` instead, so editing `012` only affects fresh DBs.
- "Sync with dev" means refreshing the seed *contents* to match dev's current demo
  state (read dev once, regenerate `012`, commit). That is a separate maintenance
  step, not part of normal reseed.

## Real BQ ID reference

| Entity | Local ID | Meaning |
|--------|---------|---------|
| Shrimp Basket advertiser | `51` | BQ `KLEVER_ADVERTISER_ID` |
| Artistry Brands agency | `12` | BQ sub-agency ID |
| Shrimp Basket DSP | `la8clii` | `normalized_klever_stores_mapping.ADVERTISER_ID` (string, not integer) |

BQ store mapping uses the DSP string ID (`la8clii`), not the integer `51`.
Querying by integer returns 0 rows.
