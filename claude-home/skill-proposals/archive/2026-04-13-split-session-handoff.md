# Skill Proposal: split-session-handoff

Date: 2026-04-13
Source: SPV-3 Team 1 / Team 2 session fork (2026-04-10 session)
Status: proposal, not yet implemented

## Trigger

User wants to fork work into a fresh session while the current session stays alive for something else. Phrases:
- "start a fresh session for X"
- "give me the prompt to kick this off in a new terminal"
- "split the work, I'll run the other part separately"
- "you do X in parallel while I focus on Y"
- "I want to pick this up in a new session"

## Scope

Global (`~/.claude/skills/split-session-handoff/`). Repo-agnostic.

## Problem it solves

When a session needs to fork, the quality of the handoff determines whether the fresh session can execute without re-learning everything. Ad-hoc handoffs typically forget:
- Hard guardrails (the fresh session doesn't inherit them)
- Known facts discovered in the source session (stale snapshots, deployment state)
- Coordination rules (Team A owns X, Team B doesn't touch X)
- Reading order for on-disk context
- The data-on-disk rule for the source session's prior findings
- The "don't ask the user questions" directive when the user is offline

A skill codifies the handoff brief structure so forks are reliably self-contained.

## Draft structure

```
~/.claude/skills/split-session-handoff/
├── SKILL.md
├── templates/
│   ├── brief.md.tmpl            # mission brief template
│   ├── kickoff-prompt.md.tmpl   # fresh-session kickoff prompt template
│   └── coordination-index.md.tmpl  # multi-team INDEX with ownership rules
├── references/
│   └── handoff-checklist.md     # things every handoff must include
```

## Draft steps (when skill is invoked)

1. **Interview** the user for: mission name, scope in-bounds, scope out-of-bounds (parking list), target ticket folder, parallel-work constraints (who owns what).
2. **Gather known facts** from the current session's conversation: stale snapshots, discovered blockers, actual deployment tags, open PRs, error signatures. These go in a "Known facts" section so the fresh session doesn't re-discover.
3. **Write brief** to `tickets/{ID}/handoffs/{team-name}-brief-YYYY-MM-DD.md` using the template. Must contain: mission, guardrails, required reading, parallel-work coordination rules, output format, return format.
4. **Write INDEX.md** with ownership rules if multiple teams are running in parallel (Team A owns PR X, Team B owns script Y).
5. **Return the fresh-session kickoff prompt** as plain text for the user to paste. Prompt must reference the brief path and include "read these in order" instructions.
6. **Log** the handoff in the current session so coordination rules are visible if both sessions converge later.

## Handoff checklist (required in every brief)

- [ ] Mission in one sentence
- [ ] Hard guardrails (DEV-only, no IAM, no external posts, no spec edits, no history rewrites — copy from template)
- [ ] Required reading list in order (global CLAUDE.md, project CLAUDE.md, MEMORY.md, ticket STATUS_SNAPSHOT, prior reports)
- [ ] Known facts section (stale snapshots, discovered blockers, deployment state corrections)
- [ ] Output location on disk (explicit folder)
- [ ] Return format (max word count, required fields)
- [ ] Coordination rules if parallel work exists
- [ ] "Do not ask user questions" directive if user is offline
- [ ] Data-on-disk rule reminder

## Non-goals

- Does not replace `ticket-init` (which scaffolds new tickets). Split-session-handoff is for mid-mission forks, not new ticket creation.
- Does not execute the forked work. The skill only scaffolds the handoff brief + kickoff prompt.
- Does not auto-orchestrate multiple sessions. Coordination is via disk, not IPC.

## Related artifacts from source session

- `tickets/SPV-3/handoffs/team1-brief-2026-04-10.md`
- `tickets/SPV-3/handoffs/team2-brief-2026-04-10.md`
- `tickets/SPV-3/handoffs/INDEX.md`
- `tickets/SPV-92/overnight-2026-04-10/` (overlaps with overnight-mission skill but the brief structure is reusable)

## Open questions

- Should the skill use a different name like `fork-session` or `handoff-brief`? "split-session-handoff" is explicit but long.
- Is there overlap with `overnight-mission`? Overnight is a specialization of handoff (single user, fire-and-forget, offline). This skill is more general (could be forking to a parallel user, a contractor, a scheduled agent).
