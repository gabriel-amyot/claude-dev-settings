---
name: operationalize-audit
description: Review accumulated tribal knowledge captures and skill proposals. Pitch each to the user with context, explain how it enhances the harness, accept or dismiss.
nav:
  bay: ops
  when: "Review accumulated tribal knowledge captures and skill proposals. Accept or dismiss."
  when_not: "Extracting new knowledge (use /gab-operationalize). Batch building (use /batch-skill-pipeline)."
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

### Step 4: Classify Skill Proposals (Anti-Drift Gate)

Before presenting proposals to the user, classify each into a tier:

| Tier | Criteria | Action |
|------|----------|--------|
| **AUTO-REJECT** | Duplicate of existing skill (same trigger pattern), conflicts with CLAUDE.md rule, targets wrong org from current context | Delete proposal, log reason, report to user |
| **AUTO-ACCEPT** | Small (single SKILL.md, no sub-files), clear trigger pattern, non-conflicting, addresses a pattern seen 3+ times in session transcripts | Build with probation tag (see Step 4b) |
| **HUMAN REVIEW** | Ambiguous scope, large (multi-file), architectural impact, introduces new workflow pattern, or modifies existing skill | Present to user for decision |

**Classification procedure per proposal:**
1. Read the proposal file
2. Glob `~/.claude/skills/*/SKILL.md` and grep for overlapping trigger words. If >60% trigger overlap with an existing skill → AUTO-REJECT (duplicate)
3. Check if the proposal's org scope matches the current working directory org. If mismatch → flag but don't auto-reject (user may be doing cross-org work)
4. If the proposal is small, clear, and non-conflicting → AUTO-ACCEPT
5. Everything else → HUMAN REVIEW

### Step 4b: Probation Lifecycle (for AUTO-ACCEPT skills)

Skills built via AUTO-ACCEPT get a `probation` field in their SKILL.md frontmatter:

```yaml
---
name: my-new-skill
description: "..."
user_invocable: true
probation: "2026-06-08"  # 30 days from creation date
---
```

At the next `/operationalize-audit` or `/context-audit`:
- Check all skills with `probation` dates that have passed
- Grep session transcripts (last 30 days) for invocations of that skill name
- If **never invoked**: flag for retirement. Present to user: "Skill X was auto-accepted 30 days ago but never used. Retire?"
- If **invoked 1+ times**: remove the `probation` field (skill graduated to permanent)

This prevents skill accumulation without usage validation.

### Step 4c: Present to User

For AUTO-REJECT items: report what was rejected and why (one line each).

For AUTO-ACCEPT items: report what was built and note the probation date.

For HUMAN REVIEW items (one at a time):
1. **Pitch it:** what the skill would do, how often it would trigger, what time it saves
2. Ask user: **build** (invoke `/skill-creator:skill-creator`), **defer** (leave for next audit), **dismiss** (delete)
3. On build: hand off to `/skill-creator:skill-creator` with the proposal file as input

### Step 5: Update Last Audit Timestamp

```bash
touch ~/.claude/skill-proposals/.last-audit
```

This resets the session-start hook counter. The hook only nudges if the last audit was >7 days ago.

### Step 6: Summary

Report what was processed:
```
Promoted: N knowledge entries
Auto-rejected: N proposals (reasons)
Auto-accepted: N proposals (probation until YYYY-MM-DD)
User-approved: N proposals
Deferred: N items
Dismissed: N items
Remaining backlog: N items
Probation skills expiring soon: N
```

---

### Scheduling

The backlog is fed automatically by the PreCompact hook (`auto-operationalize-cmd.sh`). The SessionStart hook (`proposal-backlog-check.sh`) nudges when proposals > 5 and last audit > 7 days. Run this skill weekly or when nudged.

### Drift Prevention Checklist

Before closing the audit, verify:
- [ ] No two skills have >60% trigger overlap
- [ ] All probation skills from the previous audit cycle either graduated or were retired
- [ ] Total active skill count is noted (target: under 100, alarm at 120)
- [ ] Any retired skills had their directories removed (not just emptied)
