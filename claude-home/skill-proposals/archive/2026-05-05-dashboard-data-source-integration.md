# Skill Proposal: dashboard-data-source-integration
Date: 2026-05-05
Source: Housekeeper integration into mission-control session

## Trigger
When user says "add X to mission control", "integrate X into the dashboard", "I want to see X in mission control", or when a new local data source (SQLite DB, JSON API, filesystem) should be surfaced in the dashboard.

## Scope
repo-local (mission-control-dashboard)

## Draft Steps
1. **Discover data shape**: Read the source (SQLite schema, API response, filesystem structure). Identify key entities and their cardinality.
2. **Create backend router**: `routers/{source}.py` with read-only endpoints. Follow existing patterns (PRAGMA query_only for SQLite, env var + fallback path, Pydantic models for mutations).
3. **Create frontend component**: Tab component following design system tokens (bg-slate-deck, typo-title, etc.). Start minimal (stat cards + one data table), let user iterate.
4. **Wire into MetaTab or OrgTab**: Add to META_TABS array with icon, import and render. If org-scoped, add to org-level tab routing instead.
5. **Verify**: Run vite build, test backend endpoint access, confirm data renders.

## Notes
Pattern validated with housekeeper integration. The scaffold-then-iterate approach works well. Start with 4-5 endpoints and a single-file component. User will expand into sub-tabs if needed.
