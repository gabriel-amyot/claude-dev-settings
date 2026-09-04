# Goldfish Ads API — Endpoint Reference

**Base:** `https://api.goldfishads.com` · **Version:** v2 only (v1 → 410 Gone)
**Auth:** `x-api-key: <key>` **and** `uid: app-goldfish@beklever.com` (both headers).
**Validated:** 2026-04-20 (KTP-522), Toronto 2026-05-28 (KTP-748), re-verified 2026-06-03.

> **Universal shape rule:** every response wraps its payload in a singular camelCase key.
> There is no flat array anywhere. Unwrap by the key named in the table below.

## Endpoints

| Endpoint | Method | Wrapper key | Paginates? | Purpose |
|---|---|---|---|---|
| `/v2/inventory` | GET | `inventory` (array) | No (full set in one response) | Viewport/radius screen lookup. Params: `latitude`, `longitude`, `radius`. |
| `/v2/inventory/{id}` | GET | `inventory` (object) | — | Full 56-field screen detail. |
| `/v2/location-types` | GET | `locationType` | No | 99 hierarchical venue categories. |
| `/v2/publishers` | GET | `publisher` | No | 455 publisher/network names. |
| `/v2/media-types` | GET | `mediaType` | No | ~10 media formats. |
| `/v2/slot-dimensions` | GET | `slotDimension` | No | 3,161 screen pixel dimensions. |
| `/v2/programmatic-platforms` | GET | `programmaticPlatform` | No | Platform lookup (Place Exchange). |
| `/v2/organizations` | GET | `organization` | No | Account info (Klever = id 707). |
| `/v2/data-plans` | GET | `dataPlan` + `meta` | Yes | Buy-side data plans (4 on 2026-06-03). |
| `/v2/campaigns` | GET | `campaign` + `meta` | Yes | Buy-side campaigns (167, 2 pages). |
| `/v2/advertisers` | GET | `advertiser` | — | Empty for Klever account. |

### Non-working (need an internal `market` id)
| Endpoint | Method | Issue |
|---|---|---|
| `/v2/inventory/by-market` | POST | 500 for all `market` values. Internal id, not discoverable. |
| `/v2/inventory/export` | POST | Same. Bulk/CSV export (per Jason). Not needed. |

## GET /v2/inventory — request
| Param | Type | Required | Notes |
|---|---|---|---|
| `latitude` | float | Yes | WGS84. Full word — `lat` silently fails. |
| `longitude` | float | Yes | WGS84. Full word — `lng` silently fails. |
| `radius` | float | Yes | Assumed miles (unconfirmed). |

**No pagination.** radius=1 Toronto → 1,273 screens; radius=5 Chicago → 12,506. Use a
small radius for viewports. Response: `{"inventory":[<compact record>, ...]}`.

### Compact record (list)
`id` (int), `latitude` (string), `longitude` (string), `locationTypeId` (int),
`publisherId` (int), `mediaTypeId` (int), `programmaticPlatformId` (int, nullable),
`inventoryPackageId` (int, nullable).

### Full record (detail) — 56 fields
`{"inventory":{ ... }}`. Notable fields (string-typed numerics flagged):

| Field | Type | Notes |
|---|---|---|
| `id` | int | screen id |
| `name` | string | internal screen name |
| `venueName` | string | human venue; can be a hex hash → fall back to `name` |
| `latitude` / `longitude` | **string** | WGS84 — parse to float |
| `streetAddress` | string | can be empty |
| `coordinates` / `geographicCoordinates` | string | WKT `POINT (lng lat)` |
| `publisherId` / `publisherCode` | int / string | → `/v2/publishers` |
| `locationTypeId` | int | → `/v2/location-types` |
| `mediaTypeId` | int | → `/v2/media-types` |
| `slotDimensionId` | int | → `/v2/slot-dimensions` |
| `monthlyImpressions` | int | detail only |
| `avgDailyImpressions` | **string** | parse |
| `bidstreamImpressions` / `bidstreamInferredImpressions` | int | |
| `impressionMultiplier` / `impressionsPerSpot` | float | |
| `cpm` | **string** | parse |
| `bidFloor` | float | |
| `outdoor` | bool | indoor/outdoor |
| `status` / `active` | string / bool | |
| `screenCount` | int | physical screens at venue |
| `supportsBanner` / `supportsVideo` / `supportsAudio` / `supportsDynamicCreative` / `supportsCbd` / `supportsCannabis` | bool | capabilities |
| `minDuration` / `maxDuration` | float | seconds |
| `assetImageUrl` / `assetName` | string | photo (sometimes Google-Drive-gated) |
| `dmaId` / `regionId` / `countyId` / `countryId` / `postalCodeId` / `censusBlockId` | int | geo FK ids |
| `networkId` / `organizationId` / `userId` / `currencyId` / `integrationTypeId` / `preferredAdFormatId` | int | |
| **`programmaticPlatformKey`** | string (UUID) | **BQ join → `ttd_normalized_daily_inventory_performance.SITE`** |
| `programmaticPlatformPublicKey` / `programmaticPlatformVenueKey` / `programmaticPlatformIndustryKey` | string | platform keys |
| `createdAt` / `updatedAt` / `deletedAt` | timestamp | lifecycle |

## Planning endpoints — pagination
`/v2/campaigns` and `/v2/data-plans` return `meta`:
```json
{"meta": {"pageUrl": "/v2/campaigns?page=1", "nextUrl": "/v2/campaigns?page=2",
          "previousUrl": null, "count": 167, "pages": 2, "valid": true}}
```
Walk pages by appending `?page=N` until `meta.nextUrl` is null.

- **Campaign** keys: `id`, `name`, `code`, `status`, `startDate`, `endDate`,
  `advertiserId`, `organizationId`, `userId`, `user`, `measurementRequested`,
  `measurementStatus`, `galleries`, `userInventories`, `userPOIs`, `userCoordinates`,
  `rationale`, `tsv`, `createdAt`, `updatedAt`, `deletedAt`.
- **DataPlan** keys: `id`, `name`, `code`, `status`, `dataPlanTargeting`,
  `organizationId`, `userId`, `user`, `tsv`, `createdAt`, `updatedAt`, `deletedAt`.

## Status codes
- **200** — data. **401** — key/uid missing or wrong. **410** — used a v1 path.
- **500** on `by-market` / `export` — internal `market` id required (not discoverable).
- **422** — structured validation error (missing required fields).
