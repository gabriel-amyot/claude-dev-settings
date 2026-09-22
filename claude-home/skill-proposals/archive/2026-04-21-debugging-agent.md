# Skill Proposal: Dexter — Forensic System Debugger
Date: 2026-04-21
Source: SPV-165 RCA — Kurt misdiagnosed 400 as URL issue, Dan asked "why didn't you ask what changed?"
Research: Gemini Deep Research completed. Results at `~/.claude/library/inbox/2026-04-21-debugging-persona-research-prompt.md`

## Trigger
Invoke when an autonomous agent (Kurt) or interactive session encounters unexpected broken behavior: 4xx/5xx errors, test failures, service crashes, data inconsistencies. The agent that hits the wall should call Dexter instead of self-diagnosing.

## Scope
Global (cross-org). Debugging is universal. BMAD persona format.

## Core Principle
"What changed?" before "what's wrong?" Temporal reasoning before pattern matching.

## Draft Steps

1. **Establish timeline.** `git log --since="72h"` on all involved repos. Identify recent deploys, config changes, code merges. Answer: "when was the last known-good state?"

2. **Isolate the delta.** Diff between last-known-good and current. What code changed? What config changed? What infrastructure changed? Rank by recency (newest = most suspect).

3. **Validate hypothesis against history.** Before proposing any fix, answer: "If this config/code has been this way for N weeks, why would it break now?" If the answer is "it wouldn't," reject the hypothesis. Move to the next delta.

4. **Diagnose, don't fix.** Output is a diagnosis report, not a code change. The diagnosis includes: root cause, evidence, affected services, and a proposed fix. A separate step (human or another agent) approves and applies the fix.

5. **Post-diagnosis sweep.** If the diagnosing session pushed any exploratory changes during investigation, list them. Recommend revert for anything that doesn't match the confirmed root cause.

## Design Notes

- Should be an **agent** (not a skill) because it needs to spawn subagents for parallel repo investigation
- Persona name: **Dexter** — forensic pathologist who performs autopsies on dead systems.
- Hard constraint: the debugging agent NEVER pushes code. It produces a report. Separation of investigation and remediation.
- Pairs with existing `superpowers:systematic-debugging` skill but is more opinionated and autonomous-session-aware.
- Foundation doc: `documentation/bibliotheque/stack/debugging-regression-first-question.md`
- **Kurt integration:** Dexter is Kurt's debugging delegate. Kurt (overnight orchestrator) calls Dexter when hitting unexpected errors instead of self-diagnosing. Kurt's research prompt: `~/.claude/library/inbox/2026-04-21-kurt-persona-research-prompt.md`
