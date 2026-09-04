---
name: goldfish
description: "Goldfish Ads DOOH (digital out-of-home) vendor integration for the Measurement/proximity map. One multi-mode skill: fetch (pull DOOH screen inventory by viewport/radius, enrich detail, resolve lookups — for plotting on the map), plan (planning queries: screen availability by geography, plus the buy-side campaigns/data-plans surface). Trigger: 'goldfish', 'DOOH inventory', 'fetch DOOH', 'billboard inventory', 'DOOH locations for the map', 'out-of-home planning', 'screens near X', 'DOOH availability'. Klever org. Input: lat/lng/radius or a screen id. Returns: screen pins / availability summary."
nav:
  bay: build
  when: "Any Goldfish DOOH work for the map: fetching screen inventory to plot, enriching a screen's detail, or planning screen availability by geography."
  when_not: "Foot-traffic / visit / CBG data (use adtech:placer). Geocoding addresses (use mapping:geocode — Goldfish screens arrive pre-geocoded). Pulling Klever store lists from BQ (use klever-bq-store-lookup)."
  org: [klever]
---

# adtech:goldfish — Goldfish Ads DOOH Vendor Integration (multi-mode)

The advertising-domain sibling of `adtech:placer`. Goldfish Ads is a DOOH (digital
out-of-home) inventory/planning vendor: screen locations, publishers, media types,
impression estimates. Its location data feeds the proximity/measurement map's billboard
layer (KTP-131 / KTP-748). Two modes share one auth, base URL, and set of gotchas, so
that reference lives here once. The mode sections contain the full working procedures
inline. Bundled: `scripts/fetch_inventory.sh`, `scripts/fetch_lookups.sh`,
`references/endpoints.md`.

> **Spike status: COMPLETE.** This skill was built against a live, validated API
> (re-verified 2026-06-03). Call the **REST API directly** — do NOT use the OAuth-gated
> "Goldfish DOOH Planning" MCP; the REST surface is fully documented, keyed, and
> unmetered on inventory. The OAuth MCP is unnecessary.

## Modes

| Mode | Does |
|---|---|
| `fetch` | Pull DOOH screen inventory by viewport/radius for plotting on the map; enrich a screen via the detail endpoint; resolve FK lookups (publisher / location-type / media-type / dimension) to human-readable names. Screens arrive **pre-geocoded** — they plot directly, no `mapping:geocode`. |
| `plan` | Planning queries. (a) **Availability by geography** — aggregate inventory in an area by media type / location type / publisher. (b) **Buy-side planning surface** — read existing `data-plans` and `campaigns` (paginated). |

Pick the mode from intent. "Screens near Toronto" / "DOOH inventory for the map" →
`fetch`. "How many billboards in the area" / "what's planned" / "campaign inventory" →
`plan`.

---

## Shared reference (all modes)

### Auth & access
| Detail | Value |
|---|---|
| Base URL | `https://api.goldfishads.com` |
| API version | **v2 only.** v1 returns `410 Gone`. All paths under `/v2/`. |
| Auth headers | `x-api-key: $GOLDFISH_API_KEY` **AND** `uid: app-goldfish@beklever.com` (both required) |
| Bearer/Basic | Not supported. Missing/invalid key → `401 "Invalid login credentials"`. |
| Account | `app-goldfish@beklever.com`, org "Klever Programmatic" (id 707) |
| Key source | 1Password, vault `grp-client-portal-ui`, item "Goldfish DOOH". **Not `.env`** — that file holds only `PLACER_API_KEY`. Deployed services use GCP Secret Manager. |
| Rate limits | None on inventory endpoints (per Jason Bamford, Goldfish AM). |
| Delivery | Pull-only. No webhooks. |

**Prerequisites (verify before any mode):**
```bash
GFKEY=$(op item get lptegkil5tsm5uqa6pzw7pdaue --fields credential --reveal)
GFUID=$(op item get lptegkil5tsm5uqa6pzw7pdaue --fields username --reveal)
curl -s -o /dev/null -w "HTTP:%{http_code}\n" \
  -H "x-api-key: $GFKEY" -H "uid: $GFUID" \
  "https://api.goldfishads.com/v2/media-types"
```
Do not assign the uid to `UID` — it is a read-only shell variable and the `@` throws
`bad math expression`. The bundled scripts read 1Password themselves, so they need no
exported vars.
Expect `HTTP:200`. A `401` means the key is missing/wrong. Stop and tell the user.

### Gotchas (silent failures / drift traps)
- **Every response wraps its payload in a singular camelCase key — there is no flat
  array.** `/v2/inventory` → `{"inventory":[...]}`; `/v2/inventory/{id}` →
  `{"inventory":{...}}`; lookups → `{"mediaType":[...]}`, `{"publisher":[...]}`,
  `{"locationType":[...]}`, `{"slotDimension":[...]}`, etc. Always unwrap by key.
  *(The April 2026 contract documented a flat array; the API drifted to the wrapped
  shape by May 2026. Verify the wrapper before parsing — vendor contracts drift silently.)*
