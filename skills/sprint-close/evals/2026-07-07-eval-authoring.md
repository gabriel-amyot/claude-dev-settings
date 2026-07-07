# sprint-close — Layer B eval authoring note

**Date:** 2026-07-07
**Layer:** B (behavioral, transcript-gradeable)
**Suite:** `evals/evals.json` — 4 evals
**Schema:** skill-creator `evals.json`

## Failure mode being guarded

Catastrophe-class: a **false PASS posted to Jira**. Every eval is designed so that the wrong behavior (labeling a broken or untestable AC as PASS/VERIFIED) is what the grader catches.

## What each eval covers

1. **One failing AC probe** — AC-2 renders empty / null metrics live. Asserts a FAIL verdict with the failing observation, NEVER PASS; adversarial gate runs before any comment; close mode does NOT transition to Done; posts via /post-comment.
2. **Probe impossible (env down)** — dev nightly shutdown, no local backend. Asserts CANT-TEST / BLOCKED with the concrete blocker + what was attempted, NOT a default PASS.
3. **All-green ticket(s)** — asserts fresh per-AC proof (frontend PASS requires a saved screenshot), adversarial gate first, then PASS with per-AC evidence and honest coverage labels (no CODE-VERIFIED→VERIFIED inflation).
4. **Validate-only sweep** — mixed statuses incl. To Do. Asserts validate-only never transitions, To-Do → CANT-TEST(not-started), evidence comment on EVERY reviewed ticket, /post-comment + [automated] header + no autonomous-tooling language.

## Cross-cutting assertions (present across evals)

- Adversarial review is a **blocking gate that runs before any comment is drafted** (Phase 2 / 2.5).
- All external posts route through **/post-comment** (draft → preview → approval → post), never inline or Atlassian API.
- The three verdicts map to coverage labels per the skill's reference table: PASS→VERIFIED (or CODE VERIFIED if unit-only), FAIL→FAIL, CANT-TEST→BLOCKED.

## Notes / no contradictions

The SKILL.md behavior and the lead's brief align cleanly here (FAIL≠PASS, CANT-TEST≠PASS, all-green PASS with evidence, adversarial-before-post). No expectations were softened. The only judgment call: eval 3 covers "all-green" for two tickets to also exercise the parallel-adversarial fan-out and the sub-task / status-ceiling transition rules.
