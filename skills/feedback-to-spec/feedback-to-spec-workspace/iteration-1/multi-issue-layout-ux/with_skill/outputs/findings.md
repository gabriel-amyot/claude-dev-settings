# Feedback Extraction — KTP-130 UX Review 2026-05-04

**Session:** feedback-to-spec Phase 1, Steps 1-2
**Epic:** KTP-130 (Klever Measurement Map)
**Screenshots processed:** 2
**Narration segments:** 1

---

## Step 1: Raw Findings

---

### FINDING-1

```
screenshot: sbe9-panel-width.png
quote: "The left panel is way too wide, it's eating into the map area."
observation: The left panel (containing Metrics, Points of Interest, Conversions, Channel sections)
             occupies the full left strip. It appears visually dominant relative to the map area
             behind it. The panel uses w-72 (288px) and is positioned absolute left-0.
             Additionally the POI search panel opens as a second panel at left-72 (another 288px),
             pushing the map content area significantly to the right.
issue: The left panel consumes too much horizontal space, reducing the effective map viewing area.
expected: The left panel should be narrower (around 240px or narrower), or collapsible to give
          more breathing room to the map.
category: LAYOUT
severity: P2_MEDIUM
```

---

### FINDING-2

```
screenshot: sbe9-panel-width.png
quote: "The search results are overlapping with the metrics section."
observation: In the panel, the POI search results list (location cards for Shrimp Basket stores)
             and the Metrics section (Clicks, Impressions, Spend, Devices) appear to share vertical
             space without clear separation. The search result items and the metrics labels/values
             are visually competing — there is no clear section boundary or scroll container
             isolating the search results from the static metrics above them.
issue: The POI search results list overlaps or bleeds into the metrics section above it,
       making it hard to distinguish search results from fixed metrics.
expected: The search results should be in a dedicated scrollable container clearly separated
          from (and below) the metrics section, with a visible divider or adequate padding.
category: LAYOUT
severity: P2_MEDIUM
```

---

### FINDING-3

```
screenshot: sbe9-panel-width.png
quote: "The campaign names are showing raw IDs like 'BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30'.
        Nobody wants to see that. It needs to be human-readable, like just 'Shrimp Basket — May-Jun 2025'."
observation: In the Conversions section of the left panel, conversion type labels display the raw
             BigQuery campaign string: "BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30".
             The shortenConversionName() function in store-detail-panel.tsx does attempt cleanup
             but the PANEL itself (panel.tsx / left panel area, likely via ConversionsTypeSelect)
             shows raw names before user selects them. The StoreDetailPanel's CampaignPerformanceSection
             uses shortenConversionName() for card labels, but full tooltip still shows raw name.
             The user wants brand name + date range in "Month-Month YYYY" format.
issue: Conversion campaign names in the UI show raw BQ strings with hex IDs, country codes,
       and ISO date ranges instead of human-readable labels.
expected: Conversion names should display as "{Brand} — {Mon}-{Mon} {YYYY}" format.
          Example: "BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30"
          → "Shrimp Basket — May-Jun 2025".
category: DATA
severity: P1_HIGH
```

---

### FINDING-4

```
screenshot: sbe1-controls-drift.png
quote: "These controls up top — the 'Distribution in time' and 'Summary' tabs, they're drifting."
observation: In the top-right area of the map, the 'Distribution in time' toggle button and the
             'Summary' toggle button appear misaligned or visually floating without a containing
             surface. They use flex-row with space-x-3 but have no background container, shadow,
             or pill grouping. They appear as loose, drifting elements against the map background.
             The two buttons are rendered inside a div with z-[100] top-0 right-0 but the parent
             has no background, making them visually disconnected from each other.
issue: 'Distribution in time' and 'Summary' toggle buttons in the top-right feel visually
       unanchored — they drift without a grouping container or visual surface behind them.
expected: The two controls should be presented as a unified control group (e.g., a pill container
          with a subtle background/border) so they read as a cohesive toolbar element.
category: UX
severity: P2_MEDIUM
```

