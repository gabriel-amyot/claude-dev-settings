# Skill Proposal: context-audit
Status: BUILT (2026-04-21 — functional test: PARTIAL)
Date: 2026-04-03
Source: Context engineering audit session

## Trigger
Monthly or when token usage feels high. Also useful when onboarding a new org.

## Scope
Global (works across orgs)

## Draft Steps
1. Audit memory files: check for staleness (dates), duplication (vs CLAUDE.md), bloat (line count)
2. Audit library: check On-Demand Context table entries against actual files (dead link detection)
3. Audit MEMORY.md: verify index-only format (no inline prose blocks exceeding 3 lines)
4. Compare against reference org setup (optional, if --compare flag provided)
5. Report findings with severity (P0: dead links, P1: bloat, P2: staleness, P3: missing infrastructure)
6. Execute no-brainer fixes (delete duplicates, archive stale, extract inline blocks) on approval
