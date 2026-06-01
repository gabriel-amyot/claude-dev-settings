# UX Feedback Findings — Measurement Map (KTP-130)
Date: 2026-05-04
Source: Gabriel (verbal + screenshots)

---

## Issue 1: Left Panel Too Wide

### Observation
The left panel eats into the map area. In the screenshot (sbe9-panel-width.png), the panel consumes roughly 1/3 of the total viewport width. When the POI search panel is also open, the two panels together take up approximately 2/3 of the viewport.

### Code Location
- `components/map/components/panel.tsx` — Panel is hardcoded to `w-72` (288px).
- `components/map/components/poi-search-panel.tsx` — POI search panel also hardcoded to `w-72` with `left-72` positioning, resulting in a combined 576px of left-side chrome.
- `components/map/proximity-map.tsx` line 202–203 — Top bar shifts to `left-144` (576px) when the POI panel is open.
- `components/map/components/store-detail-panel.tsx` line 908 — StoreDetailPanel is `w-80` (320px) on the right side.

### Root Cause
No responsive width scaling. Both panels use fixed Tailwind width classes (`w-72`, `w-80`). At typical laptop viewport sizes (~1440px wide), the left panel at 288px is ~20% of the screen, which is acceptable. With the POI search panel open (additional 288px) and the store detail panel on the right (320px), total chrome reaches ~896px, leaving under 550px for the map itself.

---

## Issue 2: Search Results Overlapping Metrics Section

### Observation
In sbe9-panel-width.png, the POI search results list (store name cards with address + ID badge) overlaps with or crowds out the metrics section visible in the left panel (Metrics, Points of Interest, Conversions).

### Code Location
- `components/map/components/poi-search-panel.tsx` — The panel uses `absolute z-[80]` positioning at `left-72`, placing it directly adjacent to the main panel. The panel has `top-0 bottom-0`, meaning it fills full height with a scrollable results list.
- `components/map/components/panel.tsx` — Main panel also uses `absolute z-[80]` at implied `left-0`. The two panels are flush against each other with no visual separation gap beyond a border-right.

### Root Cause
The POI search panel visually overlaps the metrics area because its `z-index` matches the main panel (`z-[80]`), and there is no guard preventing the search results from rendering in the same vertical space as the selected store's metric cards. The search panel content area (`p-4 overflow-auto`) has no max-height constraint, allowing it to run the full viewport height.

---

## Issue 3: Campaign Names Showing Raw IDs

### Observation
Conversions section in the left panel shows raw BQ campaign strings like:
`BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30`

### Code Location
- `components/map/components/store-detail-panel.tsx` — `shortenConversionName()` function (lines 53–81) already exists and attempts to clean the raw name.

### Root Cause
The `shortenConversionName` function strips hex IDs, date ranges, "BeKlever, Inc.", country codes, and trailing underscores/dashes — but the screenshot shows the raw string still rendering verbatim. Two likely causes:

1. The function is applied to `convType` (the raw BQ key) correctly in `CampaignPerformanceSection` (lines 646, 657), but the raw string in the screenshot (`BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30`) would produce `Shrimp Basket` after all the cleaning steps. The screenshot shows the raw version, suggesting either: (a) the conversion name is being rendered somewhere before going through `shortenConversionName`, or (b) the component that renders it in the left panel's Conversions section is a different component entirely.

2. The `ConversionsTypeSelect` control (visible in the left panel in the screenshot) is a separate component at `components/map/controls/conversions-type-select.tsx`. This selector likely renders conversion type names without applying `shortenConversionName`.

### Follow-up Needed
Read `components/map/controls/conversions-type-select.tsx` to confirm whether it renders raw conversion names without shortening.

---

## Issue 4: Top Bar Tab Controls Drifting ("Distribution in time" + "Summary")

### Observation
In sbe1-controls-drift.png, the "Distribution in time" and "Summary" toggle buttons appear to float unaligned in the top-right area of the map. The spacing between them is inconsistent, and they are not visually anchored to the top edge.

