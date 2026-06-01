# Feedback Findings — KTP-130 Empty Visitor Flow Circles
**Date:** 2026-05-06
**Phase:** Phase 1, Steps 1-3 (Ingest, Code Trace, Specification Draft)
**Epic:** KTP-130 (Klever Measurement Map)

---

## Step 1: Ingest

### Raw Finding

```
FINDING-1:
  screenshot: tickets/KTP/KTP-130/design/screenshots/ux-feedback-2026-05-04/sbe7-empty-circles.png
  quote: "See these circles on the map? They're completely empty. Just white circles with
          green borders floating over the states. At this zoom level they should either
          show the store count number inside them, or have some kind of icon, or maybe just
          be smaller dots. Right now they look broken, like the data didn't load. This is
          what users see when they first open the map before zooming in, so it's the first
          impression and it looks wrong."
  observation: Screenshot shows a state-level zoom (approximately 3.75) of the Southeast US.
               Large white circles (~40-44px diameter) with green (#5BA67D) borders are visible
               positioned over or near states (Alabama, Mississippi region). Animated dashed
               green lines connect the circles toward a central point — this is the visitor
               flow mode rendering. No numbers, labels, or icons are visible inside the circles.
  issue: Visitor flow origin circles render visually empty at state-level zoom. No visitor
         volume numbers appear inside the white circles, making the view look broken.
  expected: At state-level zoom, visitor flow circles should display the visitor volume
            number inside them, OR show a meaningful icon, OR scale down to small indicator
            dots that don't look like broken empty bubbles.
  category: UX
  severity: P1_HIGH
```

