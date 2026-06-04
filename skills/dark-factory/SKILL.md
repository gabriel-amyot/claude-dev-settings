---
name: dark-factory
version: "0.6.0"
description: "The ticket-to-dev factory for a SINGLE ticket, orchestrated by the Workflow tool instead of prose. Gates are code (un-skippable), with a human concierge gate at the front. The concierge proposes a tool belt from the crib (java or scripting); the build + tester sockets are equipped from that belt, so the same line handles multiple work-types without duplication. Review + bounded fix loop + QA. The workflow does code work and pushes the branch (terminal state READY_TO_SHIP); the main loop creates the MR + Jira comment and runs post-merge validate. For multi-ticket / epic DAGs use Sprint Factory (/sprint-factory). Triggers on: '/dark-factory', 'dark factory', 'ticket to dev', 'run this ticket'. Klever."
user_invocable: true
nav:
  bay: build
  when: "Run a Java-service OR scripting/side-effect Klever ticket through the v2 (workflow-orchestrated) factory. Code gates, front human gate, tool belt per work-type."
  when_not: "Frontend/SQL tickets (no belt racked yet - rack one in toolcrib/ first). Multi-ticket epics (use /sprint-factory). Overnight per-AC autonomous (use sprint-crawl). Quick ship (use /autonomous-ticket-ship)."
  personas: [amelia, quinn, winston]
  org: [klever]
---

# Dark Factory

The **single-ticket** ticket-to-dev factory, built on the **Workflow tool**. Orchestration is a
deterministic script; the phase gates are JavaScript, not prose, so no step can be skipped or
self-certified past. A human concierge gate at the front stops for the engineer on spec/context/prereq/infra
decisions. (Formerly "dark-factory v2"; renamed when v1 became **Sprint Factory**, the multi-ticket conductor.)

**Scope:** one ticket at a time; review + bounded fix loop + QA; work-types via tool belts in the crib
(see below). Multi-ticket / epic DAGs are **Sprint Factory** (`/sprint-factory`), which conducts each
ticket through this factory. More belts + rigor on the roadmap (`docs/roadmap.md`).

**Design:** `docs/seed-spec-v1.md` · **Decision:** `docs/adr/ADR-001-...md` · **Why/limits:**
`docs/grounding-and-decisions.md` · **Review fixes:** `docs/review-findings-v0.1.0.md`
**0.5.0 hardening:** `docs/hardening-spec-0.5.0.md` · **Live-verify decision:** `docs/adr/ADR-003-live-verify-data-claims.md`

## Division of labor (important)