### Code Location
- `components/map/proximity-map.tsx` lines 217–232 — The right-side controls are in:
  ```
  absolute z-[100] top-0 right-0 pointer-events-auto transition-all duration-300
  ```
  with `right-80` applied when a location is selected.
- `components/layout/toggle-button.tsx` — The ToggleButton uses Shadcn `Button` with `size="sm"` and conditional black/white background. No explicit width or min-width constraint.

### Root Cause
The two buttons (`DistributionInTimeButton` + `Summary`) live in a `flex flex-row` div with `space-x-3`. When `selectedLocationId` is set, the container shifts left by `right-80` (320px). The flex layout with `space-x-3` (12px gap) has no min-width on each button, so shorter or longer labels cause visual width variation. Combined with the offset transition, the buttons appear to drift rather than stay anchored.

---

## Issue 5: Hero Cards All Showing N/A

### Observation
In sbe1-controls-drift.png, all four hero metric cards (Attributed Visits, Incremental Lift, Cost / Visit, ROAS) show "N/A".

### Code Location
- `components/map/components/store-hero-bar.tsx` — `StoreHeroBar` renders N/A for any field that is null: `visits != null ? formatCount(visits) : "N/A"`. All four metrics are null-guarded.
- `StoreHeroBar` uses `storeMetrics.totalVisitors`, `storeMetrics.incrementalLiftPct`, `storeMetrics.costPerVisit`, `storeMetrics.onlineRoas`.
- The bar is conditionally rendered in `proximity-map.tsx` line 213: `{selectedLocationId && <StoreHeroBar />}`.
- `store-hero-bar.tsx` line 76–78: Early return `null` if `!selectedLocationId || storeMetricsLoading || !storeMetrics?.mapped`.

### Root Cause
Two possible causes:
1. The selected store location is not mapped in Placer.ai (`storeMetrics.mapped === false`), which causes the bar to return null entirely. However, the screenshot shows the bar is visible but with N/A values, meaning `mapped` is true but the metric fields themselves are null.
2. The underlying data fields (`incrementalLiftPct`, `costPerVisit`, `onlineRoas`) legitimately have no data for the selected period/store. These require InMarket integration (lift), spend data (CPV), and conversion pixel revenue (ROAS). For a test store or an early campaign, all four could realistically be null.

This is likely a data availability issue rather than a code bug, but the UX should communicate this differently than showing "N/A" in large bold text across all four cards.

---

## Issue 6: Timeline Dashed Lines

### Observation
In sbe1-controls-drift.png, the timeline at the bottom shows a series of small vertical tick marks along the slider track that look like dashed lines.

### Code Location
- `components/map/controls/timeline-slider.tsx` lines 100–110 — The timeline renders a `dailyTicks` array with one `<div>` per day across the total date range:
  ```tsx
  <div className="w-[1px] h-1 bg-black"></div>
  ```
  Each tick is 1px wide and 4px tall (`h-1`), black, positioned absolutely along the track.

### Root Cause
For a campaign spanning several months (e.g., Shrimp Basket US_2025-05-19_2025-06-30 = ~42 days), the timeline renders 42 individual 1px black tick marks across the slider width. At small rendered widths, these ticks are visually indistinguishable from a dashed line. This is intentional (daily granularity indicator) but the visual output is cluttered and reads as visual noise rather than a clean timeline marker.

---

## Summary Table

| # | Issue | Severity | Component | Type |
|---|-------|----------|-----------|------|
| 1 | Left panel too wide | Medium | `panel.tsx`, `poi-search-panel.tsx` | Layout |
| 2 | Search results overlapping metrics | Medium | `poi-search-panel.tsx` | Layout |
| 3 | Raw campaign names in Conversions select | High | `conversions-type-select.tsx` (suspected) | Data display |
| 4 | Top bar controls drifting | Low | `proximity-map.tsx`, `toggle-button.tsx` | Layout |
| 5 | Hero cards all N/A | Medium | `store-hero-bar.tsx` | UX/Data |
| 6 | Timeline dashed tick lines | Low | `timeline-slider.tsx` | Visual polish |
