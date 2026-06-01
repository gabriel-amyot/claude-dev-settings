# SBE Catalog — Empty Circles at Country Zoom
**Date:** 2026-05-04
**Epic:** KTP-130 (Klever Measurement Map)
**Author:** Mary (Business Analyst lens)
**Status:** DRAFT — pending confirmation (Step 4 not executed per task scope)

---

## SBE-1: Country Zoom Circles Must Display Store Count Label

**Context:** A user opens the Measurement Map for the first time. The map initializes at zoom 3.75 (country view). Metrics circles appear over states that have conversion data.

```
GIVEN the user is viewing the Measurement Map at country zoom (zoom level ≤ 5)
  AND at least one state has a conversion count > 0
  AND the METRICS_CIRCLES layer is visible

WHEN the map finishes loading and renders state-level metrics circles

THEN each circle over a state with count > 0 displays the formatted count number
     inside the circle (e.g., "1.2K", "45", "2.1M")
  AND the count number is legible (sufficient contrast, font size fits within the circle)
  AND circles over states with count = 0 are either hidden or rendered as visually
     distinct minimal dots (not as large empty circles)
```

**Current behavior:** Circles appear as large white/semi-transparent outlines with no visible text inside. The text is technically rendered but either: (a) font-size (fixed 14px) is too large for the circle's radius at country zoom, making it clip or overflow; or (b) the icon image fails to load, leaving only an invisible text element; or (c) the text-color (#000000) for zero-data states renders invisible on the near-transparent black icon.

**Root cause:** `text-size` is hardcoded at 14px in `update-zip-layers.tsx` (line 667). It is not zoom-responsive. At zoom 3.75, icon-size interpolation gives a circle radius of ~9–12px for typical data counts. A 14px font inside a 12px radius = text overflows or is clipped by Mapbox.

**Fix scope:** FRONTEND_ONLY

**Files:**
- `components/map/functions/update-map-layers/update-zip-layers.tsx` (line 667: `"text-size"`)
- `components/map/consts/config.tsx` (`metricsLabels.fontSize = 14`)

**Fix direction:** Make `text-size` a zoom-responsive interpolate expression, matching the icon-size growth. Reference: `FONT_SIZE_LOOKUP` and `COUNTY_FONT_SIZE_LOOKUP` in `config.tsx` show the pattern for the legacy DOM markers. A Mapbox expression equivalent would scale text-size from ~8px at zoom 2 to ~14px at zoom 6+.

**[CLARIFY]:** Is the expected behavior for count > 0 circles to show the label at country zoom, or should label display only start at county zoom (zoom ≥ 6)? The user said "they should show the store count number inside them" which implies they expect it at country zoom.

---

## SBE-2: Zero-Data State Circles Must Not Look Broken

**Context:** After a user opens the map, states without conversion data in the selected date range also receive circles (they are pre-generated for all states present in the CONVERSIONS data). At 10% opacity, these appear as near-invisible or "ghost" circles.

```
GIVEN the user is viewing the Measurement Map at country zoom
  AND one or more states have count = 0 for the selected date and data layer

WHEN the map renders metrics circles for those zero-data states

THEN zero-data states do NOT show a large visible circle outline
  AND zero-data states are either (option A) fully hidden (display: none / opacity: 0)
      OR (option B) shown as a visually distinct tiny dot (≤ 4px radius) that
      communicates "there are stores here" without implying loadable data
  AND the zero-data visual treatment is clearly distinguishable from the non-zero treatment
```

**Current behavior:** Zero-data states render with `icon-opacity: 0.1` — a 10% opacity black circle with invisible text. On a light-gray map background, this appears as a faint semi-transparent circle outline, which users interpret as a broken loading state.

**Root cause:** The current zero-state design uses partial transparency to "hide" the circle without removing it. The result reads as broken rather than intentional. `icon-opacity: 0.1` was chosen as a "10% for zero-data" visual hint, but 10% black on light gray still produces a perceptible circle shape.

**Fix scope:** FRONTEND_ONLY

**Files:**
- `components/map/functions/update-map-layers/update-zip-layers.tsx` (lines 698–705)

**Fix direction:** Option A: Set `icon-opacity: 0` for count=0 to hide circles entirely at country zoom. Option B: Raise `metricsCircles.minZoom` to 5 or 6 so zero-data circles are only shown at county/zip zoom levels where the UI is in a more detailed exploration mode.

**[CLARIFY]:** Should zero-data circles be completely hidden at country zoom, or should they be "ambient dots" to show store coverage? Gabriel mentioned "smaller dots" as an acceptable option — confirming this covers zero-data states too would remove ambiguity.

---

## SBE-3: Initial Map Load Must Not Show Circles Until Data Is Ready

**Context:** The state centers are loaded progressively from Mapbox vector tiles. On first render, some state centers may not yet be available, causing partial or no circle rendering. As tiles load, circles appear one-by-one, which produces an jarring visual.

```
GIVEN the user has just opened the Measurement Map (first load)
  AND state center tiles are still loading from the Mapbox tileset

WHEN the map finishes its initial render cycle

THEN metrics circles are either all visible (all centers loaded) or all hidden (tiles still loading)
  AND there is no intermediate state where some circles appear and others are absent
  AND once all circles are ready, they appear together (not one-by-one)
```

**Current behavior:** `extractStateCenters()` fires on `sourcedata` events as tiles load progressively. Each `calculateStateExpressions()` call produces metrics for only the states whose centers have been extracted so far. Circles appear one-by-one as tiles load, creating a visually inconsistent intermediate state.