- **`latitude` / `longitude` (full words)** as query params, never `lat`/`lng` (wrong
  names silently fail with a misleading error).
- **Numbers come back as strings.** `latitude`, `longitude`, `cpm`, `avgDailyImpressions`
  are JSON strings, not floats — parse on ingestion.
- **`/v2/inventory` does NOT paginate** — it returns the entire result set in one
  response (1,273 screens at radius=1 in Toronto; 12,506 at radius=5 in Chicago). Use a
  small radius for map viewports.
- **Planning endpoints DO paginate.** `/v2/campaigns` and `/v2/data-plans` return a
  `meta` block (`count`, `pages`, `nextUrl`, `previousUrl`); follow `meta.nextUrl` until
  null. (Campaigns: 167 across 2 pages.)
- **`venueName` can be a hex hash** (e.g. `892664c8d0fffff`) when the venue is unnamed —
  fall back to `name`.
- **`streetAddress` can be empty**; `assetImageUrl` sometimes points to Google Drive
  (may need Drive auth).
- **`radius` unit is assumed miles** (unconfirmed by Goldfish — flag if precision matters).

### Lookup tables (cache at startup, refresh daily)
FK ids on screen records resolve against these. Each wraps in a singular key.

| Endpoint | Wrapper key | Count (2026-06-03) | Resolves |
|---|---|---|---|
| `/v2/location-types` | `locationType` | 99 | `locationTypeId` → hierarchical category ("Retail\|Gas Station") |
| `/v2/publishers` | `publisher` | 455 | `publisherId` → network name (Clear Channel, Lamar) |
| `/v2/media-types` | `mediaType` | ~10 | `mediaTypeId` → format (Billboard, Cinema, Display Panel) |
| `/v2/slot-dimensions` | `slotDimension` | 3,161 | `slotDimensionId` → screen pixel dimensions |
| `/v2/programmatic-platforms` | `programmaticPlatform` | 1 | `programmaticPlatformId` → platform (Place Exchange) |
| `/v2/organizations` | `organization` | 1 | `organizationId` → owner org (Klever = 707) |

`bash scripts/fetch_lookups.sh` pulls and caches all six to `/tmp/goldfish-lookups/`.

### BQ bridge — DOOH has its OWN join (not the Placer entity map)
DOOH screens join to The Trade Desk campaign-performance data, **not** to
`klever_placer_entity_map`. The join key is **`programmaticPlatformKey`** (a UUID on the
screen detail record) which matches the `SITE` column in BQ table
`ttd_normalized_daily_inventory_performance`. Foot-traffic (Placer) and DOOH (Goldfish)
are separate bridges; do not conflate them.

### Non-working endpoints (need an internal market id)
| Endpoint | Method | Issue |
|---|---|---|
| `/v2/inventory/by-market` | POST | 500 for all `market` values — `market` is an internal id not exposed via any discovery endpoint. |
| `/v2/inventory/export` | POST | Same. This is the bulk/CSV export (per Jason). |

Not needed — the real-time viewport approach covers our use case. Revisit with Jason
only if a bulk national sync is required.

---

## Mode: `fetch` (pull DOOH inventory for the map)

Pull screen inventory for a viewport/radius, optionally enrich a screen's full detail,
and resolve FK lookups to human-readable names. Verify prerequisites (Shared reference)
first.

### 1. Viewport / radius query (compact records)
```bash
bash scripts/fetch_inventory.sh 43.6532 -79.3832 1   # lat lng radius(mi) → /tmp/goldfish-inventory.json
```
Or directly:
```bash
curl -s -H "x-api-key: $GOLDFISH_API_KEY" -H "uid: app-goldfish@beklever.com" \
  "https://api.goldfishads.com/v2/inventory?latitude=43.6532&longitude=-79.3832&radius=1"
```
Response: `{"inventory":[ ... ]}`. **Unwrap the `inventory` key.** Compact record (8
fields): `id`, `latitude` (string), `longitude` (string), `locationTypeId`,
`publisherId`, `mediaTypeId`, `programmaticPlatformId` (nullable), `inventoryPackageId`
(nullable). Parse `latitude`/`longitude` to float to plot.

Keep the radius small for map viewports — there is no pagination and dense metros return
thousands of screens in one payload.

### 2. Detail enrichment (on click / hover)
```bash
curl -s -H "x-api-key: $GOLDFISH_API_KEY" -H "uid: app-goldfish@beklever.com" \
  "https://api.goldfishads.com/v2/inventory/{id}"
```
Response: `{"inventory":{ ... }}` — a 56-field record. Map-relevant fields:
`name`, `venueName` (hex-hash fallback → `name`), `streetAddress` (may be empty),
`monthlyImpressions` / `avgDailyImpressions` (string), `cpm` (string), `outdoor`,
`status`, `active`, `screenCount`, `supportsVideo`/`supportsBanner`/`supportsAudio`,
`assetImageUrl`, `slotDimensionId`, and the FK ids. **`programmaticPlatformKey`** (UUID)
is the BQ join to TTD `SITE`. Full field list: `references/endpoints.md`.

