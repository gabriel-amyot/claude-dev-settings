# Dark Factory v2 — Seed Spec (One-Pager)

**Session:** wise-owl · **Date:** 2026-06-01 · **Status:** Accepted. Seed ticket = **KTP-728**. No code until build starts.

The smallest thing that proves the thesis. Not the platform. Not all the floors. One spine,
one floor, **KTP-728**, measured.

> Cross-refs in this folder: `roadmap.md`, `grounding-and-decisions.md`, `adr/ADR-001-workflow-orchestration-over-prose.md`.

---

## Goal

Run **one real Klever ticket** end-to-end through a **workflow-orchestrated** factory where the
gates are JS (un-skippable), and measure the result against the three predictions in the
grounding record.

## Anti-overfitting constraint (hard rule)

KTP-728 is the **validation input, not the design target.** The floor must run *any* backend/Java
ticket. Therefore:
- The factory is built **blind to KTP-728.** Do not read the KTP-728 handoff during the build.
- Every phase contract is sourced from v1's *proven, multi-ticket* backend phases (KTP-681/682 +
  the tech-adaptation table), never from one ticket's specifics.
- KTP-728 enters only at run time, as a black-box `ticket` argument.
- Smell test: if any conditional in the workflow names KTP-728, that's overfitting — delete it.

## Build architecture (decided this session)

Three artifacts, kept deliberately separable so v1 vs v2 can be benchmarked in two terminals:
1. **`dark-factory.workflow.js`** — the deterministic spine (Workflow tool script). Phase order,
   gates as JS `if`s, the concierge human-gate split. Ticket-agnostic.
2. **`contracts/*.md`** — the per-phase reasoning instructions (the "muscle"), harvested from v1.
   Each phase agent is told to *read its contract and execute it* (mirrors v1's analyst pattern).
   Keeps prompts editable as markdown, keeps the workflow script lean.
3. **`SKILL.md`** — thin entry point: "to run, invoke the Workflow tool with the script, args =
   ticket key." Written last, once the spine + contracts exist.

**Concierge human gate = two-stage split (not mid-workflow pause).** A Workflow `agent()` cannot
call `AskUserQuestion`, and the run is backgrounded. So: Stage A runs the concierge (analyze +
context + prereqs + infra surfacing) and **returns a decision packet** if human input is needed.
The main loop presents it, collects answers, and **re-invokes with `resumeFromRunId`** plus the
answers in `args.humanDecisions` — the cached concierge result makes resume cheap; Stage B
(design→validate) proceeds. Front gate always stops; this is how.

## In scope (the seed)

1. **Workflow skeleton** (`dark-factory.workflow.js`): deterministic orchestration of the
   per-ticket phase chain. Gates (verdict-cap, pre-ship artifact check) are JS `if`s, not prose.
2. **Concierge front gate (human-in-the-loop):** spec analysis + context gathering + prerequisite
   check + (greenfield) infra-level decision. **Always pauses for the human here** regardless of
   floor — this is where wrong = re-run everything. Workflow pauses, surfaces the decision, resumes.
3. **ONE floor:** pick the floor matching the chosen ticket's stack (likely **backend/Java** — the
   best-tested path, KTP-681/682 as reference). Frontend/SQL/scripting floors deferred.
4. **Phase contracts harvested from the current skill** as the agent prompts (TDD discipline,
   analysis-over-advocacy, tech-adaptation, the 12 lessons). Muscle reused; skeleton rebuilt.
5. **Like-for-like first:** single-pass review + single-pass QA (segregated agents, as today).
   This isolates substrate cost (prediction #3) before adding rigor.

## Out of scope (deferred, by design — all detailed in `03-roadmap.md`)

- Blind-impl / two-buildings, design deliberation (redesign + compare + judge), multi-gate
  verification, model diversity → **rigor additions** (Roadmap R1–R3). Note: the redesign/compare/
  judge rigor targets *a specific step's design decision*, not the overall architecture.
- Confidence scoring math, Dempster-Shafer, dark-tier auto-merge, and the infra it requires
  (Firecracker microVMs, Leash/Cedar, Temporal.io) → Roadmap R6 ("lights-out per floor").
- Multi-floor expansion (frontend/SQL/scripting/...) → Roadmap R4. Seed = backend/Java only.
- Multi-ticket tiers / dependency graphs → current skill does this in prose; port later.
- floor-manager-as-tool-crib / dispatcher → Roadmap R5 (separate job from today's recommender).
- Reasoning-class failure tracking → Roadmap R7 (known gap; future Supervisr.ai integration).

## The hard design problem (must solve in the seed)

**Human gates inside a background workflow.** A workflow `agent()` cannot call `AskUserQuestion`.
The concierge gate must therefore: run to the gate → return a "needs decision" payload → the main
loop asks the human → resume via `resumeFromRunId`. The seed must prove this pause/resume loop
works for at least the front gate. **[JUDGMENT — highest-risk unknown in the seed.]**

## Autonomy model (config, not hardcode)

- The skeleton is rigid about *structure and gates.*
- *How much it bothers the human* is **per-floor + per-invocation config** (e.g.
  `--autonomy cautious|hold`). Front gate always stops. Design gate stops only on "unworkable"
  (threshold = "likelihood we'd have to re-run everything if this assumption is wrong"), and even
  then self-heals (redesign + compare) before escalating — deferred to post-seed rigor.

## Success criteria

- One real ticket reaches a mergeable MR through the workflow.
- The front-gate pause/resume loop works with a human decision in the middle.
- Prediction #1 holds (no skipped gate / no self-certified QA).
- Prediction #3 measured: like-for-like substrate cost is flat-or-cheaper vs. the prose skill.
- If any criterion fails: that is a *finding*, recorded, not a failure to hide.

## Optional post-v1 validation (Gabriel's method — not required, run if curious)

After v1 ships: run the **same ticket** through the old prose skill and the new workflow, each in
its **own worktree**, and gather price/time metrics to compare. This is the concrete way to settle
prediction #3 with real numbers. Cost is not a current priority (tokens are not constrained now);
do this if/when cost optimization becomes timely.

## Build order (when approved — still no code until then)

1. Choose the ticket + floor (backend/Java preferred).
2. Write `dark-factory.workflow.js` skeleton (phases as `agent({schema})`, gates as `if`).
3. Harvest phase-contract prompts from current SKILL.md.
4. Solve the front-gate pause/resume.
5. Run on the ticket. Measure against predictions. Write findings.
6. Decide: grow a floor / add rigor / stop.
