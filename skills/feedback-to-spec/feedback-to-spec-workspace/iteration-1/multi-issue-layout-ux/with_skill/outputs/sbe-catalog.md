# SBE Catalog — KTP-130 UX Review 2026-05-04

**Phase:** Phase 1, Step 3 (Specification Draft — Mary's Pass)
**Epic:** KTP-130 (Klever Measurement Map)
**Draft status:** Awaiting Step 4 confirmation gate
**Findings processed:** 7 → 6 SBEs (FINDING-4 and FINDING-7 grouped — same root cause, same fix surface)

---

### SBE-1: Left panel width must not consume more than 240px

**Context:** Gabriel is reviewing the Measurement Map for Shrimp Basket. The left panel (filters, metrics, POI, channels) and the POI search panel together take up too much horizontal space, visually crowding the map.

GIVEN the user is viewing the Measurement Map
  AND the left filter panel (Panel component) is visible

WHEN the page renders (default state or any advertiser is selected)
THEN the left filter panel width must not exceed 240px (w-60)
  AND the total horizontal space consumed by the left panel area (filter panel + POI search panel combined when both open) must not exceed 480px
  AND the map container offset (left-N class) must match the actual panel widths in use

**Current behavior:** `panel.tsx` uses `w-72` (288px). When POI search panel is also open (`poi-search-panel.tsx` at `left-72`, `w-72`), 576px of screen width is consumed.

**Root cause:** Hardcoded `w-72` in `panel.tsx` line 11 and `poi-search-panel.tsx` line 111. No responsive or user-controlled collapse.

**Fix scope:** FRONTEND_ONLY

---

### SBE-2: POI search results must be visually separated from the metrics section above

**Context:** Gabriel is using the POI search panel (open to the right of the filter panel) to browse Shrimp Basket store locations. The search result cards visually bleed into or compete with the panel's metric labels above them.

GIVEN the user is viewing the Measurement Map
  AND the POI search panel is open (poiPanelOpen = true)
  AND search results are displayed (results.length > 0)

WHEN the search results list renders below the search input and header
THEN the results list must be contained in a dedicated scrollable area
  AND a clear visual divider (border-top or minimum 16px padding section break) must separate the search input / header from the results list
  AND the results container must have overflow-y: auto with a defined max-height so it cannot overflow into other UI regions

**Current behavior:** `poi-search-panel.tsx` results div (line 156) has `overflow-auto` but the header section has no fixed height, allowing the results to compress and visually bleed against adjacent UI.

**Root cause:** `poi-search-panel.tsx` — no explicit height partitioning between fixed header and scrollable results. Header uses `px-4 py-2` with `border-b` but results div has no `flex-1 min-h-0` guard.

**Fix scope:** FRONTEND_ONLY

---

### SBE-3: Conversion campaign names must display as "Brand — Mon-Mon YYYY" format

**Context:** Gabriel is viewing the Conversions section in the left panel and the Campaign Performance section in the StoreDetailPanel. Raw BigQuery campaign name strings are visible to the user.

GIVEN the user is viewing the Measurement Map with a store selected (e.g. Shrimp Basket Navarre)
  AND conversion data is available for that store

WHEN conversion names render in the ConversionsTypeSelect dropdown OR the Campaign Performance card labels
THEN the displayed name must follow the format: "{Brand Name} — {MonthAbbr}-{MonthAbbr} {YYYY}"
  AND the brand name must be extracted from the campaign string as the consumer-facing brand (e.g. "Shrimp Basket", not "BeKlever, Inc.")
  AND the date range must be reformatted from ISO "YYYY-MM-DD_YYYY-MM-DD" to "Mon-Mon YYYY" using the start and end months
  AND if start month == end month, format as "{Brand} — {Mon} {YYYY}"
  AND the full raw name must remain available as a tooltip (not visible by default)
  AND if no brand name or date can be extracted, fall back to a max-22-char truncation of the cleaned name (current fallback behavior)

**Example transformation:**
- Input: `"adsquare weekly tag config 682b9f539c2f56120e6c0cf9-BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30"`
- Output label: `"Shrimp Basket — May-Jun 2025"`
- Tooltip: full raw string

**Current behavior:** `shortenConversionName()` in `store-detail-panel.tsx` lines 53-81 strips hex IDs, ISO dates, company suffixes, country codes, then truncates to 22 chars. Produces output like `"Shrimp Basket Us"` — still not human-readable in the desired format. ConversionsTypeSelect (not yet read) likely shows raw names in the dropdown.

**Root cause:** `shortenConversionName()` does not implement date reformatting or structured "{Brand} — {Mon}-{Mon} YYYY" assembly. Logic is string-scrubbing rather than format-assembly.

**Fix scope:** FRONTEND_ONLY

[CLARIFY] The user said "like just 'Shrimp Basket — May-Jun 2025'". This interpretation uses the campaign's date range months. Confirm: should we use start-month to end-month of the BQ string dates, or the currently selected map date range?

---

### SBE-4: "Distribution in time" and "Summary" controls must render as a grouped control unit

**Context:** Gabriel is looking at the top-right area of the map. The "Distribution in time" toggle and "Summary" toggle appear visually unanchored, floating over the map without a grouping surface.

GIVEN the user is viewing the Measurement Map
  AND at least one of the top-right toggle controls is rendered (DistributionInTimeButton or Summary)

WHEN the top-right controls area renders
THEN the "Distribution in time" and "Summary" buttons must be wrapped in a shared container with a visible background surface (e.g., white/90 with backdrop-blur-sm) and a border (border border-gray-200 rounded-lg)
  AND the container must maintain pointer-events-auto so clicks pass through correctly
  AND the "Presentation mode" toggle must also be included in or visually aligned with this grouped surface
  AND the grouped container must shift left by w-80 (320px) when the StoreDetailPanel is open (selectedLocationId is set), preserving the current right-shift behavior

**Current behavior:** `proximity-map.tsx` lines 216-232 — bare `flex flex-row p-3` div with no background surface. Each button has its own `bg-white`/`bg-black` but no grouping wrapper ties them together visually.

**Root cause:** No wrapper container with shared background/border. Individual `ToggleButton` styling is per-button, not per-group.

**Fix scope:** FRONTEND_ONLY

---

### SBE-5: StoreHeroBar must be suppressed when all four metric values are null

**Context:** Gabriel selects a Shrimp Basket store location. The hero bar appears at the top of the map but all four cards (Attributed Visits, Incremental Lift, Cost / Visit, ROAS) display "N/A", providing no value.

GIVEN the user is viewing the Measurement Map
  AND a store location is selected (selectedLocationId is set)
  AND storeMetrics is loaded and mapped is true

WHEN all four hero metric values (totalVisitors, incrementalLiftPct, costPerVisit, onlineRoas) are null or undefined
THEN the StoreHeroBar must NOT render (return null)
  AND optionally, a single compact "Metrics not yet available for this location" inline note may be shown instead (inside the top-left controls strip, not as four N/A cards)

WHEN at least one hero metric value is non-null
THEN only the cards with non-null values must render as full hero cards
  AND cards with null values must either be hidden or shown as a compact placeholder (not a full-size N/A card)

**Current behavior:** `store-hero-bar.tsx` line 76 — only checks `selectedLocationId && storeMetricsLoading && storeMetrics?.mapped`. No check for all-null values. Four N/A cards always render when store is mapped.

**Root cause:** No all-null guard before rendering in `StoreHeroBar`. Each card individually falls back to `"N/A"` string.

**Fix scope:** FRONTEND_ONLY

---

### SBE-6: Timeline slider daily tick marks must be replaced with sparse interval markers

**Context:** Gabriel is viewing the Distribution in Time timeline at the bottom of the map. The dense daily tick marks across the slider track appear as "weird dashed lines" — visual noise rather than useful date guides.

GIVEN the user is viewing the Measurement Map
  AND the "Distribution in time" mode is active (distributionInTime = true)
  AND the TimelineSlider is rendered with a campaign spanning N days

WHEN N > 14 (more than 2 weeks of data)
THEN daily ticks must NOT be rendered for every single day
  AND tick marks must be rendered only at weekly intervals (every 7 days) when N ≤ 60
  AND tick marks must be rendered only at monthly intervals (every 30 days) when N > 60
  AND each tick mark must use a light color (bg-gray-300, not bg-black) and a reduced height (h-1 → h-0.5 or remove entirely in favor of date labels only)

WHEN N ≤ 14 (14 days or fewer)
THEN daily tick marks may remain but must use bg-gray-300 (not bg-black)

**Current behavior:** `timeline-slider.tsx` lines 32-110 — `generateDailyTicks(totalDays)` creates one tick div per day. Ticks are `w-[1px] h-1 bg-black` — solid black. For a 42-day campaign, 42 ticks are drawn in ~600px, appearing as a dashed/hatched line.

**Root cause:** `generateDailyTicks()` always generates per-day ticks regardless of campaign length. Tick styling is `bg-black` with no size scaling.

**Fix scope:** FRONTEND_ONLY

---

## SBE-7 (composite): Top bar area requires a unified visual design treatment

**Context:** Gabriel's "this whole top bar area needs polish" comment is a composite observation covering both the left controls strip and the right controls strip. This is treated as a UX polish SBE grouping FINDING-4 (controls drift) and FINDING-7 (top bar polish) since they share the same root cause (no unified surface) and the same fix (add consistent background containers to both strips).

**Context:** Gabriel is viewing the Measurement Map. The top area of the map contains two floating horizontal control strips with no shared visual language.

GIVEN the user is viewing the Measurement Map in non-presentation mode

WHEN the map top bar renders (both the left-aligned strip and right-aligned strip)
THEN both control strips must apply a consistent container treatment:
  - Background: `bg-white/90` with `backdrop-blur-sm`
  - Border: `border border-gray-200`
  - Corner rounding: `rounded-lg`
  - Shadow: `shadow-sm`
  AND the StoreHeroBar (when visible) must visually connect to the left strip (matching background surface or seamless vertical extension)
  AND the overall impression must read as a single coherent toolbar band across the top of the map, not two independent floating rows

**Current behavior:** `proximity-map.tsx` — two separate bare `flex flex-row p-3` divs (lines 206-213 and 221-232) without any shared container background. Individual buttons have their own `bg-white` per `ToggleButton` but no grouping surface ties them together.

**Root cause:** `proximity-map.tsx` top bar layout — no shared wrapper surface. Left strip and right strip are independent absolute-positioned divs with no visual cohesion.

**Fix scope:** FRONTEND_ONLY

---

## Coverage Summary

| SBE | Finding(s) | Category | Severity | Fix Scope |
|-----|-----------|----------|----------|-----------|
| SBE-1 | FINDING-1 | LAYOUT | P2_MEDIUM | FRONTEND_ONLY |
| SBE-2 | FINDING-2 | LAYOUT | P2_MEDIUM | FRONTEND_ONLY |
| SBE-3 | FINDING-3 | DATA | P1_HIGH | FRONTEND_ONLY |
| SBE-4 | FINDING-4 | UX | P2_MEDIUM | FRONTEND_ONLY |
| SBE-5 | FINDING-5 | UX | P2_MEDIUM | FRONTEND_ONLY |
| SBE-6 | FINDING-6 | UX | P2_MEDIUM | FRONTEND_ONLY |
| SBE-7 | FINDING-4+7 | UX | P2_MEDIUM | FRONTEND_ONLY |

**Open clarifications:**
- [SBE-3 CLARIFY] Date range source for conversion name formatting: use BQ campaign string dates vs selected map date range?
- [SBE-1 CLARIFY] Is panel narrowing (288px → 240px) sufficient, or should a collapse/hide mechanism be added for power users?

**Code traces:** 6 successful, 1 partial (ConversionsTypeSelect not read — TRACE_PENDING)
