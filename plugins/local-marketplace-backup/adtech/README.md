# adtech

Advertising-vendor skills whose data feeds maps. **Vendors first, mapping second** —
these are advertising-domain tools, not generic map tooling, so they live here and
NOT in the portable `mapping` plugin. They compose WITH `mapping` for advertising use
cases (e.g. Klever proximity); a generic hiking/travel map never installs `adtech`.

See `project-management/documentation/architecture/mapping-ecosystem-design.md` for
the full layering.

## Skills

| Skill | Invocation | Status | What it does |
|---|---|---|---|
| `placer` | `adtech:placer` | ✅ merged + fully self-contained | Placer.ai foot-traffic. Modes: onboard / api-check / entity-match. Fully inlines the former `placer-onboarding` + `klever-placer-api` + `placer-entity-matcher` (deletable after Phase 3). |
| `goldfish` | `adtech:goldfish` | ✅ built (2026-06-03) | Goldfish DOOH inventory/planning. Modes: fetch (screen inventory by viewport, detail, lookups) / plan (availability by geography + buy-side campaigns/data-plans). Calls the REST API directly (OAuth MCP unnecessary). |

## Composition (proximity use case)
`mapping:geocode` → `klever-bq-store-lookup` → **`adtech:placer` entity-match** →
bridge table → live map. The cross-layer wiring (bridges, BQ tables, gaps) is
documented in the Klever Bibliothèque use-case page `onboard-advertiser-stores`.

## Migration status
- `placer` — merged into one multi-mode skill; shared API/BQ reference consolidated.
  The three source skills remain until Phase 3 (erase), then are removed.
- `goldfish` — built from the on-disk API spike (KTP-522 + KTP-748), re-verified live
  2026-06-03. REST-direct; mirrors `placer`'s shape (shared reference + modes + scripts + eval).
