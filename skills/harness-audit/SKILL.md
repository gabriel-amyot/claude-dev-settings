---
name: harness-audit
description: "Adversarial audit of the Claude Code harness: skills, agents, hooks, proposals, and processes. Detects drift (duplicates, org bleeding, sprawl, unused probation skills, stale proposals), identifies workflow gaps, and proposes improvements ranked by impact. Use this skill whenever the user mentions auditing skills, checking harness health, cleaning up their setup, reviewing skill sprawl, or asks 'am I using the right skills', 'audit my harness', 'harness health check', 'skill audit', 'clean up skills', 'check for drift'. Also trigger proactively when total skill count exceeds 100 or when /context-audit surfaces skill-related issues."
user_invocable: true
nav:
  bay: ops
  when: "Adversarial audit of skills, agents, hooks, proposals. Detects drift and sprawl."
  when_not: "Context engineering audit (use /context-audit). Wiki health (use /wiki-lint)."
---

# Harness Audit

Adversarial audit of the Claude Code harness. Two phases: tear-down (findings), then rebuild (proposals).

**Usage:** `/harness-audit [--org ORG] [--apply] [--quick]`

- `--org`: Scope to a specific org (klever, supervisr). Default: detect from cwd.
- `--apply`: After reporting, enter interactive fix mode (user approves each action).
- `--quick`: Skip gap analysis (faster, no memory reads). Drift + metrics only.

## Phase 1: Inventory (Parallel Recon)

Dispatch 3 Sonnet subagents simultaneously. Each returns a condensed summary (under 2K tokens).

### Subagent A: Skill & Agent Census

Scan `~/.claude/skills/*/SKILL.md` (global) and `<project>/.claude/skills/*/SKILL.md` (project-scoped) for the current org's project root. Also scan `~/.claude/agents/*.md`.

For each skill/agent, extract:
- Name, description (first line), `user_invocable` flag
- Org affinity (infer from description keywords: "Klever", "Supervisr", "Origin8", or "global")
- `probation` date from frontmatter (if present)
- Directory size (number of sub-files)

Return: JSON array of `{name, type, org, probation, file_count, description_snippet}`.

### Subagent B: Hook & Config Census

Read `~/.claude/settings.json`. For each hook event type, count entries. Flag any hook pointing to a script that doesn't exist on disk (`test -f`). Count enabled vs disabled plugins. Note any event types with 0 hooks (cleaned out).

Also check:
- `~/.claude/skill-proposals/` count and oldest file date
- `~/.claude/knowledge-capture/` count
- `~/.claude/skill-proposals/.last-audit` timestamp (days since last operationalize-audit)

Return: JSON with `{hooks_by_event, broken_hooks, plugin_counts, proposal_backlog, knowledge_backlog, days_since_audit}`.

### Subagent C: Workflow Pattern Extraction

Read `MEMORY.md` index file for the current project. Scan feedback memory entries (filenames matching `feedback_*.md`) for skill references, workflow mentions, and pain points. Read user memory entries for role/domain context.

Build a "workflow fingerprint": the top 10 activities this user does, based on feedback density and recency.

Return: JSON array of `{workflow, frequency_signal, skills_referenced, last_mentioned}`.

## Phase 2: Analysis (Orchestrator)

Combine all three subagent outputs. Run these checks:

### Drift Detection

| Check | How | Severity |
|-------|-----|----------|
| **Duplicates** | Skills with >60% trigger-word overlap in descriptions | HIGH |
| **Org bleeding** | Skill's org affinity doesn't match current project org | MEDIUM |
| **Sprawl** | Total global skills > 100 | MEDIUM |
| **Expired probation** | Skills with `probation` date in the past that were never invoked | HIGH |
| **Stale proposals** | Proposals older than 14 days | MEDIUM |
| **Broken hooks** | Hook scripts that don't exist on disk | CRITICAL |
| **Empty event types** | Hook events with 0 entries (leftover from cleanup) | LOW |
| **Orphan agents** | Agents with no corresponding skill or CLAUDE.md reference | LOW |
| **Missing nav:** | Skill exists but has no `nav:` frontmatter and no `harness-overrides.yaml` entry | LOW |

### Gap Analysis (skip if `--quick`)

Compare the workflow fingerprint against the skill inventory:

1. For each top-10 workflow, check if a skill exists with matching trigger words
2. Flag workflows that have no skill coverage (potential new skill)
3. Flag skills that match no workflow (potential retirement candidate)
4. Check if the user's On-Demand Context table in CLAUDE.md covers all documented satellite files

### Impact Ranking

Score each finding and gap:

- **CRITICAL** (broken functionality): broken hooks, skills that error on load
- **HIGH** (daily workflow impact): gaps in top-5 workflows, expired probation (skill bloat), duplicates causing misfires
- **MEDIUM** (weekly impact): org bleeding (wasted context tokens), sprawl, stale proposals
- **LOW** (housekeeping): empty events, orphan agents, cosmetic issues

## Phase 3: Report

Write report to stdout (not to disk, unless `--apply` mode saves actions taken).

### Report Structure

```markdown
# Harness Audit Report — YYYY-MM-DD

## Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Global skills | N | <100 | OK/WARN |
| Project skills | N | — | — |
| Agents | N | — | — |
| Hook entries | N | — | — |
| Broken hooks | N | 0 | OK/CRIT |
| Proposal backlog | N | <5 | OK/WARN |
| Days since audit | N | <7 | OK/WARN |
| Probation expired | N | 0 | OK/WARN |

## Findings (by severity)

### CRITICAL
[findings or "None"]

### HIGH
[findings with affected skill names, root cause, recommended action]

### MEDIUM
[findings]

### LOW
[findings]

## Gap Analysis

### Uncovered Workflows
[workflows with no skill, ranked by frequency]

### Unused Skills
[skills matching no workflow pattern, candidates for retirement]

## Proposals (ranked by impact)

| # | Action | Target | Impact | Effort |
|---|--------|--------|--------|--------|
| 1 | [verb] | [skill/hook/file] | HIGH | LOW |
| ... | | | | |
```

## Phase 4: Apply (only with `--apply` flag)

If `--apply` is passed, after the report, enter interactive mode:

For each proposal (highest impact first):
1. Present the action: what will change, what files are affected
2. Ask user: **apply**, **skip**, or **stop** (exit apply mode)
3. On apply: execute the action (move files, edit settings.json, remove directories)
4. Log each action taken

After all proposals processed (or user stops), print summary of actions taken.

Actions that are NEVER auto-applied (always require `--apply` + user confirmation):
- Deleting skill directories
- Modifying settings.json hooks
- Moving files between org scopes
- Editing SKILL.md frontmatter

## Scheduling

Run this skill:
- Monthly (add to sprint boundary checklist)
- When `/morning-primer` Subagent D reports harness health issues
- When the session-start proposal-backlog-check hook fires
- When total skill count feels "heavy" (slow skill matching, frequent misfires)

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `/operationalize-audit` | Reviews proposal backlog. Harness-audit detects the backlog; operationalize-audit processes it. |
| `/context-audit` | Reviews memory and library health. Harness-audit focuses on skills/hooks/agents. No overlap. |
| `/challenge` | Challenges specific work products. Harness-audit challenges the harness itself. |
| `skill-creator:skill-creator` | Builds new skills. Harness-audit identifies which skills to build. |
