# Feedback Extraction — KTP-130 (Klever Measurement Map)
## Date: 2026-05-06
## Input Mode: Narration only (no screenshots)
## Source: Gabriel, narrating from memory

---

## Ingestion Note

No screenshots provided. Observations are drawn entirely from Gabriel's verbal narration. Per skill protocol, each finding reflects only what the user explicitly stated, not inferences made during code trace. Code sub-causes discovered during tracing are captured in `code_trace.notes`.

---

## FINDING-1: Channel filter resets to "All channels" when switching advertisers

```
FINDING-1:
  screenshot: <none>
  quote: "When I filter by 'Online' channel and then switch to a different advertiser,
          the filter resets to 'All channels'. It should remember my filter selection
          when I switch advertisers. This has been bugging me for weeks."
  observation: <not available — narration only>
  issue: The active channel/filter selection is lost when the user switches to a different
         advertiser. The filter panel reverts to showing all options selected.
  expected: The selected filter (e.g., single-channel or single-conversion-type selection)
            should be preserved across advertiser switches.
  category: BUG
  severity: P1_HIGH
```

**Severity rationale:** Gabriel said "this has been bugging me for weeks" and "should remember" — tone signals a persistent, meaningful pain point. Upgraded to P1_HIGH (not P0) because he did not say "blocker" or "can't ship."

**Clarification note:** Gabriel names "Online" channel, but the Channel filter panel contains Video, DOOH, CTV, Audio, Display — no "Online" option. "Online" IS a valid label in the Conversions filter ("Online Conversions"). Gabriel may be narrating from memory and conflating the Conversions filter with the Channel section. The behavior he describes (filter resets to "All") is consistent with the Conversion filter, which also starts at an empty-selection default on store init.

[CLARIFY] Does "Online" refer to the Channel filter or the Conversions (Online Conversions) filter? The fix scope differs slightly but the root cause pattern is the same.

---

## Code Trace — FINDING-1

```
code_trace:
  component: setAdvertiserId (Zustand action)
  file: components/map/store/map-store.tsx
  lines: 325–341
  fix_scope: FRONTEND_ONLY
  classification: FRONTEND_ONLY

  notes:
    - setAdvertiserId resets: advertiserId, advertiserName, countyMapData,
      countyMapDataCacheKey, zipMapData, zipMapDataCacheKey, stateMapData,
      stateMapDataCacheKey, dateRange, dateRangeLoading, dateRangeError.
    - It does NOT reset: selectedChannels, selectedConversionTypes.
    - Therefore, if Gabriel reports the filter IS resetting, the reset is happening
      somewhere else. Possible causes:
        (a) The Page component unmounts+remounts ProximityMap between advertiser switches,
            destroying and recreating the Zustand store. Zustand store is defined via
            create() at module level so it is a singleton — this is unlikely for the
            channel state itself.
        (b) The AppProvider re-initializes brands on org switch (line ~251:
            setActiveBrand(brands[0])), causing activeBrand to change and triggering
            setAdvertiserId. The store itself is not reset but the channel display
            appearance could re-render to the default visual state if a parent key
            changes.
        (c) Gabriel may be observing the Conversions filter (not Channel). The
            Conversions filter is driven by available data — when advertiser switches,
            the new advertiser's data may have no "Online" conversion entries,
            causing availableConversionNames to return [] and the filter to disappear
            (which could feel like "reset to all").
        (d) The fetchedAdvertiserId guard (line 940) prevents re-fetching for same
            advertiser, but does not touch selectedChannels.
    - [SEVERITY_NOTE]: If cause (c) is correct, the root cause is a data-driven
      disappearance of the Conversion filter, not a state reset. The fix would be
      to preserve the last selection even when filter items are unavailable.
    - setSelectedChannels exists (line 359) but is never called by setAdvertiserId.
    - DEFAULT_CHANNELS (line 233) is ["Video", "DOOH", "CTV", "Audio", "Display"] —
      this is the initial store value. Nothing calls setSelectedChannels externally.
```

---

## FINDING-2: Location count in header does not update after clearing filters until map pan

```
FINDING-2:
  screenshot: <none>
  quote: "When I clear all filters, the location count in the header doesn't update
          until I pan the map. That's definitely a bug."
  observation: <not available — narration only>
  issue: After clearing all active filters, a location count displayed in the header
         area retains the old filtered count. It only refreshes when the user pans
         the map.
  expected: The location count should update immediately when filters are cleared,
            without requiring a map interaction.
  category: BUG
  severity: P1_HIGH
```

