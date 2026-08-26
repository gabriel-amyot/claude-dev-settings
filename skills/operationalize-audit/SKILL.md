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
- [ ] **Description tax is measured and noted** — run `python3 ~/.claude/skill-proposals/skill_tax_scan.py`
- [ ] Any retired skills had their directories removed (not just emptied)

**Measure the tax, not the count.** A skill count is the wrong bloat signal. Skills are
progressively disclosed: only the name and description load at session start, the body loads
on invocation. So the standing cost is the sum of all descriptions, paid every session
regardless of use — 115 skills carried 43,385 characters, about 10,800 tokens per session.

A narrowly-scoped skill that fires only in niche scenarios is close to free and should not be
counted against a ceiling alongside a vague one that mis-fires weekly. Track two numbers:

| Signal | Meaning |
|---|---|
| Total description characters | The standing per-session tax |
| Generic-word density | Mis-fire risk. `ui-probe` is the most expensive single description (1,454 chars) but only 1.3% generic, so it fires precisely and earns its cost. `jira` at 17.5% generic is the shape that fires on situations it was not written for. |

Judge a proposal on its description cost and trigger precision. The old "under 100, alarm at
120" count ceiling was arbitrary and is retired (2026-08-18).

### Retirement Pass

Zero invocations is a candidate, not a verdict. Run both scanners and respect their exclusions:

```bash
python3 ~/.claude/skill-proposals/skill_usage_scan.py --days 90   # → USAGE-SCAN.md
python3 ~/.claude/skill-proposals/skill_refs_scan.py              # → RETIREMENT-CANDIDATES.md
```

Four false-negative classes, all found the hard way:

1. **Cron-invoked** — a launchd job runs outside any session and writes no transcript. `skill-evals` fires monthly from `com.harness.skill-evals-monthly`. Auto-excluded.
2. **Too new** — a skill under 30 days old cannot accumulate usage in a 90-day window. Auto-excluded.
3. **Referenced in prose** — `inbox-writer` was archived and restored because `skill-evals` names it as its escalation path. The scanner now matches emphasis markers, but re-check every archived skill for dangling references before committing.
4. **The work happens manually** — `cloudflare-pages` shows zero invocations while the work runs through raw `wrangler` commands. That is a trigger problem, not a dead skill. Search trigger phrases, not just the name.