---

### FINDING-5

```
screenshot: sbe1-controls-drift.png
quote: "The hero cards all show N/A."
observation: The StoreHeroBar component (store-hero-bar.tsx) renders four cards: "Attributed Visits",
             "Incremental Lift", "Cost / Visit", "ROAS". All four show "N/A" in the screenshot.
             The component only renders when selectedLocationId is set AND storeMetrics.mapped is true
             AND storeMetricsLoading is false. When a store is selected and metrics are loaded but
             specific data fields (visits, lift, cpv, roas) return null, the component shows N/A
             for each card but still renders the bar.
             For Shrimp Basket, this suggests storeMetrics.mapped is true (bar is visible) but
             the individual metric values (totalVisitors, incrementalLiftPct, costPerVisit, onlineRoas)
             are all null — likely because data pipeline hasn't fully populated these fields yet.
issue: The StoreHeroBar appears with four "N/A" values, providing no information to the user
       and creating visual clutter without utility.
expected: If all hero metrics are N/A, either (a) hide the hero bar entirely, or (b) show a
          single informational "Metrics loading or unavailable" state instead of four N/A cards.
          Individual cards with data should still show; cards with N/A should be suppressed or
          replaced with a graceful "data pending" message.
category: UX
severity: P2_MEDIUM
```

---

### FINDING-6

```
screenshot: sbe1-controls-drift.png
quote: "The timeline at the bottom has some weird dashed lines."
observation: The Distribution in Time timeline (distribution-in-time.tsx + timeline-slider.tsx)
             renders a Radix UI Slider track with daily tick marks. The tick marks are rendered as
             1px-wide black divs via dailyTicks array. Over a campaign period spanning many days,
             these dense black tick marks create a visually noisy "dashed" or "hatched" appearance
             on the timeline track — the ticks are too close together and too visually prominent
             (solid black, h-1) against the slider track background.
             The Slider track itself uses "bg-muted" which may conflict with the white override
             via [&>[data-orientation=horizontal]]:bg-white. The combination of dense ticks +
             white track + no visual differentiation between active/inactive range creates the
             "weird dashed lines" effect.
issue: The timeline bottom bar shows dense tick marks that appear as visual noise ("dashed lines")
       rather than meaningful date markers.
expected: Daily ticks should either be removed or reduced to only major interval markers
          (e.g., monthly or weekly). Tick styling should be lighter (e.g., gray-200, thinner,
          shorter). The active range portion of the slider should be visually distinct.
category: UX
severity: P2_MEDIUM
```

---

### FINDING-7

```
screenshot: sbe1-controls-drift.png
quote: "This whole top bar area needs polish."
observation: The top bar area contains two separate horizontal strips:
             (1) Left-offset strip: MapZoomControls, MapBackButton, DatePickerCalendar, ActivePoiControls — positioned at top-0 left-72
             (2) Right strip: DistributionInTimeButton, Summary, PresentationModeToggle — positioned at top-0 right-0
             When a store is selected (selectedLocationId), the StoreHeroBar appears below the left strip.
             These two strips have no unifying visual surface. They float over the map without a
             consistent background treatment. The right strip has no visual container; the left strip
             uses p-3 but no background. Overall the top area feels unpolished and inconsistent.
issue: The top bar area lacks a cohesive visual treatment — two separate floating control strips
       with no unified container, inconsistent spacing, and no background surface.
expected: The top bar controls should share a unified design language: either a consistent
          frosted-glass / white strip spanning the top of the map, or individual pill-style
          button groups with matching backgrounds and spacing. The two strips should feel like
          one coherent toolbar, not two independent floating rows.
category: UX
severity: P2_MEDIUM
```

---

## Step 2: Code Trace Summary

### FINDING-1: Panel width
```
code_trace:
  file: components/map/components/panel.tsx
  lines: 11-13
  component: Panel (left filter panel)
  fix_scope: FRONTEND_ONLY
  notes: "w-72 = 288px hardcoded. No collapse mechanism. POI search panel (poi-search-panel.tsx:111)
          also uses w-72, placed at left-72, totaling 576px when open. Map area offset via
          left-72 class in proximity-map.tsx:178,202."
```

