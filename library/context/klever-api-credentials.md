# Klever API Credentials Reference
**Type:** Reference — DO NOT store actual key values here. This file is committed.

---

## Placer.ai API

| Field | Value |
|-------|-------|
| Auth header | `x-api-key: <key>` |
| Base URL | `https://papi.placer.ai` |
| Docs | `https://docs.placer.ai` |
| Contract tier | Includes premium CBG endpoint (confirmed 2026-04-17) |
| Rate limit | 5,000 calls/hour |
| Weekly cap | 10,000 API calls |

**Where the key lives:**
- `project-management/.env` → `PLACER_API_KEY=...` (gitignored via `.env` pattern)
- Frontend: `grp-app/grp-frontend/app-front-portal/.env.local` → `PLACER_API_KEY=...` (gitignored via `.env*`)
- Backend: `grp-app/grp-backend/grp-ms/app-proximity-report/src/main/resources/application.local.properties` → `placer.api.key=...` (gitignore must cover `*.local.properties`)

**How to get the key:** Ask Gabriel. It's in `project-management/.env` locally.

**Known endpoints we use:**
| Endpoint | Purpose | Tier |
|----------|---------|------|
| `GET /v1/poi` | List account entities | Standard |
| `GET /v1/poi/my-properties` | List custom POIs | Standard |
| `POST /v1/reports/visit-metrics` | Visit summary | Standard |
| `POST /v1/reports/visit-trends` | Time series | Standard |
| `POST /v1/reports/trade-area-demographics` | Demographics | Standard |
| `POST /v1/reports/visit-metrics/cbgs` | CBG visitor origins | Premium — access confirmed |

**Async pattern:** Heavy reports return HTTP 202. Poll with exponential backoff. Placer reimburses 202 calls hourly (don't burn quota).

**B1 blocker (as of 2026-04-17):** Artistry Brand locations NOT yet in Placer system. `my-properties` returns 0. Custom POI build request pending with Nick Christensen (Placer AM). ~1 week build time once submitted.

---

## Tooling Note

**`gcloud` skill is Supervisr-only.** For Klever BQ queries, use the `bq` CLI directly:
```bash
bq query --project_id=prj-p-biz-report-fo53kywlio --nouse_legacy_sql "SELECT ..."
```

---

## Adding New Credentials

1. Store value in the appropriate `.env` / `.env.local` / `application.local.properties` (must be gitignored)
2. Add a row to the table above with service name, auth pattern, base URL, and where key lives
3. Never write the actual key value in this file
