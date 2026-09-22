# Skill Proposal: batch-api-crawl-wrapper
Date: 2026-04-17
Source: Cost optimization session — harness self-management plan

## Trigger
Building or modifying sprint-crawl, night-crawl, or dev-crawl. Any long-running agent that doesn't need immediate results.

## Scope
Global (`~/.claude/scripts/` + skill updates for sprint-crawl, night-crawl, dev-crawl)

## Usefulness
High. 50% cost reduction on all overnight and background crawls. Gabriel runs ralph-loop multi-hour sessions regularly.

## Create vs Update
Create new `batch-wrap.sh` script. Update 3 existing skills to wire it in.

## Draft Steps
1. Build `~/.claude/scripts/batch-wrap.sh`: parse `--no-batch` flag, route to Batch API or direct exec
2. Batch path: serialize invocation → POST to Anthropic Batch API → poll with exponential backoff (max 4h) → pipe result
3. Print startup banner: "🔄 BATCH MODE — 50% cost. Results in 15min-2h. Skip with --no-batch"
4. Update `sprint-crawl` skill: default batch ON, document `--no-batch`
5. Update `night-crawl` skill: same (overnight = always batch)
6. Update `dev-crawl` skill: same, but note `--no-batch` recommended for interactive dev validation
7. Log mode + cost to `~/.claude/cost-log.jsonl` on completion

## Reference
`~/.claude/library/context/harness-self-management.md` — Idea C, full design and build order.
