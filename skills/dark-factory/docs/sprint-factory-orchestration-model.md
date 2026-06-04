# Sprint Factory — orchestration model (the v1 → multi-ticket-conductor reframe)

**Status:** Design (2026-06-03, session deft-heron). Decided with Gab. This is the target shape for what
is currently the `dark-factory` (v1) skill: rename it to **Sprint Factory** (a.k.a. sprint orchestrator)
and reframe its role. It stops being a per-ticket lifecycle engine and becomes the **multi-ticket
conductor** that drives tickets through `dark-factory-v2` (the per-ticket factory).

## Role split (why this exists)

- **dark-factory-v2** owns the *single-ticket* lifecycle: concierge → design → grill → implement →
  review → fix loop → QA → ship-prep. It has a human concierge front gate and ends at `READY_TO_SHIP`.
- **Sprint Factory** owns the *multi-ticket DAG*: it reads a flat list or a plan-file YAML dependency
  graph, computes topological tiers, and conducts each ticket through v2 — it does NOT re-implement the
  8-phase lifecycle inline (v1's current design). v1's lifecycle prose becomes legacy/reference.

The hard problem this solves: v2's concierge is an interactive human front gate (`AWAITING_HUMAN`). If
Sprint Factory called v2 directly for N tickets autonomously, that gate would fire N times and break
autonomy. The two modes below resolve that.

## Mode 1 — Handoff orchestration (build this first; uses existing machinery)

Sprint Factory leans on the session **handoff / pickup / report-back** system (the same plumbing in
`project-management/sessions/`). No new substrate.

1. **Plan.** Sprint Factory computes the DAG and tiers from the plan-file/flat-list (v1's existing tier
   logic). Example: 10 tickets, 3 cascading branches → Tier 1 has 3 startable tickets.
2. **Surface + fan out.** It surfaces the startable tickets and writes **one handoff per startable
   ticket** into `sessions/active/prompts/`. Each handoff says: "Run {TICKET} through `/dark-factory-v2`."
   The three Tier-1 handoffs can be picked up in parallel (separate sessions/terminals).
3. **Execute.** Each handoff session runs `/dark-factory-v2 {TICKET}` — full per-ticket factory with its
   own human concierge gate. The human is naturally in the loop per ticket (that's fine in this mode).
4. **Report back + unlock.** On completion, each session produces a **report-back** (`/session:report-back`).
   You paste the report-back into the Sprint Factory session; it marks that ticket done in the DAG and
   **unlocks the next tier for that branch**, writing the next handoff(s). Work trickles back in.

This is the manual-but-easy mode. It is buildable now because every piece (DAG/tier computation,
handoff write, pickup, report-back) already exists. Sprint Factory becomes the conductor + DAG state.

## Mode 2 — Autonomous concierge with question-packs (the desired evolution; document, build later)

The future: run Sprint Factory once and walk away. It fans out the startable tickets in parallel; each
ticket's **concierge runs first**. If the concierge has blocking doubts, instead of pausing for an
interactive human, it **emits a concise question-pack** and self-blocks that branch until answered.

**Where the question-pack goes (escalating maturity):**
1. **Now / first cut:** write it locally as a *blocker entity* — a handoff/blocker file in
   `sessions/active/prompts/` (or an inbox) that blocks only that branch. The other branches keep going.
   The blocked items surface to the human as a clean action list.
2. **Then (try it, don't pre-dismiss):** the concierge posts the question-pack as a **Jira comment on the
   ticket itself**. Jira is the natural home for ticket questions. Caveat: do NOT transition the ticket to
   `Blocked` (the PO watches that status). Just post the comment; keep the block local to the run.

**Question-pack format (caveman-level — concise, NOT a wall of text).** The concierge produces a short
list of points/questions. For each doubt:
- state the question in one line,
- give 2-3 candidate **assumptions**,
- pick the **best** one and propose it as the recommended action ("proceed as if X").

So each item is: *question → assumptions → recommended assumption → proposed action.* The human can
rubber-stamp the recommendation or correct it. (This mirrors a format already used elsewhere in the
harness — reuse it; don't reinvent.) The point is a decision the human can make in seconds, not an essay.

This format also improves v2's concierge `open_questions` / `decision_packet` independent of Sprint
Factory — each open question should carry assumptions + a recommended option, not just the bare question.

## Build order

1. **Now:** rename v1 → Sprint Factory (skill id + dir + reference sweep), strip/relegate the inline
   8-phase lifecycle to "legacy reference," rewrite the orchestration section to Mode 1 (handoff fan-out
   + report-back unlock), keep the DAG/tier/plan-file logic (its crown jewel).
2. **Next:** enrich v2's concierge `open_questions` to the question-pack format (assumptions + recommended
   action). Small, valuable on its own.
3. **Later:** Mode 2 — concierge emits the local blocker question-pack autonomously; then the Jira-comment
   variant. This is the "run once, walk away, blocked items appear as an action list" end-state.

## Idempotency & rerun (core requirement)

Sprint Factory is **rerunnable and idempotent.** You run it once per sprint and keep the session open,
but it must survive a closed session and a re-run without redoing work. The way to get this: **do not
trust a private state file as the source of truth — reconcile from ground truth on every run.**

**Ground-truth sources (read on every invocation):**
1. **Jira ticket status** — a ticket that is Closed/Done (or merged) is *done*, regardless of what any
   local file says. Done tickets unlock their children in the DAG.
2. **Handoff ledger** (`project-management/sessions/ledger.yaml`) — a handoff with `status: initiated`
   means that ticket is *in progress in another session*: do NOT re-create its handoff. `completed`
   (or a close report `closes:` it) means that branch reported back: advance the tier.
3. **The DAG itself** (plan-file / flat-list deps) — defines parent→child edges.

**Reconcile algorithm (every run):**
```
load DAG (plan-file or flat list)
for each ticket: status = resolve(Jira status, ledger handoff status)
  - Closed/Done/merged        -> DONE   (unlocks children)
  - handoff initiated         -> IN_PROGRESS (skip; do not re-handoff)
  - handoff completed/report  -> DONE-pending-verify (advance)
  - blocked by un-DONE parent -> BLOCKED (leave alone)
  - startable & no handoff    -> STARTABLE -> create handoff now
emit: newly-created handoffs + a status board
```
A re-run with no changes creates zero new handoffs (pure idempotent). A re-run after a ticket closed
creates exactly the handoffs for the children it just unlocked. Nothing in flight is touched.

**Persist the board, but treat it as a cache, not truth:** write a DAG status board to the sprint
scaffolding — `project-management/tickets/sprints/{Sprint}/sprint-factory-board.yaml` (the
`tickets/sprints/Q2-Sprint-N/` folders already exist). It is a convenience snapshot + audit trail; the
reconcile step always re-derives from Jira + ledger so a stale board cannot cause double-work. This is
the synergy point with the existing sprint infrastructure (and the `klever-sprint-mgmt` / `sprint-dispatcher`
skills): Sprint Factory reads the sprint's ticket set + statuses there and writes its board alongside.

**Net effect:** "run once per sprint, keep the session open" is the happy path; "closed it, re-run
tomorrow" is safe — it picks up exactly where ground truth says the tree is, fans out the next unlocked
tier, and never re-does an in-flight or closed ticket.

## Preserved from v1 (must not be lost in the rename)

- Plan-file YAML schema (`type: execution-plan`, `tickets[].depends_on`, `gates`, `integration_tests`).
- Topological tier determination + lane isolation + `optional: true` tickets.
- Inter-tier gate verification (custom_checks, e.g. curl a tileset endpoint).
- LESSONS.md catalog + retrospective cross-run pattern detection.
