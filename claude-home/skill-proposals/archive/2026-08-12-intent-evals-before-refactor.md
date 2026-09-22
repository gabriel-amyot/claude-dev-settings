# Skill Proposal: intent-evals-before-refactor
Date: 2026-08-12
Source: pressure-test skill review — a refactor passed 12/12 regression tests while breaking a core intent

## Problem

Regression tests pin defects that were found and fixed. They do not pin what an artifact is *for*. A refactor validated against them alone can go green while gutting the thing.

Observed concretely: a rigor-floor edit to a review skill broke its one anti-escalation rule — reversible internal work started drawing heavyweight treatment. All twelve regression cases still passed. Only a purpose-level case caught it.

The existing `skill-evals` program covers calibration gates and paper-replay. It does not cover intent extraction, and nothing in the harness prompts for it before a restructuring.

## Trigger

Before restructuring, compressing, splitting into `references/`, or otherwise refactoring any skill, agent prompt, or long-lived instruction file. Also on request: "extract evals for this", "what is this skill actually for", "pin the behavior before I change it".

Not for adding a new rule to a skill — that is a regression case, not an intent case.

## Scope

Global. Applies to `~/.claude/skills/`, agent definitions, and any prompt artifact under version control.

## Draft steps

1. **State the intents.** Read the artifact and write what it is *for* as a numbered list — not what it does, what it exists to achieve. Flag any intent that pushes *against* the artifact's dominant direction; that is the one a refactor kills silently.
2. **Map existing coverage.** For each intent, check whether any existing eval already exercises it. Most regression suites cover a third of the intent surface at best.
3. **Write one case per uncovered intent.** One user message plus artifact, one objective pass criterion, no mention of the discipline under test in the dispatch prompt.
4. **Run green before touching anything.** A red baseline means fix first, refactor second. Never refactor against a failing contract.
5. **Refactor, then re-run everything** — intent cases and regression cases both. Report per-case verdicts with the deciding line quoted.

## Notes

- Collect each case synchronously (`run_in_background: false`). A fire-and-forget batch lost 14 runs in the source session and they were unrecoverable.
- Mark each case calibrated or guard-only. A case that has never failed is not evidence.
- Consider folding into `skill-evals` as a mode rather than shipping a separate skill — the harness already has a large `review` bay and adding another entry point risks the trigger collision this proposal's source session spent effort diagnosing.
