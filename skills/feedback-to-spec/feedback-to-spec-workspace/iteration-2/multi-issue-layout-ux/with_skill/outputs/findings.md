# Feedback Extraction — KTP-130 Measurement Map UX
**Date:** 2026-05-06
**Session:** Phase 1, Steps 1-3 (Ingest + Code Trace + Spec Draft)
**Screenshots processed:** 2 (sbe9-panel-width.png, sbe1-controls-drift.png)

---

## Raw Findings

### FINDING-1
```
screenshot: sbe9-panel-width.png
quote: "The left panel is way too wide, it's eating into the map area."
observation: The left panel (Panel component) occupies a fixed w-72 (288px). When the POI
             search panel is also open (another w-72 left-72), both panels stack side by
             side, consuming 576px of horizontal space before the map even begins.
issue: The left filter/metrics panel is too wide relative to the available map canvas.
expected: The panel should be narrower to leave more map area visible.
category: LAYOUT
severity: P1_HIGH

code_trace:
  file: components/map/components/panel.tsx
  lines: 11
  component: Panel
  fix_scope: FRONTEND_ONLY
  notes: >
    Panel is hardcoded to `w-72` (288px Tailwind = 18rem). No max-width constraint,
    no responsive variant. The POI search panel (poi-search-panel.tsx:111) is also
    w-72 positioned at `left-72`, doubling the footprint when open. The top-bar
    control strip (proximity-map.tsx:199-205) reads `left-72` or `left-144`
    conditionally — left-144 is 576px, confirming both panels together push controls
    off-screen. Fix: reduce Panel width (e.g. w-60 = 240px) and update all
    left-72/left-144 offsets consistently.
```

---

### FINDING-2
```
screenshot: sbe9-panel-width.png
quote: "The search results are overlapping with the metrics section."
observation: In sbe9-panel-width.png, the POI search panel's result list visually intrudes
             into the area where the Metrics section (left panel) is rendered. Both panels
             share the same z-[80] layer and no visual separator enforces the boundary.
issue: When the POI search panel is open, its results list visually overlaps or butts up
       against the Metrics/filter panel without clear separation.
expected: The two panels should be clearly delimited — search results and filter/metrics
          content should never visually bleed into each other.
category: LAYOUT
severity: P1_HIGH

code_trace:
  file: components/map/components/poi-search-panel.tsx
  lines: 110-117
  component: PoiSearchPanel
  fix_scope: FRONTEND_ONLY
  notes: >
    PoiSearchPanel is positioned `left-72` (sits immediately right of Panel).
    Both Panel and PoiSearchPanel share `z-[80]`. Panel has `border-r border-border`
    but PoiSearchPanel uses `bg-sidebar` with its own border. The overlap is a
    z-index/positioning side-effect, not a transparency bug. When the store
    detail panel is also open (right-0, w-80, z-[110]), the map canvas is squeezed
    from both sides — left 576px panels + right 320px panel = only ~400px of map
    at typical 1280px viewport. A visual divider or a narrower Panel would fix
    the perceived overlap.
    [SEVERITY_NOTE] Technically a layout compression issue that may be more
    severe at smaller viewports. User described it as P1 ("overlapping").
```

---

### FINDING-3
```
screenshot: sbe9-panel-width.png
quote: "The campaign names are showing raw IDs like 'BeKlever, Inc.
        CA_US_Shrimp Basket US_2025-05-19_2025-06-30'. Nobody wants to see that.
        It needs to be human-readable, like just 'Shrimp Basket — May-Jun 2025'."
observation: In the Conversions section of the left panel, conversion type labels show the
             raw BigQuery string including hex config IDs, date ranges, country codes, and
             advertiser branding noise.
issue: Conversion type names in the panel are raw BQ identifiers, not human-readable labels.
expected: Conversion names should display a short, human-readable label (e.g., campaign name
          + month-year date range, stripping hex IDs and country codes). Gabriel's example:
          "Shrimp Basket — May-Jun 2025".
category: DATA
severity: P1_HIGH

code_trace:
  file: components/map/components/store-detail-panel.tsx
  lines: 53-81
  component: shortenConversionName (function)
  fix_scope: FRONTEND_ONLY
  notes: >
    A `shortenConversionName` function already exists and is applied in
    CampaignPerformanceSection (lines 644-659). However this function is only
    applied in the store-detail-panel (right slide-out panel). The left panel's
    conversions section (ConversionsTypeSelect control) likely renders raw names.
    Also the current algorithm: strips hex IDs and dates, strips country codes,
    truncates to 22 chars — but does NOT produce the "May-Jun 2025" date format
    Gabriel wants; it strips dates entirely. The desired format requires extracting
    and reformatting dates, not discarding them.
    Next step: check ConversionsTypeSelect to confirm raw names appear there.
    The fix has two parts: (1) update shortenConversionName to preserve and
    reformat date ranges as "Mon-Mon YYYY", (2) apply the function in
    ConversionsTypeSelect.
    [CLARIFY] Gabriel's example "Shrimp Basket — May-Jun 2025": should the
    advertiser name prefix be kept or stripped? Current algorithm strips it.
    Proposed interpretation: keep brand name, reformat dates, strip noise.
```

---

