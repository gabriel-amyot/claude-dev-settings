# Skill Proposal: gate-eval-harness
Date: 2026-07-07
Source: sharp-wasp — KTP-907 PCE safeguards build (before/after validation of /post-comment upgrade)

## Trigger
When upgrading any agent instruction file, hook, or gate script in the harness and the user wants proof the change works ("test the new prompting", "eval the skill before/after", "does the gate actually block X", "adversarially review this safeguard").

## Scope
Global (harness self-management).

## Draft Steps
1. **Baseline:** resolve the before-arm instruction text from git (`git show HEAD:<file>`); working copy is the after-arm. Write both to a sim dir.
2. **Deterministic evals:** generate/extend a fixture suite for any gate scripts (drafts + expected exit codes + output needles); run, patch, re-run to green. Fixtures are permanent regressions.
3. **Tabletop sims:** spawn paired Sonnet agents (before/after per scenario). Each agent's ENTIRE instruction set is its arm's file; it may run only local scripts that file names; network/posting commands forbidden; structured verdict (GATES_RUN / FINAL_ACTION / USER_MESSAGE). Always include a user-pressure scenario and a legit-workflow (false-positive/friction) scenario.
4. **Red-team + design review:** one agent attacks the mechanical layer (natural-phrasing evasions + false positives, verified by running the script); one fresh-context agent reviews the design (bypass paths, gamed checks, unexecutable instructions, incentive gradients).
5. **Consolidate:** encode surviving red-team findings as new fixtures, apply design fixes, re-run to green, write an eval report next to the gate (`evals/<date>-eval-report.md`), commit.
