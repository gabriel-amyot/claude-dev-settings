# Session Lifecycle: Five Skills, One Ledger

Five skills manage session lifecycle and cross-session continuity. Each has one verb. A shared ledger (`sessions/ledger.yaml`) is the coordination mechanism. A schema (`sessions/schema.yaml`) defines the folder contract.

## The skills

| Skill | Verb | Direction | What it does |
|-------|------|-----------|-------------|
| `/session-initialize` | Start | Inward | Extract intent, generate fun name (adjective-animal), scaffold session folder, build task list, suggest skills, write ledger entry |
| `/handoff` | Branch | Forward | Compress a tangent into a self-contained prompt for another session. Write to session's `prompts/`, update ledger. Idempotent by `related_ticket`. |
| `/pickup` | Resume | Inward | Read handoffs from ledger (not directory scanning). Exact filename match. Mark as initiated in ledger and file. `--list` for inbox view, `--triage` for batch archive. |
| `/report-back` | Report | Backward | Write a structured completion report (Result, Deliverables, Deferred, Surprises, State Updates, Side Output). Mark the original forward handoff as completed. Tone guard: facts only, no instructions. |
| `/session-check` | Assess | Present | Reconstruct intent tree, surface open branches, offer triage (Continue, Restart, Bookmark, Hand off + close, Close). Shutdown sequence updates ledger and archives session folder. |

## The ledger

`sessions/ledger.yaml` in the project-management directory. One file, versioned, timestamped. Every skill reads it, every skill writes it, every write increments `version`.

Two sections: `sessions` (active/paused/closed/abandoned) and `handoffs` (awaiting_initiation/initiated/completed/abandoned). The `parent`/`children` fields on sessions model the cross-session tree. The `closes` field on report-back entries links back to the original forward handoff.

## The lifecycle

**Fresh start:** `/session-initialize` asks until intent is clear, generates a fun name, scaffolds, checks ledger for related handoffs, builds tasks, presents session card.

**Resuming:** `/pickup` (or `/pickup --list`) reads ledger, presents menu, marks initiated. Then `/session-initialize` wires the new session as a child.

**Branching:** `/handoff` mid-session compresses a tangent into a tracked prompt file.

**Completing a branch:** `/session-check` detects the session started from a handoff and work is DONE. Invokes `/report-back` for a structured report, then proceeds to shutdown.

**Checking in:** `/session-check` at any point. Intent tree, context health, triage.

**Closing:** Shutdown sequence: update ledger (status: closed), archive session folder to `done/` or `abandoned/`, persist state, operationalize, librarian, report, repo cleanup, suggest `/clear` then `/session-initialize` or `/pickup`.

## Mental model

Message-passing between tabs. `/handoff` is send. `/report-back` is reply. `/pickup` is receive. `/session-initialize` is open. `/session-check` is status. The ledger is the mailbox. Session folders are workspaces. The schema is the building code.

## Key files

| File | Path | Role |
|------|------|------|
| Ledger | `sessions/ledger.yaml` | Master index. All skills read/write. |
| Schema | `sessions/schema.yaml` | Locked contract. Defines folder structure. |
| Design spec | `documentation/architecture/session-management-design.md` | Full architecture with examples. |
| Session folders | `sessions/active/{slug}/` | Per-session workspace (state.yaml, initial-intent.md, checkpoints/, prompts/, reports/) |
| Archive | `sessions/archive/done/` and `sessions/archive/abandoned/` | Terminal state folders |

All paths relative to the project-management directory.

## CLI Gotchas

`~/.claude/plugins/local-marketplace/session/bin/ledger.py` takes `--org {klever|supervisrai|...}` (or `--ledger PATH`) as a **global flag that must precede the subcommand**. `ledger.py claim --ledger ...` fails with `unrecognized arguments`; `ledger.py --org klever claim ...` works. One of `--org` or `--ledger` is required on every call.

**How to apply:** When scripting a `ledger.py` call, always put `--org`/`--ledger` immediately after `ledger.py` and before the verb (`claim`, `report-back`, etc.), never after.

**Source:** KTP-1039 ship + dev-validate session, Klever project (2026-08-04).

## Claim Keys May Be Full Relative Paths, Not Bare Filenames

`ledger.py claim --key <x>` matches a handoff entry's `file` field exactly. Some handoff entries
store the full relative path (`sessions/active/prompts/<name>.md`), not the bare filename. A
`ledger: handoffs has no file=<name>` error does not mean the entry is missing — it can mean the
key you passed is the wrong shape.

**How to apply:** On `ledger: handoffs has no file=<name>`, grep `sessions/ledger.yaml` for the
filename before concluding the entry does not exist. The real key may be the full relative path.

**Source:** session fierce-ibis, KTP-1062/1065 crit follow-through review, Klever project
(2026-08-12).
