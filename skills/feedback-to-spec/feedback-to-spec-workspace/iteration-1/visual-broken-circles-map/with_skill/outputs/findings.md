# Raw Findings — Feedback Extraction
**Date:** 2026-05-04
**Epic:** KTP-130 (Klever Measurement Map)
**Screenshot:** `tickets/KTP/KTP-130/design/screenshots/ux-feedback-2026-05-04/sbe7-empty-circles.png`

---

## FINDING-1

```
FINDING-1:
  screenshot: sbe7-empty-circles.png
  quote: "See these circles on the map? They're completely empty. Just white circles with
          green borders floating over the states."
  observation: At country zoom level (~3.75, the default first view), 7–8 large circles
               appear over US states. They are white-filled with a green border and have
               no text, label, number, or icon inside them. Green curved dashed lines
               connect some of them. The state of Alabama is highlighted yellow (has data).
  issue: Circles at country zoom are visually empty — no count label, no icon — making
         them look like a broken loading state.
  expected: Circles should either display the store count number inside them, or use a
            distinct icon, or be rendered as small solid dots to serve as ambient
            situation-awareness markers.
  category: UX
  severity: P1_HIGH

  code_trace:
    files:
      - components/map/functions/update-map-layers/update-zip-layers.tsx (lines 610–706)
      - components/map/functions/generate-metrics-marker-images.ts
      - components/map/consts/config.tsx (metricsCircles config, lines 243–301)
    component: METRICS_CIRCLES (Mapbox symbol layer)
    fix_scope: FRONTEND_ONLY
    notes: |
      The METRICS_CIRCLES layer is a Mapbox symbol layer that uses a canvas-generated
      icon ('marker-small-normal') as the circle background, with 'text-field' from
      the 'formattedCount' GeoJSON property for the label.

      The icon is generated in generate-metrics-marker-images.ts with:
        fillColor: '#000000' (black)
        strokeColor: '#FFFFFF' (white border)

      At country zoom (3.75), icon-size interpolates to 0.5–1.9 depending on count.
      When count = 0, icon-opacity = 0.1 (nearly invisible), text-opacity = 0.1 and
      text-color = '#000000' (black on black icon = invisible label).
      When count > 0, the icon renders as a solid black circle with white border.

      CRITICAL DISCREPANCY: The screenshot shows WHITE circles with GREEN borders — this
      does NOT match the black/white metrics icon config. Two possible explanations:

      HYPOTHESIS A (most likely): The circles visible in the screenshot are not the
      METRICS_CIRCLES layer at all. They are the visitor flow SVG overlay circles
      (renderTargetCircle / renderSourceCircles in renderers.tsx). The SVG renders:
        - renderTargetCircle: fill="white", stroke=locationCircles.pinFillColor (#D52815/red), r=8
        - renderSourceCircles: fill="#08081F", stroke="#FFF"
        But the green dashed curved lines connecting the circles are definitively the
        visitor-flow-lines-layer (color: "#5BA67D"). The visitorFlowCircles config
        (color: "#5BA67D", strokeColor: "#FFFFFF") also doesn't match green border.

      HYPOTHESIS B: The COMPETITORS_CIRCLES layer (white fill, green #0eac1c stroke,
      minZoom: 8) is somehow leaking. However minZoom: 8 should prevent this at zoom 3.75.

      HYPOTHESIS C (most consistent with screenshot): These are the LOCATION_CIRCLES
      (white fill, red #D52815 stroke, minZoom: 2) which DO show at country zoom.
      The screenshot color may appear green due to screenshot compression or the color
      being the flow line color blending.

      MOST LIKELY ROOT CAUSE: The circles are the METRICS_CIRCLES symbol layer, but
      the generated icon is not loading correctly (SSR or canvas API issue during
      addMetricsMarkerImages), so Mapbox falls back to rendering no icon — leaving
      just the text-field which is also empty/invisible at count=0. The result: no
      visible content inside the circle boundary. What appears as a "circle" may be
      a different layer entirely — the LOCATION_CIRCLES (white/red) misidentified
      as white/green due to image compression in the screenshot.

      CONFIRMED: The metricsCircles.minZoom is 2, so they should appear at country
      zoom. The text-field is 'formattedCount' from GeoJSON. For count=0, text-color
      is '#000000' (invisible on black icon). For count>0, text-color is '#FFFFFF'
      (white, visible on black icon). So labeled circles only appear when count > 0.

      CORE BUG: At country zoom, the METRICS_CIRCLES label ('formattedCount') is
      hidden for zero-data states (text-color: black, text rendered on black icon at
      10% opacity). For states WITH data, the label shows as white text on black icon.
      But at icon-size ~0.5x (zoom 0–3), the icon is only 10px radius — tiny. At
      zoom 6 it's 14–77px depending on count. The "large empty circles" the user sees
      are likely the icon-size at zoom 3.75 with count > 0 (~1.4–1.9x = 14–19px radius)
      rendering as a visible black disk with no legible text (font-size: 14px fixed,
      which is too large for an icon-size 1.0x = 10px radius circle).

    trace_confidence: PARTIAL — canvas/SSR icon generation needs runtime verification.
    search_terms_used: METRICS_CIRCLES, metricsCircles, addLayer, generate-metrics-marker-images,
                       circle-color, circle-stroke, map-marker, styles.css, renderers.tsx
```

