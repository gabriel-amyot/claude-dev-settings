# SBE Catalog — KTP-130 (Klever Measurement Map)
## Date: 2026-05-06
## Status: DRAFT — Pending confirmation (Phase 1 gate not yet passed)
## Input: Narration only (no screenshots)

> These SBEs are extracted from Gabriel's verbal narration. Two [CLARIFY] tags must be resolved before specs can be locked. The SBEs below use the most probable interpretation of each ambiguity, which must be confirmed by Gabriel before Phase 2 begins.

---

### SBE-1: Filter selection persists across advertiser switches

**Context:** Gabriel is using the Measurement Map with a specific channel or conversion filter active. He then selects a different advertiser from the top bar.

```
GIVEN the user is viewing the Measurement Map left panel
  AND at least one filter is in a non-default state
    (e.g., only "Online Conversions" selected, or a specific channel deselected)

WHEN the user switches to a different advertiser via the top navigation bar

THEN the previously selected filter state is preserved
  AND the map re-fetches data for the new advertiser using the previously active filters
  AND the filter panel visually reflects the same selection as before the switch
```

**Current behavior:** After switching advertisers, the filter panel reverts to its default state (all channels selected, no conversion types selected). Any narrowed filter is lost.

**Root cause:** `setAdvertiserId` in `map-store.tsx` (lines 325–341) does not preserve `selectedChannels` or `selectedConversionTypes`. There are two sub-cases:
- If the user means the Channel filter: the store state likely persists (not explicitly reset), but the appearance may reset due to a component remount or data unavailability for the new advertiser.
- If the user means the Conversion filter: the `availableConversionNames` is data-driven from the new advertiser's dataset. If the new advertiser has no "Online" conversion data, the Conversions filter disappears entirely, which feels like a reset.

**Fix scope:** FRONTEND_ONLY

**[CLARIFY]** Does "Online" refer to:
  - (a) A single channel deselected in the Channel filter panel (Video/DOOH/CTV/Audio/Display)?
  - (b) "Online Conversions" in the Conversions filter panel?
  
  The fix approach differs: (a) requires confirming why `selectedChannels` appears to reset; (b) requires preserving the conversion selection even when the new advertiser's data doesn't include that conversion type (show it as "unavailable" rather than hiding it).

---

### SBE-2: Location count in map header updates immediately on filter clear, not deferred to pan

**Context:** Gabriel has applied filters on the Measurement Map and can see a location count in the header/panel area. He then clears all filters.

```
GIVEN the user is viewing the Measurement Map
  AND a filter is active that affects the displayed location count
  AND the location count in the header/panel area reflects the filtered state

WHEN the user clears all active filters (via "Clear" button or equivalent)

THEN the location count in the header updates immediately to reflect the unfiltered total
  AND the user does not need to pan or zoom the map to trigger the count refresh
```

**Current behavior:** After clearing filters, the location count in the header retains the pre-clear value. It only refreshes to the correct post-clear count after the user pans the map (triggering a Mapbox tile re-render event).

**Root cause:** Map-level counts (locationCount fed into Mapbox layer expressions via `map-updater.tsx` line 233) are recalculated only when Mapbox fires a tile render event — which requires a map interaction (pan/zoom). There is no explicit "recalculate layers on store change" trigger that fires when filter state changes in isolation.

**Fix scope:** FRONTEND_ONLY

**[CLARIFY-A]** What specific action is "clear all filters"?
  - (a) Clicking the "Clear" button in the POI search panel (clears search text only)?
  - (b) Deselecting all conversion types?
  - (c) A "Reset filters" button not yet built?

**[CLARIFY-B]** Which location count display is Gabriel referring to?
  - (a) The "{N} locations found" text in the POI search panel (driven by `results.length` in `poi-search-panel.tsx` lines 141–143)?
  - (b) A count derived from Mapbox layer expressions passed via `onPopupDataChange` in `map-updater.tsx`?

  Most likely (b) given the pan-triggers-refresh symptom. If (a), the bug is that `locationData` is stale post-clear rather than the count derivation itself.

---

## Catalog Summary

| SBE | Title | Finding ref | Fix scope | CLARIFY pending |
|-----|-------|-------------|-----------|----------------|
| SBE-1 | Filter selection persists across advertiser switches | FINDING-1 | FRONTEND_ONLY | Yes (which filter?) |
| SBE-2 | Location count updates immediately on filter clear | FINDING-2 | FRONTEND_ONLY | Yes (which count, which clear?) |

**Next step:** Present SBEs to Gabriel (Phase 1, Step 4 confirmation loop) to resolve the two [CLARIFY] items before locking specs. Phase 2 (Jira diff, ticket creation) must not start until Gabriel confirms.

---

## Phase 1 Gate Status

Phase 2 is NOT authorized to begin. The gate requires explicit confirmation from Gabriel that:
1. The SBE descriptions match his intent
2. The [CLARIFY] items are resolved
3. He approves the chosen pipeline mode (Full auto / Review first / Comment only / Park it)

SBEs are saved locally as drafts. Nothing has been posted to Jira or committed to agent-os.
