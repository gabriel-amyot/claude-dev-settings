---
name: archive
description: Archive completed project tickets with intelligent promotion of architecture artifacts (ADRs, contracts) to global documentation. Use when user mentions archiving tickets, closing tickets, cleanup of completed work, or moving finished tickets. Handles the full workflow - scanning for unpromoted ADRs/contracts, merging to global docs, and moving to archive folder.
allowed-tools: Read, Glob, Bash, Edit, Write
---

# Archive Ticket Skill

Archive completed project tickets while intelligently promoting architecture artifacts to global documentation.

## When to use this Skill

Use this Skill when the user:
- Asks to "archive" a ticket (e.g., "archive MVP-001")
- Says "close ticket" or "move ticket to archive"
- Mentions "cleanup completed tickets"
- Wants to finalize a ticket and preserve its artifacts
- Combines with Jira skill for batch operations (e.g., "cleanup done Jira tickets")

## Available Commands

Use the Python script to interact with the archive system:

### Scan a ticket (dry-run)
```bash
python3 ~/.claude/skills/archive/archive_skill.py scan MVP-001
```
Returns JSON with:
- Ticket path and artifacts found (ADRs, contracts, meeting notes)
- Analysis of conflicts and issues
- Implementation plan status

### Archive a ticket
```bash
python3 ~/.claude/skills/archive/archive_skill.py archive MVP-001
```
Performs the full archive operation:
- Promotes ADRs to global documentation
- Promotes contracts to global documentation
- Moves ticket to archive with timestamp

### Dry-run archive
```bash
python3 ~/.claude/skills/archive/archive_skill.py archive MVP-001 --dry-run
```
Shows what would happen without actually moving files.

## Instructions

### Step 1: Scan the ticket first

Always start by scanning to understand what needs to be archived:

```bash
python3 ~/.claude/skills/archive/archive_skill.py scan MVP-001
```

The script will:
- Find the ticket automatically in project-management structure
- Scan for ADRs in `architecture/adr/`
- Scan for contracts in `architecture/contracts/`
- Check implementation plan for open tasks
- Detect numbering conflicts with global ADRs
- Identify new vs modified contracts

### Step 2: Report findings to user

Parse the JSON output and present it clearly:

```
Found artifacts to promote:

ADRs (2):
- 0005-use-firestore.md
  → Will copy to documentation/architecture/adr/
  ✓ No conflicts

Contracts (1):
- DATA_MODEL_AND_MAPPING.md
  → Modified (will merge with global)
  ⚠️  Review changes before promoting

Tasks:
- Implementation plan: ✓ All tasks complete
- Meeting notes: 8 files to archive
```

Ask user: "Ready to proceed with archival?"

### Step 3: Execute archival (after confirmation)

Run the archive command:

```bash
python3 ~/.claude/skills/archive/archive_skill.py archive MVP-001
```

The script automatically:
- Copies ADRs to global (renumbering if conflicts)
- Copies contracts to global (you may need to merge manually if conflicts)
- Moves entire ticket to `project-management/tickets/archive/MVP-001-{YYYYMMDD}/`

### Step 4: Handle manual tasks

After the script completes, you should:

1. **For modified contracts:** Read both versions and intelligently merge if needed
2. **Update DECISIONS_LOG:** Add entry to `documentation/architecture/DECISIONS_LOG.md`:
   ```markdown
   ## [DATE] - Ticket MVP-001 Closed
   **Promoted Artifacts:**
   - ADR-0005: Use Firestore for data storage
   - Updated DATA_MODEL_AND_MAPPING.md

   **Summary:** [Brief ticket description]
   ```
3. **Check git status:** Warn user if uncommitted changes

### Step 5: Confirm completion

Report to user:
```
✓ Ticket MVP-001 archived successfully

Promoted:
- 2 ADRs → documentation/architecture/adr/
- 1 contract → documentation/architecture/contracts/

Archived to: project-management/tickets/archive/MVP-001-20251128/

Next steps:
- Review merged contracts
- Update DECISIONS_LOG.md
- Commit changes
```

## Safety checks

Before archiving, verify:
1. ✓ IMPLEMENTATION_PLAN.md has no open tasks (or warn user)
2. ✓ All ADRs have proper frontmatter and status
3. ✓ No uncommitted git changes in ticket folder (warn user to commit first)
4. ✓ User confirmed promotion plan

## Examples

### Example 1: Simple archive
```
User: "Archive MVP-001"

You:
1. Read project-management/CLAUDE.md
2. Scan tickets/MVP-epic/MVP-001/
3. Find 1 ADR, no contracts
4. Report findings
5. After confirmation, copy ADR and move ticket
6. Report success
```

### Example 2: Archive with conflicts
```
User: "Close ticket MVP-001"

You:
1. Scan ticket
2. Find ADR-0005 but global already has ADR-0005
3. Report conflict: "ADR numbering conflict - will renumber to 0006"
4. User confirms
5. Copy as ADR-0006, move ticket
```

### Example 3: Batch operation with Jira
```
User: "Fetch Jira tickets and cleanup completed ones"

You:
1. Invoke jira skill → get list: [MVP-001: Done, MVP-002: Done]
2. Invoke archive skill for MVP-001
3. Invoke archive skill for MVP-002
4. Report summary of all archived tickets
```

## Integration with other skills

This Skill works well with:
- **jira skill**: Fetch completed tickets → archive them
- **git skills**: Check status before archiving, commit promotions

## Notes

- Archive location is always: `project-management/tickets/archive/{TICKET_ID}-{YYYYMMDD}/`
- Never delete ticket artifacts - always preserve in archive
- ADR numbering follows format: `XXXX-title.md` (4 digits)
- Always read CLAUDE.md first to understand project-specific rules
- If CLAUDE.md is missing, use GEMINI.md as fallback
