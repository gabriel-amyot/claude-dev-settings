# Skill Proposal: transcript-knowledge-miner
Date: 2026-04-17
Source: Cost optimization session — harness self-management plan

## Trigger
Setting up automated harness self-improvement. Monthly scheduled run to mine historical transcripts for knowledge.

## Scope
Global (`~/.claude/`)

## Usefulness
High. Transcripts kept for 365 days are a knowledge goldmine. PreCompact hook only captures live sessions. This covers everything before the hook existed and sessions that never hit compaction.

## Create vs Update
Create new skill + companion scheduled agent.

## Draft Steps
1. Scan `~/.claude/projects/*/` for transcript dirs without a `.mined` sentinel
2. For each unprocessed session: extract decisions, corrections, procedures, gotchas
3. Write nuggets to `~/.claude/knowledge-capture/YYYY-MM-DD-HHmm-{slug}.md` (same format as PreCompact hook)
4. Propose repeatable procedures to `~/.claude/skill-proposals/`
5. Touch `.mined` sentinel so each transcript is processed only once
6. Schedule via `/schedule` skill: cron `0 3 1 * *` (1st of month, 3am)

## Dependency
`/schedule` plugin must be stable. Verify before building.

## Reference
`~/.claude/library/context/harness-self-management.md` — Idea A, full design and cadence.
