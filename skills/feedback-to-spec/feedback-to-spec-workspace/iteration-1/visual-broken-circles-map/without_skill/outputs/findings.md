# Findings: Empty Circles on Measurement Map (Country Zoom)

**Date:** 2026-05-04
**Ticket context:** KTP-130 (Measurement Map)
**Reported by:** Gabriel (UX feedback)

---

## Visual Observation

The screenshot (`sbe7-empty-circles.png`) shows 6-7 large circles at country zoom level (~3.75). All circles share the same appearance:
- White fill
- Green stroke/border (~2-3px)
- No label or number inside
- Sizes range from small to very large (roughly 30-100px diameter)
- Located at state-center positions across the Southeast US

The circles look like empty shells — they signal presence but convey zero information.

---

## Root Cause Analysis

### Finding 1 — Wrong circle type is visible at country zoom

The green-bordered circles are **competitor circles** (`COMPETITORS_CIRCLES` layer), not metrics circles. Cross-referencing config:

- `competitorsCircles.strokeColor = "#0eac1c"` — matches the green in the screenshot exactly
- `competitorsCircles.color = "#FFFFFF"` — white fill, matches
- `competitorsCircles.minZoom = 8` — **this is the problem**: the layer's `minzoom` is set to 8, but the visual evidence shows circles appearing at zoom ~3.75

There is a mismatch: the config says `minZoom: 8` but either (a) the layer is being added without the minzoom constraint applying correctly, or (b) there is a different source of these circles. The circles are definitely appearing before zoom 8.

**Source file:** `/components/map/functions/update-map-layers/update-zip-layers.tsx` — `addCompetitorsLayer()` function uses `minzoom: CONFIG.styling.competitorsCircles.minZoom` (line 384).

### Finding 2 — Metrics circles exist but have no visible label at country zoom

The `METRICS_CIRCLES` symbol layer (`update-zip-layers.tsx`, `addMetricsLayer()`) renders a Mapbox `symbol` type with both `icon-image` and `text-field`. The text field uses `"formattedCount"` from feature properties. However:

- The `icon-opacity` paint property is set to 0.1 when `count === 0` — meaning zero-data states show ghost circles.
- The icon base is `marker-small-normal` (10px radius, black fill with white stroke) — this does NOT match the green circles in the screenshot.
- `metricsCircles.color = "#000000"` (black) — again does not match.

So the metrics circles (black) are correct and include labels. They are **not** what is broken in the screenshot.

### Finding 3 — Competitors show as large unsized empty circles at low zoom

The `competitorsCircles.radius` expression starts at `zoom: 8` with radius `5`. At zoom levels below 8, Mapbox GL will extrapolate the interpolation backwards, producing a radius of 5 or potentially larger depending on internal extrapolation. Combined with the `minZoom: 8` config value that is not enforced (or is being bypassed), these circles can appear at zoom ~3.75 with their full "large" size driven by the interpolation edge value.

More critically: at zoom 3.75, the store count filter is the country zoom level. Competitor data (`competitorsData`) contains raw store locations — they do not have a "count" value that drives visibility. They are always rendered as white circles with green borders regardless of whether there is meaningful data to show at that zoom.

**The circles are empty because competitor circles show location presence, not a metric value.** They have no text label. At country zoom they are oversized relative to the scale, and there are no counts to display.

### Finding 4 — No zoom-aware suppression for competitor circles at country scope

In `MapUpdater.tsx`, `handleCompetitorsData` is called regardless of `geographicScope`. There is no guard that suppresses competitor pins when `geographicScope === GeographicScope.COUNTRY`. Competitors are individual store pins — displaying them at country zoom is not meaningful and creates the "broken" appearance.

**Source file:** `/components/map/components/map-updater.tsx` — lines 132-135, 294-295. Called in all three on-demand data paths and the fallback path.

### Finding 5 — Marker image generation uses black fill, not green

`generate-metrics-marker-images.ts` generates images with `fillColor: '#000000'` and `strokeColor: '#FFFFFF'`. These are the metrics/conversion circles (black with white border). They do not produce the green-bordered circles. This confirms the green circles are the native Mapbox `circle` type from the `COMPETITORS_CIRCLES` layer, not the symbol layer.

---

## Summary Table

| Circle type | Fill | Stroke | Has label | Visible at zoom 3.75 | Expected at zoom 3.75 |
|---|---|---|---|---|---|
| Metrics (conversions) | Black | White | Yes (`formattedCount`) | Yes (if count > 0) | Yes |
| Location pins (red) | White | Red `#D52815` | No | Yes (minZoom: 2) | Yes (small dots) |
| Competitors (green) | White | Green `#0eac1c` | No | Yes (bug) | No — should be hidden |

The circles Gabriel sees are **competitor circles appearing at country zoom** where they should be suppressed. They are empty (no label), oversized, and the green border makes them visually prominent and confusing — looking like data failed to load.

---

## Affected Files

- `/components/map/functions/update-map-layers/update-zip-layers.tsx` — `handleCompetitorsData()` and `addCompetitorsLayer()` lack scope-based suppression
- `/components/map/components/map-updater.tsx` — calls `handleCompetitorsData` unconditionally at all scopes
- `/components/map/consts/config.tsx` — `competitorsCircles.minZoom = 8` is a config value but not sufficiently enforced at the data-handling level
