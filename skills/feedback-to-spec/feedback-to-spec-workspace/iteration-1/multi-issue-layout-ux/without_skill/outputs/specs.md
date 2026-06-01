# Structured Specifications — Measurement Map UX Issues
Date: 2026-05-04
Epic: KTP-130
Source: Gabriel feedback + screenshots (ux-feedback-2026-05-04)

---

## SPEC-1: Reduce Left Panel Width

### Summary
The left panel (`Panel` component) is hardcoded at `w-72` (288px). At typical laptop widths, this is acceptable when only the main panel is open, but becomes cramped when the POI search panel is also visible (combined 576px). No responsive scaling exists.

### Acceptance Criteria

**AC-1.1 — Single panel width is appropriate**
- Given the user is on the Measurement Map with no POI search panel open
- When the viewport is at least 1280px wide
- Then the left panel width should be at most 256px (`w-64`) so the map retains at least 75% of the viewport

**AC-1.2 — Double panel (main + POI search) does not crowd the map**
- Given the user opens the POI search panel (both panels visible)
- When the viewport is at least 1440px wide
- Then the combined left chrome (main panel + search panel) must not exceed 500px total
- And the map area must remain at least 600px wide

**AC-1.3 — StoreDetailPanel does not compound the problem**
- Given both the left panel and the store detail panel (right side, `w-80` = 320px) are open simultaneously
- When the viewport is 1440px wide
- Then the total chrome (left + right) must leave at least 500px for the map center

### Implementation Notes
- `panel.tsx`: Change `w-72` to `w-64`.
- `poi-search-panel.tsx`: Change outer `w-72` and `left-72` to match, add `max-w-xs` guard.
- `proximity-map.tsx`: Update `left-72` / `left-144` offset classes to match new widths.
- `store-detail-panel.tsx`: Reduce `w-80` to `w-72` to reclaim 32px on the right.
- Consider a CSS variable or Tailwind config token (`--panel-width`) so all references stay in sync.

---

## SPEC-2: Prevent Search Results from Overlapping Metrics

### Summary
The POI search results list renders at full viewport height (`top-0 bottom-0`) with `z-[80]`, the same z-index as the main panel. The results list has no max-height or scroll viewport constraint, causing it to visually crowd or overlap the metrics/conversions sections visible in the main panel.

### Acceptance Criteria

**AC-2.1 — Search results are fully contained within the search panel**
- Given the user has the POI search panel open with multiple results
- When there are more results than fit in the visible panel area
- Then the results scroll within the panel boundaries and do not overflow or overlap adjacent UI

**AC-2.2 — Search panel and main panel are visually distinct**
- Given both panels are open side by side
- When the user looks at the left edge of the screen
- Then a clear visual separator (shadow, border, or spacing) distinguishes the search panel from the main panel

**AC-2.3 — Search panel does not overlap the metrics section**
- Given the POI search panel is open and a location is selected (metrics visible in main panel)
- When the user scrolls the search results
- Then the main panel metrics section remains fully visible and interactive

### Implementation Notes
- `poi-search-panel.tsx`: The results container `<div className="p-4 overflow-auto">` needs an explicit `flex-1 min-h-0` to constrain scrolling within the flex column, not against the viewport.
- Ensure the outer panel div uses `flex flex-col` with `overflow-hidden`.

---

## SPEC-3: Human-Readable Campaign Names in Conversions Section

### Summary
The `ConversionsTypeSelect` left-panel control calls `buildConversionLabel()` which only handles `"Online"` and `"Offline"` as special cases. Any other BQ campaign string (e.g., `BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30`) renders verbatim in the checkbox label. The `shortenConversionName()` function in `store-detail-panel.tsx` exists and works, but is not called from `conversions-type-select.tsx`.

### Acceptance Criteria

**AC-3.1 — Conversions filter shows human-readable labels**
- Given the Conversions section is visible in the left panel
- When the BQ conversion name contains patterns like `BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30`
- Then the displayed label must strip: hex IDs, date ranges (YYYY-MM-DD), "BeKlever, Inc.", country/region codes (XX_XX_ patterns), and trailing underscores/dashes
- And the result must be title-cased and at most 22 characters (with `…` truncation beyond that)

**AC-3.2 — Full name remains accessible on hover**
- Given a conversion label has been shortened
- When the user hovers over the label in the filter list
- Then a tooltip displays the full raw conversion name

**AC-3.3 — Legacy "Online" and "Offline" names are unaffected**
- Given conversion names are exactly `"Online"` or `"Offline"`
- When `buildConversionLabel` processes them
- Then the result is `"Online Conversions"` and `"Offline Conversions"` respectively, unchanged from current behavior

**AC-3.4 — Shrimp Basket campaign shows "Shrimp Basket" not the raw string**
- Given a conversion named `BeKlever, Inc. CA_US_Shrimp Basket US_2025-05-19_2025-06-30`
- When rendered in the Conversions filter
- Then the label reads `Shrimp Basket` (or similar cleaned form, max 22 chars)

### Implementation Notes
- `conversions-type-select.tsx`: Import `shortenConversionName` from `store-detail-panel.tsx` (or extract it to a shared utility, e.g., `lib/format-conversion-name.ts`).
- Replace the body of `buildConversionLabel` with: if legacy name → append " Conversions"; else → call `shortenConversionName(name)`.
- Add a `title` attribute or Tooltip wrapper on the `CollapsibleFilters` item to show the raw name.
- Extracting `shortenConversionName` to `lib/format-conversion-name.ts` is preferred so both components share a single source of truth.

---

## SPEC-4: Top Bar Controls Alignment Polish

