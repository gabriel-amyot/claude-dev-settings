# SBE Catalog — KTP-130 Measurement Map UX Feedback
**Date:** 2026-05-06
**Status:** DRAFT — awaiting Step 4 confirmation loop
**Epic:** KTP-130 (Klever Measurement Map)
**Source findings:** findings.md (6 findings, all survived Mary's audit)

---

### SBE-1: Left panel width reduced to preserve map canvas

**Context:** Gabriel is viewing the Measurement Map for Shrimp Basket with the POI search
panel open and the store detail panel open on the right.

GIVEN the user is on the Measurement Map
  AND the POI search panel is open (left-72 anchor)

WHEN the map loads or the POI panel is toggled open
THEN the left filter panel (Panel component) must not exceed 240px wide
  AND the total left-side panel footprint (filter + search) must not exceed 480px at 1280px viewport

**Current behavior:** Panel is hardcoded `w-72` (288px). With POI search panel also at `w-72`
anchored at `left-72`, total left footprint = 576px. At 1280px viewport width, the map canvas
receives only ~384px (minus the 320px right detail panel), which is less than a third of the screen.

**Root cause:** `panel.tsx` line 11 — `w-72` hardcoded, no responsive override. All downstream
offsets (`left-72`, `left-144`) are coupled to this value.

**Fix scope:** FRONTEND_ONLY

---

### SBE-2: POI search results and filter panel are visually separated

**Context:** Gabriel is on the Measurement Map with the POI search panel open next to the
filter/metrics panel.

GIVEN the user is on the Measurement Map
  AND the POI search panel is open

WHEN the POI search panel renders its results list
THEN the results list must have a clear visual boundary that does not visually bleed into
     the filter/metrics panel content
  AND the border or background contrast between the two panels must be sufficient to read
     each panel's content independently

**Current behavior:** Both `Panel` and `PoiSearchPanel` share `z-[80]`, with `PoiSearchPanel`
at `left-72` immediately adjacent. When content is dense (many results or long metric names),
the visual boundary between the two panels is not clear enough.

**Root cause:** `poi-search-panel.tsx` lines 110-117 — panel uses `bg-sidebar` while the
parent Panel uses `bg-white`, but both share the same z-level with only a `border-r` as
separator.

**Fix scope:** FRONTEND_ONLY

---

### SBE-3: Conversion type names displayed as human-readable short labels

**Context:** Gabriel is viewing the Conversions section, which lists campaign conversion
types. The raw BigQuery strings are being shown as labels.

GIVEN the user is viewing a store that has conversion data
  AND conversion type names in BigQuery contain patterns like
      "BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30"

WHEN the conversion type name is rendered in any panel or control
THEN the displayed label must strip all hex config IDs, country codes, and advertiser
     boilerplate
  AND any date range must be reformatted as "Mon-Mon YYYY" (e.g., "May-Jun 2025")
  AND the full raw name must be available in a tooltip for traceability
  AND the resulting label must not exceed 30 characters visible

**Current behavior:** Raw BQ strings are displayed verbatim in the Conversions selector.
The `shortenConversionName()` function in `store-detail-panel.tsx` exists and strips noise
but (a) strips dates entirely rather than reformatting them, and (b) is not applied in
`ConversionsTypeSelect`.

**Root cause:** `store-detail-panel.tsx` lines 53-81 (`shortenConversionName`) — date stripping
logic removes all `YYYY-MM-DD` patterns rather than extracting and reformatting them. Also
not applied in `controls/conversions-type-select.tsx`.

**Fix scope:** FRONTEND_ONLY

**[CLARIFY]** Gabriel's example "Shrimp Basket — May-Jun 2025": should the brand/advertiser
name be preserved in the short label, or stripped? Current algorithm strips it. Proposed:
keep brand name + reformatted date range, strip everything else.

---

### SBE-4: Top-right control buttons vertically aligned

**Context:** Gabriel is looking at the top-right control area of the Measurement Map where
"Distribution in time", "Summary", and "Presentation mode" buttons appear.

GIVEN the user is on the Measurement Map
  AND at least two of the three top-right controls are visible

WHEN the controls render
THEN all visible controls must share the same vertical midline (items-center alignment)
  AND no button must appear higher or lower than its siblings

**Current behavior:** The top-right flex container (`proximity-map.tsx` line 222) uses
`flex flex-row p-3 space-x-3` without `items-center`. The `DistributionInTimeButton` is
conditionally rendered, causing remaining elements to shift when it is absent. The `Summary`
component wraps a `RelativeSheet` which may have different intrinsic height.

**Root cause:** `proximity-map.tsx` line 222 — missing `items-center` on the flex container.

**Fix scope:** FRONTEND_ONLY

---

### SBE-5: Hero cards show "—" with tooltip when metric data is absent

**Context:** Gabriel has clicked a store on the Measurement Map. The StoreHeroBar appears
with all four cards showing "N/A" even though the panel is visible (store is mapped).

GIVEN the user is viewing a store location in the Measurement Map
  AND the store is mapped in Placer.ai (storeMetrics.mapped = true)
  AND one or more hero card values are null (no data for that metric)

WHEN a hero card value is null
THEN the card must display "—" instead of "N/A"
  AND the card must show a tooltip explaining why the data is absent
     (e.g., "Incremental Lift requires InMarket integration with 10M+ impressions"
      or "ROAS requires pixel-based conversion revenue data")

**Current behavior:** `store-hero-bar.tsx` lines 89, 103, 113, 123 — all four cards display
the string "N/A" for null values. No tooltip is shown to distinguish expected absence from
a data error. All four values (totalVisitors, incrementalLiftPct, costPerVisit, onlineRoas)
are null for the Shrimp Basket Navarre location in this session.

**Root cause:** `store-hero-bar.tsx` — fallback text is "N/A" with no tooltip. The Placer
metrics are mapped but numeric fields are null (likely insufficient historical data or BQ
join producing no rows for this location/period).

**Fix scope:** FRONTEND_ONLY

**Note:** If totalVisitors is also null despite `storeMetrics.mapped = true`, the backend
Placer integration may have an issue fetching POI-level data for this specific location.
That would be a separate investigation (data gap, not a display bug).

---

### SBE-6: Timeline bottom area free of unexpected dashed visual artifacts

**Context:** Gabriel is looking at the timeline area at the bottom of the map in
"Distribution in time" mode. Dashed lines appear across the timeline area unexpectedly.

GIVEN the user is on the Measurement Map
  AND "Distribution in time" mode is active (timeline visible at bottom)

WHEN the timeline renders
THEN no dashed line artifacts must appear outside of the timeline slider track itself
  AND if flow lines (animated Mapbox dashes) are visible, they must be constrained to
     the map canvas and must not visually bleed into the DOM timeline overlay

**Current behavior:** Dashed lines are visible in the bottom timeline area. Candidate causes:
(a) animated Mapbox flow line layer (`line-dasharray: [3, 4]`, update-flow-lines.tsx:296)
bleeding through a z-index gap between the map canvas and the timeline DOM overlay, or
(b) `dailyTicks` in `timeline-slider.tsx` (lines 101-110) rendering so densely at high
`totalDays` counts that tick marks visually merge into a dashed pattern.

**Root cause:** TRACE_PENDING — requires visual comparison with flow lines disabled vs.
enabled, and with different `totalDays` values. Most likely candidate: the animated flow
line layer renders on the map canvas which sits behind the timeline overlay, but at high
z-index values the Mapbox canvas and DOM overlay boundaries may be inconsistent.

**Fix scope:** FRONTEND_ONLY

**[CLARIFY]** Are the dashed lines the animated flow lines (intentional data visualization
for visitor origins) or a rendering artifact from the tick marks? If the former, the fix is
z-index isolation or pausing flow animation while the timeline overlay is active. If the
latter, the fix is reducing tick density above a threshold (e.g., render every 7th tick
when totalDays > 60).

---

## Summary Table

| SBE | Title | Category | Severity | Fix Scope | Code File |
|-----|-------|----------|----------|-----------|-----------|
| SBE-1 | Panel width reduction | LAYOUT | P1_HIGH | FRONTEND_ONLY | panel.tsx:11 |
| SBE-2 | Panel visual separation | LAYOUT | P1_HIGH | FRONTEND_ONLY | poi-search-panel.tsx:110-117 |
| SBE-3 | Human-readable conversion labels | DATA | P1_HIGH | FRONTEND_ONLY | store-detail-panel.tsx:53-81 + conversions-type-select.tsx |
| SBE-4 | Top-right controls alignment | UX | P2_MEDIUM | FRONTEND_ONLY | proximity-map.tsx:222 |
| SBE-5 | Hero cards null state polish | UX | P1_HIGH | FRONTEND_ONLY | store-hero-bar.tsx:89-123 |
| SBE-6 | Timeline dashed artifacts | UX | P2_MEDIUM | FRONTEND_ONLY | timeline-slider.tsx + update-flow-lines.tsx |

**Open clarifications before Step 4 confirmation:**
- SBE-3: Preserve brand name in short label, or strip it?
- SBE-6: Are the dashes the animated flow lines or tick artifacts?
