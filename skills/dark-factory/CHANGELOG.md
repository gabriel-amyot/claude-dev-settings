# Dark Factory v2 — Changelog

Every SKILL.md / workflow.js / contract change bumps the version and adds an entry.

## 0.6.0 (2026-06-03)

**Bounded fix loop — per-AC resilience harvested from v1 + sprint-crawl.**

Before: a review CRITICAL terminated the run (`BLOCKED_REVIEW_CRITICAL`) on the first pass. Now the
workflow bounces back to a targeted fix and re-reviews, up to 2 rounds, before halting. This brings v2
in line with v1's "Quinn attacks → Amelia fixes" loop and sprint-crawl's review→implement revert,
without breaking the segregated-review or ADR-002 spine boundaries.

- New `Fix` phase in the workflow + meta: on `review.criticals_open > 0`, dispatch a fix agent
  (`readContract('4-implement')` in FIX MODE) scoped to ONLY the open CRITICAL findings — no new scope,
  no unrelated refactors — in its own worktree; it fixes, re-runs affected tests, and pushes the branch.
  A fresh segregated reviewer then re-reviews the updated branch.
- Bounded at `MAX_FIX_ROUNDS = 2`. A CRITICAL that survives both rounds still returns
  `BLOCKED_REVIEW_CRITICAL` (now carrying `fix_rounds`). A round that fails to push returns the new
  `HALT_FIX_NOT_PUSHED`.
- Review prompt factored into a reused `reviewPrompt` const (identical fresh reviewer each round; the
  branch differs because the fix pushed). `node --check` clean.
- Design context: harvested from the sprint-crawl analysis (`docs/harvest-from-sprint-crawl.md`). The
  full per-AC restructure (iterate implement→review→QA per AC with persisted per-AC verdicts) remains a
  roadmap item; this is the spine-safe increment.

## 0.5.0 (2026-06-03)

**Hardened from the first live trial (KTP-728 + KTP-699 retros). Front gate's relationship to truth is
the headline — see `docs/hardening-spec-0.5.0.md` and ADR-003.**

The trial proved the JS gates work (`HALT_PRESHIP`, `BLOCKED_SPEC_QUALITY` both fired correctly). The
dominant cost was upstream: a concierge **false data-layer blocker** from a stale local checkout (two
abandoned runs) — a reasoning/staleness failure the substrate cannot catch. 0.5.0 fixes that, and
promotes two patterns flagged in BOTH retros (schema preflight; structured findings). Built blind —
generic rules only, no KTP-728/699 specifics in the spine or shared contracts (ADR-002 boundary holds).

- **Concierge live-verifies every data-layer claim (ADR-003)** [contract 1]: any blocker asserting a
  table/view/column/count/serving-path is verified live (`bq show --schema`/`bq ls`/`bq query`;
  `git show origin/dev:<path>`) before it is emitted; a stale local tree is not evidence. Every blocker
  carries a one-line assumption audit. No live access → mark `unverified` + flag, never assert.
- **Live-schema preflight** [contract 1 writes → contract 2 reads]: concierge pins exact column
  count + names into `analyst/assumptions.json` marked `VERIFIED`; design reads those rather than
  re-deriving from a checkout. Kills the F4 "no COUNTRY column" / "22-vs-20 columns" errors.
- **New brand ⇒ new advertiser id** [contract 1]: a fabricated/new brand must not reuse an existing
  demo-advertiser entity; the id must be unused in BOTH the perf tables AND the demo-agency registry.
- **Backend-gated sub-ACs flagged/split at the gate** [contract 1]: a sub-criterion depending on
  un-landed backend work is named as deferred (or the AC is split) at the concierge, not discovered at
  HALT_PRESHIP.
- **Structured artifacts on disk** [contracts 5 + 6]: review writes `review/findings.json` on every run
  (even at `criticals:0`); QA writes `qa/result.yaml` with a real `test_ref` (command + output path).
  A PARTIAL is now auditable without re-deriving from a raw diff.
- **Resume path fixed** [workflow.js + SKILL.md]: on `resumeFromRunId` with `humanDecisions`, the
  decisions are folded into the concierge prompt — busting the resume cache so the concierge **re-runs
  live** and re-reads the ticket, instead of replaying its stale needs_human verdict.
  `BLOCKED_NEEDS_HUMAN_AGAIN` now means a genuinely new/unanswered blocker remains.
- **Bucketed ticket-folder guard** [contract 1]: `ticket_folder` must resolve under
  `<PM_ROOT>/tickets/<PREFIX>/<EPIC-or-no-epic>/<TICKET>/` and never the PM root; stop and fix if it
  would land at root or a non-`tickets/` child.
- SKILL.md version → 0.5.0; references ADR-003 + the hardening spec. `node --check` clean.

## 0.4.1 (2026-06-02)

**Stack-agnostic hardening — no Java or ticket specifics in the factory itself.**

- Removed all Java/Spring/Maven specifics from the spine (concierge prompt) and the shared contracts
  (1 concierge, 2 design, 6 QA, 7 ship, 8 validate, 9 retro). They now defer to the run's tool belt.
  Java build/test/execute tooling lives only in `toolcrib/java.md` (multi-module Maven note moved there).
- Concierge now **discovers** belts by reading the new `toolcrib/INDEX.md` + each belt's `detect` rule,
  instead of the spine naming/​describing belts.
