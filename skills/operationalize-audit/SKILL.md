---
name: operationalize-audit
description: Review accumulated tribal knowledge captures and skill proposals. Pitch each to the user with context, explain how it enhances the harness, accept or dismiss.
---

# Operationalize Audit

Review the backlog of auto-captured tribal knowledge and skill proposals. Pitch each one, explain its value, let the user decide.

**Usage:** `/operationalize-audit`

---

## Execution

### Step 1: Scan

Read `~/.claude/knowledge-capture/` and `~/.claude/skill-proposals/`. If both are empty, report "Nothing in the backlog" and exit.

### Step 2: Summarize

Group entries by date and org. Present a table:

```
| Date | Org | Nuggets | Skill Proposals | Topics |
|------|-----|---------|-----------------|--------|
```

### Step 3: Review Knowledge Entries

For each file in `~/.claude/knowledge-capture/`:
1. Read the file, show the nugget
2. Propose durability promotion:
   - High usefulness → CLAUDE.md rule or `~/.claude/library/context/`
   - Medium → project library (`documentation/library/`)
   - Low → keep as-is or dismiss
3. Ask user: **promote** (write to target), **keep** (leave in capture dir), **dismiss** (delete)
4. On promote: write to target, update INDEX.md, move original to `~/.claude/knowledge-capture/processed/`

### Step 4: Review Skill Proposals

For each file in `~/.claude/skill-proposals/`:
1. Read the proposal
2. **Pitch it:** explain what the skill would do, how often it would trigger, what time it saves, whether it's create or update
3. Check if a similar skill already exists (Glob `~/.claude/skills/*/SKILL.md` for related names)
4. Ask user: **build** (invoke `/skill-creator:skill-creator`), **defer** (leave for next audit), **dismiss** (delete)
5. On build: hand off to `/skill-creator:skill-creator` with the proposal file as input

### Step 5: Summary

Report what was processed:
```
Promoted: N knowledge entries
Built: N skills (or handed to skill-creator)
Deferred: N items
Dismissed: N items
Remaining backlog: N items
```

---

> **Tip:** Run this daily or weekly. The auto-operationalize hooks on Stop and PreCompact feed this backlog automatically.
