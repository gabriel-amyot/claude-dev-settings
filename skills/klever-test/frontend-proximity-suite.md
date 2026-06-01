# Frontend: Proximity Map 14-UC Suite

Targeted UI test for the Proximity Map feature. 14 use cases covering map layers, location pins, flow lines, filters, and presentation mode.

## Environment

- **Local:** `http://localhost:3001/proximity` (backend on 8097)
- **Dev:** `https://portal.dev.beklever.com/proximity` (IAP auth required)

Always ask the user which mode before starting.

## Primary Tool: Agent Browser CLI

```bash
agent-browser open http://localhost:3001/proximity
agent-browser wait --load networkidle
agent-browser snapshot -i          # cheap text tree
agent-browser screenshot <path>    # evidence only
agent-browser eval "<js>"          # Mapbox/Zustand
agent-browser close
```

**Fallback: Chrome MCP** (`mcp__claude-in-chrome__*`) when Agent Browser is unavailable or when using user's existing authenticated Chrome session.

Chrome MCP session startup:
1. `mcp__claude-in-chrome__tabs_context_mcp`
2. `mcp__claude-in-chrome__tabs_create_mcp`
3. `mcp__claude-in-chrome__navigate`

## Mapbox Map Interaction

Map object exposed as `window.mapObj`:
```js
window.mapObj.flyTo({ center: [-87.68, 30.28], zoom: 10, duration: 0 }); 'done'
```

## Zustand Store Access

Store exposed as `window.mapStore`:
```js
// Read state
JSON.stringify(window.mapStore.getState().selectedLocationId)

// Set selected location (triggers flow lines)
window.mapStore.getState().setSelectedLocationId('854'); 'set'

// Clear selected location
window.mapStore.getState().setSelectedLocationId(null); 'cleared'

// Check visitor origins
const s = window.mapStore.getState();
JSON.stringify({ origins: s.visitorOrigins.length, loading: s.visitorOriginsLoading, error: s.visitorOriginsError })
```

## Advertiser Selection (Radix DropdownMenu)

1. Find trigger button (contains "Advertiser" or brand name)
2. Click trigger
3. Find menuitem (e.g., "Shrimp Basket")
4. Click menuitem

JS fallback:
```js
(() => {
  const items = [...document.querySelectorAll('[role=menuitem]')];
  const target = items.find(i => i.textContent.includes('Shrimp Basket'));
  if (!target) return 'not found: ' + items.map(i=>i.textContent).join(', ');
  target.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, cancelable:true, isPrimary:true}));
  target.click();
  return 'selected';
})()
```

## Location Pins: Canvas Circles (NOT DOM markers)

Layer ID: `location-circles`. Rendered on Mapbox GL canvas, not DOM.

```js
// Check if pins exist
window.mapObj.getLayer('location-circles')

// Programmatic selection (same as clicking a pin)
window.mapStore.getState().setSelectedLocationId('854')
```

## Use Cases

### UC-1: State Layer (KTP-329 AC-2, AC-7)
Navigate to `/proximity`, select advertiser. Map at state zoom (<=5), boundaries with data coloring. Screenshot.

### UC-2: County + ZIP Drill-Down (KTP-329 AC-3, KTP-337)
flyTo Seattle area, zoom 11. ZIP boundaries (green outlines), "Back to County" button visible. Screenshot.

### UC-3: Location Pins (KTP-105 AC-1, AC-2)
flyTo Gulf Shores, AL (30.28, -87.68, zoom 13). Circle pins (white fill, red stroke #D52815). Verify layer. Screenshot.

### UC-4: Console + Network Health (KTP-329 AC-3, AC-7)
Console: pattern "error|Error|500". Network: urlPattern "/api/map/". Backend log check (local).

### UC-5: Graceful Degradation (KTP-105 AC-4)
Advertiser with 0 data renders without crash. No white screen, no JS errors.

### UC-6: Feature Flag Rollback (KTP-329 AC-8)
Local mock: `lastUpdated` equals `2025-07-15T02:00:00Z`. Dev: NOT the mock sentinel. Via JS: `window.mapStore.getState().dateRange`.

### UC-7: Advertiser Switching
Switch advertiser. Map re-fetches, 0 errors, no stale data.

### UC-8: Channel Filters
Uncheck one channel, verify map stable. Re-check, verify stable.

### UC-9: Presentation Mode
Click "Presentation mode" toggle. Sidebar hides, map full width. Exit, sidebar returns.

### UC-10: Date Picker
Open calendar. Select different date, verify network refetch.

### UC-11: Competitor Data from API (KTP-105 AC-3)
Verify `public/mock/competitors/mock_data_competitors.json` does NOT exist. No mock imports.

### UC-12: Date Refetch (KTP-430 AC-3)
Verify `date` in useEffect deps: `grep -n "date," components/map/components/map-updater.tsx`.

### UC-13: Visitor Flow Lines (KTP-130 Phase 1)
Primary KTP-130 test. Full pipeline: pin click -> Placer API -> flow line render.
1. Select Shrimp Basket advertiser
2. flyTo Gulf Shores (30.28, -87.68, zoom 10)
3. Screenshot "before"
4. `setSelectedLocationId('854')`
5. Wait 8s
6. Verify source: `!!window.mapObj.getSource('visitor-flow-lines-source')`
7. Verify styling: color=#5BA67D, dasharray present, cap=round
8. Verify store: locationId=854, origins>0, loading=false, error=null
9. Screenshot "after"
10. Clear: `setSelectedLocationId(null)`, verify source removed

### UC-14: Flow Line Console Observability (KTP-130)
Clear console, trigger flow lines, wait 8s, read console pattern "Visitor Origins|Flow Lines".
Expected: centroid load count, render count, flow line count.

## Data Notes

- **Shrimp Basket:** locationId 854 (Gulf Shores), bridge table mapped
- **Placer entity:** venue:bed76627e8fa02183a216205
- **Expected:** ~250 ZIP-level origins, ~2793 total volume
- **Mock locations (local):** 11 WA locations, best test: Shoreline (47.74, -122.35, zoom 13) Store #4

## Output

Screenshots: `tickets/KTP/KTP-115/reports/testing/screenshots/`
Results: `tickets/KTP/KTP-115/reports/testing/ui-test-results-{date}.md`
