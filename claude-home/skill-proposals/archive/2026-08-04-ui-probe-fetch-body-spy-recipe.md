# Skill Proposal: ui-probe recipe — fetch body spy (payload-shape proof)
Date: 2026-08-04
Source: KTP-1039 dev validation (prove map requests carry no channels key)

## Trigger
During ui-probe validation, when the claim to verify is about REQUEST PAYLOAD SHAPE (a key
present/absent in a POST body) and `read_network_requests` cannot help (no body access, tracking
armed after page load, or in-memory store cache suppresses refetches).

## Scope
Update existing skill: `~/.claude/skills/ui-probe/references/recipes.md` (add as a numbered
recipe next to the DOM sampler and fiber reader). Not a new skill.

## Draft Steps
1. Arm the spy via javascript_tool: patch `window.fetch`, filter on the API path, record ONLY
   sanitized shape — `bodyKeys` (Object.keys of parsed body) and `has<Key>` booleans. Never raw
   strings (sensitive-value blocker + transcript hygiene).
2. Force fresh traffic: page reload kills both cache and spy, so reload FIRST, then arm, then
   drive the UI (advertiser/date selection). In-memory store caches skip refetches otherwise.
3. Read back `window.__probe` and report keys/booleans as the fact timeline.
4. Note in report: spy dies on navigation; re-arm after any navigate.
