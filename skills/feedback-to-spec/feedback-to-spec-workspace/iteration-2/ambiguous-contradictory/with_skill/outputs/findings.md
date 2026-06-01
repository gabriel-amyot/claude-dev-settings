# Feedback Extraction — KTP-130 Right Panel
**Date:** 2026-05-06
**Epic:** KTP-130 (Klever Measurement Map)
**Screenshot:** `tickets/KTP/KTP-130/design/screenshots/right-panel-empty.png`
**Phase:** 1, Steps 1–3 only (no Jira interaction)

---

## Mary's Discipline Audit (Pre-Extraction)

Gabriel described **3 distinct problems** during this narration:
1. The text in the panel is cramped (panel too narrow)
2. Opening the panel pushes the map left / loses context (panel is a DOM-shifting sidebar)
3. The close button is hard to hit

He also introduced **one ambiguous / contradictory intent** between #1 and #2:
- "wider but not taking so much space" — these two desires conflict. They cannot both be satisfied with a simple width change. A resolution (overlay vs. resize vs. overlay-with-padding) must be chosen by Gabriel before implementation can proceed.

Finding count: **3**. Mary's count check passes (3 observations, 3 findings). No inflation.

---

## Raw Findings

---

### FINDING-1

```
screenshot: right-panel-empty.png
quote: "The panel feels too narrow, the text is cramped."
observation: The StoreDetailPanel renders at w-80 (320px, Tailwind class). The panel
             contains dense content: 2x3 metric grids with 11px labels, truncated store
             name, mini bar charts, and a Top Origin ZIPs table with 4 columns. At 320px,
             multi-column tables and metric card labels truncate or wrap awkwardly.
issue: The panel's fixed width (320px) is too narrow to display its content without
       crowding; text labels, table columns, and metric values visually compete for space.
expected: Content renders at a comfortable reading width with no truncation on primary
          labels and no wrapping inside metric cards.
category: UX
severity: P1_HIGH
```

**code_trace:**
```
file: components/map/components/store-detail-panel.tsx
lines: 908
component: StoreDetailPanel (root div className)
fix_scope: FRONTEND_ONLY
notes: |
  Hard-coded Tailwind class "w-80" (320px) on the outer panel wrapper.
  Metric cards use "grid-cols-2 gap-2" — at 320px with p-4 padding, each
  card is roughly 136px wide, which forces 11px labels like "Cost / Visit (est.)"
  to truncate. Table columns in TopOriginZipsTable (4 cols: ZIP, Visitors,
  Impr., Conv.) also compress at this width. No responsive breakpoint logic exists.
  [SEVERITY_NOTE] Technical impact is higher than P1 — the 4-column table
  at 320px makes "Impr." and "Conv." columns nearly unreadable — but user
  tone was "feels" / "cramped", not "broken", so kept at P1.
```

---

### FINDING-2

```
screenshot: right-panel-empty.png
quote: "When it opens it pushes the map too far left and I lose context.
        Maybe a slide-over that doesn't push the map? Or maybe the map should
        resize gracefully. I'm not sure."
observation: The StoreDetailPanel is positioned `absolute right-0 top-0 bottom-0`
             inside the map container. However, the top-bar controls div in
             proximity-map.tsx applies `right-80` when selectedLocationId is truthy
             (line 219), shifting the top-right button cluster leftward. Additionally,
             the map canvas itself (absolute inset-0, full-width) does NOT reflow
             when the panel opens — but the visible center-of-map shifts because the
             panel physically covers the right portion of the map canvas. The user
             perceives the map as "pushed left."
issue: Opening the StoreDetailPanel covers the right ~320px of the map canvas without
       adjusting the map's viewport center or bounds, so the user loses geographic
       context around the clicked store (it may end up partially hidden behind the panel).
expected: [CLARIFY — see below] The user expressed two contradictory solutions:
          (A) a slide-over / overlay that does NOT take space from the map, OR
          (B) the map resizing gracefully to accommodate the panel.
          These are mutually exclusive patterns:
          - Option A: panel floats over the map (position absolute, no layout shift);
            map viewport is padded right so the selected store re-centers in visible area.
          - Option B: map container shrinks (flexbox layout, panel takes a column),
            map re-renders at reduced width, center stays correct.
          Gabriel said "I'm not sure" — this is an explicit open question.
category: UX
severity: P1_HIGH
```

**code_trace:**
```
file: components/map/proximity-map.tsx
lines: 161–253
component: ProximityMap
fix_scope: FRONTEND_ONLY
notes: |
  The panel is already `absolute` (overlay) — it does NOT push other DOM elements.
  The map canvas div (id="map-container", absolute inset-0) renders underneath.
  The perceived "push" happens because:
    1. The panel covers the map canvas visually (right 320px is hidden behind white panel).
    2. The top-bar controls shift left via `right-80` class at line 219, which the
       user may read as "the map moved."
  The map library viewport is NOT adjusted when the panel opens — no `map.setPadding()`
  or `map.easeTo()` call exists in useStoreMetrics or the panel open handler.
  True fix depends on Gabriel's choice:
    - Option A (true overlay): add `map.easeTo({ padding: { right: 320 } })` when
      panel opens. Panel stays absolute. Map canvas stays full-width but re-centers.
    - Option B (layout resize): restructure ProximityMap to use flex-row,
      shrink map container width dynamically. Higher complexity, more reflow.
  [CLARIFY] tag required in SBE. Do not implement until Gabriel resolves.
```

---

### FINDING-3

```
screenshot: right-panel-empty.png
quote: "The close button is tiny, I keep missing it."
observation: The close button in StoreDetailPanel header uses `h-7 w-7 p-0`
             (28×28px) with an X icon at size={14}. The hit target is 28px, below
             the WCAG 2.5.8 recommended minimum of 24px CSS (met) but the icon
             within is only 14px, and the button sits in the top-right corner with
             2px gap from the panel edge (ml-2 on the button, p-4 on the header).
             In practice, the user is clicking a 14px icon with no visual affordance
             (ghost variant, low contrast gray).
issue: The close button is visually undersized and has insufficient contrast/affordance
       in ghost variant; users miss it, requiring multiple attempts to close the panel.
expected: The close button should be large enough to hit confidently on the first try,
          with enough visual weight to locate it immediately without hunting.
category: UX
severity: P2_MEDIUM
```

**code_trace:**
```
file: components/map/components/store-detail-panel.tsx
lines: 934–942
component: StoreDetailPanel header — Button (close)
fix_scope: FRONTEND_ONLY
notes: |
  Current: variant="ghost", size="sm", className="h-7 w-7 p-0", X size={14}.
  Ghost variant on white background = very low contrast. The 28px button
  is technically acceptable per WCAG 2.5.5 (44px preferred, 24px minimum)
  but the icon within renders at 14px with ~7px padding each side.
  Enlarging to h-8 w-8 and X size={16} with a light bg-gray-100 on hover
  (already handled by ghost variant) would improve discoverability without
  redesigning the header.
```

---

## Mary's Post-Extraction Audit

| Check | Result |
|-------|--------|
| Finding count vs. user observations (3) | 3 findings. Pass. |
| All findings from user's words | Yes. No screenshot-inferred extras. |
| Business intent statable for each | F1: "content is cramped and hard to read". F2: "I lose map context when the panel opens". F3: "I can't reliably close the panel". All pass. |
| Contradictory input handled | F2 carries [CLARIFY]. Not resolved autonomously. Pass. |

---
