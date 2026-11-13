---
name: ticket-cross-linker
description: "Refresh bidirectional wikilinks and Linked Items sections across an epic's ticket README and INDEX files. Detects orphan tickets, Jira-vs-folder mismatches, and missing cross-references. Use when user says 'cross-link tickets', 'refresh ticket links', 'link the tickets', 'add wikilinks to epic', or after /epic-reorganization completes."
user_invocable: true
---

# Ticket Cross-Linker

Refreshes `## Linked Items` sections in ticket README.md files and `## Children` / `## Related Epics` sections in epic INDEX.md files. Ensures bidirectional link integrity across the ticket tree.

## Usage

```
/ticket-cross-linker KTP-558              # Single epic
/ticket-cross-linker KTP-558 KTP-559      # Multiple epics
/ticket-cross-linker --all                 # All active epics
```

## Execution

### Phase 1: Gather Sources

For each epic key provided:

1. **Jira:** Fetch children via `/jira` skill (`get-issue {EPIC-KEY}` for child list)
2. **Disk:** Glob `tickets/KTP/{EPIC-KEY}/*/README.md` for on-disk tickets
3. **INDEX.md:** Read `tickets/KTP/{EPIC-KEY}/INDEX.md` for currently listed children

Build three sets per epic: `jira_children`, `disk_children`, `index_children`.

### Phase 2: Detect Mismatches

Compare the three sets. Flag:

| Finding | Meaning | Action |
|---------|---------|--------|
| In Jira, not on disk | Ticket exists in Jira but has no folder | Report as "missing folder" |
| On disk, not in Jira | Folder exists but ticket not a child of this epic in Jira | Report as "orphan folder" (may have been moved) |
| In INDEX, not in Jira | INDEX.md lists a ticket that Jira says belongs elsewhere | Report as "stale INDEX entry" |
| In Jira, not in INDEX | Jira child missing from INDEX.md | Add to INDEX.md |

Present mismatch report before proceeding. Do not auto-fix orphans or stale entries without confirmation.

### Phase 3: Update Linked Items (Parallel)

Dispatch parallel Sonnet agents (one per epic) to update ticket files.

**For each ticket README.md:**

Read the file. If `## Linked Items` section exists, update it. If not, add it after the ticket description header.

**Link type taxonomy:**

```markdown
## Linked Items

- **Epic:** [[KTP-558]] (Measurement Map Refinements)
- **Blocks:** [[KTP-XXX]] (reason)
- **Blocked by:** [[KTP-XXX]] (reason)
- **Related:** [[KTP-XXX]] (brief explanation of relationship)
- **Depends on:** [[KTP-XXX]] (must complete before this ticket)
- **Informed by:** [[KTP-XXX]] (findings from this ticket shaped the approach)
- **Supersedes:** [[KTP-XXX]] (this ticket replaces the older one)
- **Split from:** [[KTP-XXX]] (originated from a larger ticket)
```

**Rules for agents:**
- Preserve existing manually-written links. Only add missing ones.
- The `**Epic:**` link is always present and always matches the Jira parent.
- `**Related:**` links come from Jira issue links and from shared file references (two tickets modifying the same source file).
- Always include a parenthetical explanation. Never write a bare `[[KTP-XXX]]` link.
- Use the Edit tool to surgically update the section. Do not rewrite the full file.

**For each epic INDEX.md:**

Update the `## Children` list to match Jira. Preserve the status suffix format:
```
- [[KTP-582]] — Rename Proximity feature to Measurement — **TO DO**
```

Update `## Related Epics` if cross-epic links exist.
Update `## Tickets moved OUT` if tickets were re-parented.

### Phase 4: Verification

After all agents complete:

1. **Bidirectional check:** For every `**Related:**` or `**Blocks/Blocked by:**` link in ticket A pointing to ticket B, verify ticket B has a reciprocal link back to A. If not, add it.
2. **Orphan scan:** Grep all README.md files under the target epics for `[[KTP-` references. Verify each referenced ticket exists on disk. Report broken links.
3. **Summary report:**

```
Cross-Link Report for {epic(s)}
════════════════════════════════
  Updated:  {N} ticket README.md files
  Added:    {N} new Linked Items sections
  Fixed:    {N} missing reciprocal links
  Orphans:  {N} broken [[KTP-XXX]] references
  Mismatches: {N} Jira-vs-folder discrepancies

  Files modified: {list}
```

## Integration Points

- **Post `/epic-reorganization`:** Run automatically after epic reorg to fix links broken by moves.
- **`/wiki-lint` detection:** When wiki-lint reports missing cross-references, suggest running this skill.
- **Sprint boundaries:** Run at sprint start/close to ensure link integrity.
