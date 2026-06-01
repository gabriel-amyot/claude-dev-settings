---
name: klever-local-stack-real-bq
description: "Start Klever local stack wired to real dev BigQuery data. Handles ADC setup, 1Password Placer key fetch, BQ project/dataset overrides, component 9 pre-insert, and seed ID mismatch warnings. Trigger: 'local stack with real data', 'real BQ locally', 'test against dev BQ', 'full local e2e', 'local with real BigQuery'. Klever org. Input: none. Returns: running services health check + BQ connectivity confirmation."
nav:
  bay: build
  when: "Local stack wired to real dev BigQuery. ADC, 1Password Placer key, BQ overrides."
  when_not: "Mock data sufficient (use /klever-local-stack). Dev environment check (use /dev-status)."
  org: [klever]
---

# Klever Local Stack — Real Dev BigQuery

Extends `klever-local-stack` to wire the proximity-report service against real dev BigQuery instead of mocked data. Read-only BQ access only. Never write to dev BQ from local.

## Pre-flight

Before starting, verify the base stack skill has been reviewed. This skill picks up after Docker and MySQL are confirmed running. If the base stack is not already up, run `/klever-local-stack` first, then return here for BQ wiring.

---

## Step 1. Docker and MySQL (same as base stack)

Check MySQL container:
```bash
docker ps --filter name=klever-mysql-local --format "{{.Names}} {{.Status}}"
```

If `klever-mysql-local` is not running, fall back to:
```bash
docker ps --filter name=user-management-mysql --format "{{.Names}} {{.Status}}"
```

If neither exists, start a fresh container:
```bash
docker run -d --name klever-mysql-local \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=user_management_local \
  -p 3306:3306 \
  mysql:8.0 --lower-case-table-names=1
```

Wait for readiness:
```bash
docker exec klever-mysql-local mysqladmin ping -uroot -proot --wait=30
```

---

## Step 2. Component 9 Pre-insert (fresh DB only)

On a fresh database, Liquibase component migration only seeds 8 components (IDs 1-8). The proximity-report references component 9 (Proximity). Pre-insert it before starting UM so the FK constraint resolves.

Check if component 9 exists:
```bash
docker exec klever-mysql-local mysql -uroot -proot user_management_local \
  -e "SELECT id, name FROM component WHERE id = 9;" 2>/dev/null
```

If the row is missing:
```bash
docker exec klever-mysql-local mysql -uroot -proot user_management_local \
  -e "INSERT IGNORE INTO component (id, name) VALUES (9, 'Proximity');"
```

---

## Step 3. User Management Backend

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-user-management
JAVA_HOME=$(/usr/libexec/java_home -v 17) mvn package -DskipTests
JAVA_HOME=$(/usr/libexec/java_home -v 17) java -jar target/user-management.jar \
  --spring.profiles.active=local \
  --spring.liquibase.contexts=local \
  --server.port=8090
```

The `--spring.liquibase.contexts=local` flag auto-seeds test data (changeset 012). Verify seed counts after startup:
```bash
docker exec klever-mysql-local mysql -uroot -proot user_management_local \
  -e "SELECT 'users' as t, COUNT(*) as n FROM user
      UNION ALL SELECT 'advertisers', COUNT(*) FROM advertiser
      UNION ALL SELECT 'dsp_accounts', COUNT(*) FROM dsp_account;"
