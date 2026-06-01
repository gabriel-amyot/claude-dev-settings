---
name: um-local-seed
description: "Seed local User Management MySQL database with test data. Checks Docker container, verifies state, runs changeset SQL, verifies counts. Trigger: 'seed UM data', 'populate local database', 'fresh UM data', 'reset local users'. Klever org. Input: none. Returns: seeded record counts."
nav:
  bay: build
  when: "Seed local User Management MySQL with test data. Checks Docker, runs changeset SQL."
  when_not: "Full local stack (use /klever-local-stack). Production data."
  org: [klever]
---

# UM Local Seed

Seeds the local User Management MySQL database with test data for development.

## Container Facts

**Active container:** `klever-mysql-local` (MySQL 8.0) — this is the running container, not `user-management-mysql` (stopped/legacy).
**Database name:** `user_management_local`
**Port:** 3306

Connect: `docker exec klever-mysql-local mysql -uroot -proot user_management_local`

## Steps

### 1. Check MySQL Container

```bash
docker ps --filter name=klever-mysql-local --format "{{.Names}} {{.Status}}"
```

If port 3306 is busy and `klever-mysql-local` is already running, use it directly — don't try to start `user-management-mysql`.

### 2. Check Existing Data

```bash
docker exec klever-mysql-local mysql -uroot -proot user_management_local \
  -e "SELECT COUNT(*) as user_count FROM user;" 2>/dev/null
```

If data exists (count > 0), warn user and ask whether to proceed. Seeding may overwrite existing data.

### 3. Find and Run Seed SQL

The changeset files are in the app-user-management repo:
```bash
ls ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-user-management/src/main/resources/db/changelog/release.1.0.0/
```

Seed data is in `012-insert-local-test-data.sql`. Read it to confirm it contains INSERT statements for users, permissions, and DSP accounts.

Execute:
```bash
docker exec -i klever-mysql-local mysql -uroot -proot user_management_local \
  < ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-user-management/src/main/resources/db/changelog/release.1.0.0/012-insert-local-test-data.sql
```

If the changeset is in Liquibase XML format (not raw SQL), extract the SQL statements and run them directly, or run the full Liquibase migration via Maven:
```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-user-management
mvn liquibase:update -Dspring.profiles.active=local
```

### 4. Verify Counts

```bash
docker exec klever-mysql-local mysql -uroot -proot user_management_local -e "
  SELECT 'users' as entity, COUNT(*) as count FROM user
  UNION ALL
  SELECT 'advertisers', COUNT(*) FROM advertiser
  UNION ALL
  SELECT 'dsp_accounts', COUNT(*) FROM dsp_account;"
```

Expected: ~21 users, ~12 advertisers, ~12 DSP accounts.

### 5. Verify Shrimp Basket Real IDs

```bash
docker exec klever-mysql-local mysql -uroot -proot user_management_local -e "
  SELECT a.id, a.name, ag.id as agency_id, ag.name as agency, d.provider_id
  FROM advertiser a
  JOIN agency ag ON ag.id = a.agency_id
  LEFT JOIN dsp_account d ON d.advertiser_id = a.id
  WHERE a.name = 'Shrimp Basket';"
```

Expected: id=51, agency_id=12, provider_id=`la8clii`.

### 6. Optional: Live PK Patch (if IDs are stale)

If the DB has old fake IDs (advertiser 200 instead of 51), patch in-place:

```sql
SET FOREIGN_KEY_CHECKS=0;
UPDATE agency SET id = 12 WHERE id = 100;
UPDATE advertiser SET agency_id = 12 WHERE agency_id = 100;
UPDATE advertiser SET id = 51 WHERE id = 200;
UPDATE user_permission SET agency_id = 12 WHERE agency_id = 100;
UPDATE user_permission SET advertiser_id = 51 WHERE advertiser_id = 200;
UPDATE dsp_account SET agency_id = 12 WHERE agency_id = 100;
UPDATE dsp_account SET advertiser_id = 51, provider_id = 'la8clii' WHERE advertiser_id = 200;
SET FOREIGN_KEY_CHECKS=1;
```

### 7. Optional: Start Backend

If backend is not already running:
```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-user-management
java -jar target/*.jar --spring.profiles.active=local --server.port=8090
```

## Notes

- Never modify `.env.local` files
- The `@Profile("local")` mock prevents creating real Auth0 users
- If Liquibase has already run the changeset, it will skip it (idempotent via DATABASECHANGELOG table)
- **Liquibase checksum risk:** modifying an existing changeset file (e.g., `012`) invalidates its checksum if the container already applied it. Only safe on a fresh/stopped container. On live containers, create an additive changeset (`014-fix.sql`) with UPDATE statements instead.

## Real BQ ID Reference

| Entity | Local ID | Meaning |
|--------|---------|---------|
| Shrimp Basket advertiser | `51` | BQ `KLEVER_ADVERTISER_ID` |
| Artistry Brands agency | `12` | BQ sub-agency ID |
| Shrimp Basket DSP | `la8clii` | `normalized_klever_stores_mapping.ADVERTISER_ID` (string, not integer) |

Note: BQ store mapping uses DSP string ID (`la8clii`), not the integer `51`. Querying by integer returns 0 rows.
