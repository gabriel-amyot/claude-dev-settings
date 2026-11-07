# Queue triage procedure (`/pickup --triage`)

Use this procedure for a large `awaiting_initiation` queue. The queue was drained by hand three times, and each pass found the same method again. The method is stable. A naive version is dangerous: "the ticket is Done" was wrong on 15% of archive candidates in the first full run, and one of them was a live prod write gate.

The human approves every archival batch. This procedure never archives on its own.

## 1. Build the worksheet on disk

```bash
python3 ~/.claude/plugins/local-marketplace/session/skills/pickup/scripts/triage_worksheet.py \
  --org <org> --out <session-folder>/reports/queue-worksheet.csv [--jira-status <jira.json>]
```

The script is read-only on the ledger. It writes one CSV row per awaiting forward handoff and prints one summary line. Do not load the rows into context. Read only the rows you present.

## 2. Join Jira

Query the distinct ticket keys in one batched call. Save the result as `{"KEY": "status"}` JSON and run step 1 again with `--jira-status`. Diff requested keys against returned keys. A missing key is usually a project move, not a deleted ticket. The script marks it `CHECK_KEY`.

## 3. Read the verdicts

| Verdict | Meaning | Action |
|---|---|---|
| `HOLD` | A scope flag fired | Probe before any archive. Never batch-archive. |
| `PROBE` | Ticket is `none` | Probe the exact artifact the ask names. |
| `CHECK_KEY` | Key missing from Jira result | Find the new key, then re-run. |
| `ARCHIVE_CANDIDATE` | Terminal Jira status, no scope flag | Present for batch approval. |
| `REVIEW` | A newer handoff has the same ticket+theme | Compare the two asks. An umbrella ticket has many parallel handoffs. |
| `KEEP` | Live ticket, nothing newer | No change. |
| `UNCHECKED` | No Jira join yet | Do step 2. |

## 4. Scope audit (the step that makes this safe)

"Ticket Done" is not proof that the handoff's ask landed. The script hard-blocks (`HOLD`) a row when any of these is true:

- `blocked_marker`: the file carries a `BLOCKED` marker.
- `env_named`: the ask (the `## Prompt` section) names prod, production or uat. Confirm that environment is covered before archive.
- `programme_shaped`: the ask names three or more ticket keys.
- `ticket_mismatch`: the file's `related_ticket` disagrees with the ledger ticket.
- `file_missing`: the file is not on disk, so nobody can read its scope.

## 5. Probe the HOLD and PROBE rows

Each probe must name the exact artifact the ask names: the MR, the deployed version, the ledger entry, the file. A probe that can pass while the work is undone is not a probe. If you cannot probe a row, report it as `UNPROBED`. Do not guess.

## 6. Batch approval, then CAS writes

Present grouped batches with the evidence for each row. Write each approved row with a compare-and-swap claim, never a blind batch. Other sessions write the same ledger at the same time.

```bash
ledger --org <org> claim --key <file> --expect-status awaiting_initiation \
  --set status=completed --set archived=<YYYY-MM-DD> --set archive_reason="<evidence>"
```

Use `status=abandoned` for an abandoned row. Every archived row gets an `archive_reason`. A non-zero exit means another session changed the row: skip it and report it. Do not retry blindly. Then move the file to `sessions/archive/done/` or `sessions/archive/abandoned/` (quarantine, never `rm`).

## 7. Rank what survives

List the surviving handoffs by priority. If the queue grew back since the last sweep, write the reason as a proposal (for example, a skill that creates too many handoffs). Do not prune harder to compensate.
