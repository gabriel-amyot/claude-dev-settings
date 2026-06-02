# Contract 9 — Retro (run eval + auto-improve)

The final phase. Runs on EVERY terminal outcome (success or halt/block), not just clean runs. Score
the run, capture red flags, and emit feedback so the NEXT run is better. This is the factory's
auto-improvement loop (migrated from v1).

You are given in your prompt: the ticket, the terminal status, the ticket folder, and a per-phase
trace (JSON) including each phase's soft `confidence`.

## Two scores, out of 100, every lost point accounted for

1. **task_confidence (0-100)** — "Is the TASK actually done and deployable?" Start at 100; for every
   deduction, record `{ points, reason }`. Deduct for: halts, partial/incomplete QA, infra-blocked
   execution, low per-phase confidence, unresolved review findings, skipped/stuck ACs.
2. **factory_fitness (0-100)** — "Did the FACTORY perform well on this task (would it handle similar
   work well next time)?" Deduct for: gates that fired late, prompt ambiguity that caused rework,
   schema/validation friction, brittle steps, anything that needed a workaround.

Every point below 100 on BOTH scores must appear in `deductions` with a concrete reason. No silent
gaps. (This is the v1 principle: account for each lost point.)

## Red flags

List concrete `red_flags` — small problems, near-misses, smells observed during the run (e.g. "QA
returned PASS with no test_ref", "implement retried 3x on Spring wiring", "concierge confidence 60 on
repo resolution"). These are the seeds of next-run improvements.

## Improvements (actionable, for the next run)

Propose `improvements` as `{ title, detail }` — specific, actionable changes to the workflow.js gates,
a contract's prompt, or a schema. Not vague ("be better") — concrete ("contract 6 should require a
test_ref before allowing PASS").

## Write two files

1. **Telemetry YAML** → `/Users/gabrielamyot/.claude/skills/dark-factory-v2/runs/run-<DATE>-<TICKET>.yaml`
   (use the date from the environment; if unknown, ask — do not invent). Include: run id, ticket,
   terminal status, per-phase status + confidence (from the trace), the two scores + deductions, red
   flags, improvements. Update `runs/INDEX.md` with a one-line entry if it exists.
2. **Next-run improvement handoff** → the current session's prompts folder
   (`~/Developer/grp-beklever-com/project-management/sessions/active/<current-session>/prompts/` — or
   if you cannot resolve the active session, write to the ticket folder under `reports/`). Title it
   `dark-factory-v2-improvements-<TICKET>.md`. Content: the red flags + the ranked improvements, framed
   as a prompt a future session can pick up to harden the factory. Keep it short and actionable.

## Return

- `task_confidence`, `factory_fitness`: integers 0-100
- `deductions`: array of `{ points, reason }` (covers both scores)
- `red_flags`: array of strings
- `improvements`: array of `{ title, detail }`
- `telemetry_written`, `handoff_written`: the paths you wrote
- `summary`: 1-2 sentences

This phase does NOT gate anything (yet). It is signal + memory. Future (roadmap): low scores could
trigger a retry, a divergent strategy, or trickle work back to an earlier phase.