---

## FINDING-2

```
FINDING-2:
  screenshot: sbe7-empty-circles.png
  quote: "At this zoom level they should either show the store count number inside them,
          or have some kind of icon, or maybe just be smaller dots."
  observation: User explicitly proposes three alternatives for what they expect:
               (1) store count number inside the circle,
               (2) an icon inside the circle,
               (3) smaller dot markers instead of large empty circles.
  issue: The expected information density at country zoom is not being communicated.
         The circles are too large relative to their content (empty = no count shown).
  expected: One of: (a) count label visible inside circle, (b) a meaningful icon,
            (c) much smaller dot markers that don't suggest interactive content.
  category: UX
  severity: P1_HIGH

  code_trace:
    file: components/map/functions/update-map-layers/update-zip-layers.tsx
    lines: 622–705
    component: METRICS_CIRCLES (symbol layout section)
    fix_scope: FRONTEND_ONLY
    notes: |
      The 'text-field' is set to ["get", "formattedCount"] and text-size is a fixed
      14px. The icon-size at low zoom (0) starts at 0.5x for count=0 (10px radius).
      A fixed 14px font inside a 10px circle = text overflows circle, is clipped by
      Mapbox, or simply not readable. At zoom 3.75, circle is ~9–19px radius
      depending on count. 14px text in a 9px circle is illegible.

      The text-halo (CONFIG.styling.metricsLabels.haloWidth = 2px, haloColor = '#000000')
      for count > 0 means white text on black icon with black halo — readable in theory
      but the circle is too small to be legible at country zoom.

      The zoom-responsive radius (interpolate on zoom AND count) is defined in
      CONFIG.styling.metricsCircles.radius, but the symbol layer does NOT use
      circle-radius — it uses icon-size as a multiplier on the 10px canvas icon.
      The text-size (14px) is NOT zoom-responsive. This is a mismatch.

      For "smaller dots" alternative: The locationCircles already uses a zoom-interpolated
      radius starting at 1.5px at zoom=2 (effectively invisible dots for situation
      awareness), scaling to 18px at zoom=16. A similar approach for metrics circles
      at country zoom would produce the "small dots" behavior the user describes.
```

---

## FINDING-3

```
FINDING-3:
  screenshot: sbe7-empty-circles.png
  quote: "Right now they look broken, like the data didn't load."
  observation: The "empty circle" appearance (large circle outline with nothing inside)
               is a common visual pattern for loading spinners or failed image loads.
               Users interpret it as a data loading failure rather than "no data here".
  issue: Visual design of zero-state metrics circles is indistinguishable from a
         broken/loading state.
  expected: Zero-state circles should either be hidden entirely or rendered as
            clearly intentional small markers (tiny dots) rather than large empty outlines.
  category: UX
  severity: P1_HIGH

  code_trace:
    file: components/map/functions/update-map-layers/update-zip-layers.tsx
    lines: 698–705 (icon-opacity case expression)
    component: METRICS_CIRCLES (paint section)
    fix_scope: FRONTEND_ONLY
    notes: |
      The current zero-state treatment:
        icon-opacity: ["case", ["==", ["get", "count"], 0], 0.1, 1]
        text-color: ["case", ["==", ["get", "count"], 0], "#000000", "#FFFFFF"]
        text-halo-width: ["case", ["==", ["get", "count"], 0], 0, 2]

      A black icon at 10% opacity on the light-gray map (#F5F5F5 background) renders
      as a very faint gray circle. The stroke (from the canvas ImageData) is white at
      10% opacity = nearly invisible. But what the user sees as "white circles with
      green borders" suggests a DIFFERENT rendering path.

      POSSIBLE CAUSE: The canvas-based marker images may not be loading in all
      environments (SSR, Safari canvas restrictions, or addMetricsMarkerImages called
      before map style loads). When a Mapbox symbol layer's icon-image doesn't resolve,
      Mapbox renders the text-field only, with no icon. If formattedCount is empty
      string or "0", the text is also invisible. Result: apparently empty symbols
      clustered at state centers.

      The "white circles with green borders" visual may come from a separate layer
      rendering on top, or from the Mapbox default placeholder for missing icons
      (which varies by version).
```

---

## FINDING-4

