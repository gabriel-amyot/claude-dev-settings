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
**CRITICAL: field is `apiIds` (not `entityIds`).** Using `entityIds` silently returns empty data (HTTP 200).
```json
{
  "apiIds": ["venue:xxxx"],
  "startDate": "2024-01-01",
  "endDate": "2024-02-01",
  "granularity": "month"
}
```
**Date range must span at least one full period.** Monthly: endDate >= startDate + 1 month. Weekly: endDate >= startDate + 1 week.

## CBG Response (actual structure, verified 2026-04-23)
```json
{
  "data": {
    "location": "Home",
    "granularity": "month",
    "apiIds": ["venue:xxxx"],
    "trafficVolPct": 70,
    "visitsByCBGs": [
      {
        "visitDurationSegmentation": "allVisits",
        "apiId": "venue:xxxx",
        "dates": ["2024-01-01"],
        "visitsByCBGsTrend": [
          [
            { "CBGCode": 10030114161, "visits": 195.9 },
            { "CBGCode": 10030114194, "visits": 149.3 }
          ]
        ]
      }
    ]
  }
}
```
`CBGCode` = numeric (not string). Zero-pad to 12 digits for FIPS. `visits` = float.
Missing CBGs = privacy redacted, not an error.
Weekly granularity for Gulf Shores: ~519 CBGs, ~5.5K total visits per week.

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
