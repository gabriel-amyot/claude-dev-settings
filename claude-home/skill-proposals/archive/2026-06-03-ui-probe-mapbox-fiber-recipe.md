# Skill Proposal: ui-probe — add "grab the Mapbox map via React fiber" recipe
Date: 2026-06-03
Source: keen-lynx KTP-754 Canada map investigation

## Trigger
Update (not new skill): the existing `ui-probe` skill, when live-debugging the Klever Measurement Map and needing the Mapbox `Map` instance to read layers/sources/features.

## Scope
Global (ui-probe skill, references/recipes).

## Draft Steps
1. From `.mapboxgl-map`, get the React fiber (`__reactFiber$*`), climb to root.
2. BFS the fiber tree; for each node walk the `memoizedState` hook chain; find `hook.memoizedState.current` where the object `isMap` (has getStyle + queryRenderedFeatures + getZoom).
3. Stash on `window.__mref` for reuse across calls.
4. Inspect: `getStyle().layers` (vis/paint), `getSource(id)._data` (GeoJSON sources), `querySourceFeatures(srcId,{sourceLayer})` (tileset feature props), `project([lng,lat])` (screen coords — note container vs screenshot scale).
5. Sanitize all returns (typeof/boolean/length, neutral key names) — the Chrome bridge blocks token/auth-looking keys AND values.

## Why
Found the CA-province "no NAME field" root cause and the metrics-circles=conversions binding in minutes. This is the highest-leverage move for any live Klever map debugging and isn't yet in the ui-probe recipes.
