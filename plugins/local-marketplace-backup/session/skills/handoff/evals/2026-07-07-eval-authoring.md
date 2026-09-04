# session:handoff — Layer B eval authoring note

**Date:** 2026-07-07
**Layer:** B (behavioral, transcript-gradeable)
**Suite:** `evals/evals.json` — 2 evals
**Schema:** skill-creator `evals.json`
**Plugin:** `session@local` — SOURCE dir authoritative, synced to cache (see below).

## Paths

- **Source (authored here):** `/Users/gabrielamyot/.claude/plugins/local-marketplace/session/skills/handoff/evals/evals.json`
- **Cache (synced with `/bin/cp -f`):** `/Users/gabrielamyot/.claude/plugins/cache/local/session/1.0.0/skills/handoff/evals/evals.json`
- `diff -q` reports IDENTICAL.

## What each eval covers

1. **Idempotent skip** — a handoff already exists for KTP-681 with status `awaiting_initiation`. Asserts the ledger is checked by `related_ticket` (exact match) BEFORE creating, the existing file is updated in place, and NO duplicate ledger entry is added. Match is by related_ticket, not source_session.
2. **Normal handoff** — no prior KTP-617 handoff. Asserts the session is located/force-created, the prompt file is written under `sessions/active/{slug}/prompts/` (never a bare `prompts/` path), frontmatter is correct (type: handoff, status: awaiting_initiation, related_ticket), a new ledger entry is added with version/modified bumped, and `autopilot: approved` is NOT set (no unattended authorization given).

## Terminology anchored to SKILL.md

- **Ledger** = `sessions/ledger.yaml`; handoffs live in its `handoffs:` section.
- **Idempotency key** = `related_ticket` exact string match, skipped when "none".
- **Force-create** = derive slug + write state.yaml/knowledge-manifest.yaml + prompts/ without asking, even if other unrelated sessions are active.
- **Autopilot opt-in** = only valid when the live user types it this turn; headless sessions never set it.

## No contradictions found

Both evals map directly onto SKILL.md's Idempotency and Autopilot-opt-in sections. The "never write to a bare `sessions/active/prompts/`" rule (legacy mode removed) is asserted in eval 2.