The **workflow** does the code work: concierge → design → grill → implement (TDD, execution check,
**pushes the feature branch**) → review → **fix loop** (on a CRITICAL: targeted fix + re-review, max 2
rounds) → QA → ship-prep (version bump + push). It ends at `READY_TO_SHIP`. The **main loop** (this conversational context) does the things a workflow agent
can't safely do: create the MR (`/klever-mr`), post the Jira comment (`/post-comment`), transition the
ticket, and — after the human merges — run post-merge validate (contract 8). This split is forced by
verified Workflow-API limits (skills aren't reliably callable inside an agent; no native wait).

## Instrumentation (auto-improve loop)

Every phase returns a soft `confidence` (0-100) + `confidence_deductions` (signal, not a gate). A final
**Retro** phase runs on every terminal outcome (success or halt): it scores the run twice out of 100
(`task_confidence` = is the task done; `factory_fitness` = did the factory perform well), accounts for
every lost point, lists red flags, and **writes telemetry (`runs/`) + a next-run improvement handoff**.
So each run makes the next better. Future (roadmap): low scores trigger retry / divergent strategy /
trickle work back to an earlier phase.

## Tool belts (multi-work-type, one line)

The line (the "blueprint" / workflow spine) is single. Only two sockets are work-type-specific — the
**build station** (Implement) and the **tester station** (execution-verify + QA). The **concierge
proposes a tool belt** from the crib; the build/tester steps equip it. Racked belts:
`java` (running Java/Spring service) and `scripting` (a script whose value is its output/side-effect —
make tiles, populate BQ, transform data, change state). Unknown work-type → honest
`BLOCKED_UNSUPPORTED_FLOOR` halt (rack a belt first). Rule (ADR-002): a belt swaps **tools only**; a
work-type needing different room *logic* is a rare new floor, not a belt. Refining-phase ideas
(dispatcher, spec/architect personas in the loop) are parked in `docs/second-floor-refining-notes.md`.

## Files

- `dark-factory.workflow.js` — the orchestrator (steps + JS gates + tool-belt routing + Retro).
- `contracts/*.md` — per-phase instructions worker agents read and execute (1-8 + 9-retro).
- `toolcrib/*.md` — tool belts (build/tester loadouts per work-type): `java`, `scripting`.

## Invocation

```
/dark-factory <TICKET>      # e.g. /dark-factory ABC-123
```

## How to run it

1. **Resolve** org from the ticket key (KTP/INS → klever).
2. **Invoke the Workflow tool** with:
   - `scriptPath`: `/Users/gabrielamyot/.claude/skills/dark-factory/dark-factory.workflow.js`
   - `args`: `{ "ticket": "<TICKET>", "org": "<org>" }`
   This is explicit Workflow opt-in (the user invoked this skill). **Note the returned `runId`** — you
   need it to resume after the human gate.
3. **Handle the workflow's return `status`:**
   - `AWAITING_HUMAN` → present each item in `decision_packet` via `AskUserQuestion`. Collect answers.
     **Re-invoke the Workflow** with `resumeFromRunId: <runId>` and
     `args: { ticket, org, humanDecisions: { <id>: <answer>, ... } }`. On resume the concierge **re-runs
     live** (the `humanDecisions` are folded into its prompt, which busts the resume cache) and re-reads
     the ticket — so a ticket-side resolution is picked up, not the stale needs_human verdict (0.5.0 #6).
   - `BLOCKED_NEEDS_HUMAN_AGAIN` → the concierge already re-ran live with the supplied answers and a
     **genuinely new/unanswered blocker** still remains (it is NOT a replayed cached verdict). Show the
     open questions, resolve them in the ticket or refine with the user, then resume with the added
     answer (or run fresh).
   - `BLOCKED_SPEC_QUALITY` → report the concierge findings; suggest a Jira clarification (don't post
     automatically).
   - `HALT_DESIGN_STUCK` / `HALT_GRILL_UNWORKABLE` / `HALT_IMPLEMENT_STUCK` → report the reason; the
     code (if any) stays on its branch. Operator decides.
   - `BLOCKED_REVIEW_CRITICAL` → a CRITICAL survived the bounded fix loop (up to 2 fix+re-review rounds);
     report the open finding(s) and `fix_rounds`; unshipped.
   - `HALT_FIX_NOT_PUSHED` → a fix-loop round did not push its branch; report and stop.
   - `HALT_PRESHIP` → report `blockers` (execution not verified / branch not pushed / open CRITICAL /
     QA not green); do not ship.
   - `HALT_SHIPPREP_FAILED` / `HALT_AGENT_SKIPPED` → report; nothing shipped.
   - `READY_TO_SHIP` → the code is done, reviewed, QA'd, version-bumped, and pushed. Now the MAIN LOOP:
     1. `/klever-mr` (no auto-merge) for `branch`.
     2. `/post-comment` — Jira comment: MR link + AC summary + QA evidence highlights.
     3. Transition the ticket to In Review/Testing (ceiling).
     4. After the human merges: run contract 8 (`docs`/`contracts/8-validate.md`) as a post-merge step.
4. **Write a short run note** to the ticket folder (status, MR if any, what the gates did).

## Guardrails

No direct push to dev/main; no destructive git; DAC repos dev-only; ticket transition ceiling =
In Review/Testing; all external posts via `/post-comment`. The workflow's JS gates enforce
execution-verified, branch-pushed, zero-open-CRITICAL, evidence-backed QA, and QA-green-before-ship,
plus the front human gate.

## Lineage note

This skill was "dark-factory v2" during its seed build (orchestrated by the Workflow tool, vs the
original prose-driven factory). When the original was reframed into **Sprint Factory** (the multi-ticket
conductor, `/sprint-factory`), v2 took the plain **dark-factory** name as the single-ticket factory.
Historical design docs in `docs/` may still say "v2"; that means this skill.

## Status

`0.6.0` — added the bounded fix loop (per-AC resilience harvested from v1 + sprint-crawl): a review
CRITICAL now bounces to a targeted fix + re-review (max 2 rounds) before `BLOCKED_REVIEW_CRITICAL`,
instead of halting on first pass. See `docs/harvest-from-sprint-crawl.md`.

`0.5.0` — hardened from the first live trial (KTP-728 + KTP-699 retros). Front gate now live-verifies
every data-layer claim (ADR-003): schema preflight pins VERIFIED columns, new brands get a fresh
advertiser id, backend-gated sub-ACs are flagged/split at the gate, and the ticket folder is bucketed
under `tickets/...` (never PM root). Review/QA now persist structured `review/findings.json` +
`qa/result.yaml` (with `test_ref`). Resume re-runs the concierge live so a ticket-side resolution is
read instead of a stale needs_human verdict. Belts racked: `java`, `scripting`.
