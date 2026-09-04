# ADR-003: Theme field lives in the ledger only, not in handoff files

**Date:** 2026-05-29
**Status:** Accepted
**Context:** Session plugin v2.0 design grill

## Context

v2 adds a `theme` field to handoff entries for grouped display in `/pickup --list`. The field could live in the ledger entry, the handoff file frontmatter, or both.

## Decision

Theme lives in the ledger entry only. Handoff file frontmatter is unchanged.

## Rationale

1. **Pickup reads the ledger, not files.** The ledger-as-index design means list mode never opens individual handoff files. Theme in the file would require pickup to read every file for grouping, defeating the index pattern.
2. **Lean file format.** Handoff files are self-contained documents meant to be read by humans and future sessions. Adding a grouping tag that only serves the pickup list view adds noise to the file's purpose.
3. **Consistency with existing pattern.** The ledger already carries `ticket`, `status`, `source_session` as operational fields that don't need to be in the file to be useful. Theme is the same category.

## Tradeoff

If the ledger is ever rebuilt from files, theme data is lost. This is acceptable because:
- The ledger is the operational source of truth.
- File-based ledger rebuilds have never occurred and are not a planned recovery path.
- Theme is a convenience for display grouping, not a critical data field. Losing it degrades the pickup list view but doesn't break any workflow.

## Alternatives considered

- **Both ledger + file:** Dual-write, file wins on conflict. Same pattern as status. Rejected because it adds complexity for no practical benefit (pickup never reads files for listing).
- **File only:** Theme in frontmatter, pickup reads files. Rejected because it violates the ledger-as-index design and makes pickup slower with a large handoff backlog.
