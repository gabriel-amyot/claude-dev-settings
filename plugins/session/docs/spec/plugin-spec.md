# Session Plugin Specification

**Version:** 2.0.0 (unreleased)
**Last updated:** 2026-05-29

## Purpose

Session lifecycle management for Claude Code. Tracks intent across conversations, enables cross-session continuity via handoff prompts, and persists session artifacts for analysis.

## Architecture

### Data Model

**Primary state:** `sessions/ledger.yaml` in the project-management directory. Single file, versioned, all skills read/write.

**Session folders:** `sessions/active/{slug}/` for live sessions, `sessions/archive/{done|abandoned}/{slug}/` for closed sessions.

**Handoff files:** `sessions/active/prompts/` (or `sessions/active/{slug}/prompts/`). Self-contained prompt documents with YAML frontmatter.

**Intent trees:** `sessions/archive/{slug}/intent-tree.md` (persisted at close time).

### Lifecycle Phases

```
BIRTH           → init         (scaffold a session)
WORKING         → (no skill)
REFLECTION      → check        (where am I? what's open?)
COMMUNICATION   → handoff      (forward: prescriptive)
                  report-back  (backward: descriptive)
CONSUMPTION     → pickup       (receive a handoff)
DEATH           → check --close (end the session)
ANALYSIS        → insights     (learn from past sessions)
```

### Hook

**SessionStart** command hook (plugin-level, `hooks/hooks.json`). Reads ledger, counts awaiting handoffs, emits one-line nudge:
```
SESSION: N handoff(s) awaiting (M stale). Run /session:init or /session:pickup.
```

---

## Skills

### session:init

