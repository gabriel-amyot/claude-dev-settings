---
name: report-back
description: "Write a completion report from a dispatched session back to its parent. The complement of /handoff: where /handoff tells a future agent what to do (prescriptive, forward), /report-back tells the dispatching agent what happened (descriptive, backward). Use when: 'report back', 'close this handoff', 'completion report', 'done with this branch', 'report to orchestrator'."
---

# Report Back

Write a factual completion report so the parent session knows what happened. Report results, not instructions. The parent decides what to do next.

**Ledger:** `sessions/ledger.yaml` in the project-management directory.

## Tone guard

This is a completion report, not a dispatch order. Every sentence should answer "what happened?" not "what should happen next?"

**Write this:** "AC-6 deferred to KTP-682. BQ data still stores 'United States' until KTP-680 migrates it."
**Not this:** "The orchestrator should pick up AC-6 next and coordinate with KTP-680."

**Write this:** "Two skill improvement handoffs written from lessons learned."
**Not this:** "Suggested next step: review and apply the skill improvements."

If you catch yourself writing "should", "next steps", "the parent/orchestrator needs to", or "suggested skills", stop and reframe as a factual statement about what exists now.

## Find the original forward handoff

If the user provides a filename argument, use it directly.

Otherwise, auto-detect by scanning `sessions/ledger.yaml` handoffs:
1. Look for entries with `status: initiated` whose `ticket` matches the current session's ticket
2. If exactly one match, use it. If multiple, ask the user which one this closes.
3. If no match (standalone session, no parent), set `closes` to `null`. The report is still valuable as a session summary.

## Template

The completion report uses fixed sections. Include all six. If a section has nothing to report, write "None." on a single line. Predictable structure lets the parent session scan quickly.

### Frontmatter

```yaml
---
created: {ISO timestamp}
source_session: "{one-line description of THIS session, what it did}"
type: report-back
status: awaiting_initiation
related_ticket: {Jira key or "none"}
closes: {filename of the original forward handoff, or null}
---
```

### Body

```markdown
## Result

{What was built, decided, or found. Factual summary.}

{For code work: branch name, version, test counts, which ACs passed.}
{For research: key findings, questions answered.}
{For pipeline work: which pipeline nodes completed, current pipeline state.}

## Deliverables

{Every real external side effect this session produced. Only things that exist outside the local filesystem: merged or pushed code, posted comments, database mutations. Each item is a clickable link or verifiable reference. Local files, reports, and harness artifacts do NOT belong here.}

{Format as a bullet list. One line per deliverable, link first:}

- MR [!102](https://cicd.prod.datasophia.com/.../merge_requests/102) — Canadian region support, 10 commits, v0.1.69
- Commit `a1b2c3d` pushed to `origin/KTP-681-canadian-region-support`
- Jira comment [#33580](https://beklever.atlassian.net/browse/KTP-681?focusedId=33580) — AC-6 deferral rationale on KTP-681
- Jira comment [#33581](https://beklever.atlassian.net/browse/KTP-682?focusedId=33581) — AC-6 pickup instructions on KTP-682
- BQ table `dataset.table_name` — 47 rows inserted via migration script

{If the session produced no external side effects (pure research, planning): "None."}

## Deferred

{Anything punted, with WHERE it was punted to.}

{Format: "AC-6 deferred to KTP-682. Jira comment #33581 has the exact change."}
{Format: "Performance investigation parked. Spike ticket KTP-700 created."}

## Surprises

{Things the parent session should know that were NOT in the original forward handoff.}

{These are facts the parent may need to adjust its plan, not suggestions.}
{Format: "MapStateDataRequest.normalize() uppercases IDs before validation runs. Had to remove toUpperCase to enforce uppercase-only input."}

## State updates

{Which shared files were modified during this session.}

{Format: "pipeline-state.yaml: KTP-681 status set to complete, snag logged for AC-6."}
{Format: "ac.yaml: ACs 1-5 marked PASS, AC-6 marked DEFERRED."}
{If no shared state files were touched: "None."}

## Side output

{Artifacts produced that are not the primary deliverable.}

{Format: "Handoff written: 2026-05-26-dark-factory-skill-improvement.md (lessons learned)"}
{Format: "ADR drafted: tickets/KTP/KTP-559/KTP-681/architecture/adr/ADR-normalize-removal.md"}
{If nothing extra: "None."}
```

## Dual-write

Same as `/handoff`:
1. `/tmp/report-back-{slug}.md` (ephemeral, quick access)
2. `sessions/active/prompts/{YYYY-MM-DD}-{slug}-close.md` (tracked)

Use a `-close` suffix in the filename to distinguish from the forward handoff for the same ticket.

## Update the original handoff

If a `closes` filename was identified:

**Ledger entry (helper — never hand-edit `ledger.yaml`):** mark the original forward handoff completed —
`python3 ~/.claude/plugins/local-marketplace/session/bin/ledger.py --org <org> update --section handoffs --key {closes} --set status=completed --set modified={ISO}`

**Forward handoff file:**
5. Read the original forward handoff file from `sessions/active/prompts/{closes}`
6. Edit its YAML frontmatter: set `status: completed`
7. Add a `## Completed` section with today's date and a reference to the close report filename

Both the ledger and the file must agree on status. The parent picks up the close report via `/pickup` as a new ledger entry.

## Update ledger

**Never hand-edit `sessions/ledger.yaml`** (a hook blocks it). Use the helper — it locks, journals, validates, and bumps `version`+`modified`. Reference: `bin/LEDGER_WRITES.md`.

After writing the close file, append the close-report entry:
```bash
python3 ~/.claude/plugins/local-marketplace/session/bin/ledger.py --org <org> append --section handoffs --json '{"file":"{YYYY-MM-DD}-{slug}-close.md","ticket":"{Jira key or none}","status":"awaiting_initiation","source_session":"{this session}","target_session":null,"created":"{ISO}","modified":"{ISO}","closes":"{original handoff filename or null}","version":1}'
```
(`--org` from cwd: grp-beklever-com→klever · supervisr-ai→supervisr · gabriel-amyot→personal.) If `closes` was set, also mark the original entry `completed` (see the Ledger-entry step above).

## Idempotency

Before creating, check `sessions/ledger.yaml` for an existing entry with matching `related_ticket` AND a non-null `closes` field (this distinguishes close reports from forward handoffs for the same ticket). Skip matching when ticket is "none".

- **Match found, status `awaiting_initiation`:** update the existing file in place. No new ledger entry.
- **Match found, status `initiated`:** ask user before overwriting. Someone may be reading the report.
- **No match:** create new file and new ledger entry.