```

Expected: ~21 users, ~12 advertisers, ~12 DSP accounts.

---

## Step 4. Application Default Credentials (ADC)

Proximity-report uses the GCP Java client library, which reads ADC automatically. Set up once per machine or when credentials expire.

Check if credentials are current:
```bash
gcloud auth application-default print-access-token > /dev/null 2>&1 && echo "ADC OK" || echo "ADC MISSING"
```

If missing or expired:
```bash
gcloud auth application-default login --account=gamyot@beklever.com
```

The account `gamyot@beklever.com` has BigQuery Data Viewer on:
- `prj-d-biz-report-im9q1fvvc7` (main dev BQ: `klever_proximity_data`, `portal_dashboards_data`, `klever_core_entities`)
- `prj-d-grid-insigt-3vm2fcstbw` (insights BQ: `dts_insights`)

**Read-only rule:** ADC is scoped to Data Viewer. Never attempt INSERT/UPDATE/DELETE against dev BQ from local. BQ mutations from local are not permitted.

Verify BQ connectivity:
```bash
bq query --project_id=prj-d-biz-report-im9q1fvvc7 --use_legacy_sql=false \
  "SELECT COUNT(*) as row_count FROM \`prj-d-biz-report-im9q1fvvc7.klever_proximity_data.state_performance_data\` LIMIT 1"
```

Expected: a numeric row count. Any auth error means ADC needs refresh.

---

## Step 5. Placer API Key (1Password)

The proximity-report contacts the Placer API for visitor-origins data when `proximity-map.visitor-origins.source=placer-live`. Fetch the key from 1Password CLI and cache it locally.

Check if `op` CLI is available:
```bash
op --version 2>/dev/null || echo "1Password CLI not installed"
```

Fetch and cache:
```bash
op read "op://Private/Placer API Key/credential" > /tmp/placer-api-key.txt 2>/dev/null \
  && echo "Placer key cached" \
  || echo "WARN: 1Password fetch failed — run 'op signin' or set PLACER_API_KEY manually"
```

If 1Password CLI is unavailable, read from the project `.env` fallback:
```bash
PLACER_API_KEY=$(grep PLACER_API_KEY ~/Developer/grp-beklever-com/project-management/.env 2>/dev/null | cut -d= -f2)
```

Export the key for the Java process:
```bash
export PLACER_API_KEY=$(cat /tmp/placer-api-key.txt 2>/dev/null || echo "$PLACER_API_KEY")
```

---

## Step 6. Start Proximity Report with Real BQ

Run with the `local` profile (reads `application-local.properties`) and override BQ projects to dev values:

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-proximity-report
JAVA_HOME=$(/usr/libexec/java_home -v 17) mvn package -DskipTests
JAVA_HOME=$(/usr/libexec/java_home -v 17) java -jar target/*.jar \
  --spring.profiles.active=local \
  --proximityreport.bigquery.projectId=prj-d-biz-report-im9q1fvvc7 \
  --proximityreport.bigquery.datasetId=klever_proximity_data \
  --bizreport.bigquery.projectId=prj-d-biz-report-im9q1fvvc7 \
  --bizreport.portal.dashboards.bigquery.datasetId=portal_dashboards_data \
  --bizreport.klever.core.entities.bigquery.datasetId=klever_core_entities \
  --proximityreport.bigquery.insightsProjectId=prj-d-grid-insigt-3vm2fcstbw \
  --proximity-map.visitor-origins.source=placer-live \
  --placer.api.key="$PLACER_API_KEY"
```

If port 8097 is busy:
```bash
kill -9 $(lsof -t -i:8097) 2>/dev/null; echo "port 8097 cleared"
```

---

## Step 7. Frontend (Portal)

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal
npm install
npm run dev
```

Required `.env.local` vars (check, never modify):
- `KLEVER_USER_MANAGEMENT_URL=http://localhost:8090`

---

## Step 8. Health Check and BQ Connectivity

```bash
echo "=== Service Health ==="
curl -s http://localhost:8090/user/actuator/health | python3 -m json.tool 2>/dev/null || echo "UM: no actuator"
curl -s http://localhost:8097/proximity-report/actuator/health | python3 -m json.tool 2>/dev/null || echo "Proximity: no actuator"
curl -s -o /dev/null -w "Portal: %{http_code}\n" http://localhost:3000
```

Smoke-test a real BQ query through the service:
```bash
# Replace 51 with a seeded advertiser ID
curl -s "http://localhost:8097/proximity-report/reports/state?advertiserId=51&startDate=2024-01-01&endDate=2024-12-31" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Rows: {len(d.get(\"data\", []))}')"
```

