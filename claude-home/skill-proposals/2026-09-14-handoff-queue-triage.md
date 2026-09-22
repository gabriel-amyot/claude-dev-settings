# Skill Proposal: handoff-queue-triage
Date: 2026-09-14
Source: session `tidy-shrike` — took the Klever handoff queue from 88 to 50

## Trigger

"triage the handoffs", "the handoff queue is huge", "clean up awaiting_initiation",
a SessionStart line reporting a large pending-handoff count, or any periodic queue sweep.

## Scope

Org (any org whose `project-management/sessions/ledger.yaml` follows the v2 schema).

## Why it is worth a skill

The queue has been drained three times by hand (22 → ~42 → 88) and each pass re-derived
the same method from scratch. The method is stable; the per-run work is mechanical. A
naive version of it is also dangerous — see step 4.

## Draft Steps

1. **Worksheet to disk.** One row per `awaiting_initiation` handoff: file, ticket, theme,
   source session, age, on-disk path, and whether a later handoff on the same ticket
   exists. Never load the rows into context.
2. **Jira join.** Batch-query the distinct tickets. Diff requested-vs-returned keys — a
   mismatch means a project move, not a missing ticket.
3. **Rule pass.** Terminal ticket → archive candidate. Superseded → candidate. Live ticket
   and nothing newer → keep. No ticket → needs an artifact probe.
4. **Scope audit — the step that makes this safe.** "Ticket Done" is not proof the
   handoff's ask landed; it was wrong on 15% of candidates in the first run, including a
   live prod bid-WRITE gate. Hard-block any candidate whose ask names an uncovered
   environment, is programme-shaped, carries a BLOCKED marker, or whose own frontmatter
   ticket disagrees with the ledger's.
5. **Probe the unlinked ones.** Each probe must name the exact artifact the ask names. A
   probe that can pass while the work is undone is not a probe. Report UNPROBED honestly
   rather than guessing.
6. **Batch-approve, then CAS-write.** Present grouped batches with per-row evidence. Write
   with `ledger claim --expect-status`, never a blind batch — other sessions write the
   same file concurrently. Set `archive_reason` on every archived entry.
7. **Rank what survives** and diagnose why the queue regrew, as a proposal.

## Eval set

`sessions/active/tidy-shrike/reports/queue-worksheet.csv` — 88 rows with verdicts and
evidence. Pass condition: spare all 5 rescued handoffs, archive the 26 clean ones.

## Related

Design proposal for the automated half:
`documentation/process/proposals/2026-09-14-handoff-closure-hook-design.md`