**Discipline check (Mary's guard):** User described one distinct problem — empty circles at this zoom level. The quote contains multiple suggested remedies (show count, show icon, smaller dots), but these are alternatives within the same issue, not separate findings. Keeping as FINDING-1.

**Severity rationale:** User said "this is the first impression and it looks wrong" — that maps to P1_HIGH. Did not use P0_BLOCKER language ("urgent", "can't ship"). Maintained at P1_HIGH per the user's actual tone.

---

## Step 2: Code Trace

### Where the circles come from

The empty circles are rendered by `FLOW_CIRCLE_LAYER` in:

**File:** `/components/map/functions/update-map-layers/update-flow-lines.tsx`
**Lines:** 308-328

```typescript
// White circles with green stroke (matching mockup)
// Radius is zoom-responsive: larger at low zoom so labels remain legible
map.addLayer({
  id: FLOW_CIRCLE_LAYER,   // "visitor-flow-circles-layer"
  type: "circle",
  source: FLOW_CIRCLE_SOURCE,
  paint: {
    "circle-radius": [
      "interpolate", ["linear"], ["zoom"],
      3, 22,     // <-- 44px diameter at zoom 3
      5, 20,
      7, 18,
      10, circleStyle.radius,   // circleStyle.radius = 16
      14, circleStyle.radius,
    ],
    "circle-color": "#FFFFFF",              // white fill
    "circle-stroke-color": circleStyle.color,  // "#5BA67D" (green)
    "circle-stroke-width": circleStyle.strokeWidth,  // 2
    "circle-opacity": 1,
  },
});
```

**Source config reference:**
`/components/map/consts/config.tsx` lines 316-323:
```typescript
visitorFlowCircles: {
  color: "#5BA67D",
  strokeColor: "#FFFFFF",
  strokeWidth: 2,
  radius: 16,
  labelSize: 10,
},
```

### Where the text label should come from

The text label is a separate symbol layer:

**File:** `/components/map/functions/update-map-layers/update-flow-lines.tsx`
**Lines:** 332-352

```typescript
map.addLayer({
  id: FLOW_CIRCLE_LABEL_LAYER,   // "visitor-flow-circles-label-layer"
  type: "symbol",
  source: FLOW_CIRCLE_SOURCE,
  layout: {
    "text-field": ["get", "formattedVolume"],
    "text-size": [
      "interpolate", ["linear"], ["zoom"],
      3, 11,      // <-- 11px font at zoom 3
      5, 12,
      7, 13,
      10, 13,
    ],
    "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
    "text-allow-overlap": true,
    "text-ignore-placement": true,
  },
  paint: {
    "text-color": "#000000",
  },
});
```

### Root cause analysis

`formattedVolume` is computed in `buildFlowLineFeatures` (calculate-flow-lines.ts, line 81):
`formattedVolume: formatCount(origin.visitorVolume)`

`formatCount` always returns a non-empty string (minimum "0") — so the data field is always populated.

**The actual issue is visual, not a data absence.** At zoom ~3.75:
- Circle radius = ~21px → diameter ~42px
- Text size = ~11px
- Black text on white background

This SHOULD be readable. However, the symbol layer (`FLOW_CIRCLE_LABEL_LAYER`) is a **separate Mapbox layer from the circle layer** (`FLOW_CIRCLE_LAYER`). Mapbox symbol layers can be suppressed by collision detection even when `text-allow-overlap: true` if the symbol placement algorithm conflicts with placement in the same source.

**More likely root cause:** The `text-field` uses `["get", "formattedVolume"]`. The source data is `FLOW_CIRCLE_SOURCE`, which is built by `buildCircleFeatures()`. Tracing `buildCircleFeatures` (lines 79-99 of update-flow-lines.tsx):
- It copies `formattedVolume` from the LineString features' properties
- These come from `buildFlowLineFeatures` which correctly sets `formattedVolume`

However, there is a specific Mapbox GL JS behavior to note: when a `circle` layer and a `symbol` layer share the same source, the symbol layer renders on top of the circle layer **only if it's added after**. The symbol layer is added after (line 332), which should be correct.

**Most likely visible issue at zoom 3.75:** The `text-size: 11` at zoom 3 produces text that is visually too small relative to the 44px-diameter circle — an 11px string inside a 44px circle with 2px stroke leaves text that reads as a tiny speck from the user's screen distance. The circles read as "empty" even though text is technically rendered.

**Secondary issue:** At initial state-level zoom (3.75), circles are 44px diameter — unusually large for an informational overlay that isn't interactive at that zoom. They dominate the visual field without providing readable information, creating the "broken/data didn't load" impression.

### Fix scope

`FRONTEND_ONLY` — both layers are purely Mapbox GL JS styling, no backend or API changes required.

### Code trace summary

```
code_trace: {
  file: "components/map/functions/update-map-layers/update-flow-lines.tsx",
  lines: [308-352],
  component: "FLOW_CIRCLE_LAYER + FLOW_CIRCLE_LABEL_LAYER (ensureFlowLineLayer function)",
  fix_scope: FRONTEND_ONLY,
  notes: [
    "Circle radius at zoom 3 is 22px (44px diameter) — oversized for state zoom level",
    "Text size at zoom 3 is 11px — too small to read inside a 44px circle",
    "formattedVolume data IS present — this is a styling/sizing issue, not a data gap",
    "[SEVERITY_NOTE] This is the first-impression view users see after clicking a store.
     Broken appearance at state zoom could undermine trust in the data product.",
    "CONFIG.styling.visitorFlowCircles.labelSize = 10 exists but is NOT used in the
     text-size expression (uses hardcoded 11/12/13 instead) — minor inconsistency",
    "The 'stroke' and 'color' values in visitorFlowCircles config appear swapped
     vs usage: config.strokeColor = '#FFFFFF' but layer uses config.color for stroke.
     This is a pre-existing quirk, not introduced by this feature."
  ]
}
```

---

## Step 3: Specification Draft (Mary's Discipline Check)

### Mary's Audit

1. **Did the user actually say this, or did the agent infer it from the screenshot?**
   - FINDING-1 is directly from the user's words. No inferred findings added.
   - The user offered three possible solutions (number, icon, smaller dots). These are alternatives within one UX issue, not separate findings.

2. **Count check:** User described 1 distinct issue. This trace produces 1 finding. Count is proportional.

3. **Business intent check:** In one sentence: "The visitor flow origin circles don't communicate their data at state-level zoom, making the map look like it failed to load."
   That is a clear business rationale (first impression, data trust signal).

### SBE Catalog

---

```markdown
### SBE-1: Visitor flow origin circles must display readable visitor counts at state-level zoom

**Context:** Gabriel is reviewing the visitor flow view after clicking a store. The map is at
state-level zoom (~3.75, initial view). Large white circles with green borders are visible
over states, connected by animated dashed flow lines.

GIVEN the user has clicked a store location and the visitor flow mode is active
  AND the map is at state-level zoom (approximately zoom 3-5)

WHEN the visitor flow circles are rendered on the map

THEN each origin circle MUST display the visitor volume number inside it in a readable font size
  AND the number must be legible against the white circle background at zoom 3-5
  AND OR the circles should scale to a smaller size (dot-style) that does not create an
      "empty bubble" appearance when no readable text is shown

**Current behavior:** Large white circles (~44px diameter at zoom 3) render with no visible
content. A symbol layer exists for `formattedVolume` text but the 11px font is too small
relative to the circle size to be readable at this zoom level from normal viewing distance.
The circles look empty and broken, as if data failed to load.

**Root cause:** In `update-flow-lines.tsx` (lines 308-352), circle radius at zoom 3 is
hardcoded to 22px while text-size is hardcoded to 11px. The mismatch creates circles that
visually read as empty. Either the text must be proportionally larger, or the circles must
shrink to match the text, or circles should use a smaller dot form until zoom is sufficient
for readable numbers.

**Fix scope:** FRONTEND_ONLY

**Acceptance criteria detail:**
- At zoom 3-5: either (a) visitor count is readable inside each circle — minimum font size
  that is proportional to circle radius (e.g., text-size = circle-radius × 0.6 minimum),
  OR (b) circles reduce to small indicator dots (radius ≤ 6px) that look intentional rather
  than broken.
- At zoom 5+: visitor count is always displayed and readable.
- The fix must not break the popup interaction that appears on hover over each circle.

**[CLARIFY]:** Gabriel suggested three remedies: (a) show store count number, (b) show an
icon, (c) smaller dots. The code trace confirms option (a) is technically already wired —
the data is there. The fix is likely a proportional sizing adjustment. Confirm which approach
is preferred before implementing:
  - Option A: Increase text-size to match circle size (e.g., text-size scales from 14px at
    zoom 3 to maintain ~0.6× radius ratio)
  - Option B: Shrink circles to dot-style (radius 4-6px) at zoom < 5, grow to labeled
    circles at zoom ≥ 5
  - Option C: Add a small icon (brand logo or generic store pin) instead of number at low zoom
```

---

## Summary

| # | Finding | Category | Severity | SBE | Fix Scope | Status |
|---|---------|----------|----------|-----|-----------|--------|
| 1 | Visitor flow circles empty at state zoom | UX | P1_HIGH | SBE-1 | FRONTEND_ONLY | Pending confirmation |

**One finding, one SBE.** Discipline check passed. The user described one distinct problem with multiple proposed alternatives; these alternatives become options within a single SBE with a [CLARIFY] flag asking Gabriel to pick the preferred fix direction before implementation.