### Summary
The "Distribution in time" and "Summary" toggle buttons are positioned in an `absolute flex flex-row` container at the top-right of the map. When `selectedLocationId` is set, the container shifts left (`right-80`). The buttons lack a fixed width, so different label lengths cause them to appear at inconsistent positions across interactions.

### Acceptance Criteria

**AC-4.1 — Controls stay visually anchored to the top bar**
- Given the user opens and closes the store detail panel
- When the top-right controls shift position (right-0 to right-80)
- Then the transition is smooth (`transition-all duration-300` already applied) and the buttons maintain consistent vertical alignment

**AC-4.2 — "Distribution in time" and "Summary" have consistent button height**
- Given both buttons are visible
- When rendered at any viewport width above 1024px
- Then both buttons are the same height and appear vertically centered on the same baseline

**AC-4.3 — Controls do not overlap the StoreHeroBar**
- Given a location is selected and the StoreHeroBar is visible
- When the top controls render alongside the hero cards
- Then the controls and the hero cards do not overlap

### Implementation Notes
- `proximity-map.tsx` lines 217–232: The right-side controls container uses `space-x-3 flex flex-row p-3`. Add `items-center` to ensure vertical alignment.
- `toggle-button.tsx`: Add `whitespace-nowrap` to prevent label wrapping.
- The `DistributionInTimeButton` and `Summary` components both render `null` in presentation mode and when not loaded — verify their early returns don't cause layout shift.

---

## SPEC-5: Hero Cards N/A — Improve Empty State Communication

### Summary
When a location is selected but the hero metrics (`totalVisitors`, `incrementalLiftPct`, `costPerVisit`, `onlineRoas`) are all null, all four `HeroCard` components display `"N/A"` in large bold text. This is technically correct (data not available) but communicates nothing useful to the user about why or what they can do.

### Acceptance Criteria

**AC-5.1 — N/A values include a brief explanation**
- Given a hero card has a null value
- When rendered
- Then instead of just `"N/A"`, a sub-label explains the reason:
  - Attributed Visits N/A: `"No Placer.ai data for this period"`
  - Incremental Lift N/A: `"Requires InMarket integration"` (already shown in subLabel — verify it renders)
  - Cost / Visit N/A: `"No spend data for this location"`
  - ROAS N/A: `"No conversion revenue data"` (already shown in subLabel — verify it renders)

**AC-5.2 — If all four are N/A, StoreHeroBar may be conditionally hidden or collapsed**
- Given all four hero metric values are null
- When `storeMetrics.mapped` is true but all metric fields are null
- Then consider collapsing the hero bar entirely or rendering a single "Metrics unavailable for this location" message instead of four N/A cards

**AC-5.3 — Existing non-null subLabels are preserved**
- Given a hero card has a non-null value
- When the subLabel is set (e.g., YoY delta, "All visits (organic + influenced)")
- Then the subLabel still renders correctly below the value

### Implementation Notes
- `store-hero-bar.tsx`: Check each metric individually. For null values, the `subLabel` prop is already available on `HeroCard` — populate it with a concise reason string for each metric.
- The "Requires InMarket integration" subLabel (line 107) and "No conversion revenue data" (line 127) are already coded but only show when `lift != null` or `roas != null` respectively. Invert the condition.

---

## SPEC-6: Timeline Tick Mark Visual Polish

### Summary
The `TimelineSlider` renders one 1px × 4px black tick mark per day across the full campaign date range. For campaigns spanning 30–90 days, this produces 30–90 tightly packed tick marks that visually read as a dashed/noisy line rather than clean date markers. The user described these as "weird dashed lines."

### Acceptance Criteria

**AC-6.1 — Tick density is reduced for long date ranges**
- Given a campaign spans more than 14 days
- When the timeline renders
- Then tick marks are shown at most every 7 days (weekly intervals) instead of daily
- And the track does not appear as a dashed line

**AC-6.2 — Short date ranges (< 14 days) retain daily ticks**
- Given a campaign spans 14 days or fewer
- When the timeline renders
- Then daily tick marks are acceptable (up to 14 visible ticks)

**AC-6.3 — Tick marks are visually lighter**
- Given any campaign date range
- When tick marks render
- Then they use a lighter color (e.g., `bg-gray-300` instead of `bg-black`) so they don't dominate the track visually

**AC-6.4 — Date labels remain readable**
- Given tick density is reduced
- When date markers render below the timeline
- Then the date labels (month/day) still appear at meaningful intervals and are not clipped

### Implementation Notes
- `timeline-slider.tsx`: `generateDailyTicks` returns one entry per day. Change logic to: `const tickInterval = totalDays > 14 ? 7 : 1; Array.from({ length: Math.ceil(totalDays / tickInterval) }, (_, i) => i * tickInterval)`.
- Change tick color from `bg-black` to `bg-gray-300`.
- The `dateMarkers` array is generated separately by `generateDateMarkers()` in `distribution-in-time-animation.ts` — that function controls label placement and can remain unchanged.

---

## Cross-Cutting Notes

1. **`shortenConversionName` should be a shared utility.** It currently lives in `store-detail-panel.tsx`, a large file. Extract to `lib/format-conversion-name.ts` so Spec-3 can import it cleanly.

2. **Panel width constants should be centralized.** The values `w-72`, `left-72`, `left-144`, `w-80`, `right-80` are repeated across `panel.tsx`, `poi-search-panel.tsx`, `proximity-map.tsx`, and `store-detail-panel.tsx`. Any change to panel width requires updating 4+ files. A Tailwind `theme.extend` entry or a `consts/layout.ts` export would prevent future drift.

3. **Hero bar empty state (Spec-5) and store detail panel empty state (in `store-detail-panel.tsx` lines 958–968) should be consistent.** Both currently show slightly different messaging for "not mapped" vs. "data unavailable" cases. Align language.
