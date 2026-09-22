# Skill Proposal: skill-retirement-audit

Date: 2026-08-24
Source: session amber-finch — adversarial review of `sprint-dispatcher` vs `sprint-factory`

## Trigger

User asks whether an existing skill/agent still adds value, suspects sprawl or duplication ("do we still need X", "review and consolidate Y skills", "is this dead weight"), or a harness/skill audit surfaces an overlapping cluster (e.g. the "sprint/ticket-lifecycle cluster" flagged in `general/reports/harness-friction-audit-2026-07-07.md`).

## Scope

Global (`~/.claude/skills/`). Applies to any harness component (skill, agent, hook) suspected of being unused or superseded, not just Klever-specific ones.

## Draft Steps

1. **Diff the candidate against its suspected replacement.** Identify the specific overlapping mechanism (not just "they sound similar") — same inputs, same core loop, same output shape.
2. **Git-log the candidate's own creation commit.** Read the full commit message, not just the diff — the original author's own framing often already states an assessment ("built X, also wrote a proposal to retire it").
3. **Grep the repo for a sibling proposal or decision doc.** A prior session may have already litigated this exact question and left a written recommendation that was never actioned.
4. **Check for independent later corroboration.** Search friction audits, harness reviews, or retros for the same skill name flagged without prompting — independent confirmation is stronger than a single analysis.
5. **Look for concrete invocation evidence, not existence.** A handoff actually picked up, a `/session:report-back`, ledger/session-archive activity referencing the skill by name. "It's in the skills folder" is not evidence of use.
6. **Synthesize a verdict with the evidence trail, not just a recommendation.** State what each of steps 2-5 found; if they converge, the retirement call is solid. If they conflict, say so and don't force a verdict.
7. **On retirement: archive, don't delete.** `git mv` to `_archive/{name}/` (create the convention if the tree doesn't have one yet — user-global `~/.claude/skills/_archive/` is the existing precedent), add a retirement banner in the body (not stripped from frontmatter) stating what/why/where-the-decision-lives, and update any docs/routing tables that reference the retired skill as live.

## Notes

First real run of this shape: `sprint-dispatcher` (built 2026-06-03, same-session proposal recommended retiring it, never actually invoked in 11 weeks, independently flagged by a 2026-07-07 friction audit). All four evidence steps converged, which is what made the retirement call solid rather than a guess. See `documentation/bibliotheque/development/dark-factory/sprint-factory-vs-dispatcher-merge-proposal.md` for the full worked example.
