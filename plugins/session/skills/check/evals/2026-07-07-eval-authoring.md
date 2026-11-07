# session:check — Layer B eval authoring note

**Date:** 2026-07-07
**Layer:** B (behavioral, transcript-gradeable)
**Suite:** `evals/evals.json` — 3 evals
**Schema:** skill-creator `evals.json`
**Plugin:** `session@local` — SOURCE dir authoritative, synced to cache (see below).

## Paths

- **Source (authored here):** `/Users/gabrielamyot/.claude/plugins/local-marketplace/session/skills/check/evals/evals.json`
- **Cache (synced with `/bin/cp -f`):** `/Users/gabrielamyot/.claude/plugins/cache/local/session/1.0.0/skills/check/evals/evals.json`
- `diff -q` reports IDENTICAL. Plugin skills load from the cache copy, so the sync is required for the eval to be discoverable at runtime.

## What each eval covers

1. **`--close` with an unresolved OPEN branch** — asserts G0 (Teardown Confirmation) fires because an OPEN branch remained at close, and that Phase 1b offers only single-action choices (no composite "do it then close"). No capture/archive/ledger/branch-switch before explicit G0 confirm.
2. **Close on a handoff-origin session** — asserts pre-check reads `sessions/ledger.yaml`, detects handoff origin, and produces a **report-back** (Phase S-0.5), with capture-first (S-2) before teardown.
3. **Plain "where was I"** — asserts the intent tree is rendered with status symbols + summary, and NO close is performed (triage only; AskUserQuestion for the decision; CLOSE not recommended while OPEN nodes remain).

## Terminology anchored to SKILL.md

- **G0** = "Gate G0: Teardown Confirmation" (runs first in the Shutdown Sequence).
- **Report-back** = the `/report-back` skill auto-invoked at Phase S-0.5 for handoff-origin sessions.
- **Intent tree** symbols: ◉ DONE / ◎ OPEN / ⊘ ABANDONED / ⤴ HANDOFF / 🎫 TICKET.
- **Capture-first** = Phase S-2 (`gab-operationalize`) runs before any teardown.

## No contradictions found

The three evals map directly onto behaviors the SKILL.md promises (G0 gate, no composite option per the explicit "never bundle then-close" rule, report-back auto-invoke, non-destructive checkpoint on a plain check).
