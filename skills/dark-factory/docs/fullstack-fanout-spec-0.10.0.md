# Full-Stack Fan-Out — spec (0.10.0)

**Origin:** deft-falcon. Builds on the full-stack investigation (sprint-factory is the wrapper) + the
**observed fan-out spike** (run `wf_3743e789-d3b`, 2026-06-10).
**Status:** SPEC. Multi-belt *detection* is BUILT (0.9.2); the fan-out *pipeline* + dual-MR is the work here.

## What's already built (0.9.x)

- **0.9.1 concierge-only / dry-run** (`args.concierge_only`) — front-gate-only review, zero trickle.
- **0.9.2 multi-belt detection** — concierge sets per-AC `repo` + `belt` in `acs`; ACs spanning >1 repo/belt
  are flagged "full-stack" in `summary`. In a concierge-only review this makes full-stack tickets visible
  up front. The single-belt pipeline is unchanged (still uses the top-level `tool_belt`).

## The spike (observed proof, not reasoning)

Question: does `parallel()` run two isolated agents concurrently; what repo does `isolation:'worktree'`
place each in; can each reach a DIFFERENT target repo? Two read-only probe agents, run as a real Workflow.

Observed:
- **`both_ran: true`** — `parallel()` ran two agents concurrently. ✓
- **`both_reached_distinct_targets: true`** — each reached its own target repo (app-user-management on
  `dev`, app-front-portal on `dev`). ✓
- Each agent's `isolation:'worktree'` placed it in a **temporary worktree of the WORKFLOW's repo**
  (`project-management/.claude/worktrees/wf_..._1` and `_2`) — **NOT** of the target code repo.
- Each agent reached its DIFFERENT target repo cleanly via `git -C <abs-path>` (cwd resets between bash
  calls, so absolute paths are required).
- **Hazard (agent's own words):** "an isolated parallel agent is NOT sandboxed to its own worktree at the
  filesystem level. A non-read-only agent could mutate the target repo (edit, commit, even switch its `dev`
  branch) from inside this worktree. The protection is the explicit instruction + branch-guard/worktree-guard
  hooks, not the parallel()/worktree isolation itself."

## Architect analysis (Winston)

1. **`parallel()` is sound for the fan-out.** The full-stack fan-out can be ONE workflow with a `parallel()`
   of two belt-specific sub-sequences. We do NOT need two sibling workflows for the build step. This is
   simpler than the earlier "Option B = two sibling runs" framing.
2. **`isolation:'worktree'` is the WRONG isolation for two-repo work.** It sandboxes the workflow's own repo
   (project-management), which is irrelevant to code that lives in app-front-portal / app-user-management.
   Relying on it for the fan-out would give a false sense of isolation while writes land on the target
   repo's **main checkout**.
3. **Therefore each fan-out agent MUST self-manage a worktree in its TARGET repo.** Pattern: the agent runs
   `git -C <target-repo> worktree add <tmp> <TICKET>-<belt> origin/dev`, works there, pushes, and removes
   the worktree. `isolation:'worktree'` on the fan-out agent is redundant (it isolates the wrong repo) —
   leave it off; the target-repo worktree is the real isolation.
4. **Latent finding to verify (not blocking, but flag it):** the CURRENT single-ticket implement contract
   says "the runtime gave you your own worktree, do NOT git worktree add." The spike shows that worktree is
   of the workflow's repo. If dark-factory is run from `project-management` (per the BMAD convention), a
   single-ticket implement agent working on app-front-portal is NOT actually isolated either — it would be
   working on the target repo's main checkout. This has worked functionally (KTP-759 etc. produced correct
   branches), but the isolation is partly illusory. **Verify** whether single-ticket runs should also adopt
   the self-managed-target-worktree pattern, or whether dark-factory is meant to run from inside the target
   repo. Either way, the fan-out should NOT inherit the "don't git worktree add" instruction verbatim.

## Resolved fan-out mechanism (for the 0.10.0 build)

ONE concierge (the splitting concierge) → ONE consolidated question-pack (human answers once) → a
`parallel()` of two sub-sequences, each running Design→Grill→Implement→Review→QA for its belt's AC subset,
**each agent self-managing a worktree in its own target repo** (NOT relying on `isolation:'worktree'`) →
collect both branches → hand to the MAIN LOOP for dual-MR sequencing (backend MR first when the frontend
depends on it) + a cross-stack smoke test (sprint-factory's inter-tier gate, extended).

## Build plan (0.10.0)

1. **Splitting concierge fan-out:** consume the `acs[].repo`/`belt` partition (already produced in 0.9.2);
   group into belt subsets; run `parallel()` of two phase-2→6 sub-sequences, bypassing a second concierge.
2. **Self-managed target worktrees:** a fan-out variant of the implement instruction — create + use a
   worktree in the target repo; do NOT assume the workflow's worktree is the code repo. Remove on finish.
3. **Spanning-AC rule:** decompose into backend-AC + frontend-AC + integration-AC (integration-AC owned by
   step 4's smoke test).
4. **Dual-MR + integration (main loop / sprint-factory gate):** sequence the two MRs; after merge, run the
   cross-stack smoke test (frontend hits the new backend endpoint, e.g. via local stack).
5. Tests (mutation-checked) for the partition→subset grouping + the readiness across two branches.
   Adversarial pass. Bump 0.10.0 + CHANGELOG.

## Guardrail
Because target-repo writes are NOT isolated by the workflow, the fan-out agents must (a) create their own
target-repo worktree, and (b) never touch dev/main directly — the branch-guard/worktree-guard hooks are the
backstop, but the design must not lean on them.