### 3. Resolve lookups (names for ids)
Cache the six lookup tables once (`bash scripts/fetch_lookups.sh`), then map each
screen's `publisherId`/`locationTypeId`/`mediaTypeId`/`slotDimensionId` to its name from
the cached `{"<wrapper>":[...]}` payloads.

### 4. Billboard-pin output mapping
| Pin field | Goldfish source | Transform |
|---|---|---|
| `id` | `id` | direct |
| `name` | `venueName` (fallback `name`) | hex-hash → use `name` |
| `lat` / `lng` | `latitude` / `longitude` | parse string → float |
| `address` | `streetAddress` | may be empty |
| `publisher` | `publisherId` | join `/v2/publishers` |
| `locationType` | `locationTypeId` | join `/v2/location-types` |
| `screenFormat` | `mediaTypeId` | join `/v2/media-types` |
| `dimensions` | `slotDimensionId` | join `/v2/slot-dimensions` |
| `impressions` | `monthlyImpressions` or `avgDailyImpressions` | detail only; parse |
| `cpm` | `cpm` | parse string → float |
| `isProgrammatic` | `programmaticPlatformId != null` | derive |
| `isOutdoor` | `outdoor` | direct |
| `imageUrl` | `assetImageUrl` | may be empty / Google-Drive-gated |
| `ttdJoinKey` | `programmaticPlatformKey` | detail only; → BQ `ttd_normalized_daily_inventory_performance.SITE` |

**Output:** write pins to disk (do not paste large payloads into chat). Summarize:
screens found, by media type, % with impressions, % geocoded (all are, by construction).

---

## Mode: `plan` (availability by geography + buy-side planning surface)

Two complementary planning capabilities. Verify prerequisites (Shared reference) first.

### (a) Availability by geography
Aggregate the viewport inventory (Mode `fetch` step 1) for an area, then group by FK
ids (resolved via cached lookups) to answer "what DOOH is available here":
```bash
bash scripts/fetch_inventory.sh 43.6532 -79.3832 5
python3 -c "
import json, collections
inv = json.load(open('/tmp/goldfish-inventory.json'))['inventory']
print('total screens:', len(inv))
for dim in ('mediaTypeId','locationTypeId','publisherId'):
    c = collections.Counter(r.get(dim) for r in inv)
    print(dim, 'distinct:', len(c), 'top:', c.most_common(5))
"
```
Resolve the top ids to names via the cached lookups. Report: total screens, distribution
by media type / location type / top publishers. This is the validated, primary planning
capability (no extra endpoints, no auth beyond inventory).

### (b) Buy-side planning surface (data-plans & campaigns)
The account's existing DOOH plans and campaigns. **These paginate** — follow
`meta.nextUrl` until null.
```bash
curl -s -H "x-api-key: $GOLDFISH_API_KEY" -H "uid: app-goldfish@beklever.com" \
  "https://api.goldfishads.com/v2/campaigns"          # {"campaign":[...], "meta":{...}}
curl -s -H "x-api-key: $GOLDFISH_API_KEY" -H "uid: app-goldfish@beklever.com" \
  "https://api.goldfishads.com/v2/data-plans"         # {"dataPlan":[...], "meta":{...}}
```
- `meta` = `{count, pages, pageUrl, nextUrl, previousUrl, valid}`. Add `?page=N` to walk
  pages (campaigns: 167 across 2 pages on 2026-06-03).
- **Campaign** record carries: `name`, `code`, `status`, `startDate`/`endDate`,
  `advertiserId`, `organizationId`, `measurementRequested`/`measurementStatus`,
  `galleries`, `userInventories`, `userPOIs`, `userCoordinates`, `rationale`. This is the
  buy-side object the "Createplan" MCP action writes to.
- **DataPlan** record carries: `name`, `code`, `status`, `dataPlanTargeting`,
  `organizationId`.
- `/v2/advertisers` is **empty** for the Klever account (`{"advertiser":[]}`) — expected.

Reading is GET-only and safe. Creating/modifying plans (POST) is out of scope for this
skill — it is a buy-side write path; surface to the user before attempting any write.

**Output:** summarize plans/campaigns (count, statuses, date ranges, measurement status).
Write detail to disk, not chat.

---

## Composition (proximity use case)
Goldfish screens arrive **pre-geocoded** (lat/lng on every record), so the DOOH layer
skips `mapping:geocode` entirely: **`adtech:goldfish` fetch → billboard pins → map**.
The performance overlay joins via `programmaticPlatformKey` → BQ
`ttd_normalized_daily_inventory_performance.SITE` (its own bridge, separate from the
Placer foot-traffic path). See `documentation/bibliotheque/vendors/goldfish/` for the
vendor reference and the validated data contract.
