# Placer API — Endpoint Reference

## Auth
Header: `x-api-key: <key>` only. Bearer/Basic fail.

## Endpoints

| Endpoint | Method | Tier | Async? |
|----------|--------|------|--------|
| `/v1/poi` | GET | Standard | No |
| `/v1/poi/my-properties` | GET | Standard | No |
| `/v1/reports/visit-metrics` | POST | Standard | No |
| `/v1/reports/visit-trends` | POST | Standard | No |
| `/v1/reports/trade-area-demographics` | POST | Standard | Yes (202) |
| `/v1/reports/retail-sale` | POST | Standard | No |
| `/v1/reports/visit-metrics/cbgs` | POST | Premium | Yes (202) |

`/v1/search` → 404 in our tier.

## CBG Request
```json
{
  "entityIds": ["venue:xxxx"],
  "startDate": "2024-01-01",
  "endDate": "2024-01-31",
  "granularity": "month"
}
```
## CBG Response
```json
{
  "data": {
    "location": "Home",
    "granularity": "month",
    "trafficVolPct": 70,
    "visitsByCBGs": [
      { "regionCode": "060372037101", "visits": 145, "population": 1205 }
    ]
  }
}
```
`regionCode` = 12-digit FIPS CBG code. Missing CBGs = privacy redacted, not an error.

## Visit Metrics Request
```json
{
  "entityId": "venue:xxxx",
  "startDate": "2024-01-01",
  "endDate": "2024-01-31"
}
```

## Visit Trends Request
```json
{
  "entityId": "venue:xxxx",
  "startDate": "2024-01-01",
  "endDate": "2024-03-31",
  "granularity": "weekly"
}
```

## 202 Polling
On 202: response contains `report_id`. Poll `/v1/reports/{report_id}` until status = COMPLETED.
Backoff: 5s → 15s → 30s → 60s cap.
