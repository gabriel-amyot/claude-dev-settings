# SBE Catalog — KTP-130 Visitor Flow Circles
**Date:** 2026-05-06
**Phase:** Phase 1, Step 3 — Draft (awaiting confirmation, Step 4 not executed per task scope)
**Epic:** KTP-130 (Klever Measurement Map)
**Status:** DRAFT — not confirmed, not sent to Jira

---

## SBE-1: Visitor flow origin circles must display readable visitor counts at state-level zoom

**Context:** User is viewing the Measurement Map in visitor flow mode (triggered by clicking a
store location). The map is at state-level zoom (~3.75, the default initial zoom). Large white
circles with green borders appear over states, connected by animated dashed green flow lines.

GIVEN the user has clicked a store location and visitor flow mode is active
  AND the map is at state-level zoom (zoom 3 to 5)

WHEN the visitor flow origin circles are rendered on the map

THEN each origin circle MUST display the visitor volume number in a font size readable at that zoom
  AND the visitor count label must be legible (minimum effective text size proportional to circle radius)
  AND the circles must not appear visually empty or broken at state-level zoom

**Current behavior:** White circles render at ~44px diameter (radius=22 at zoom 3) with a
`text-size: 11` label. The 11px font inside a 44px circle is too small to read at normal viewing
distance, creating the appearance that no data is loaded. The circles look like empty broken
bubbles rather than data-bearing UI elements.

**Root cause:**
- File: `components/map/functions/update-map-layers/update-flow-lines.tsx`
- Lines: 308-352 (`ensureFlowLineLayer` function)
- `FLOW_CIRCLE_LAYER` sets `circle-radius: 22` at zoom 3 (44px diameter)
- `FLOW_CIRCLE_LABEL_LAYER` sets `text-size: 11` at zoom 3
- Ratio is ~0.25× (text:diameter) — minimum readable ratio is approximately 0.4-0.6×
- `formattedVolume` data IS correctly set via `formatCount(origin.visitorVolume)` — this
  is NOT a data absence bug. It is purely a visual sizing mismatch.

**Fix scope:** `FRONTEND_ONLY`

**Fix options (requires Gabriel's decision before implementation):**

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A | Increase text-size to maintain ≥0.45× text:radius ratio at all zoom levels (e.g., `text-size: 18` at zoom 3, scaling up to 13 at zoom 7+) | Circles stay large, numbers are readable; may feel crowded at state view |
| B | Reduce circle radius to dot-style (radius 4-6px) at zoom < 5, expand to labeled circles (radius 16px) at zoom ≥ 5 | Clean small indicators at state zoom, full labeled circles at county zoom |
| C | Replace circle with a small icon (e.g., store/pin SVG) at zoom < 5, switch to labeled circle at zoom ≥ 5 | Most visually polished; requires icon asset; more implementation complexity |

**Recommended option (from code trace):** Option B is the lowest-effort, most defensible fix.
The current radius interpolation was likely designed for a higher minimum zoom and the low-zoom
value (22) was added as an attempt to keep circles legible but had the opposite effect. Reducing
radius at zoom < 5 to ≤6 makes the circles look intentional (small indicator dots) rather than
broken empty bubbles.

**[CLARIFY] for Gabriel before implementation:**
Which option do you prefer? Option A (bigger text), Option B (smaller circles at state zoom),
or Option C (icon at state zoom)?

---

## Non-SBE Notes (code trace observations, not user-reported)

These observations were made during code trace. They are NOT SBEs — they were not reported by the
user. Captured here for completeness and future reference:

- `CONFIG.styling.visitorFlowCircles.labelSize = 10` exists but is not used in the text-size
  expression (hardcoded 11/12/13 is used instead). If the config value were used, the inconsistency
  would be obvious. Minor cleanup opportunity for a future ticket.

- `CONFIG.styling.visitorFlowCircles.strokeColor = '#FFFFFF'` and
  `CONFIG.styling.visitorFlowCircles.color = '#5BA67D'` — but in the layer definition, `color` is
  used for `circle-stroke-color` and the fill is hardcoded `"#FFFFFF"`. The naming
  (color vs strokeColor) is inverted vs how they're actually used. Pre-existing quirk, not
  introduced by this feature. Not part of the user's feedback.

- `CONFIG.layer.STATE_CIRCLES = "state-circles"` is referenced in `LAYERS_TO_HIDE_IN_FLOW_MODE`
  but no code creates a layer with this ID. The hide/restore calls for it are no-ops. This is a
  dead reference — left as-is per no-refactoring policy.

---

## Metadata

```yaml
sbe_id: SBE-1
epic: KTP-130
date: 2026-05-06
screenshot: sbe7-empty-circles.png
category: UX
severity: P1_HIGH
fix_scope: FRONTEND_ONLY
status: DRAFT
clarify_required: true
clarify_question: "Which fix approach: (A) larger text, (B) smaller circles at state zoom, or (C) icon at low zoom?"
primary_file: components/map/functions/update-map-layers/update-flow-lines.tsx
primary_lines: 308-352
confirmed: false
```
