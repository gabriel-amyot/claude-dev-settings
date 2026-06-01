---
name: klever-local-stack
description: "Start Klever backend and frontend services locally for development. Handles Docker, Java 17, MySQL, backend jar, frontend npm. Trigger: 'start user-management locally', 'spin up the backend', 'run the portal locally', 'local stack'. Klever org. Input: which services (backend/frontend/both). Returns: running services with health check URLs."
nav:
  bay: build
  when: "Start Klever backend + frontend locally. Docker, Java, MySQL, npm."
  when_not: "Need real BQ data locally (use /klever-local-stack-real-bq). Just checking dev status (use /dev-status)."
  org: [klever]
---

# Klever Local Stack

Starts Klever backend (User Management) and frontend (Portal) locally.

## Steps

### 0. Preflight (run before starting anything)

Two classes of failure waste hours: a stale process squatting on a port (every curl hits the old build), and a broken auth chain (access-denied with no obvious cause). Run both sweeps first.

**Port squatter sweep.** Check the Klever local ports for existing listeners: 8090 (UM backend), 8096 (proximity-planning), 8097 (proximity-report), 8098 (UM default), 3000 (frontend), 3306 (MySQL).
```bash
for p in 8090 8096 8097 8098 3000 3306; do
  pid=$(lsof -ti :$p 2>/dev/null)
  [ -n "$pid" ] && echo "Port $p occupied by PID $pid: $(ps -p $pid -o command= | cut -c1-80)"
done
```
- If a port is held by a **stale `java -jar ... .jar`** (started hours ago), warn and offer to kill it. A Friday-started proximity-report jar on 8097 once caused 2+ hours of false investigation because every curl hit the stale local JAR instead of the tunneled service.
- If a port is held by an **active SSH tunnel**, report it as healthy (do not kill).
- If a port is held by **anything unexpected**, warn and do NOT kill automatically.

**Auth readiness sweep** (needed before e2e tests, proof runner, or any UM-permissioned browser flow):
1. **ADC identity:** `gcloud auth application-default print-access-token` → resolve to email. Must be `gamyot@beklever.com`. If wrong org: `gcloud auth application-default login --account=gamyot@beklever.com`.
2. **UM health:** `curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/actuator/health` (000 = not started, 404 = wrong context path).
3. **Demo user in MySQL:** `SELECT auth0_id FROM user WHERE email = 'g.amyot@beklever.com'` against the local MySQL container. Compare to `.env.local` `KLEVER_DEMO_AUTH0_USER_ID` (read-only; never modify `.env.local`).
4. **Component grant:** verify the demo user has component 8 (Measurement) via the `user_component` join.
5. **DSP accounts:** `SELECT * FROM dsp_account WHERE agency_id = 133` — verify at least `efbuw` (Shrimp Basket) exists.

Report green/red per check with the fix command for any red. A 30-second preflight here surfaces no-tunnel / wrong-ADC / missing-DB-user / stale-cache problems that otherwise eat a full debugging session.

### 1. Docker and MySQL

Check if Docker is running:
```bash
docker info > /dev/null 2>&1
```

Check if MySQL container exists and is running:
```bash
docker ps --filter name=user-management-mysql --format "{{.Status}}"
```

If not running:
```bash
docker run -d --name user-management-mysql \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=user_management \
  -p 3306:3306 \
  mysql:8.0 --lower-case-table-names=1
```

Wait for MySQL to be ready:
```bash
docker exec user-management-mysql mysqladmin ping -uroot -proot --wait=30
```

### 2. Java Version Check

```bash
java -version 2>&1 | head -1
```

Must be Java 17. If wrong version, check `JAVA_HOME`:
```bash
echo $JAVA_HOME
/usr/libexec/java_home -V 2>&1
```

If Java 17 is installed but not default, instruct user to set:
```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

Fail fast with clear message if Java 17 is not installed.

### 3. Backend (User Management)

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-user-management
mvn clean package -DskipTests
```

Start with local profile. IMPORTANT: override port to 8090 (frontend expects 8090, backend defaults to 8098):
```bash
java -jar target/*.jar --spring.profiles.active=local --server.port=8090
```

The `@Profile("local")` mock prevents creating real Auth0 users (safe for local dev).

Run this in background or instruct user to use a separate terminal.

### 4. Frontend (Portal)

Check `.env.local` exists and has required vars (DO NOT modify this file):
```bash
ls ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal/.env.local
```

Required vars (check, don't write):
- `KLEVER_USER_MANAGEMENT_URL=http://localhost:8090`

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal
npm install
npm run dev
```

### 5. Health Check

- Backend: `curl -s http://localhost:8090/actuator/health`
- Frontend: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000`

Print summary:
```
Backend (User Management): http://localhost:8090 [RUNNING]
Frontend (Portal): http://localhost:3000 [RUNNING]
MySQL: localhost:3306 [RUNNING]
```

## Critical Rules

- NEVER modify `.env.local` files. They are gitignored and local-only.
- Port 8090 is mandatory for backend (frontend expects it).
- `--spring.profiles.active=local` is mandatory (prevents real Auth0 calls).
