# Skill Proposal: vendor-api-ingest
Date: 2026-04-23
Source: KTP-130 Placer API documentation session

## Trigger
When the user provides a list of vendor API documentation URLs and wants them fetched, stored, indexed, and analyzed. "Download the API docs", "ingest the vendor docs", "save these API pages".

## Scope
org (Klever project-management, could generalize to global)

## Draft Steps
1. Parse URL list, group by category (endpoints, reference, account)
2. Create `bibliotheque/vendors/{vendor}/api/` directory
3. Parallel-fetch all URLs via WebFetch (batch by category for parallelism)
4. Promote reference pages (glossary, FAQ, error codes) to vendor level (above api/)
5. Create `api/INDEX.md` (endpoint catalog with method, path, purpose, custom POI support)
6. Create `CLAUDE.md` at vendor level (usage guide: auth, endpoint selection, constraints)
7. Create `api-summary.md` (capabilities overview, what the API can/cannot do)
8. Create `INDEX.md` at vendor level (catalog of all docs + key findings)
9. Update bibliotheque root INDEX.md with new vendor entry
10. If ticket context exists: write comparison report at ticket level (new vs prior research, delta analysis)

## Notes
- WebFetch can't render JS-heavy pages. Flag partial fetches.
- Goldfish showed that some vendor docs require login. Skill should handle gracefully (consolidate from spike/email/contract instead).
- Pattern: raw docs in `api/`, distilled reference at vendor level, ticket-specific analysis in ticket `reports/architecture/`.
