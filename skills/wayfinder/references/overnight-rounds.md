# Overnight rounds on a map

Use this only when Gabriel explicitly asks to run a map over several nights ("run another round on
this map", "work this map overnight") and the destination is a live system. Invocation stays manual.
For one ticket overnight, use `sprint-crawl`. For a dependency-linked set of Jira tickets, use
`sprint-factory`. This file adds a **contract** around the rounds. It does not add an executor.

Execution on a map is an override of "Plan, don't do". The map's `## Notes` must say that the
map carries execution. If it does not, stop and ask.

## 1. The charter

Before round one, write a charter file (for example `HANDOFF.md` in the run folder) and link it
from the map's Notes. Every agent in every round reads it first. It holds:

- **Destination**: the live state that ends the map, stated so a test can check it.
- **Verified facts**: each with its evidence or `verified_against` stamp. No unverified claims.
- **Authority**: what agents may do without asking (for example: deploy to dev) and what needs
  Gabriel (prod, IAM, shared CI variables, data mutation, external posts). The global shipping
  safeguards apply. The charter can narrow them, never widen them.
- **Hard rules and incident rules**: what to do on a failed deploy, a data risk, or a blocked gate.

Decisions taken during a round are appended to the charter as dated sections. Do not rewrite
earlier sections.

## 2. One round

1. **Task list.** Take the map frontier, plus any explicit ask from Gabriel. Explicit asks go first.
   Order tasks only by hard dependencies.
2. **Per task:** implement, then QA with live proof, then at most a bounded fix loop, then record.
   Use the existing executors: `dark-factory` for a ticket that needs a build line, `sprint-crawl`
   for one long unattended ticket. Do not copy their gates into the round.
3. **A blocked task** gets one short unblock spike. If the spike fails, record the blocker on the
   ticket and move to the next task.
4. **Record** every task: a comment on its ticket (through `wayfinder_runs.py resolve` or `report`),
   an update to the run STATE file, and a commit of the run folder after a secret scan.

## 3. Gate rules

- A gate never passes on a rollback, a revert, or a "best effort" result. A rolled-back change is a
  failed task with a recorded cause.
- A judge or reviewer works on a **frozen packet**: the diff, the evidence, and the criteria, fixed
  before the judge starts. The judge does not see the implementer's own verdict.
- Parallel tasks follow the concurrency rule in SKILL.md: expect other sessions on the same issues,
  and use the guarded map append from [dispatch-template.md](dispatch-template.md).

## 4. Resume

A round that dies resumes from the STATE file and the map, not from memory. Append new tasks at
the end of the task list. Do not edit records of tasks that already ran.

## 5. Morning brief

End each round with:

- A completeness check against the charter: which destination criteria now hold, with live proof,
  and which do not.
- A short brief for Gabriel: done, failed with cause, blocked, and decisions waiting for him.
  Decisions go to his inbox, reviews go through `/crit`.
- An update to the map: Decisions so far, fog graduated, and new tickets.
