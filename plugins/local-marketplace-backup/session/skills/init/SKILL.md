---
name: init
description: "Initialize a new session with intent extraction, fun name, folder scaffold, task list, and skill suggestions. Handles both fresh starts and handoff detection (checks ledger for related intents). Use when: 'new session', 'start fresh', 'initialize session', after /clear, or when a hook triggers on the first prompt of a new conversation."
---

# Session Initialize

Set up a new session: extract intent, scaffold folder, build task list, suggest skills.

**Load tools first:** `ToolSearch(query: "select:AskUserQuestion,TaskCreate")`

**Paths:** `sessions/schema.yaml` (read), `sessions/ledger.yaml` (read+write), `sessions/active/` (write). All relative to the project-management directory.

## Step 0: Bootstrap org infrastructure (first run in a new org)

The session system is per-org: each org's `project-management/sessions/` is self-contained and **must never reference another org's files** (no cross-org handoff pickup, no fallback to another org's ledger). The first time this skill runs in an org, that infrastructure won't exist yet. Create it before doing anything else.

Check for `sessions/schema.yaml` and `sessions/ledger.yaml` (relative to the project-management dir). If **either** is missing, bootstrap:

1. **`sessions/schema.yaml`** — write the canonical v2 schema verbatim. This file is org-agnostic and marked DO-NOT-MODIFY; copy it identically from any org that already has it (e.g. Klever's `project-management/sessions/schema.yaml`). Do not hand-edit per org.
2. **`sessions/ledger.yaml`** — create fresh via the **helper** (never hand-write it):
   `python3 ~/.claude/plugins/local-marketplace/session/bin/ledger.py --org <org> bootstrap`
   (creates `version: 1`, empty `sessions`/`handoffs`, atomically + refuses to clobber an existing ledger).
3. **`sessions/archive/done/`** and **`sessions/archive/abandoned/`** — create both (with `.gitkeep`).
4. Detect the org from CWD (Organizations table in global CLAUDE.md) and use that org slug everywhere below.

Announce briefly: "First session run in {org} — scaffolded sessions/ infrastructure." Then continue to Step 1.

**Org isolation invariant:** when reading the ledger (Step 2) or any handoff, only ever touch *this* org's `sessions/`. Never read, count, or pick up handoffs from another org's ledger.

## Step 1: Extract intent

This skill has two real entry modes. Pick the one that matches how the session started.

**Interactive (a human is present).** Ask the user what they're working on. Do not accept vague answers. Ask follow-up questions until the intent is clear and specific enough to act on. Target 2-4 exchanges if needed. Examples of insufficient intent: "fix stuff", "work on the project", "continue where I left off" (which one?).

If the user arrived via `/pickup`, the handoff file IS the intent. Summarize it and confirm.

**Autonomous (no human to ask).** If the session was dispatched by an orchestrator, a ralph-loop, or otherwise started with the intent already supplied as args or a task/dispatch message, take that supplied intent verbatim as the frozen intent. Do NOT ask questions — there is no one to answer, and fabricating an exchange is dishonest. Record `intent_source: autonomous` in `state.yaml` and skip straight to Step 2. (Interactive sessions record `intent_source: interactive`.) The launching agent owns intent quality in this mode; this skill does not challenge it.

## Step 2: Check ledger for connections

Read `sessions/ledger.yaml`:
- **Handoff match:** if any handoff entry with `status: awaiting_initiation` matches the stated intent by `ticket` or topic, flag it. Ask: "This looks related to handoff '{file}'. Link as continuation?" If yes, mark handoff `status: initiated` and set `target_session` to the new session slug. Set `started_from_handoff` in state.yaml.
- **Related session:** if an active session covers overlapping work, mention it. Ask if this is intentional parallel work or accidental duplication.
- **Fresh:** no parent, no handoff link. Proceed.
- **Queue-depth nudge (don't dump):** count `awaiting_initiation` handoffs. If more than 8, surface only the count and staleness, not the list — e.g. "31 handoffs awaiting (14 stale >3d). Run `/pickup --triage` to sweep." A growing queue is noise; nudge toward triage instead of listing all of it here.

## Step 3: Generate fun name

Two word lists. Pick one adjective + one animal, then run the collision check below. Retry on collision.

**Check the ledger, not just the folders.** Folders are archived and pruned; the ledger keeps every session forever. A slug that is free on disk can already be taken in the ledger, which is how 10 duplicate slugs got in. Both checks must pass:

```bash
# 1. ledger (authoritative — every session ever, closed ones included)
ledger --org <org> get --section sessions --key {slug} >/dev/null 2>&1 && echo TAKEN || echo FREE
# 2. folders (active + archived)
ls -d sessions/active/{slug} sessions/archive/{slug} sessions/archive/*/{slug} 2>/dev/null
```

Only a slug that is FREE in the ledger AND matches no folder may be used. `get` exits 0 when the slug exists, so exit 0 means TAKEN.

**Adjectives:** brave, calm, swift, quiet, bold, keen, wise, warm, sharp, bright, noble, gentle, steady, fierce, clever, happy, quick, strong, merry, witty, grand, deep, crisp, wild, cool, free, true, clear, fresh, neat, plain, prime, rare, safe, tidy, vast, vivid, agile, lucid, deft

**Animals:** falcon, otter, lynx, heron, panda, fox, wolf, hawk, raven, crane, finch, cobra, viper, eagle, bison, stork, owl, bear, seal, lark, pike, wren, robin, toad, newt, moth, wasp, dove, crow, crab, deer, hare, mole, swan, kite, ibis, tern, shrike, jackal, badger

## Step 4: Scaffold folder

Read `sessions/schema.yaml` for the contract. Create:

```
sessions/active/{slug}/
  state.yaml
  initial-intent.md
  latest-answer.md        (empty placeholder)
  knowledge-manifest.yaml (seeded — see below)
  checkpoints/
  prompts/
  reports/
```

Write `initial-intent.md` with the frozen intent (verbatim from the user's final statement, not paraphrased).

Write `knowledge-manifest.yaml` (per schema `knowledge_manifest_format`). This is the session's in-session memory of captured knowledge — `/operationalize` appends to it on every run, and `/session:check` close reads `last_run` to confirm capture happened before tearing the session down:
```yaml
session_slug: {slug}
created: {ISO timestamp}
last_run: null        # set by the first /operationalize run
run_count: 0
nuggets: []           # {subject, inbox_file, captured} — cumulative dedup ledger
skills: []            # {name, proposal_file, captured}
runs: []              # {at, mode, nuggets_added, skills_added}
```

Write `state.yaml`:
```yaml
session_slug: {slug}
org: {detected from CWD}
status: active
intent: "{one-liner}"
intent_source: {interactive | autonomous}   # how Step 1 resolved intent
ticket: {Jira key or none}
parent_session: {parent slug or null}
started_from_handoff: {handoff filename or null}
drift: none
generation: 0
context_health: fresh
tasks: []
suggested_skills: []
created: {ISO timestamp}
last_activity: {ISO timestamp}
```

## Step 5: Suggest skills

Surface 2-4 relevant skills based on the intent. Use your knowledge of the skill catalog (floor-manager bays: build, fix, review, ship, plan, know, ops). Be specific, not generic. Mention `/bmad-help` for BMAD workflow guidance.

## Step 6: Build task list

Break the intent into 3-7 concrete tasks via `TaskCreate`. Each task should be actionable and specific. If the intent came from a handoff, use the handoff's implementation steps.

## Step 7: Update ledger

**Never hand-edit `sessions/ledger.yaml`** (a hook blocks it). Use the **helper** — it locks, journals, validates, and bumps `version`+`modified`. Reference: `bin/LEDGER_WRITES.md`.

1. Append this session: `... append --section sessions --json '{"slug":"{slug}","intent":"...","org":"<org>","status":"active",...}'`
2. If linked to a handoff, claim it: `... claim --key {file} --expect-status awaiting_initiation --set status=initiated --set target_session={slug}`
3. If linked to a parent session, add this slug to the parent's children: `... update --section sessions --key {parent} --append-list children={slug}`

## Step 7.5: Commit the scaffold (survive git clean)

Immediately commit the freshly scaffolded bookkeeping so it is **born tracked**, never long-lived-untracked. Untracked files under `sessions/active/` are the one thing a `git clean` (or a `checkout`/`stash` that discards untracked working changes) can silently destroy. Committing here closes that window at creation time.

```
git add sessions/active/{slug}/ sessions/ledger.yaml
git commit -q -m "session({slug}): scaffold — init state.yaml, manifest, ledger entry"
```

Do this on `main` (project-management is single-trunk; never branch here). If the commit fails (e.g. nothing staged), continue — do not block session start on it.

> Why: on 2026-06-30 a prior session's untracked `state.yaml` + `knowledge-manifest.yaml` were wiped mid-run by a `sessions/`-scoped working-tree reset during a suspension gap; only the just-written file survived. Committing at scaffold time makes the bookkeeping immune to that mechanism regardless of which command triggered it.

## Step 8: Present session card

```
Session: {slug}
Intent: "{intent}"
Tasks: {N} created
Ticket: {key or none}
Parent: {slug or none}

Relevant skills: {list}
Workflow help: run /bmad-help for BMAD guidance
```
