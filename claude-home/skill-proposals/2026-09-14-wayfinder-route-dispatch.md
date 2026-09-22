# Skill Proposal: wayfinder-route-dispatch
Date: 2026-09-14
Source: autonomous wayfinder run across four maps (14 tickets resolved via dispatched Opus subagents)

## Trigger
An orchestrator (or Gabriel) wants a subagent to work one wayfinder ticket. The wayfinder skill itself is `disable-model-invocation`, so every dispatch today hand-wrote the same ~20-line relayed procedure — six times, with drift risk each time.

## Scope
Global (`~/.claude/skills/`), since wayfinder maps span orgs via gabriel-amyot/klever-project-management.

## Draft Steps
1. Emit a canned dispatch prompt template for one ticket: claim first (`--add-assignee @me`), read map body + recent comments (report-backs), zoom closed tickets on demand.
2. Bake in the mechanics the skill would have provided: `wayfinder_runs.py resolve` direct invocation (skill is gated for subagents), the `wayfinder:` label pre-check (resolve refuses unlabeled tickets), friction-tag vocabulary, outcome semantics (resolved/partial/horizon/out_of_scope).
3. Bake in the concurrency discipline: fetch-patch-verify guarded map append (marker appears exactly once, idempotence check, verify survivors), expect concurrent editors.
4. Bake in session-day constraints as slots: Jira read-only vs staged actions, external-post policy, codex prompt-size rule (never a whole document), model choice.
5. On agent completion, verify the run trailer landed (`mode: resolve`, outcome) and the map gist appended — the two writes the telemetry needs.

## Notes
The verify-and-skip etiquette for orchestrator races (idle pings vs completion reports) belongs in the same template's "on re-issued work" clause.
