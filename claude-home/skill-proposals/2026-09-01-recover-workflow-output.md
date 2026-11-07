# Skill Proposal: recover-workflow-output
Date: 2026-09-01
Source: Local-Hermes tribal-knowledge audit session — lost a completed Workflow result to `/private/tmp` cleanup, recovered it from the run journal.

## Trigger
"recover workflow output", "the workflow result is gone", "restore a lost workflow/agent result",
"my `/private/tmp` output was cleaned", or any time a `Workflow` result needs to be persisted or
re-fetched after the fact. Also proactively: right after any long/expensive `Workflow` completes.

## Scope
Global (Claude Code harness behavior — not org-specific).

## Problem
The `Workflow` tool writes its return value to `/private/tmp/claude-501/<proj>/tasks/<taskid>.output`,
which the OS reaps within days. Long/expensive workflow results are silently lost if not persisted, and
the file's structure (return wrapped under a top-level `result` key) trips naive parsers.

## Draft Steps
1. **Persist-on-complete (preferred):** the moment a workflow finishes, `cp` the raw
   `/private/tmp/.../tasks/<taskid>.output` to a durable repo path BEFORE parsing anything.
2. **Parse correctly:** load JSON and read `data["result"]` (not the root); the root also carries
   `summary`, `agentCount`, `logs`. Extract the workflow's actual return fields from there.
3. **Recover a lost result:** if the `.output` is gone, read
   `~/.claude/projects/<proj>/subagents/workflows/<runId>/journal.jsonl` and pull the synthesis/last
   agent's cached result (search lines for the expected output keys); the workflow script itself is at
   `.../workflows/scripts/<name>-<runId>.js`.
4. **Write out deliverables** to their durable destinations (repo docs, INDEX, etc.); confirm sizes are
   non-trivial (a 1-byte file means you read the wrong JSON key — see step 2).

## Notes
Overlaps in spirit with `transcript-knowledge-miner`/`tribal-knowledge` but is distinct: this is about
**not losing** and **recovering** workflow/agent *results*, not mining conversations. Keep small; may be
better as a CLAUDE.md rule than a full skill — flag for triage.