Expected: numeric row count from real dev BQ. Zero rows may indicate the seed advertiser ID does not match real BQ data (see Seed ID Mismatch Warning below).

---

## Step 9. Seed ID Mismatch Warning

The local seed data uses specific advertiser IDs that must match BQ `KLEVER_ADVERTISER_ID` values:

| Entity | Local Seed ID | BQ ID | DSP String ID |
|--------|--------------|-------|---------------|
| Shrimp Basket advertiser | `51` | `51` | `la8clii` |
| Artistry Brands agency | `12` | `12` | -- |

If the smoke-test in Step 8 returns 0 rows for advertiser 51, verify the seed data IDs are correct:
```bash
docker exec klever-mysql-local mysql -uroot -proot user_management_local \
  -e "SELECT a.id, a.name, d.provider_id FROM advertiser a
      LEFT JOIN dsp_account d ON d.advertiser_id = a.id
      WHERE a.name LIKE '%Shrimp%';"
```

If IDs are wrong (e.g., id=200, provider_id=`fake`), apply the known patch:
```bash
docker exec -i klever-mysql-local mysql -uroot -proot user_management_local << 'EOF'
SET FOREIGN_KEY_CHECKS=0;
UPDATE agency SET id = 12 WHERE id = 100;
UPDATE advertiser SET agency_id = 12 WHERE agency_id = 100;
UPDATE advertiser SET id = 51 WHERE id = 200;
UPDATE user_permission SET agency_id = 12 WHERE agency_id = 100;
UPDATE user_permission SET advertiser_id = 51 WHERE advertiser_id = 200;
UPDATE dsp_account SET agency_id = 12 WHERE agency_id = 100;
UPDATE dsp_account SET advertiser_id = 51, provider_id = 'la8clii' WHERE advertiser_id = 200;
SET FOREIGN_KEY_CHECKS=1;
EOF
```

---

## Summary Output

Print at the end:
```
=== Klever Local Stack (Real BQ) ===
User Management:    http://localhost:8090  [RUNNING]
Proximity Report:   http://localhost:8097  [RUNNING]
Frontend (Portal):  http://localhost:3000  [RUNNING]
MySQL:              localhost:3306         [RUNNING]

BQ Projects (dev, read-only):
  Main:     prj-d-biz-report-im9q1fvvc7
  Insights: prj-d-grid-insigt-3vm2fcstbw
ADC Account: gamyot@beklever.com

Visitor Origins: placer-live
Placer Key: [set]

Seed ID Check: Shrimp Basket -> advertiser_id=51, provider_id=la8clii
```

---

## BQ Reference

| Property | Value |
|----------|-------|
| Main dev project | `prj-d-biz-report-im9q1fvvc7` |
| Insights dev project | `prj-d-grid-insigt-3vm2fcstbw` |
| Proximity dataset | `klever_proximity_data` |
| Portal dashboards dataset | `portal_dashboards_data` |
| Core entities dataset | `klever_core_entities` |
| Insights dataset | `dts_insights` |
| Auth account | `gamyot@beklever.com` |
| Access level | Data Viewer (read-only) |

---

## Critical Rules

- **Never write to dev BQ from local.** ADC is Data Viewer. Any mutation attempt will 403.
- **Never modify `.env.local` files.** They are gitignored and local-only.
- **Port 8090** is mandatory for UM (portal expects it). **Port 8097** for proximity-report.
- **`--spring.profiles.active=local`** is mandatory on UM (prevents real Auth0 calls).
- **Java 17 required.** Use `JAVA_HOME=$(/usr/libexec/java_home -v 17)` prefix on all Maven/java commands.
- **Placer key is secret.** Never log it, never commit it, cache only to `/tmp/`.
- If ADC expires mid-session, the proximity-report will return 403 on BQ calls. Rerun `gcloud auth application-default login` and restart the service.
