---
name: pickup
description: "Pick up a pending handoff and start working on it, or triage/archive handoffs. Reads from the session ledger (one file, no scanning). Exact filename match for targeted mode. Use when: 'pickup', 'pick up a handoff', 'what handoffs are pending', 'continue from handoff', 'start the handoff', 'resume from where I left off', 'triage handoffs'."
---

# Pickup

Pick up a handoff prompt and start working on it, or triage the handoff queue.

**Load tools first:** `ToolSearch(query: "select:AskUserQuestion")`

**Ledger:** `sessions/ledger.yaml` in the project-management directory. One file read, never scan directories.

## Modes

### List mode (`/pickup` or `/pickup --list`)

Read `sessions/ledger.yaml` handoffs section.

**Default: show only `awaiting_initiation` forward handoffs** (entries without a `closes:` field). Hide completed, initiated, abandoned, and close reports. This is the actionable pickup queue.

**`/pickup --all`**: show everything (all statuses, including close reports).

**Grouped by theme.** Read the `theme` field from each ledger entry. Group entries under their theme header. Entries without a theme go under "uncategorized."

```
Handoff Queue (awaiting)
═══════════════════════════════════════════════════════
🔧 harness (3)
  ⏳ dark-factory-eval-harness.md              (2d)
  ⏳ harness-taxonomy.md                       (1d)
  ⏳ local-harness-fix.md                      (2d)

🗺 canada-map (2)
  ⏳ canada-map-orchestrator-resume.md         (3d, stale?)
  ⏳ province-name-abbreviations.md            (1d)

📋 uncategorized (1)
  ⏳ proof-system-skill.md                     (8d, stale?)

6 awaiting  ·  3 stale
═══════════════════════════════════════════════════════
```

**Theme icons (best-effort):** Use contextual emoji for known themes. Fallback to `📌` for unrecognized themes. `📋` for uncategorized.

Visual indicators: `⏳` for `awaiting_initiation`. Append `(stale?)` for handoffs older than 3 days still awaiting. Show ages. Prepend `🤖` for entries with `autopilot: approved` (queued for unattended execution — see `/session:autopilot`); show `🤖✗` for `autopilot: failed` (needs human).

**Collapse a large queue — don't dump it.** A deep queue is noise that buries the 2-3 handoffs that matter. If more than **8** handoffs are `awaiting_initiation`, show the freshest 8 (across themes, newest `created` first) in full, then collapse the rest into one line per theme:

```
  … 22 older handoffs (11 stale >3d) — run /pickup --triage to sweep
```

Do not enumerate all of them. The full set is always one `/pickup --all` away; the point of the default view is signal, not the archive.

**With `--all` flag**, also show non-awaiting entries after the queue, grouped separately:

```
─── Active (initiated) ───
  ✅ dark-factory-ktp-681.md                   INITIATED (4d)

─── Completed ───
  ✅ dark-factory-ktp-679.md                   COMPLETED (4d)
  ✅ handoff-close-skill.md                    COMPLETED (3d)
```

Present awaiting ones via `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Which handoff do you want to pick up?",
    "header": "Pickup",
    "multiSelect": false,
    "options": [
      {"label": "{filename}", "description": "{theme} · {source_session} · {ticket} · {age}d old"}
    ]
  }]
}
```

### Targeted mode (`/pickup {filename}`)

Exact filename match against ledger entries' `file` field. No partial matching. No fuzzy search.

If not found: "File not found in ledger. Run `/pickup --list` to see available handoffs."

### Triage mode (`/pickup --triage`)

**Expiry sweep first (pre-triage).** Before presenting, compute each awaiting handoff's age from its ledger `created` timestamp and pre-classify, so triage leads with the items most likely to be dead weight:

1. **Age flag:** mark any handoff `awaiting_initiation` for **> 14 days** as a staleness candidate.
2. **Ticket-closed flag:** for handoffs with a real `related_ticket` (not `none`), batch-check Jira status via `jira_skill.py get <KEY>` (or `sprint-board`). If the ticket is **Done / Closed / Won't Do**, mark it a completion candidate — the work it points at is very likely already shipped.
3. Order the triage prompts **most-stale / ticket-closed first**, and in each option set make the recommended action the first option (`Done` for a closed-ticket handoff, `Abandon` for an ancient no-ticket one). The human still confirms every move — nothing is auto-archived.

**Quarantine, never delete.** Archiving moves the file to `sessions/archive/` (reversible); it is never `rm`. This mirrors the memory-prune governance (quarantine, human-confirm). A handoff whose ticket *looks* closed but has follow-up work is why the human confirms each one.

For each handoff (sweep order above), present batch triage via `AskUserQuestion` (group 2-4 at a time):

```json
{
  "questions": [{
    "question": "What should happen to '{filename}'?",
    "header": "Triage",
    "multiSelect": false,
    "options": [
      {"label": "Keep", "description": "Leave in active queue. Still needed."},
      {"label": "Autopilot", "description": "Approve for unattended execution (sets autopilot: approved; the scheduled runner will pick it up)."},
      {"label": "Done", "description": "Work completed. Archive to sessions/archive/done/."},
      {"label": "Abandon", "description": "No longer needed. Archive to sessions/archive/abandoned/."}
    ]
  }]
}
```

Archive actions (all ledger writes via the **helper** — never hand-edit `ledger.yaml`; see `bin/LEDGER_WRITES.md`):
- **Done**: `... update --section handoffs --key {file} --set status=completed --set archived={today}`, set the same in file frontmatter, move file to `sessions/archive/done/`.
- **Abandon**: `... update --section handoffs --key {file} --set status=abandoned --set archived={today}`, set the same in file frontmatter, move file to `sessions/archive/abandoned/`.
- **Autopilot**: `... update --section handoffs --key {file} --set autopilot=approved --set autopilot_approved={now} --set autopilot_attempts=0`. File stays in place, status stays `awaiting_initiation`.
- **Keep**: no change.

Apply all triage entry-edits in ONE `batch` call so the header bumps once (see `bin/LEDGER_WRITES.md` → Batch). The helper bumps `version`+`modified` for you.

**Report inflow, don't just prune harder.** At the end of a triage sweep, print a one-line summary: `Triaged: {kept} kept · {done} done · {abandoned} abandoned · {autopilot} autopilot → {N} still awaiting`. Handoff creation is expected inflow (the harness writes them every session); the sweep is garbage collection, not prevention. If the awaiting count stays high sweep-over-sweep, that signals upstream over-creation (`/session:handoff` firing too liberally) to fix at the source — not a reason to prune more aggressively.

## On pickup (list and targeted modes)

1. Read the handoff file from `sessions/active/prompts/{filename}`
2. If `status: awaiting_initiation`: edit file frontmatter to `status: initiated`, fill `## Initiated` section with date and time
3. Claim the handoff in the ledger via the **helper** (CAS — never hand-edit `ledger.yaml`): `... claim --key {filename} --expect-status awaiting_initiation --set status=initiated --set target_session={slug}`. If it exits with a claim conflict, another session already took it — inform the user instead of forcing.
4. If already `initiated` or `completed` (idempotent): inform user, ask if they still want the instructions
5. Display the file's `## Prompt` section as the session's starting context

## Archive directory structure

```
sessions/
├── active/
│   └── prompts/          # Live handoffs (awaiting or initiated)
└── archive/
    ├── done/             # Completed handoffs (work finished)
    └── abandoned/        # Dropped handoffs (no longer needed)
```