### FINDING-4
```
screenshot: sbe1-controls-drift.png
quote: "These controls up top — the 'Distribution in time' and 'Summary' tabs,
        they're drifting."
observation: In sbe1-controls-drift.png, the "Distribution in time" and "Summary" buttons
             in the top-right bar appear misaligned — they sit at different vertical
             positions relative to each other (one appears higher or shifted).
issue: The top-right control buttons (Distribution in time + Summary + Presentation mode)
       are not vertically aligned with each other.
expected: All three top-right control buttons should be vertically centered on the same
          baseline.
category: UX
severity: P2_MEDIUM

code_trace:
  file: components/map/proximity-map.tsx
  lines: 216-232
  component: Top-right controls div
  fix_scope: FRONTEND_ONLY
  notes: >
    The top-right control container uses `flex flex-row p-3 space-x-3` but lacks
    `items-center`. The `DistributionInTimeButton` is conditionally rendered
    (`Boolean(distributionInTimeTotalDays)`), meaning when it's absent the
    remaining two buttons recenter without constraint. When it IS present,
    the three elements may drift if any child has different intrinsic height
    (e.g., Summary has a RelativeSheet wrapper that adds vertical padding).
    The ToggleButton uses `size="sm"` consistently, but Summary wraps a Button
    inside additional JSX. Adding `items-center` to the flex container should fix
    vertical alignment.
```

---

### FINDING-5
```
screenshot: sbe1-controls-drift.png
quote: "The hero cards all show N/A."
observation: The four StoreHeroBar hero cards (Attributed Visits, Incremental Lift,
             Cost/Visit, ROAS) all display "N/A" as their value even when a store
             location is selected.
issue: Hero cards display N/A instead of actual metric values for the selected store.
expected: When a store is selected and metrics are loaded, hero cards should display
          real values (visit count, lift %, cost/visit, ROAS).
category: DATA
severity: P1_HIGH

code_trace:
  file: components/map/components/store-hero-bar.tsx
  lines: 76-131
  component: StoreHeroBar
  fix_scope: FRONTEND_ONLY
  notes: >
    StoreHeroBar renders `null` unless `selectedLocationId && !storeMetricsLoading
    && storeMetrics?.mapped`. The hero card values (visits, lift, cpv, roas) all
    fall back to "N/A" when null. This points to one of:
    (a) storeMetrics is null/unmapped for this location (Placer not connected),
    (b) the metrics fetch is failing silently,
    (c) metrics are mapped but the specific fields (totalVisitors, incrementalLiftPct,
        costPerVisit, onlineRoas) are null because Placer data for that location is
        incomplete or the BQ join yields no rows.
    The screenshot shows the bar IS visible (not null), meaning storeMetrics.mapped
    is truthy — so the data reaches the component but individual fields are null.
    This is likely a data gap rather than a code bug: Shrimp Basket Navarre may
    not have InMarket lift data and cost/ROAS require campaign spend data from BQ
    that may not be joined. ROAS requires pixel-based revenue data.
    [SEVERITY_NOTE] For a demo context, all N/A hero cards look broken even if
    technically correct. Minimum: show "—" with a "data pending" tooltip instead
    of "N/A" to signal expected absence vs. error.
```

---

### FINDING-6
```
screenshot: sbe1-controls-drift.png
quote: "The timeline at the bottom has some weird dashed lines."
observation: In sbe1-controls-drift.png, the timeline area at the bottom of the map shows
             a teal/green dashed line pattern running horizontally across the timeline
             area.
issue: The timeline displays unexpected dashed lines that look visually broken or
       unintentional.
expected: The timeline should show a clean, continuous track with date markers and a
          progress indicator only — no orphan dashed lines.
category: UX
severity: P2_MEDIUM

code_trace:
  file: components/map/functions/update-map-layers/update-flow-lines.tsx
  lines: 296, 425-460
  component: update-flow-lines (animated dash array for flow lines)
  fix_scope: FRONTEND_ONLY
  notes: >
    Two candidate sources for dashed lines:
    1. Flow lines from update-flow-lines.tsx: animated `line-dasharray: [3, 4]`
       rendered as Mapbox GL layers on the map canvas itself. These are intentional
       animated dashes showing visitor flow origin-to-store. If they appear on the
       timeline area (which is a DOM overlay, not the map canvas), this would be
       a positioning bug.
    2. timeline-slider.tsx: The `dailyTicks` render as `w-[1px] h-1 bg-black` tick
       marks above the slider. At high `totalDays` counts these dense ticks could
       visually appear as a dashed line.
    The screenshot shows the dashes running along the bottom bar, most consistent
    with the flow line animation bleeding through a z-index gap, or with the tick
    marks at high density. The DistributionInTime component wraps the timeline;
    its container z-index relative to the map canvas needs verification.
    [CLARIFY] Are these dashes the animated flow lines (intentional, but visually
    jarring in timeline context) or dense timeline tick marks? Context from
    Gabriel: "weird dashed lines" suggests unexpected appearance.
```

---

## Mary's Discipline Audit

**Count check:** Gabriel's narration described 6 distinct issues:
1. Panel too wide
2. Search results overlapping metrics
3. Campaign names raw/unreadable
4. Controls drifting (top bar)
5. Hero cards all N/A
6. Dashed lines on timeline

Finding count: 6. Ratio: 1.0x. Within bounds.

**Inferred vs. stated check:**
- FINDING-2 (overlap): Gabriel said it — stated.
- FINDING-5 N/A detail (data vs. code): The root cause breakdown (a/b/c) is code archaeology, correctly placed in `notes` only.
- FINDING-6 dashed lines: Gabriel called them "weird" — severity P2 is correct; tone was observational, not alarmed.

**Business intent check (all pass):**
1. F-1: Users need more map visible to do their job.
2. F-2: Users cannot distinguish search results from metrics when panels overlap.
3. F-3: Users cannot identify which campaign is which without human-readable names.
4. F-4: Users expect controls to be aligned and professional-looking in a client demo context.
5. F-5: Users expect hero cards to show the KPIs they opened the panel to see.
6. F-6: Users are confused by visual artifacts that don't correspond to any understood UI element.

All 6 findings survive Mary's audit.
