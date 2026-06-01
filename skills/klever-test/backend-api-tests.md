# Backend: API E2E Tests

Python scripts that call proximity-report REST endpoints with assertions. Run standalone against `localhost:8097`.

## Scripts

Located at `~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-proximity-report/`:

| Script | Endpoint | Tests | Purpose |
|--------|----------|-------|---------|
| `test_map_api.py` | `POST /api/v1/map/data/state` | 18 | State-level map data: valid requests, invalid inputs, cache behavior |
| `test_visitor_origins_api.py` | `GET /api/v1/map/visitor-origins` | 4 | KTP-130 visitor origin data: array shape, field presence, sort order |

**Total: 22 tests**

## Prerequisites

Backend must be running on port 8097:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8097/actuator/health
# Expected: 200
```

Python 3 with `requests` library:
```bash
python3 -c "import requests; print('OK')"
```

## Run Commands

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-backend/grp-ms/app-proximity-report

# Run all backend tests
python3 test_map_api.py 2>&1
python3 test_visitor_origins_api.py 2>&1

# Or both sequentially
python3 test_map_api.py 2>&1 && python3 test_visitor_origins_api.py 2>&1
```

## What They Test

### test_map_api.py (18 tests)

**Phase 1 — Valid requests (200s):**
- Single state (WA)
- Multiple states (WA, OR, CA)
- Lowercase state IDs
- Multi-channel filter
- All 50 states
- East coast states
- Date variations

**Phase 2 — Invalid requests (400s):**
- Empty advertiser ID
- Missing date
- Future date
- Empty IDs array
- Invalid state code
- Pre-2020 date
- Unknown channel

**Phase 3 — Cache behavior:**
- Two identical requests, timing comparison

### test_visitor_origins_api.py (4 tests)

- locationId=854 (Shrimp Basket Gulf Shores): 200, non-empty array, fields present, sorted desc by volume
- locationId=999 (unmapped): 200, empty array
- locationIds 855/856/857: smoke check
- Missing locationId param: 400

## Report

Parse stdout for pass/fail lines. Report inline or to ticket folder if context exists.
