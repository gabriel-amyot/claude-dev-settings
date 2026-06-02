# Dark Factory v2 — Review Findings (v0.1.0, pre-run)

**Date:** 2026-06-02 · **Reviews:** adversarial-cascade (Quinn logic + Codex-framed skepticism) + an
independent prompt-engineering specialist. **Status:** triaged, NOT yet applied. Decide per item.

Headline: moving gates into JS did **not** prevent reasoning/implementation bugs — the cascade found
a pile of them. That is exactly prediction #2 from `grounding-and-decisions.md` confirming itself.
The build is **not run-ready** until Batch 1 + the verified items are resolved.

---

## Batch 1 — workflow.js code bugs (no API uncertainty; safe to fix on approval)

| ID | Severity | Fix |
|----|----------|-----|
| B1 | CRITICAL | Null-guard EVERY `agent()` return (it can return null on skip). Today `concierge.spec_quality` / `impl.branch` crash first. On null → return a HALT status. |
| B2 | CRITICAL | Enforce `status:'stuck'`: after design, grill, ship — `if (.status==='stuck') return HALT_*`. Today a stuck design/grill falls through to Implement; a failed ship still reports COMPLETE. |
| B3 | LOW | Add missing `phase('Design')`. |
| B4 | HIGH | `execution_verified`: canonicalize to string, drop the dead `=== true` boolean check, `log()` a warning when an unrecognised value falls through to INCOMPLETE. |
| B5 | HIGH | `preShipBlockers`: make the execution gate explicitly reject `infra_blocked(...)` (today it clears the execution check and is only caught later by the QA cap). |
| B6 | MEDIUM | Thread `decisionsNote` into phases 4–8 (or have Design persist decisions to disk for downstream). |
| B7 | MEDIUM | Remove unused `args.ticketFolder`; fix `org` threading (substitute `org` into contract prompts, or declare klever-only and enforce). |
| B8 | MEDIUM | Resolve `notes`: it's in contracts 2/3/8 Return but not in PHASE_SCHEMA. Add `notes` to PHASE_SCHEMA or drop from contracts. |
| B9 | MED/LOW | Schema tightening: `criticals_open` `minimum:0`; `branch` `minLength:1`; add `repos` to required; consider requiring QA `code_ref`/`test_ref`; `enum`/pattern on `execution_verified`. |
| B10 | LOW | Use the ABSOLUTE contracts path in prompt strings (`~` may not expand inside an agent prompt → agent reads nothing, runs with no instructions). |

## Batch 2 — contract prompt-quality (markdown; safe; from prompt specialist)

- **1-concierge:** add `summary` to Return (it's a required schema field, currently omitted); add an example `open_question` object; brownfield step must say what to DO with a finding.
- **6-qa:** add an Inputs section (how to get AC list + `git diff --name-only`); add an example `per_ac` row; state "PASS with no test_ref → treat as PARTIAL".
- **5-review:** define `demonstrated` explicitly (true ⇔ wrote a test, ran it, it FAILED); add a CRITICAL/HIGH/MEDIUM/LOW rubric; restate segregation ("don't read the plan even if you can find it").
- **3-grill:** add explicit reason-before-filing step (state assumption → find code evidence → then file); specify artifact paths; tiebreaker for equivalent choices ("fewer new files").
- **2-design:** specify how to find the ticket-folder path; light reasoning prompt for brownfield avoidance.
- **4-implement** (already strongest): add dependent-AC stuck propagation (if a stuck AC blocks later ACs, mark them stuck too).
- **7-ship:** clarify the `/post-comment` human-approval expectation inside an autonomous phase.
- **8-validate:** specify max poll window (e.g. 5 polls / 5 min) instead of "reasonable window".

## Batch 3 — VERIFY against the real Workflow API before fixing (do NOT fix blind)

| ID | Question | Blocks |
|----|----------|--------|
| V1 | `resumeFromRunId` semantics + does a resumed run skip completed `agent()` calls (concierge cache)? Can the AWAITING_HUMAN re-entry loop forever if the agent re-answers `needs_human:true`? Need a resume-count guard? | The whole human-gate design |
| V2 | Can a Workflow-spawned `agent()` invoke Skills (`/klever-mr`, `/post-comment`)? Or must Ship use Bash (`git`, `gitlab_skill.py`, `jira_skill.py`) directly? | Contract 7 (Ship) |
| V3 | Does `isolation:'worktree'` conflict with contract 4's own `git worktree add` (double worktree, branch mismatch)? Can the Review/QA sibling agents see the Implement worktree to `git diff`? | Implement/Review/QA wiring |
| V4 | Is there a sleep/poll primitive for an agent? (Validate polling.) | Contract 8 (Validate) — likely "pull Validate out of auto-run" regardless, since it runs before the human merges. |

## Proposed sequence

1. Dispatch `claude-code-guide` to answer V1–V4 (API truths).
2. One consolidated fix pass applying approved Batch 1 + Batch 2, incorporating the V answers
   (worktree ownership, ship-via-Bash-vs-Skill, validate split, resume guard).
3. Re-commit. Then the guarded KTP-728 trial.

---

## Batch 3 — VERIFIED (claude-code-guide, 2026-06-02) + design decisions

| Q | Verified | Decision |
|---|----------|----------|
| V1a | Changing `args` on resume likely busts the cache for dependent agents (strong-inference). | Concierge must be idempotent; accept it may re-run on resume. |
| V1b | **No built-in loop guard** (confirmed). | Add guard: if `humanDecisions` provided and concierge still `needs_human` → return `BLOCKED_NEEDS_HUMAN_AGAIN`, never loop. |
| V2 | **Skill invocation inside a workflow agent is unsafe/unconfirmed.** Bash + MCP safe. | **Ship = code-prep only** in the workflow (version bump + CHANGELOG + commit + push, via git). MR + Jira move to the MAIN LOOP (`/klever-mr` + `/post-comment`). Honors the external-post approval rule. |
| V3a | `isolation:'worktree'` + agent's own `git worktree add` = redundant. | Single owner: keep `isolation:'worktree'`; remove `git worktree add` from contract 4. |
| V3b | **A later agent cannot see an earlier agent's worktree unless the branch is pushed** (confirmed). | Implement **pushes the feature branch** at the end; Review/QA/Ship-prep run with `isolation:'worktree'` and `git fetch origin <branch> && git checkout <branch>`. Implement also writes a diff artifact to the ticket folder (absolute path) as a backup channel. |
| V4 | No native wait primitive; long waits belong outside the workflow. | **Validate removed from the auto-run.** Workflow terminal state = `READY_TO_SHIP`. Validate is a post-merge step the main loop runs later. |

**Net architecture:** workflow ends at "code done → reviewed → QA'd → branch pushed → version bumped → READY_TO_SHIP." Main loop then runs `/klever-mr` + `/post-comment`, and post-merge `/validate`.
