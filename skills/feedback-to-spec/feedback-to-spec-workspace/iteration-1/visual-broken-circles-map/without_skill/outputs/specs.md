# Specification: Fix Empty Green Circles on Measurement Map (Country Zoom)

**Date:** 2026-05-04
**Ticket context:** KTP-130 (Measurement Map)
**Priority:** High — this is the first-impression view (default zoom on map open)

---

## Problem Statement

When the Measurement Map loads at country zoom (~3.75), large white circles with green borders appear over states. They contain no text, no count, no icon. They look broken — as if data failed to load. These are competitor location pins rendered at a zoom level where they are not meaningful.

---

## Specification

### AC-1 — Competitor circles are hidden at country scope (COUNTRY geographic scope)

**Given** the map is displayed at `GeographicScope.COUNTRY`
**When** competitor data is loaded and `competitorsVisible` is true
**Then** the `COMPETITORS_CIRCLES` layer must not be rendered (layer must not be added, or must be removed if already present)

**Implementation note:**

In `handleCompetitorsData()` in `update-zip-layers.tsx`, add a scope guard before adding the layer:

```ts
// Guard: competitors are individual store pins, not meaningful at country zoom
const { geographicScope } = useMapStore.getState();
if (geographicScope === GeographicScope.COUNTRY) {
  removeCompetitorsLayer(map);
  removeCompetitorsSource(map);
  return;
}
```

This guard should be added immediately after the existing `!competitorsData || !competitorsVisible` check.

---

### AC-2 — Competitor circles appear correctly at county and zip scopes

**Given** the map transitions to `GeographicScope.COUNTY` or `GeographicScope.ZIP_CODE`
**When** competitor data is loaded and `competitorsVisible` is true
**Then** competitor circles render with white fill, green border, at the correct zoom-based radius

No change to the existing rendering logic for county and zip scopes.

---

### AC-3 — Competitor circles are removed when scope returns to country

**Given** the user has zoomed in to county or zip scope (competitors visible)
**And** the user zooms back out to country scope
**When** `geographicScope` changes to `GeographicScope.COUNTRY`
**Then** the `COMPETITORS_CIRCLES` layer is removed from the map

**Implementation note:**

The `MapUpdater` useEffect already re-runs when `geographicScope` changes (it is in the dependency array). The scope guard in AC-1 will cause `handleCompetitorsData` to remove the layer on every render at country scope, including on scope transitions.

---

### AC-4 — Metrics circles (conversions) display a count at country zoom

**Given** the map is at country scope
**And** a state has conversion data with count > 0
**When** the metrics circles layer renders
**Then** each circle shows its `formattedCount` label (e.g. "1.2K", "450")

**Given** a state has count = 0
**Then** the circle is rendered at 10% opacity with no visible label (current behavior is acceptable)

**Note:** This AC is likely already working correctly based on code review. It is included to provide a clear acceptance target for regression testing.

---

### AC-5 — No empty circles appear at country zoom as first impression

**Given** the user opens the Measurement Map for the first time (default zoom ~3.75)
**And** an advertiser is selected
**When** the map finishes loading
**Then** no empty circles appear — only:
- Colored state fill polygons (if data is available)
- Small red location dots (if locations are toggled on and zoom ≥ 2)
- Black metrics circles with count labels (if conversion data exists)
- State boundary lines

---

## Out of Scope

- Changing the visual design of competitor circles at county/zip zoom (separate UX ticket)
- Adding a label to competitor circles (separate ticket)
- Changing the metrics circle color scheme

---

## Test Plan

1. Open the Measurement Map at default zoom (~3.75) with a configured advertiser.
2. Verify no green circles are visible.
3. Zoom in to county level — verify green competitor circles appear (if `competitorsVisible` is on).
4. Zoom back out to country — verify green circles disappear.
5. Zoom to zip level — verify green competitor circles still appear.
6. Toggle competitors off — verify no circles at any scope.

---

## Relevant Files

| File | Change needed |
|---|---|
| `components/map/functions/update-map-layers/update-zip-layers.tsx` | Add scope guard in `handleCompetitorsData()` |
| `components/map/components/map-updater.tsx` | No change needed — dependency array already includes `geographicScope` |
| `components/map/consts/config.tsx` | No change needed — `minZoom: 8` config is correct but insufficient alone |