**Phase:** BIRTH
**Responsibility:** Scaffold a new session: intent, folder, tasks, ledger entry.
**Does NOT:** Resume handoffs (that's pickup).

**Flow:**
1. Extract intent (interactive, 2-4 exchanges if needed)
2. Check ledger for connections (handoff match, related session, fresh)
3. Generate fun name (adjective + animal, collision-checked)
4. Scaffold folder (`state.yaml`, `initial-intent.md`, `latest-answer.md`, subdirs)
5. Suggest skills (2-4 relevant, based on intent)
6. Build task list (3-7 tasks via TaskCreate)
7. Update ledger (session entry, handoff link if applicable)
8. Present session card

### session:check

**Phase:** REFLECTION + DEATH
**Responsibility:** Diagnose session state, recommend next action. Optionally execute shutdown.
**Does NOT:** Create handoffs on its own (delegates to `/handoff` for OPEN branches).

**Flags:**
- `/session:check` — full checkpoint: intent tree + health + triage
- `/session:check --close` — skip triage, execute shutdown

**Flow:**

**Phase 1a: Reconstruct Intent Tree**
Scan conversation history, build tree of every intent thread. Classify nodes: DONE (◉), OPEN (◎), ABANDONED (⊘), HANDOFF (⤴), TICKET (ticket emoji). Integrate TaskList results as ground truth for task-derived intents. Check ledger for existing handoff files before creating duplicates.

**Phase 1a-visual: Render Tree**
ASCII art tree with connectors, status symbols, file paths (absolute, clickable), and convergence notation. Summary line counts each status.

**Phase 1b: Resolve Open Branches**
For each OPEN node: AskUserQuestion (done / hand off / keep working / abandon). For "hand off": invoke `/session:handoff`. For each awaiting HANDOFF: AskUserQuestion (completed / initiated / still pending). Persist status changes immediately. For handoff-origin sessions: detect completion, propose `/report-back`. Re-render tree after resolution.

**Phase 1c: Evaluate Completion**
Synthesize overall status: ALL DONE, PARTIAL, BLOCKED, DRIFTED.

**Phase 1d: Context Health**
Rate: fresh / aging / compacted. Estimate context efficiency (% useful). Assess drift, re-reads, dead-end explorations.

**Phase 1e: Triage**
Present assessment + AskUserQuestion menu. Options drawn from: CONTINUE, RESTART, CLOSE, BOOKMARK, HAND OFF + CLOSE.

**Bias rule (v2):** If OPEN node count > 0 after Phase 1b, CLOSE is never the recommended option. User can still select it.

**Checkpoint Persistence:** On BOOKMARK or full check completion, persist tree to `sessions/active/{slug}/checkpoints/`.

**Path: CONTINUE** — Re-contextualize (re-render tree, highlight active branch, recommend next step). Skill ends.

**Path: RESTART** — Craft restart prompt, persist to file, proceed to shutdown.

**Path: CLOSE** — Proceed to shutdown.

**Retroactive init (v2):** If the session was never initialized (no slug, no folder), scaffold retroactively before shutdown. Generate slug, create archive folder, write ledger entry. Intent derived from intent tree root node.

**Shared scaffold contract:** Slug generation uses init's word lists (adjective + animal). Folder structure follows `sessions/schema.yaml`. Ledger entry follows established format. Both init and check implement independently but follow the same rules.

**Shutdown Sequence:**

| Phase | What |
|-------|------|
| S-1 | **Intent tree persistence (v2).** Write `intent-tree.md` to `sessions/archive/{slug}/`. Format per `sessions/schema.yaml` `intent_tree_format`. |
| S-0.5 | **Auto report-back (v2).** If session originated from a handoff, invoke `/report-back`. Automatic, no confirmation. |
| S0 | Update ledger (session status → closed/abandoned). Move session folder to archive. |
| S1 | Persist state. Git status per repo, propose commits, write state files. |
| S2 | Operationalize. Invoke `/operationalize`. Mandatory, never skip. |
| S3 | Librarian. Invoke `/bibliotheque-librarian`. |
| S4 | Report. Summary of intent, outcome, verdict, persisted artifacts. |
| S5 | Repo branch cleanup. Switch touched repos back to dev. |
| S6 | Clear. Tell user to run `/clear`. |

### session:handoff

**Phase:** COMMUNICATION (forward)
**Responsibility:** Create a deliberate forward prompt for another session.
**Does NOT:** Auto-sweep loose ends (that's check's shutdown).

**Flow:**
1. Locate current session in ledger
2. Check idempotency (match by `related_ticket`)
3. Write handoff file (dual-write: `/tmp/` + tracked location)
4. **Derive theme (v2).** Auto-derive from ticket epic or session context keywords. Ask user only when derivation fails.
5. Update ledger (new entry with `theme` field)

**Frontmatter:** `created`, `source_session`, `type: handoff`, `status: awaiting_initiation`, `related_ticket`.

**Ledger entry (v2):** Adds `theme` field. Example: `theme: canada-map`, `theme: harness`, `theme: session-mgmt`.

### session:pickup

**Phase:** CONSUMPTION
**Responsibility:** Present the handoff queue, initiate a specific handoff.
**Does NOT:** Scaffold a session (that's init).

**Modes:**
- `/pickup` or `/pickup --list` — **Default (v2): awaiting-only forward handoffs**, grouped by theme. `--all` shows everything (including completed, close reports).
- `/pickup {filename}` — targeted pickup by exact filename match.
- `/pickup --triage` — batch triage with keep/done/abandon per handoff.

**Themed display (v2):**
```
Handoff Queue (awaiting)
═══════════════════
🔧 harness (3)
  ⏳ dark-factory-eval-harness.md (2d)
  ⏳ harness-taxonomy.md (1d)
  ⏳ local-harness-fix.md (2d)

🗺 canada-map (2)
  ⏳ canada-map-orchestrator-resume.md (3d)
  ⏳ province-name-abbreviations.md (1d)

📋 uncategorized
  ⏳ proof-system-skill.md (8d, stale?)
```

Grouping key: `theme` field from ledger entry. Entries without theme go to "uncategorized."

### session:report-back

**Phase:** COMMUNICATION (backward)
**Responsibility:** Create a structured completion report to the parent session.
**Does NOT:** End the session (that's check --close).

**Template:** 6 fixed sections: Result, Deliverables, Deferred, Surprises, State updates, Side output.

**Flow:**
1. Find original forward handoff (by argument, or auto-detect from ledger)
2. Write report (dual-write)
3. Update original handoff status to completed
4. Update ledger (new entry for close report, update original entry)

### session:insights (v2, stub)

**Phase:** ANALYSIS
**Responsibility:** Analyze persisted intent trees for patterns and health.
**Does NOT:** Assess real-time session state (that's check).

**Modes (contracted, minimal implementation):**
- `/session:insights` — full analysis across all intent trees
- `/session:insights --ticket KTP-XXX` — one ticket's cross-session graph
- `/session:insights --patterns` — recurring sub-intent patterns (skill candidates)
- `/session:insights --health` — efficiency benchmarks + orphaned handoffs

**Input:** All `intent-tree.md` files from `sessions/archive/`.

**Schema contract (what insights expects):**
- Required: `session_slug`, `intent`, `closed`, `node_counts`, `tickets_referenced`
- Optional: `efficiency_estimate`, `context_health`, `handoffs_generated`

**Status:** Stub. Ships when 10+ intent trees accumulate.

---

## Data Contracts

### Ledger Entry — Session

```yaml
- slug: {adjective-animal}
  intent: "{one-liner}"
  org: {klever|supervisrai|personal}
  status: {active|paused|closed|abandoned}
  ticket: {Jira key or none}
  parent_session: {slug or null}
  started_from_handoff: {filename or null}
  children: [{slug list}]
  created: {ISO timestamp}
  closed: {ISO timestamp or null}
```

### Ledger Entry — Handoff (v2)

```yaml
- file: {filename}
  ticket: {Jira key or none}
  theme: {short tag or null}          # v2: grouping key
  status: {awaiting_initiation|initiated|completed|abandoned}
  source_session: "{description}"
  target_session: {slug or null}
  created: {ISO timestamp}
  modified: {ISO timestamp}
  closes: {filename or null}          # non-null for close reports
  version: {N}
```

### Handoff File Frontmatter

```yaml
---
created: {ISO timestamp}
source_session: "{description}"
type: {handoff|restart|followup|report-back}
status: {awaiting_initiation|initiated|completed|abandoned}
related_ticket: {Jira key or "none"}
closes: {filename or null}            # report-back only
---
```

### Intent Tree File (v2)

```yaml
---
session_slug: {slug}
intent: "{root intent}"
org: {org}
created: {session start}
closed: {close timestamp}
verdict: {CLOSE|RESTART|ABANDON}
node_counts:
  done: N
  open: N
  abandoned: N
  handoff: N
  ticket: N
efficiency_estimate: N%
context_health: {fresh|aging|compacted}
handoffs_generated: [filenames]
tickets_referenced: [KTP-XXX]
---

## Intent Tree
{Full ASCII tree}

## Open Branches at Close
{List of nodes still OPEN + their handoff paths}

## Session Timeline
- Started: {timestamp}
- Closed: {timestamp}
- Duration: {calculated}
- Compactions: {count}
```

---

## Composition Rules

- `check` may invoke `report-back` automatically when session originated from a handoff (during shutdown)
- `check` may invoke `handoff` for each OPEN branch during Phase 1b resolution
- `check` may recommend invoking `init` retroactively but never invokes init directly (shared contract, independent implementation)
- `init` may detect a handoff match and link to it, but `pickup` does the actual initiation
- `pickup` reads ledger only for list mode. Never reads handoff files for listing. File reads happen only during targeted pickup.

---

## File Structure

```
session/
├── .claude-plugin/plugin.json     # manifest
├── plugin.json                    # root manifest
├── CHANGELOG.md                   # version history
├── hooks/
│   ├── hooks.json                 # SessionStart hook declaration
│   └── session-init-reminder.sh   # hook script
├── docs/
│   ├── v2-design-decisions.md     # grill session output
│   ├── spec/
│   │   └── plugin-spec.md         # this file
│   └── adr/
│       ├── ADR-001-unified-check-skill.md
│       ├── ADR-002-plugin-level-session-hook.md
│       └── ADR-003-theme-in-ledger-only.md
└── skills/
    ├── init/SKILL.md
    ├── check/SKILL.md
    ├── handoff/SKILL.md
    ├── pickup/SKILL.md
    ├── report-back/SKILL.md
    └── insights/SKILL.md          # v2 stub
```
