# ADR-001: Keep check and close as a unified skill

**Date:** 2026-05-29
**Status:** Accepted
**Context:** Session plugin v2.0 design grill

## Context

The v2 plan proposed splitting check (681 lines) into two skills: `check` (assessment only) and `close` (shutdown only). The rationale was separation of concerns: check spans REFLECTION and DEATH lifecycle phases.

## Decision

Keep check as one skill. Do not create a separate `close` skill.

## Rationale

The split's speed advantage depended on `close` auto-generating handoff prompts without user interaction ("max 1 AskUserQuestion"). During the design grill, the auto-handoff premise was challenged:

1. **Context is almost always fresh.** With Opus 1M, compaction is essentially a non-issue. The "degraded context" scenario that justified lightweight auto-handoffs doesn't occur in practice.
2. **Auto-handoffs should use the real `/handoff` skill.** Shallow, auto-generated prompts would create confusion at pickup time. Using the real skill means each OPEN branch triggers interactive Q&A.
3. **With interactive handoffs, close becomes "check + guaranteed shutdown."** The only remaining difference is that check offers CONTINUE as a triage option while close always shuts down. That's a flag, not a skill boundary.

The triage bias (check "sells" close because it can execute it) is addressed separately via a hard rule in Phase 1e: OPEN nodes > 0 means CLOSE is never the recommended option.

## Alternatives considered

- **Full split (plan's proposal):** Two skills, close is fast with auto-handoffs. Rejected because auto-handoff quality is unacceptable with fresh context available.
- **Split with different scope:** Check does full assessment, close skips assessment. Rejected because the assessment IS the value, even when closing.

## Consequences

- Check stays at ~700 lines. Internal organization (clear section boundaries) manages complexity instead of skill boundaries.
- `--close` flag remains the fast path for sessions with zero OPEN branches.
- Future: if check grows past ~900 lines, revisit the split. The intent tree persistence and retroactive init logic are the growth vectors.
