# Skill Proposal: sitrep (Situation Report)
Date: 2026-04-25
Source: Supervisr big-picture briefing session

## Trigger
"big picture", "what's happening", "sitrep", "situation report", "status of everything", "where are we"

## Scope
Global (works for any org, auto-scopes to current org via cwd resolution)

## Draft Steps
1. **Resolve org** from cwd using Organizations table
2. **Parallel fetch** (all independent, run concurrently):
   - Inbox: `general/user/inbox/critical/*.json` + `decisions/*.json` (open items only)
   - Active tickets: STATUS_SNAPSHOT.yaml for in-progress epics
   - Jira: `--org {resolved}` search for assigned + in-progress tickets
   - Strategic context: relevant project memories from MEMORY.md
3. **Synthesize** into three tiers:
   - CRITICAL (blocked on you, time-sensitive)
   - DECISIONS (queued, can answer in 5 min)
   - IN-FLIGHT (no action needed, awareness only)
4. **Propose next actions** with parallelization opportunities
5. **Never cross org boundaries** unless user explicitly requests it