- Removed every KTP-728 mention from the operational files (spine, contracts, toolcrib, SKILL, CHANGELOG).
  Only `docs/` (the design archive that documents the build-blind rule) retains historical references.
- Belt ids (`java`, `scripting`) remain named in the registry/catalog — that's the rack's contents, not
  stack logic in a shared room.

## 0.4.0 (2026-06-02)

**Multi-work-type via tool belts (ADR-002). Scripting floor added so the factory can run side-effect
script tickets, not just Java services.**

Triggered by the first live trial (a scripting ticket): it halted honestly at the concierge
because validation was hardwired to `mvn spring-boot:run`. That halt = the anti-fake design working.

- ADR-002: one **blueprint** (the spine) + swappable **tool belts** from a **tool crib**, NOT
  duplicated floors. Corrected vocabulary against the Minions source (blueprint = the state machine;
  tool crib = curated tools per task). Concierge stays; dispatcher + spec/architect-persona loop
  parked to the refining phase (`docs/second-floor-refining-notes.md`).
- `toolcrib/java.md` + `toolcrib/scripting.md`: per-work-type build/tester loadouts.
- Concierge (contract 1 + schema) classifies the work-type and returns `tool_belt`; workflow halts
  `BLOCKED_UNSUPPORTED_FLOOR` when no belt is racked (then rack one + confirm with human).
- Implement (contract 4) + QA (contract 6) rewritten belt-aware: they read the run's tool belt for
  compile/execute-verify/proof instead of assuming Java/Maven. Generalized proof of work =
  "run the deliverable on declared inputs, assert the declared expected output."
- Ship-prep (contract 7) honors the belt's `has_version_file` (skips version bump for repos without
  one). Workflow `readContract` injects the belt path into every phase prompt.
- SKILL.md updated (no longer "backend/Java only"). Syntax verified.

## 0.3.0 (2026-06-02)

**Instrumentation migrated from v1: per-phase confidence + a Retro auto-improve phase.**

- Every phase now returns soft `confidence` (0-100) + `confidence_deductions` (signal, not a gate),
  injected via a shared blurb appended to every phase prompt. Schemas allow the fields.
- New final **Retro** phase (`contracts/9-retro.md`): runs on every terminal outcome (success or
  halt), scores the run twice /100 (task_confidence + factory_fitness) with every lost point
  accounted for, lists red flags, proposes concrete next-run improvements, and writes telemetry to
  `runs/` plus a next-run improvement handoff. AWAITING_HUMAN pauses skip Retro (they resume).
- Pipeline refactored into `runPipeline()` + a `trace` of per-phase status/confidence fed to Retro.
- Added `runs/` directory. Bumped to 0.3.0.

## 0.2.0 (2026-06-02)

**Adversarial-cascade + prompt-specialist fixes; back-half restructure from verified Workflow API.**

Reviews: adversarial-cascade (Quinn + Codex-framed) and an independent prompt-engineering specialist.
API behavior verified via claude-code-guide. Full triage in `docs/review-findings-v0.1.0.md`.

Code (workflow.js):
- Null-guard every `agent()` return (skip → `HALT_AGENT_SKIPPED`).
- Enforce `status:'stuck'` halts for design, grill, implement, ship-prep (previously swallowed).
- Add missing `phase('Design')`.
- `capQaVerdict`: canonicalize `execution_verified` to string, drop dead boolean check, warn on
  unrecognised values. Add `evidenceCappedOverall` (a PASS AC with no code_ref+test_ref caps to PARTIAL).
- `preShipBlockers`: execution gate now explicitly rejects `infra_blocked`/`false`/missing, and
  requires the branch to have been pushed.
- Resume loop guard: `BLOCKED_NEEDS_HUMAN_AGAIN` instead of re-looping the concierge.
- Schema tightening: required `repos`, `ticket_folder`, `summary` (concierge); `minimum:0` on
  `criticals_open`/`ac_count`; `minLength:1` on `branch`; pattern on `execution_verified`; `notes` added
  to PHASE_SCHEMA.
- Remove unused `ticketFolder` arg; concierge now RESOLVES and returns `ticket_folder`; absolute
  contracts path (no `~`).

Structure (from verified API limits):
- Skills not callable inside a workflow agent → **Ship is code-prep only**; MR + Jira + transition move
  to the main loop. New terminal state `READY_TO_SHIP`.
- Sibling agents can't see each other's worktree → **Implement pushes the feature branch**; Review/QA/
  Ship-prep run with `isolation:'worktree'` and fetch+checkout it; Implement also writes a diff artifact.
- Single worktree owner: removed `git worktree add` from contract 4 (runtime owns it).
- No native wait → **Validate removed from the auto-run**; main loop runs it post-merge.

Contracts: all 8 updated — concierge returns `ticket_folder` + example open_question; design/grill add
reason-before-file + artifact paths; implement pushes branch + writes diff + dependent-AC stuck;
review defines `demonstrated` + severity rubric + fetch/checkout; qa adds Inputs + example row +
evidence rule; ship-prep is prep-only; validate is a post-merge main-loop step.

## 0.1.0 (2026-06-01)

Initial seed build: workflow spine + 8 backend-floor contracts + SKILL.md. Never run.
