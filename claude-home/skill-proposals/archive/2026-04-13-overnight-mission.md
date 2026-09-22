# Skill Proposal: overnight-mission

Date: 2026-04-13
Source: SPV-92 Clarifying reconciliation overnight mission (2026-04-10 → 2026-04-13 session)
Status: proposal, not yet implemented

## Trigger

User signals they want a long-running autonomous mission to run while they are offline. Phrases to catch:
- "run this overnight"
- "spend the night doing X"
- "do this while I sleep"
- "I'm going offline, I need X by morning"
- "autonomous execution until Y"
- Multi-step mission with a hard morning deadline

## Scope

Global (`~/.claude/skills/overnight-mission/`). Applicable to any repo or project because the pattern is independent of service/tech stack.

## Problem it solves

Today, the ad-hoc overnight pattern requires Claude to manually scaffold: briefs on disk, hard guardrails copy-paste, parallel investigation tracks, a GREEN_LIGHT/BLOCKER synthesis gate, checkpointed execution steps, and a ralph-loop wrapper. Every time, from scratch. The scaffolding alone burns 20-30k tokens and users forget to include critical pieces (deployment authorization scope, data-on-disk rule, idempotence checks).

A skill codifies the pattern so any autonomous overnight mission gets:
1. Two-phase brief structure (Alpha investigate + Bravo execute)
2. Disk-gated handoff between phases (GREEN_LIGHT.md / BLOCKER.md files)
3. Ralph-loop completion promise automatically derived from the phase structure
4. Standard hard guardrails section reused across briefs
5. Checkpoint files per execution step for resumability across context boundaries
6. Fail-loud-fail-specific template for when things break

## Draft structure

```
~/.claude/skills/overnight-mission/
├── SKILL.md                    # trigger, behavior, invocation
├── templates/
│   ├── brief-alpha.md.tmpl     # investigate & unblock phase
│   ├── brief-bravo.md.tmpl     # execute phase
│   ├── index.md.tmpl           # mission INDEX with ralph-loop promise
│   └── hard-guardrails.md      # reusable guardrails block
├── references/
│   ├── kickoff-prompt.md       # the fresh-session kickoff template
│   └── failure-modes.md        # common blocker patterns + triage
```

## Draft steps (when skill is invoked)

1. **Interview** the user for: mission name, ticket ID, morning deadline, scope in-bounds, scope out-of-bounds, authorization for dev deploys yes/no, destructive op authorization yes/no.
2. **Scaffold** `tickets/{ID}/overnight-YYYY-MM-DD/` with INDEX.md + BRIEF-ALPHA + BRIEF-BRAVO pre-filled from templates.
3. **Inject** known facts: current repo paths, deployed tags (via gcloud), open PRs, stale STATUS_SNAPSHOT corrections, so the fresh-session agent doesn't re-discover.
4. **Pre-flight** checks: gcloud auth, gh auth, any required tokens/env files, target repo cleanliness.
5. **Output** the fresh-session kickoff prompt + the ralph-loop wrap command. User pastes into a fresh terminal.
6. **Coordination file**: if other parallel work is in flight (Team 1 / Team 2 pattern), add explicit ownership rules to the INDEX so sessions don't collide.

## Non-goals

- Does not execute the mission itself. The skill only scaffolds. Execution happens in the fresh session.
- Does not decide scope. User retains scope authority.
- Does not replace `/sprint-crawl` — that's for a single ticket's AC execution. Overnight-mission is for multi-phase investigate-then-execute work that doesn't map to a single ticket's ACs.

## Related artifacts from source session

- `tickets/SPV-92/overnight-2026-04-10/BRIEF-ALPHA-investigate-and-unblock.md`
- `tickets/SPV-92/overnight-2026-04-10/BRIEF-BRAVO-cleanup-and-reconcile.md`
- `tickets/SPV-92/overnight-2026-04-10/INDEX.md`

These three files are the reference implementation. Extract templates from them.

## Open questions

- Should the skill auto-wrap in `/loop` or leave that to the user? Default: leave to user, provide copy-paste command.
- Should Brief Alpha's investigation tracks be configurable, or is the 6-track pattern (deployment / e2e smoke / dashboard path / auth / toolkit / workaround) generic enough to hard-code?
- Does the skill need a cancellation/rollback protocol for when the user wakes up and wants to abort a partially-executed mission?
