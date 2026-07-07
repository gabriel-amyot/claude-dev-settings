# Live Evidence Generation — Probe Routing & Setup

Loaded on demand by `sprint-close` Phase 2a (Live Evidence Generation). This is the procedure for **generating fresh proof** for each acceptance criterion, rather than only judging evidence already on disk. Klever-specific.

## Verdict taxonomy

Every AC gets exactly one verdict, each backed by an artifact on disk:

| Verdict | Meaning | Required artifact |
|---------|---------|-------------------|
| **PASS** | Observed working against a live system | Screenshot (frontend) OR response log (backend) OR query result (data) OR matched pattern (code) |
| **FAIL** | Observed NOT working / produces wrong output | The failing observation: screenshot of the bug, the 4xx/5xx body, the wrong query result, the missing pattern |
| **CANT-TEST** | Could not be exercised | The reason + what was attempted (missing data, infra down, needs human, no test surface) |

`CANT-TEST` is a first-class result, not a skip. "I could not prove it" must itself be proven (show the blocker). Maps to the `BLOCKED` coverage label in the closing comment.

## AC classification → probe routing

For each AC, classify by what it asserts, then route:

| AC asserts… | Class | Probe |
|-------------|-------|-------|
| "URL shows X", "pin/circle/label renders", "panel displays", "toggle does Y" | **frontend** | **ui-probe** (live runtime) → screenshot + fiber/DOM read |
| "endpoint returns X", "API responds Z", "proxy handles error" | **backend** | **API probe** (see below) → response log |
| "BQ has column/rows", "view returns", "data shape" | **data** | `bq query` against dev BQ → result rows |
| "no reference to X in code", "flag removed" | **code** | `grep`/`rg` → matched/absent pattern |
| "deploys to demo.dev", "human confirms visually" | **manual** | flag CANT-TEST(needs-human) unless a human is in the loop |

A single ticket usually mixes classes (e.g. KTP-699: AC-1 backend, AC-2/AC-3 frontend, AC-4 backend). Probe each AC by its own class.

## Frontend probe (ui-probe)

Invoke the `ui-probe` skill. Key facts learned 2026-06-05/08:

- ui-probe attaches to the **user's running Chrome** (inherits IAP+Auth0). It does NOT log in. If the user's Chrome has an authenticated `portal.dev.beklever.com` tab, probe **dev** directly (the real deployed target).
- **Local frontend caveat:** `localhost:3000/measurement` is permission-gated. The local mock user's permission fetch to UM (`getUserPermissions`, `lib/permissions/data.ts`) returns not-ok → "Access Denied", because the seeded mock user lacks the Measurement component on the shared UM (port 8098). Do NOT mutate the shared UM to fix this if another session is using it. Prefer probing **dev** via the user's authenticated tab.
- Read Mapbox GL ground truth via the React fiber: locate the map instance by scanning fibers for an object with `getStyle` + `queryRenderedFeatures`, stash on `window.__probeMap`. Then `map.getStyle().layers`, `map.queryRenderedFeatures({layers:[id]})`, `map.getLayoutProperty(id,'visibility')`, `map.flyTo(...)`.
- **Always save the screenshot to disk** (`save_to_disk: true`) into `tickets/KTP/{EPIC}/{KEY}/design/screenshots/{KEY}-AC{n}-{date}.png`. A frontend PASS without a saved screenshot is not proof.
- Sanitize all `javascript_tool` returns: return types/booleans/counts, never raw strings (the bridge blocks token-like values AND key names containing auth/session/token/etc.).

## Backend probe (the gap — documented procedure)

There is no standalone backend-probe skill; this is the procedure. The `app-proximity-report` repo ships AC-aligned harness scripts that ARE the backend probes:

- `test_dooh_api.py` — KTP-756 DOOH proxy (Goldfish)
- `test_visitor_origins_api.py` — visitor origins / FSA shape (KTP-699/130)
- `test_map_api.py` — `/api/v1/map/data/state` (KTP-754). **STALE contract** as of 2026-06-05: it sends `stateIds`+`date`; the live endpoint wants `ids` (2-char codes) + `startDate`/`endDate`. Use direct curl with the correct shape, or fix the script first.

### Bring up the backend (port 8097, on origin/dev)
```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-proximity-report
git fetch origin && git pull origin dev          # test DEPLOYED code, not stale local
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"   # JDK 21 breaks Lombok ("TypeTag :: UNKNOWN"). MUST be 17.
export PLACER_API_KEY="$(cat /tmp/.placer_key_cache)" # visitor origins; cache from 1Password vault grp-client-portal-ui
export GOLDFISH_API_KEY="$(op item get 'Goldfish DOOH' --fields credential --reveal)"   # vault grp-client-portal-ui
export GOLDFISH_UID="$(op item get 'Goldfish DOOH' --fields username --reveal)"
nohup mvn -q spring-boot:run -Dspring-boot.run.profiles=local > /tmp/proxrp-local.log 2>&1 &
# wait for: curl -s -o /dev/null -w '%{http_code}' http://localhost:8097/proximity-report/actuator/health  → 200
```
- Local backend reads **dev BQ** (`prj-d-biz-report-im9q1fvvc7` / `klever_proximity_data`) via ADC (`gamyot@beklever.com`). So endpoint responses reflect real dev data.
- Probe each backend AC with `curl` using the correct contract; assert HTTP code + response shape/fields. Save the request+response to `tickets/.../reports/reviews/{KEY}-AC{n}-backend-{date}.txt`.

## Data probe (bq)

```bash
bq query --project_id=prj-d-biz-report-im9q1fvvc7 --use_legacy_sql=false --format=prettyjson "<SQL>"
```
- Dataset `klever_proximity_data`. `ROWS` is a reserved word (alias counts as `row_cnt`). Advertiser column is `KLEVER_ADVERTISER_ID` (not `ADVERTISER_ID`). `__TABLES__` uses `table_id`.
- Schema truth (2026-06-05): `COUNTRY` column EXISTS on `proximity_daily_geo_zip_performance` and `proximity_daily_geo_conversions` (with `PRUID`/`CDUID`/`METRIC_TYPE`). Earlier "COUNTRY doesn't exist" notes are stale.
- Save query + result to `tickets/.../reports/reviews/{KEY}-AC{n}-data-{date}.txt`.

## Output of Phase 2a

A per-ticket evidence bundle on disk:
```
tickets/KTP/{EPIC}/{KEY}/reports/reviews/{KEY}-validation-{date}.md   # the per-AC verdict table + artifact links
tickets/KTP/{EPIC}/{KEY}/design/screenshots/{KEY}-AC{n}-{date}.png    # frontend proof
tickets/KTP/{EPIC}/{KEY}/reports/reviews/{KEY}-AC{n}-{class}-{date}.txt # backend/data proof
```
This bundle feeds the adversarial judge (Phase 2) and the closing/evidence comment (Phase 3).