**Severity rationale:** Gabriel explicitly said "That's definitely a bug." Tone is direct and unambiguous — P1_HIGH.

**Clarification notes:**

[CLARIFY-A] "Clear all filters" — what action triggers this? The POI search panel has a "Clear" button (line 147–153 of poi-search-panel.tsx) that only clears the search text, not a filter state. The Channel and Conversion filters have no "clear all" button. Gabriel may be referring to: (a) clearing the search text in the POI panel, (b) deselecting all selected conversions, or (c) a future "clear all" control not yet in scope.

[CLARIFY-B] "Location count in the header" — the most prominent count visible in the map header area is the POI search panel's "{N} locations found" label (poi-search-panel.tsx line 141–143). This is driven by a `useMemo` on `locationData` filtered by `searchTerm`. Clearing the search text (setSearchTerm("")) should immediately re-run the memo and update the count. If pan is required, there may be a stale render or the count Gabriel is referring to is elsewhere.

---

## Code Trace — FINDING-2

```
code_trace:
  component: MapUpdater / onPopupDataChange pipeline
  file: components/map/components/map-updater.tsx
  lines: 233 (locationCount in expressions object)
  fix_scope: FRONTEND_ONLY
  classification: FRONTEND_ONLY

  notes:
    - The location count visible to the user may come from two sources:
        (A) poi-search-panel.tsx lines 141–143: `results.length` from useMemo on
            locationData filtered by searchTerm. This updates synchronously when
            searchTerm changes. If this is the display Gabriel refers to, the
            bug may be that locationData itself is stale after a filter-clear event,
            not the derived count.
        (B) map-updater.tsx line 233: locationCount is set inside expressions and
            fed into updateZipLayers/updateCountyLayers. This count is re-computed
            only when a Mapbox tile render event fires, which only happens on
            map pan or zoom. If a filter clear triggers a data state change but
            not a Mapbox tile re-render, the map-level count would remain stale.
    - The pan-triggered-refresh pattern is consistent with (B): Mapbox's tile
      render callback is the trigger for recalculating expressions. No explicit
      "re-render on filter change" hook forces a recalculation.
    - A fix would be to: detect filter-clearing events in the store, then call
      updateMapLayers(geographicScope, map, expressions?.colorExpression) explicitly,
      bypassing the Mapbox tile event dependency.
    - The "clear all filters" action is TRACE_PENDING for exact trigger identification.
      [CLARIFY-A] must be resolved to confirm which clearing action causes the stale count.
    - [SEVERITY_NOTE]: If the bug is in path (B), it affects the on-map visual count,
      not just the sidebar panel. Could mislead users about scope of current filter.
      Consider raising to P0 if it causes incorrect decision-making.
```

---

## Mary's Discipline Audit

**For each finding, ask: Did the user actually say this, or did the agent infer it?**

- FINDING-1: User explicitly said the filter resets. The "Online" channel / Conversions ambiguity is flagged as [CLARIFY], not promoted to a separate finding. Code trace sub-causes (4 hypotheses) are in `code_trace.notes`, not as findings. Count: 1 finding from 1 user observation. OK.

- FINDING-2: User explicitly said the count doesn't update until pan. The two possible "header counts" are flagged as [CLARIFY], not promoted to separate findings. Code trace sub-causes (two possible paths) are in `code_trace.notes`, not as findings. Count: 1 finding from 1 user observation. OK.

**Count check:** Gabriel described 2 distinct issues → 2 findings. Ratio is 1:1. Within bounds.

**Business intent check:**
- FINDING-1: "User wants their filter choice to persist when they navigate between advertisers." Can state clearly in user terms. Pass.
- FINDING-2: "User wants the location count to reflect filter state immediately, not only after a map interaction." Can state clearly. Pass.

---

## Summary

| # | Category | Severity | Status | CLARIFY pending? |
|---|----------|----------|--------|-----------------|
| FINDING-1 | BUG | P1_HIGH | Code traced | Yes — "Online" = Channel or Conversion filter? |
| FINDING-2 | BUG | P1_HIGH | Code traced (path uncertain) | Yes — which count display, which clear action? |

Total findings: 2 (matches user observation count exactly).