**Root cause:** Progressive tile extraction in `setup-map-layers.tsx` (lines 350–368). The `markersSkipped` log in `calculate-country-layers.tsx` (line 82) confirms this is known.

**Fix scope:** FRONTEND_ONLY

**Files:**
- `components/map/functions/setup-map-layers.tsx` (lines 350–368: `handleSourceData`)
- `components/map/functions/calculate-map-layers/calculate-country-layers.tsx` (lines 77–83)

**Fix direction:** Defer rendering METRICS_CIRCLES until `isSourceLoaded(US_STATES_CENTERS_TILESET_SOURCE)` returns true (all tiles for current viewport loaded). Use the `idle` event (already partially implemented for county centers at line 434) as the trigger for the initial circle render pass. This ensures circles appear all at once rather than progressively.

**[CLARIFY]:** Is a brief loading state acceptable on first open (e.g., a spinner or "Loading map data..." message), or should the state fill colors be considered sufficient feedback while circles load?

---

## SBE-4: First Impression View Must Look Intentional at Country Zoom

**Context:** Country zoom (3.75) is the default initial state of the map. This is the view that 100% of users see before any interaction.

```
GIVEN a user opens the Measurement Map for the first time
  AND the initial zoom is set to 3.75 (country view, CONFIG.map.zoom)

WHEN the map fully loads and all data is rendered

THEN the visual state of the map looks intentional and complete
  AND there are no elements that appear "broken" or partially loaded
  AND if circles are shown, they contain legible content OR are visually minimized dots
  AND the state fill colors (data layer choropleth) are visible and accurate
```

**Current behavior:** Large empty-looking circles float over states. The state fill layer works correctly (Alabama shows yellow in the screenshot). But the metrics circles layer draws large blank circles that visually conflict with the intentional choropleth and look like a loading error.

**Root cause:** Combination of SBE-1 (illegible text at country zoom) and SBE-2 (broken-looking zero-data treatment). The fixes for SBE-1 and SBE-2 together address this.

**Fix scope:** FRONTEND_ONLY

**Files:** Same as SBE-1 and SBE-2.

**Fix direction:** No separate code change needed beyond SBE-1 and SBE-2 fixes. This SBE validates the overall outcome of those fixes.

---

## SBE-5: Visitor Flow Circles Must Not Appear at Country Zoom Without User Action

**Context:** The screenshot shows green dashed curved lines connecting the circles. These are the visitor flow lines (`visitor-flow-lines-layer`, color: `#5BA67D`). Visitor flow circles should only appear when a user has selected a specific store location and the flow visualization is active.

```
GIVEN the user is viewing the Measurement Map at country zoom
  AND no store location has been selected (selectedLocationId = null)
  AND the Distribution In Time animation is not active

WHEN the map renders at country zoom

THEN no visitor flow circles or flow lines are visible on the map
  AND the visitor flow overlay (SVG canvas, DistributionInTime component) is not rendered
```

**Current behavior:** Green dashed lines and circles connected by them appear at country zoom in the screenshot, suggesting the visitor flow visualization is persisting from a previous state or is being activated unexpectedly.

**Root cause:** TRACE_PENDING — requires further investigation. The `isFlowModeActive()` function in `update-flow-lines.tsx` and the flow cleanup on `geographicScope` change (line 107 in `proximity-map.tsx`: `setPopupData(null)`) may not be fully clearing the SVG flow overlay. The `useLocationFlowClear` hook should handle this, but may have edge cases.

**Fix scope:** FRONTEND_ONLY

**Files:**
- `components/map/hooks/useLocationFlowClear.tsx` (flow cleanup logic)
- `components/map/functions/update-map-layers/update-flow-lines.tsx` (isFlowModeActive)
- `components/map/proximity-map.tsx` (line 107: geographicScope change handler)

**[CLARIFY]:** Confirm whether the green circles/lines in the screenshot are intentionally visible (user had previously selected a location and flow persisted), or if they are appearing in the initial state without prior user action. This determines if SBE-5 is a separate bug or expected behavior.

---

## Priority Matrix

| SBE | Title | Severity | P0/P1 | Fix complexity |
|-----|-------|----------|-------|----------------|
| SBE-1 | Circles must display count label | P1_HIGH | P1 | Low — text-size expression |
| SBE-2 | Zero-data circles must not look broken | P1_HIGH | P1 | Low — opacity/minZoom |
| SBE-3 | Circles must not appear until data ready | P2_MEDIUM | P2 | Medium — idle event gate |
| SBE-4 | First impression must look intentional | P0_BLOCKER | P0 | Resolved by SBE-1+2 |
| SBE-5 | Flow circles must not appear at country zoom | P1_HIGH | P1 | Medium — state cleanup |

**Recommended implementation order:** SBE-2 first (quickest fix, biggest visual impact), then SBE-1 (text-size expression), then SBE-5 (flow state cleanup). SBE-3 and SBE-4 follow naturally.

---

## Open Clarifications

1. **SBE-1 [CLARIFY]:** Should count labels display at country zoom (zoom ≤ 5), or only at county zoom (zoom ≥ 6)?
2. **SBE-2 [CLARIFY]:** For zero-data states at country zoom: fully hide, or show as tiny ambient dots?
3. **SBE-3 [CLARIFY]:** Is a brief loading state acceptable on first open while tiles load?
4. **SBE-5 [CLARIFY]:** Are the green flow circles in the screenshot an intentional pre-existing state (user had selected a location), or are they appearing on first load?