### FINDING-2: Search results overlapping metrics
```
code_trace:
  file: components/map/components/poi-search-panel.tsx
  lines: 108-160
  component: PoiSearchPanel
  fix_scope: FRONTEND_ONLY
  notes: "POI search panel is a separate absolute-positioned panel (z-[80], left-72, top-0 bottom-0).
          It sits to the right of the main Panel. The visual 'overlap' the user sees is likely the
          POI search results visually competing with the left Panel's metrics section because they
          share the same z-level and left-72 edge. The results div (line 156) has overflow-auto
          but the header section doesn't have a fixed height, causing it to compress the results area."
```

### FINDING-3: Raw conversion names
```
code_trace:
  file: components/map/components/store-detail-panel.tsx
  lines: 53-81 (shortenConversionName function)
  file2: components/map/controls/conversions-type-select.tsx (TRACE_PENDING — not read but inferred)
  component: shortenConversionName, CampaignPerformanceSection, ConversionsTypeSelect
  fix_scope: FRONTEND_ONLY
  notes: "shortenConversionName() exists and strips some patterns, but does not produce the
          'Brand — Month-Month YYYY' format requested. Current logic: strips hex IDs, date ranges,
          company suffixes, country codes. Missing: smart date reformatting (2025-05-19_2025-06-30 →
          May-Jun 2025), brand name extraction (taking 'Shrimp Basket' from the campaign string),
          and proper label format. Also need to check ConversionsTypeSelect for raw name display
          in the filter dropdown — that component was not read but is imported in proximity-map.tsx."
```

### FINDING-4: Controls drift
```
code_trace:
  file: components/map/proximity-map.tsx
  lines: 216-232
  component: Top-right controls div
  fix_scope: FRONTEND_ONLY
  notes: "Top-right div has no background container. Buttons rendered in a bare flex row (space-x-3
          flex flex-row p-3) directly over the map. ToggleButton (toggle-button.tsx) uses bg-white/
          bg-black but no grouping wrapper. Fix: wrap the two toggle buttons in a pill container
          with bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg px-2 py-1."
```

### FINDING-5: Hero cards all N/A
```
code_trace:
  file: components/map/components/store-hero-bar.tsx
  lines: 73-131
  component: StoreHeroBar
  fix_scope: FRONTEND_ONLY
  notes: "Component renders when selectedLocationId && !storeMetricsLoading && storeMetrics?.mapped.
          No check whether ALL values are null. When visits/lift/cpv/roas are all null, four N/A
          cards render. Fix: add allNullCheck before rendering — if all four values are null,
          suppress the bar or show a single 'Metrics pending' placeholder card."
```

### FINDING-6: Timeline dashed lines
```
code_trace:
  file: components/map/controls/timeline-slider.tsx
  lines: 100-110 (dailyTicks render loop)
  component: TimelineSlider
  fix_scope: FRONTEND_ONLY
  notes: "dailyTicks renders one 1px black div per day for entire campaign duration. For a 6-week
          campaign (42 days), 42 ticks are drawn inside ~600px slider width = ~14px per tick.
          They appear as a dashed pattern. Fix: replace per-day ticks with sparse interval markers
          (every 7 days or every 30 days), reduce tick height, change color from bg-black to
          bg-gray-300."
```

### FINDING-7: Top bar polish (composite)
```
code_trace:
  file: components/map/proximity-map.tsx
  lines: 198-232
  component: ProximityMap top bar layout
  fix_scope: FRONTEND_ONLY
  notes: "Two separate absolute divs form the top bar: (1) left strip lines 198-214,
          (2) right strip lines 216-232. No shared surface. StoreHeroBar (line 213) appears
          below strip 1. Fix: unify design language — add matching bg-white/90 backdrop-blur-sm
          pill containers to both strips, standardize padding/gap, ensure StoreHeroBar visually
          connects to the toolbar."
```
