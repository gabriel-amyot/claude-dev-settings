# Skill Proposal: sse-proxy-debugging
Date: 2026-05-29
Source: KTP-713 SSE regression debugging (3 iterations, 5 Dexter agents)

## Trigger
When debugging SSE/streaming responses through a Next.js proxy or similar multi-hop architecture. "SSE not streaming", "events arrive all at once", "no progress indicator".

## Scope
org (Klever, but pattern applies to any SSE-through-proxy setup)

## Draft Steps
1. Capture HAR, extract SSE events and response headers (Content-Type, Content-Encoding, Transfer-Encoding, X-Accel-Buffering)
2. Verify event data correctness (step names, types, content shapes) before investigating rendering
3. Check deployed code on correct branch (git show origin/dev, not local checkout)
4. Map the full network path: backend → proxy → LB → browser. Identify each hop.
5. Check GCP LB logs on CORRECT project (use DAC terraform to find the project, not aliases)
6. For React rendering: verify flushSync + setTimeout combo for buffered events
7. For Mapbox: verify tileset minzoom vs flyTo zoom, promoteId type, source-layer name