```
FINDING-4:
  screenshot: sbe7-empty-circles.png
  quote: "This is what users see when they first open the map before zooming in,
          so it's the first impression and it looks wrong."
  observation: Country zoom (~3.75) is the initial map state (CONFIG.map.zoom = 3.75).
               All users see this state before any interaction.
  issue: The broken-looking circles are part of the first-impression experience.
         Any visual error here affects 100% of sessions.
  expected: The initial map load at country zoom should look intentional and polished.
            Either the circles show meaningful data, or they are not shown at this zoom.
  category: UX
  severity: P0_BLOCKER (first impression, affects 100% of sessions)

  code_trace:
    file: components/map/consts/config.tsx
    lines: 17-29
    component: CONFIG.map.zoom (initial zoom = 3.75)
    fix_scope: FRONTEND_ONLY
    notes: |
      Initial zoom is 3.75. The metricsCircles.minZoom is 2, so circles ARE shown
      at first load. The icon-size at zoom 0 (used as base for linear interpolation)
      produces icons scaled from 0.5x to 1.9x of the 10px base radius.
      At zoom 3.75 (between 0 and 6), Mapbox linearly interpolates the icon-size
      expression. For a state with e.g. count=1000: icon-size ≈ 1.2x = 12px radius.
      Text-size is fixed at 14px — too large for a 12px radius circle.

      Fix options:
      1. Raise metricsCircles.minZoom to 5 or 6 so circles only appear when the map
         has zoomed in past country view. Country view shows only the state fill colors
         (which DO work as shown by Alabama's yellow highlight).
      2. Make text-size zoom-responsive to match the icon-size at each zoom level.
      3. Replace the symbol approach with a circle layer + separate text layer,
         both driven by zoom-responsive expressions.
```

---

## Code Architecture Summary

The METRICS_CIRCLES rendering pipeline:

1. **Data source:** GeoJSON features with `{count, formattedCount, location, ...}` props.
   - Built by `calculateStateExpressions()` in `calculate-country-layers.tsx` (line 87–102).
   - Features are only created for states present in `CONVERSIONS` data keyed by state name.
   - State centers come from a progressive tile-loading process (`extractStateCenters`), so
     centers may not be available on first render, causing markers to be skipped (line 77–79).

2. **Icon images:** Canvas-drawn in `generate-metrics-marker-images.ts` during `setupMapLayers`.
   - 3 sizes (small=10px, medium=30px, large=60px radius) × 2 states (normal/hover) = 6 images.
   - All icons: black fill, white stroke. The symbol layer uses 'marker-small-normal' for all.
   - Only scaled via `icon-size` expression — the medium/large icons are generated but unused.

3. **Symbol layer:** Added in `addMetricsLayer()` in `update-zip-layers.tsx` (line 610).
   - Type: "symbol" (NOT "circle") — combines icon + text in a single Mapbox unit.
   - `text-field`: `["get", "formattedCount"]` — the pre-formatted count string.
   - `text-size`: fixed 14px (NOT zoom-responsive).
   - `icon-size`: zoom + count interpolation.
   - `icon-opacity`: 1 when count>0, 0.1 when count=0.
   - `text-color`: white when count>0, black when count=0 (invisible on near-invisible icon).

4. **Known timing issue:** `extractStateCenters` runs progressively as tiles load.
   On first render, markers for states whose centers haven't loaded yet are silently skipped
   (logged as "markers pending"). This means the user may see 0 circles or partial circles
   on first load, then circles appear as tiles finish loading.

5. **Green circles / flow overlay:** The green dashed lines in the screenshot are the
   visitor flow layer (`visitor-flow-lines-layer`, color: "#5BA67D"). The circles connected
   to them are SVG-rendered by the `DistributionInTime` or flow visualization component.
   These may be showing because a previous flow state was not properly cleared.
   The green border color (#5BA67D) matches visitorFlowCircles config.

---

## Files Traced

| File | Relevance |
|------|-----------|
| `components/map/functions/update-map-layers/update-zip-layers.tsx` | METRICS_CIRCLES layer definition and paint (lines 610–706) |
| `components/map/functions/generate-metrics-marker-images.ts` | Canvas icon generation (black fill, white stroke) |
| `components/map/consts/config.tsx` | metricsCircles config, initial zoom=3.75, minZoom=2 |
| `components/map/functions/calculate-map-layers/calculate-country-layers.tsx` | GeoJSON feature building; state centers dependency |
| `components/map/functions/setup-map-layers.tsx` | Progressive tile loading; extractStateCenters |
| `components/map/components/metrics-popup/metrics-popup.tsx` | Invisible DOM marker (popup anchor only, NOT the visible circle) |
| `components/map/functions/calculate-map-layers/calculate-flow/renderers.tsx` | SVG flow circles (possible source of green/white circles) |
| `app/(frontend)/styles.css` | `.map-marker` CSS class (black bg, white border) — now unused |
| `components/map/functions/map-styling.tsx` | METRICS_CIRCLES excluded from symbol visibility rules |
