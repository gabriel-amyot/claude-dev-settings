# Skill Proposal: ui-probe-mapbox-tile-debugging
Date: 2026-06-06
Source: lucid-tern session — Measurement Map tile 404 investigation

## Trigger
Debugging Mapbox tile load behavior on the Klever Measurement Map (or any Mapbox GL app) via ui-probe: "why are there 400/404 tile errors", "are tiles loading", "check tile status", "tileset health". Extends the existing ui-probe skill.

## Scope
org (Klever) — fold into ui-probe skill as a Mapbox-debugging reference.

## Why it's needed
The Chrome-MCP read_network_requests tracker and main-thread Resource Timing both MISS Mapbox .vector.pbf fetches (worker-side). Standard network inspection silently shows nothing, leading to wrong conclusions.

## Draft Steps
1. Acquire the Mapbox map via React fiber: querySelectorAll for first `__reactFiber$` node (NOT the .mapboxgl-map container — it has no fiber key), climb to root, DFS stateNode/memoizedProps/hook-chain for object with getZoom+getStyle+querySourceFeatures+on. Stash on window.__mref.
2. Health check (no network): read map.style._sourceCaches['other:<id>']._tiles[].state — all `loaded`, zero `errored` = healthy. Read live TileJSON via map.getSource(id).minzoom/maxzoom/tiles/vectorLayerIds.
3. Status check: map._requestManager.normalizeTileURL('mapbox://tiles/<acct>.<tileset>/<z>/<x>/<y>.vector.pbf') → real https URL; fetch(url,{mode:'cors'}) → status + byteLength. (Do NOT transformRequest a raw mapbox:// string — yields null origin.)
4. Interpret: 404 (28-byte body) = empty tile (benign, Mapbox records as loaded, no error event). 200 + application/x-protobuf = real tile. Overzoom above maxzoom = 200.
