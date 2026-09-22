# Skill Proposal: session-close-hook
Date: 2026-04-03 (merged 2026-04-12)
Source: Context engineering audit session; merged from auto-operationalize-hook + session-context-check

## Trigger
Settings.json hook that fires on session end or context compaction. Runs two passes: knowledge mining (what did we learn?) and structural validation (did we maintain context hygiene?).

## Scope
Global (all projects, all orgs)

## Type
**This is a hook, not a skill.** Implemented via `settings.json` hook configuration, not a slash command. The hook calls a lightweight script that runs async/background (must NOT block session close).

## Pass 1: Knowledge Mining (formerly auto-operationalize-hook)
1. Mine conversation summary for: procedures discovered, rules learned, gotchas encountered, decisions made
2. Extract as `[KNOWLEDGE]` and `[+SKILL]` nuggets (same taxonomy as `/gab-operationalize`)
3. Write findings to staging: `~/.claude/operationalize-queue/{date}-{session-hash}.md`
4. Do NOT write to permanent knowledge targets — those require interactive review

## Pass 2: Structural Validation (formerly session-context-check)
1. Collect list of files created/modified during session (tool call history or git diff)
2. For each new file: verify nearest INDEX.md was updated
3. For each modified CLAUDE.md: verify no On-Demand Context dead links introduced
4. Check MEMORY.md: verify still index-only format (no inline prose > 3 lines)
5. Check library CATALOG.md: any new library files should be cataloged
6. Write findings to staging: `~/.claude/session-audit-queue/{date}-{session-hash}.md`

## Next-Session Review Prompt
At session start, if either queue has items:
- Knowledge queue: "N learnings from previous sessions. Review now via /gab-operationalize?"
- Audit queue: "N structural issues from previous session. Auto-fix?"

Queue files are ephemeral — processed then deleted.

## Implementation Notes
- Must be a settings.json hook (event-driven), not a slash command
- Should NOT block session close (async/background execution)
- Lightweight: mining uses conversation summary only, validation uses file-change list only
- Failure should not crash session close (silent fail + log)
- Pairs with `/gab-operationalize` for Phase 2 routing on next session start

## Why Merge the Two Originals
Both proposals targeted the same event (session-end hook) and same scope (global). Splitting them into two hooks doubles the hook registration overhead and creates coordination complexity. Single hook with two passes is simpler and shares the file-change enumeration work.
