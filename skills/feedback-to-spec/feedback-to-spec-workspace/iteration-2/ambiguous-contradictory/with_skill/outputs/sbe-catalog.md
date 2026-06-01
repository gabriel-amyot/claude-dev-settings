# SBE Catalog — KTP-130 Right Panel Feedback
**Date:** 2026-05-06
**Epic:** KTP-130 (Klever Measurement Map)
**Status:** DRAFT — awaiting confirmation (Phase 1 Step 4 gate not yet passed)
**Source findings:** findings.md (this session)

---

## Mary's Proportionality Check

Input: 3 user observations. Output: 3 SBEs (one per finding). Ratio = 1:1. No over-decomposition.

---

### SBE-1: Store detail panel width is too narrow for its content

**Context:** Gabriel reviewed the StoreDetailPanel after clicking a store location. The panel was populated with Metrics Overview cards, a Campaign Performance grid, a Top Origin ZIPs table, and sparkline charts.

```
GIVEN the user has clicked a store location on the Measurement Map
  AND the StoreDetailPanel has opened with metrics data loaded

WHEN the user reads metric card labels, table columns, or chart labels in the panel

THEN all primary text labels render without truncation
  AND the 4-column Top Origin ZIPs table (ZIP, Visitors, Impr., Conv.) is legible without horizontal scrolling
  AND metric card values (formatted numbers, currency, percentages) do not wrap mid-value
```

**Current behavior:** Panel renders at a fixed `w-80` (320px). At this width, the 2-column metric grid leaves ~136px per card, causing 11px labels like "Cost / Visit (est.)" to truncate. The 4-column ZIPs table compresses "Impr." and "Conv." columns to near-unreadable widths.

**Root cause:** `w-80` hard-coded on the root `div` of `StoreDetailPanel` (`store-detail-panel.tsx:908`). No responsive breakpoint logic.

**Fix scope:** FRONTEND_ONLY

**Notes:**
- Suggested fix: increase panel width to `w-96` (384px) or `w-[400px]`. This alone does not resolve SBE-2 (map context loss) — the two SBEs need to be considered together.
- If SBE-2 resolves as Option A (overlay with map padding), the panel can be wider without layout impact.
- If SBE-2 resolves as Option B (flex-row resize), wider panel further reduces map canvas — trade-off for Gabriel to weigh.

---

### SBE-2: Opening the store detail panel loses map geographic context

**Context:** Gabriel clicked a store on the map. The StoreDetailPanel slid in from the right, covering the right portion of the map canvas. The map did not re-center or adjust its viewport to account for the panel.

```
GIVEN the user has clicked a store location on the Measurement Map
  AND the StoreDetailPanel is opening (transition-transform slide-in)

WHEN the panel reaches its fully-open state (translate-x-0)

THEN the clicked store marker remains visible and centered in the map's usable (non-occluded) viewport area
  AND the user retains geographic context of the store's surroundings
```

**Current behavior:** The panel overlays the right 320px of the map canvas without adjusting the Mapbox viewport. The clicked store may be partially or fully behind the panel. The top-bar control cluster also shifts left (via `right-80` at `proximity-map.tsx:219`), adding to the perception that the map moved.

**Root cause:** No `map.easeTo()` or `map.setPadding()` call is issued when the panel opens. The `StoreDetailPanel` and `useStoreMetrics` hook do not communicate viewport intent to the Mapbox instance (`proximity-map.tsx:236`, `store-detail-panel.tsx:872–1008`).

**Fix scope:** FRONTEND_ONLY

---

> **[CLARIFY] — Resolution required before implementation**
>
> Gabriel described two incompatible solutions and explicitly said "I'm not sure":
>
> **Option A — True overlay with viewport padding (recommended starting point)**
> The panel floats over the map (current DOM structure, already `absolute`). When the panel opens, call `map.easeTo({ padding: { right: 320 }, around: clickedStoreCoords })` so the map re-centers the store in the visible area. The map canvas stays full-width; the panel simply overlays it.
>
> Pros: No layout refactor. Map stays full-width. Simpler.
> Cons: Panel still covers data — trade area polygons, flow lines, nearby stores on the right side remain hidden.
>
> **Option B — Flex-row layout resize**
> Restructure `ProximityMap` to use a flex-row container. Map column shrinks when panel is open. Panel occupies a real column, no overlap.
>
> Pros: Nothing is ever hidden behind the panel.
> Cons: Significant layout refactor. Map re-renders at reduced width on open/close. On smaller viewports the map becomes cramped.
>
> **Question for Gabriel:** Which of these feels right?
> - "Slide over the map, but re-center so I can still see the store" → Option A
> - "Actually shrink the map so I can always see everything" → Option B
> - Something else?
>
> This SBE is blocked for implementation until Gabriel answers.

---

### SBE-3: Store detail panel close button is difficult to target

**Context:** Gabriel reviewed the StoreDetailPanel and found the close button (X) in the panel header small and hard to click accurately on the first attempt.

```
GIVEN the user is viewing an open StoreDetailPanel

WHEN the user looks at the panel header to close the panel

THEN the close button (X) is visually distinct and large enough to click on the first attempt
  AND the button's hit target is at least 36×36px
  AND the button has sufficient visual contrast against the white panel background to be immediately locatable
```

**Current behavior:** Close button renders at `h-7 w-7` (28×28px) with a 14px X icon and `variant="ghost"` (no background on idle state). The icon occupies roughly half the hit target area, and the ghost variant provides no idle-state visual affordance on a white background.

**Root cause:** `Button` component at `store-detail-panel.tsx:934–942` uses `size="sm"` with explicit `h-7 w-7 p-0` override and `X size={14}`. Ghost variant removes background until hover.

**Fix scope:** FRONTEND_ONLY

**Notes:**
- Suggested fix: `h-8 w-8` (32px) minimum, X icon `size={16}`, optionally add a subtle `bg-gray-100 rounded` on idle state so the button is always visible.
- WCAG 2.5.5 recommends 44px; 36px is a reasonable product minimum for a secondary control.
- This is an isolated header change — no data, no layout impact.

---

## Open Items

| # | Item | Blocking |
|---|------|----------|
| 1 | SBE-2 [CLARIFY]: Gabriel must choose Option A (overlay + map.easeTo) or Option B (flex-row resize) | Yes — SBE-2 cannot be implemented without this decision |
| 2 | SBE-1 width value: exact target width (w-96 / 400px / other) should be confirmed alongside SBE-2 resolution, since the two are coupled | Soft block |

---

## Phase 1 Gate

This catalog is a **draft**. It has not been confirmed by Gabriel.

Per the skill protocol:
- SBE-1 and SBE-3 are implementation-ready once confirmed.
- SBE-2 requires Gabriel's explicit choice on overlay vs. resize before any ticket or code work proceeds.
- No Jira operations have been performed. No Phase 2 activities have started.
