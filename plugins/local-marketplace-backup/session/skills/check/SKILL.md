---
name: check
description: "Intent tracker, session health check, and session closer. Reconstructs a visual tree of every intent thread pursued in the session, surfaces open branches, persists handoff prompts to disk, and offers triage (CONTINUE, BOOKMARK, RESTART, or CLOSE). On close: persists intent tree to archive, auto-invokes report-back for handoff-origin sessions, retroactively scaffolds uninit'd sessions. Use when: 'session check', 'where was I', 'what's open', 'should I close?', 'am I done?', 'wrap up', 'close session', 'done for now', 'check my intents'."
---

# Session Check

Intent tracker and health check for Claude Code sessions. This is NOT primarily an "end session" tool. It's a checkpoint: reconstruct what you've been working on, surface open threads, offer next steps. Closing is one option among several.

Call it anytime: mid-session when you feel lost, after returning from a break, when you want to see what threads are open, or when you're ready to wrap up. Each invocation builds the intent tree from conversation context and persists it as a checkpoint, so the next call can build on the last.

**Usage:**
```
/session-check              # Full checkpoint: intent tree + health + triage
/session-check --checkpoint # Capture nuggets + intent tree, then stop (no triage, no close)
/session-check --close      # Capture nuggets (final), then the full shutdown + close
```

**Every invocation captures.** `--checkpoint` and `--close` both run `/operationalize` to flush this session's knowledge to disk before doing anything else. `--checkpoint` is the "I'm not closing, just persist now and show me my tree" milestone; `--close` captures then tears the session down. This is how knowledge is never lost to a close: it is written through to the bibliothèque inbox at every checkpoint, and the close is gated on capture having run.

---

## Tool Loading (MANDATORY FIRST STEP)

This skill uses the `AskUserQuestion` tool for native Claude Code menus and the `TaskList` tool for task integration. **Before starting Phase 1**, load both:

```
ToolSearch(query: "select:AskUserQuestion,TaskList")
```

Every interactive decision point in this skill must use the `AskUserQuestion` tool, not prose questions. The tool presents a native UI menu. Parameters:
- `questions`: array of question objects (1-4 per call)
- Each question: `question` (string), `header` (string, max 12 chars), `options` (array of 2-4 objects with `label` + `description`), `multiSelect` (boolean, always `false` for this skill)
- Users always get a built-in "Other" option for free-text input. Do not add one manually.

**If you catch yourself writing a question as plain text instead of calling the tool, STOP and use the tool.**

---

## Pre-check: Handoff-Origin Detection

Before building the intent tree, read `sessions/ledger.yaml` in the project-management directory. Check whether the current session started from a handoff: look for a session entry with `started_from_handoff` set, or check if the session's work matches a handoff entry's `ticket` field. If a match is found, record the originating handoff file path for use in Phase 1b (completion detection).

The cross-session handoff view is owned by `/pickup --list`. Session-check focuses on the current session only.

---

## Phase 1: Assess

### 1a. Reconstruct Intent Tree

Scan the full conversation history and build a tree of every intent the user pursued. This is retrospective: you're reconstructing what happened, not tracking in real time. The user may have never stated these as explicit goals, so read between the lines.

**How to identify intents:**

An intent is any thread of work the user initiated or that emerged naturally. Look for:
- The opening ask (the root intent)
- Tangents triggered by errors, curiosity, or discovered problems ("wait, let me check this first...")
- Investigations spawned by unexpected results ("why is this returning null?")
- Side-requests ("while we're here, can you also...")
- Debugging branches ("this test is failing, let me look into...")
- External lookups ("I need to check Jira / BQ / the vendor docs for this")

**Building the tree:**

Walk the conversation chronologically. Each new thread of work becomes a node. When a thread spawns a sub-thread, that's a child node. When the user returns to a parent thread after finishing (or abandoning) a child, that's a convergence. Some patterns:

- **Fork:** User starts debugging mid-feature. The debug thread is a child of the feature thread.
- **Converge:** Debug finishes, user returns to the feature. The child merges back.
- **Orphan:** User starts an investigation, gets distracted by something else, never comes back. The branch stays open.
- **Handoff:** User says "I'll check this in another session" or "I need to ask someone about this." The branch terminates with an external dependency.

**Classify each intent node:**

| Status | Symbol | Meaning |
|--------|--------|---------|
| **DONE** | `◉` | Evidence exists: code committed, question answered, user confirmed satisfaction |
| **OPEN** | `◎` | Started but not closed. No evidence of completion or explicit abandonment. |
| **ABANDONED** | `⊘` | Explicitly dropped ("skip this", "nevermind", "not going to pursue") |
| **HANDOFF** | `⤴` | Needs work in another session or by another person. Requires a handoff prompt. |
| **TICKET** | `🎫` | Resolved by creating a Jira ticket. The ticket creation IS the closure. |

**Every OPEN node is a problem.** The whole point of this tree is to surface open branches so the user can close them. When you present the tree, OPEN nodes should visually stand out as unresolved.

**Task list integration:**

Before rendering the intent tree, call `TaskList` to check for native Claude Code tasks. If tasks exist, each task maps directly to an intent node:

| Task status | Intent symbol | Meaning |
|-------------|---------------|---------|
| `completed` | `◉` DONE | Task finished |
| `in_progress` | `◎` OPEN | Task active but unfinished |
| `pending` | `◎` OPEN | Task not yet started |

Merge task-derived intents into the conversation-derived intent tree. Tasks often correspond to intents you already identified from the conversation. When a task's subject matches an existing intent node, use the task's status as ground truth (it's more precise than inferring completion from conversation flow). When a task has no matching conversation intent, add it as a new node.

If no tasks exist (TaskList returns empty), skip this step silently. Not every session uses tasks.

**Handoff rules:**

When an intent is classified as HANDOFF, you must:
1. Check `sessions/ledger.yaml` handoffs section: does an entry already exist for this handoff? Match by `related_ticket` (exact, skip when "none").
2. **If a prompt file exists:** reference it. Do not create a duplicate. Use the file's current `status` to set the tree node's display.
3. **If no prompt file exists:** write a clear, self-contained handoff prompt (see "Prompt Persistence" below). Set `status: awaiting_initiation`.
4. During the resolution phase (1b), the user can update the status interactively. Changes are persisted to the file immediately.

**Completion detection from handoff origin:**

If the pre-check detected that this session started from a handoff (via `sessions/ledger.yaml`), and the intent tree shows the handoff's work as DONE, flag the handoff for completion marking in Phase 1b. The session-check proposes: "This session completed the work from handoff '{name}'. Mark it as completed?"

### Prompt Persistence

Every handoff prompt, restart prompt, or any prompt generated during the session check gets written to disk. Prompts are the bridge between sessions and tabs. They must survive context loss.

**File location:** `sessions/active/prompts/` in the project-management directory (create if it doesn't exist).

**File naming:** `{YYYY-MM-DD}-{short-slug}.md` (e.g., `2026-05-20-statscan-fsa-coverage.md`)

**File format:**
```markdown
---
created: {ISO timestamp}
source_session: {original intent one-liner}
type: handoff | restart | followup
status: awaiting_initiation | initiated | completed
related_ticket: {Jira key if any, or "none"}
---

## Prompt

{The full, self-contained prompt. Ready to paste into a new session.}

## Context

{Why this prompt exists. What was being worked on when it was generated.
Enough context that someone reading this file cold understands the ask.}

## Initiated

{Empty until the user confirms initiation. Then: date, session/tab where it was picked up.}
```

**In the intent tree**, link to the file using its **absolute path** so it's clickable in the terminal. Most terminal emulators (iTerm2, VS Code integrated terminal, Warp, Ghostty) auto-detect absolute paths and make them cmd-clickable:

```
⤴ HANDOFF — "Cross-ref with StatsCan boundary files"
           📄 /Users/gabrielamyot/Developer/grp-beklever-com/project-management/sessions/active/prompts/2026-05-20-statscan-fsa-coverage.md
           Status: AWAITING INITIATION
```

Always use the full absolute path, never relative. This applies to all file references in the tree: prompt files, checkpoint files, and ticket report files. The user needs to click and open, not copy-paste and mentally resolve relative paths.

**Lifecycle:**
- **Created** during session-check or `/handoff` → `status: awaiting_initiation`
- **Initiated** when a new session picks up the handoff (via `/pickup`) → `status: initiated`, `## Initiated` filled
- **Confirmed** during session-check triage when user updates status interactively
- **Completed** when the handoff's work is done → `status: completed`, `## Completed` filled
- **Archived** → file moved to `sessions/archive/done/` (completed) or `sessions/archive/abandoned/` (dropped)
- The RESTART prompt from Path: RESTART also gets persisted here (type: restart)

**Pickup Signal:** Handoffs are picked up via `/pickup`. That skill handles marking files as initiated and updating the ledger.

**Completion Signal (how `completed` gets set):**

When `/session-check` runs at the end of a session that originated from a handoff (detected in the pre-check via `sessions/ledger.yaml`), and the intent tree shows that handoff's work as DONE, session-check proposes marking the handoff as `completed`. On confirmation:
1. Set `status: completed` in the YAML frontmatter
2. Add a `## Completed` section:
   ```
   Completed: {YYYY-MM-DD}
   Work confirmed done during session-check.
   ```
3. Move the file to `sessions/archive/done/` (create directory if needed)

**Why files instead of inline:** You have many tabs. You forget which tab has which intent. The `sessions/active/prompts/` folder becomes your cross-session inbox. You can `ls` it anytime to see all open handoffs across all sessions. The file IS the contract between the session that created the work and the session that picks it up.

### 1a-visual. Render the Intent Tree

Output the tree as ASCII art. This is the centerpiece of the session check. The user should see, at a glance, every thread they pursued and whether it was resolved.

**Format:**

```
Intent Tree
═══════════════════════════════════════════════════════

◉ Root Intent — e.g., "Debug KTP-667 Canada map rendering"
├── ◉ Sub-intent — "Read error logs from Cloud Run"
├── ◉ Sub-intent — "Fix province boundary GeoJSON loading"
├── ◎ Sub-intent — "Investigate FSA-to-CensusDivision gaps"  ⚠ OPEN
│   ├── ◉ Sub-sub — "Query BQ for missing FSA codes"
│   └── ⤴ HANDOFF — "Cross-ref with StatsCan 2021 boundary files"
│              Prompt: "Check StatsCan 2021 census boundary
│              shapefiles for FSA coverage gaps in NS/NB/PE"
│              Status: AWAITING INITIATION
├── 🎫 Sub-intent — "Track font rendering inconsistency" → KTP-712
└── ◉ Sub-intent — "Push fix to dev branch"

Summary: 5 DONE  ·  1 OPEN  ·  1 HANDOFF  ·  1 TICKET  ·  0 ABANDONED

⚠ 2 branches need resolution before session close
═══════════════════════════════════════════════════════
```

**Visual rules:**
- Tree uses `├──`, `└──`, `│` connectors (standard tree drawing)
- OPEN nodes get a `⚠ OPEN` suffix in the tree, making them impossible to miss
- HANDOFF nodes show the prompt file path and tracked status from `sessions/ledger.yaml`:
  - `✅ INITIATED` or `✅ COMPLETED` for handoffs that were picked up or finished
  - `⏳ AWAITING` for handoffs not yet picked up
- TICKET nodes show the Jira key they spawned
- The summary line at the bottom counts each status
- If any OPEN or uninitiated HANDOFF nodes exist, a warning line appears

**Convergence notation:** When a branch feeds its result back into a parent, use `⤵` to show the merge:

```
◉ Root — "Implement store detail panel"
├── ◎ Branch — "Debug why metrics return null"  ⚠ OPEN
│   ├── ◉ Investigation — "Check Placer API response shape"
│   └── ◉ Investigation — "Verify BQ adapter wiring"
│       ⤵ Found: adapter was using wrong column name
├── ◉ Resumed — "Fix column name in adapter" (informed by branch above)
└── ◉ Final — "Push and create MR"
```

This shows the debugging branch fed a finding back into the main line. The user can see the causal chain.

### 1a.5 Init Detection (v4)

If this session was never initialized via `/session:init`, surface that **now — not at close**. Running an entire session uninit'd is what forces `/operationalize` into legacy mode (no `knowledge-manifest.yaml` to stamp) and leaves checkpoints homeless. Catching it here gives the session a manifest from the first check onward, which is the actual fix for the "why did operationalize run in legacy mode?" surprise.

**Detect:** is there an active session folder under `sessions/active/{slug}/` that maps to this conversation's work (matching intent/ticket, or the sole active session)? Cross-reference `sessions/ledger.yaml`.

- **If a session folder already exists:** skip this step silently — already initialized.
- **If NOT initialized, gate the offer on substance:** only offer when the intent tree has real accumulated work (≥2 substantive nodes, or any node involving code/file writes/a completed deliverable). A two-message throwaway does not need ceremony — skip silently.

When the offer applies, **call the `AskUserQuestion` tool**:

```json
{
  "questions": [{
    "question": "This session was never initialized, so it has no manifest — capture runs in legacy mode and checkpoints have no home. Scaffold it now?",
    "header": "Init",
    "multiSelect": false,
    "options": [
      {"label": "Scaffold it now (Recommended)", "description": "Create the session folder + manifest + active ledger entry so capture and checkpoints work for the rest of the session."},
      {"label": "Keep it ephemeral", "description": "No folder. Capture stays in legacy mode; close will retro-scaffold if needed."}
    ]
  }]
}
```

**On "Scaffold it now":** run the SAME scaffolding as the "Retroactive Init" section below, with one difference — write the ledger entry with `status: active` (not `closed`) and seed `state.yaml` as active. Use the intent tree's root label as the intent. From this point the session behaves as if `/session:init` had run: subsequent `/operationalize` stamps the manifest instead of falling back to legacy, and `--checkpoint` has somewhere to persist.

This is the early, in-session counterpart to Retroactive Init (which remains the close-time fallback for sessions that were never scaffolded here). Do not call the full `/session:init` skill — it re-interrogates for intent you have already demonstrated in the tree; reuse the lightweight scaffolding only.

### 1b. Resolve Open Branches

Before proceeding to context health assessment, every OPEN and HANDOFF node must be resolved.

**For each OPEN intent**, call the `AskUserQuestion` tool:

```json
{
  "questions": [{
    "question": "Intent '{name}' is still open. How should we close it?",
    "header": "Open Intent",
    "multiSelect": false,
    "options": [
      {"label": "It's done", "description": "Mark as DONE. No further action needed."},
      {"label": "Hand off", "description": "Write a handoff prompt for another session or create a ticket."},
      {"label": "Keep working", "description": "Continue this intent before closing the session."},
      {"label": "Abandon", "description": "Mark as ABANDONED. Won't pursue further."}
    ]
  }]
}
```

If the user selects "Hand off", ask a follow-up about whether they want a handoff prompt or a Jira ticket. The built-in "Other" option covers any edge case.

> **Never bundle "then close" into these options.** The four choices above are about resolving *this open branch* only. Do not invent a composite option like "do it now, then close" — that smuggles a teardown decision into a work-resolution choice and bypasses the dedicated teardown gate. "Keep working" continues the branch; closing is decided separately at the Phase 1e triage and confirmed again at the Teardown Gate (G0). Keeping work and closing are distinct decisions and must stay distinct.

**For each HANDOFF with `AWAITING INITIATION`**, call the `AskUserQuestion` tool:

```json
{
  "questions": [{
    "question": "Handoff '{name}' — what's the status?",
    "header": "Handoff",
    "multiSelect": false,
    "options": [
      {"label": "Completed", "description": "Work is done. Archive the prompt file."},
      {"label": "Initiated", "description": "Picked up but not finished. Mark as in progress."},
      {"label": "Still pending", "description": "Not started. Will be flagged in the report."}
    ]
  }]
}
```

**Persist the status change immediately after each answer:**

1. **If "Completed":** Edit the prompt file's YAML frontmatter to `status: completed`. Add a `## Completed` section with today's date. Move the file to `sessions/archive/done/` (create directory if needed).

2. **If "Initiated":** Edit the prompt file's YAML frontmatter to `status: initiated`. Fill the `## Initiated` section with today's date and a note: "Confirmed during session-check triage."

3. **If "Still pending":** No file change. Remains in the ledger as awaiting.

**For handoffs that originated this session (detected in pre-check):**

If the current session started from a handoff (per `sessions/ledger.yaml`), and the intent tree shows the handoff's work as DONE, propose running `/report-back` to produce a structured completion report before marking the handoff completed. The close report captures Result, Deliverables, Deferred items, Surprises, State Updates, and Side Output. This is the artifact the parent session needs to resume intelligently. Just flipping a status flag loses that context.

On confirmation, invoke `/report-back` (which handles both the report and the status update), then continue to shutdown.

After resolving all open branches, re-render the tree with updated statuses. The tree should now show zero `⚠ OPEN` warnings (though uninitiated handoffs may remain, which is acceptable since they're tracked).

If the user chose "Keep working on it now" for any intent, the session check pauses. You hand control back to work on that intent. When the user calls `/session-check` again, the tree reconstruction picks up where it left off.

### 1c. Evaluate Overall Completion

With the intent tree resolved, synthesize an overall status. This replaces the old single-status assessment:

| Overall Status | Meaning |
|--------|---------|
| **ALL DONE** | Every leaf node is DONE, ABANDONED, TICKET, or HANDOFF (initiated). No open work. |
| **PARTIAL** | Mix of DONE and ABANDONED/HANDOFF. Core intent may be done but branches are not. |
| **BLOCKED** | Critical intents are HANDOFF (awaiting initiation). Can't proceed without external input. |
| **DRIFTED** | The tree's branches are mostly unrelated to the root intent. Session went sideways. |

### 1d. Assess Context Health and Efficiency

Check for signs of context degradation and estimate how much of the context window is actually serving the original intent.

**Context health signals:**
- Has context compaction occurred? (System messages about compressed prior messages)
- Has the session run long with many tool calls?
- Are there gaps in your recall of earlier work?
- Would you need to re-read files you already worked with?

Rate: **fresh** (no compaction, good recall) | **aging** (long session, some gaps) | **compacted** (compaction occurred, operating on partial memory)

**Context efficiency estimate:**

You can't count tokens directly, but you can estimate how much of the context budget is serving the intent vs. wasted on noise. Evaluate these signals:

| Signal | How to check | What it means |
|--------|-------------|---------------|
| **Compaction count** | System messages about "compressed prior messages" | Each compaction means the window filled and was compressed. History before compaction is lossy. |
| **Drift ratio** | What fraction of the conversation was on-topic vs. tangential? | If 60% was tangential, ~60% of accumulated tokens are noise relative to intent. |
| **Re-reads** | Did you re-read files you already worked with earlier? | Doubled token cost for the same information. Sign of context loss. |
| **Error/retry cycles** | Failed commands, debugging tangents, dead-end explorations | Pure overhead that a fresh session wouldn't carry. |
| **Skill/tool output bloat** | Large tool outputs, verbose system reminders, repeated skill listings | Fixed overhead that compounds over turns but wouldn't exist in a fresh session's early turns. |

Synthesize into an estimate:

```
**Context efficiency:** ~{N}% useful
- Compactions: {0|1|2+}
- Drift overhead: ~{N}% of conversation off-topic
- Re-reads: {count} files read multiple times
- Dead-end explorations: {count}
- Restart savings: A focused prompt would recover ~{N}% of context budget
```

This is a heuristic, not a measurement. But it makes the CONTINUE vs. RESTART decision concrete: if estimated useful context is below ~40%, a restart almost always wins. The restart prompt is ~500 tokens. The accumulated noise is orders of magnitude more.

### 1e. Triage Decision

Use your judgment across three factors to pick an outcome:

**→ CONTINUE** when:
- Intent is PARTIAL or NOT STARTED
- Context is fresh or aging (not compacted)
- The remaining work is well-defined and achievable in this session
- No significant drift

**→ RESTART** when:
- Intent is PARTIAL and the remaining work is still valuable
- BUT context is compacted or aging, OR significant drift occurred
- A fresh session with a good prompt would be more efficient than fighting stale context
- The task hasn't changed, the session just got tired

**→ CLOSE** when:
- Intent is DONE (mission accomplished)
- OR drift is terminal (the session went somewhere unrelated and there's nothing to salvage)
- OR the user explicitly wants to shut down (`--close`)

**Bias rule (v2):** If any OPEN nodes remain after Phase 1b resolution, **never recommend CLOSE** as the primary option. The user can still select it from the AskUserQuestion menu, but the "(Recommended)" label must go to CONTINUE or RESTART. This prevents check from "selling" close when work is genuinely incomplete. See ADR-001.

Present the assessment as text (including the intent tree from Phase 1a), then **immediately call the `AskUserQuestion` tool** to let the user decide. Do NOT ask as prose text.

**First**, output the assessment block:

```
## Session Check

{Intent Tree from Phase 1a-visual — render the full ASCII tree here}

**Overall completion:** ALL DONE | PARTIAL | BLOCKED | DRIFTED
**Context window:** ~{N}k tokens used (estimate from conversation length, tool calls, system prompts)
**Context health:** fresh | aging | compacted
**Context efficiency:** ~{N}% focused on root intent
  - {What the context is concentrated on — e.g., "90% on KTP-667 Canada map debugging, 10% on side investigation into font rendering"}

**Verdict: {CONTINUE | RESTART | CLOSE}**

**Rationale:** {2-3 sentences explaining WHY this verdict, not the others. Be specific about what evidence drives the recommendation. What would need to be different for a different verdict?}

**If you keep going:** {1-2 contextual suggestions for what this session's accumulated context could still be useful for. These should be concrete, not generic. Leverage the domain knowledge, file reads, and investigation results already in context. Examples: "You've already loaded the BQ schema and Placer API docs — wiring the new adapter column would be efficient here." Or: "The debugging revealed a stale assertion in StatePerformanceBigQueryAdapterTest — fixing it now saves a future session the ramp-up." If genuinely nothing, say "No adjacent work identified — context is narrowly spent."}
```

**Then call the `AskUserQuestion` tool.** Select up to 4 options from the pool below based on what makes sense for the verdict and context. The recommended option should be first with "(Recommended)" in the label. Omit options that don't apply (e.g., skip "Continue" when ALL DONE, skip "Restart" when context is fresh).

```json
{
  "questions": [{
    "question": "Session is {verdict}. What do you want to do?",
    "header": "Session",
    "multiSelect": false,
    "options": [
      {"label": "{Verdict action} (Recommended)", "description": "{Why this is the best path}"},
      {"label": "Continue here", "description": "Context is {health}. {What remains or keep-going suggestions}."},
      {"label": "Bookmark + pause", "description": "Persist intent tree checkpoint to disk. Resume later with /session-check."},
      {"label": "Close it down", "description": "Persist state, operationalize, librarian, shut down."}
    ]
  }]
}
```

Pick the 3-4 most relevant options. "Restart fresh" and "Close it down" are both valid choices depending on verdict. The built-in "Other" option covers anything unusual.

> **One action per option. Never compose a "do more work, then close" option** (e.g. "do it now, then close"). That bundling is exactly what produces a surprise teardown: the user picks it to get the work done and does not realize they also authorized the archive/ledger/branch-switch ceremony. If the user wants to finish an open branch before deciding, that is "Continue here" — closing is then re-offered on the next `/session-check`. A close (or restart) selection here only routes *into* the Shutdown Sequence; the Teardown Gate (G0) still confirms before anything is torn down.

**Additional option — "Hand off + close":** When the session is PARTIAL and has unresolved OPEN intents, include this option: `{"label": "Hand off + close", "description": "Write handoff(s) for remaining work, then shut down."}`. If selected, invoke `/handoff` for each unresolved intent, then proceed to the shutdown sequence.

**Session handoff summary:** Before the triage question, if any handoff or report-back files were created during this session, render a brief summary:

```
Handoffs created this session:
  → 2026-05-26-ktp681-canadian-region.md (awaiting)
  ← 2026-05-26-ktp679-crosswalk-close.md (close report)
```

Use `→` for forward handoffs, `←` for close reports. This gives the user a consolidated view of what this session produced for other sessions before deciding how to exit.

### Checkpoint Persistence

When the user selects "Bookmark and pause" (or when a full session-check completes), persist the intent tree as a checkpoint:

**File location:** `sessions/active/checkpoints/` in the project-management directory.

**File naming:** `{YYYY-MM-DD}-{HHmm}-checkpoint.md`

**File format:**
```markdown
---
created: {ISO timestamp}
root_intent: {one-liner}
completion: {ALL DONE | PARTIAL | BLOCKED | DRIFTED}
context_tokens_estimate: {N}k
context_health: {fresh | aging | compacted}
open_branches: {count}
---

## Intent Tree

{The full ASCII tree as rendered}

## Open Branches

{List of OPEN/HANDOFF nodes with their current status}

## Suggestions

{The "if you keep going" suggestions from the assessment}
```

On the next `/session-check` invocation, read the latest checkpoint file first. Use it as a baseline: the tree should extend or update from where the checkpoint left off, not rebuild from scratch. This makes repeated session-checks cheaper and more accurate, since each call only needs to reconstruct what happened since the last checkpoint.

**Then branch based on the user's selection**, not your verdict.

---

## Path: CHECKPOINT (`--checkpoint`)

The user wants to persist accumulated knowledge mid-session and see their intent tree, without closing. This is a milestone, not a teardown.

1. **Capture first.** Invoke the **`gab-operationalize`** skill (the `/operationalize` command — **not** `operationalize-audit`, which only reviews the backlog) and wait for completion. It mines the session for new nuggets, writes them through to the bibliothèque inbox, and stamps the session's `knowledge-manifest.yaml` (`last_run`, a new `runs` entry). Because dedup is by subject, a second or third checkpoint in the same session only extracts what's genuinely new — repeat runs are cheap.
2. **Show the intent tree** (Phase 1a-visual output) plus a one-line capture summary: "Captured N new nugget(s); manifest now holds M total."
3. **Stop.** No triage menu, no shutdown, no ledger status change. The session stays `active`.

`--checkpoint` skips Phase 1b/1c triage entirely. Skill ends here.

---

## Path: CONTINUE

The session still has value. Re-orient the user and give them direction.

### Re-contextualization

The intent tree IS the re-contextualization. The user can see exactly where they are. Supplement with a brief text summary:

```
## Where You Are

{Re-render the intent tree, highlighting the active branch with → arrow}

**Last thing you did:** {the most recent meaningful action}
**Open branches:** {count and names of OPEN intents from the tree}
**Recommended next:** {the most logical next intent to work on, with reasoning}
```

Then **call the `AskUserQuestion` tool** to present the next step options:

```json
{
  "questions": [{
    "question": "What should we tackle next?",
    "header": "Next step",
    "multiSelect": false,
    "options": [
      {"label": "{Most logical next step} (Recommended)", "description": "{Why this is the right next move}"},
      {"label": "{Alternative next step}", "description": "{What this path involves}"}
    ]
  }]
}
```

The recommended option should be concrete enough that selecting it means "do it." Not "continue working on X" but "implement Y in file Z."

Skill ends here for CONTINUE. No cleanup, no operationalize, no close.

---

## Path: RESTART

The task is worth continuing, but this session is the wrong vehicle. Craft a handoff prompt and then run shutdown.

### Craft the Restart Prompt

Write a self-contained prompt the user can paste into a new `/clear`'d session or a new terminal. This prompt must contain everything the new session needs to pick up without reading the old conversation:

```
## Restart Prompt

Copy and paste this into a fresh session:

---

{The prompt. Should include:
- What the task is and why it matters (context the new session won't have)
- What was already done (so it doesn't repeat work)
- What remains (specific next steps)
- Key decisions already made (so the new session doesn't re-litigate)
- Relevant file paths and ticket IDs
- Any gotchas discovered during this session}

---
```

The prompt should be practical, not a novel. Aim for the minimum context needed to resume at full speed. Include file paths, ticket IDs, branch names. Exclude narrative about the old session's journey.

**Persist the restart prompt to file** using the Prompt Persistence format from Phase 1a (type: `restart`). Show the user both the inline prompt and the file path:

```
📄 Saved to: /Users/gabrielamyot/Developer/grp-beklever-com/project-management/sessions/active/prompts/2026-05-20-restart-canada-map-debug.md

You can paste the prompt above into a fresh session, or just point it at the file:
"Read /Users/gabrielamyot/Developer/grp-beklever-com/project-management/sessions/active/prompts/2026-05-20-restart-canada-map-debug.md and resume."
```

After presenting the restart prompt, proceed to the **Shutdown Sequence** below.

---

## Path: CLOSE

Intent reached or drift is terminal. Proceed to the **Shutdown Sequence** below.

---

## Retroactive Init (v2)

> **This is the close-time fallback.** The preferred path is the early offer in Phase 1a.5 (Init Detection, v4), which scaffolds the session the first time you run `/session-check` so capture never falls into legacy mode. This section still runs at close for sessions that were never scaffolded — e.g. a direct `/session-check --close` on an uninit'd session, or when the 1a.5 offer was declined. If 1a.5 already scaffolded the session, this is a no-op.

Before starting the shutdown sequence, check whether this session was initialized via `/session:init`. Look for an active session entry in `sessions/ledger.yaml` whose `slug` matches a folder in `sessions/active/`.

**If the session was never initialized** (no slug, no folder, no ledger entry):

1. **Generate a slug** using init's word lists (adjective + animal). Check for collision against **both the ledger and the folders**, and retry on collision. The ledger is the authoritative namespace: folders get archived and pruned, so a slug free on disk can already be taken in the ledger. Skipping the ledger check is how 10 duplicate slugs got in.
   ```bash
   ledger --org <org> get --section sessions --key {slug} >/dev/null 2>&1 && echo TAKEN || echo FREE
   ls -d sessions/active/{slug} sessions/archive/{slug} sessions/archive/*/{slug} 2>/dev/null
   ```
   Use the slug only when the ledger says FREE and no folder matches.
   - **Adjectives:** brave, calm, swift, quiet, bold, keen, wise, warm, sharp, bright, noble, gentle, steady, fierce, clever, happy, quick, strong, merry, witty, grand, deep, crisp, wild, cool, free, true, clear, fresh, neat, plain, prime, rare, safe, tidy, vast, vivid, agile, lucid, deft
   - **Animals:** falcon, otter, lynx, heron, panda, fox, wolf, hawk, raven, crane, finch, cobra, viper, eagle, bison, stork, owl, bear, seal, lark, pike, wren, robin, toad, newt, moth, wasp, dove, crow, crab, deer, hare, mole, swan, kite, ibis, tern, shrike, jackal, badger

2. **Create an active folder** (so the rest of the shutdown — capture, gate, archive move — runs identically to a normal session; Phase S0 moves it to `archive/done/` at the end):
   ```
   sessions/active/{slug}/
     state.yaml               (status: active, created/last_activity = now)
     knowledge-manifest.yaml  (seeded — see below)
   ```
   Seed `knowledge-manifest.yaml` per schema `knowledge_manifest_format`:
   ```yaml
   session_slug: {slug}
   created: {ISO now}
   last_run: null
   run_count: 0
   nuggets: []
   skills: []
   runs: []
   ```
   This is what lets Phase S-2 capture stamp `last_run` and the close gate pass even for a session that was never formally initialized. Without it, capture would have nowhere to record its run and the gate would deadlock.

3. **Append the ledger session entry via the helper** (never hand-edit): `... append --section sessions --json '{"slug":"{slug}","intent":"{root label}","org":"<org>","status":"closed","created":"{ISO}","closed":"{ISO}"}'` — see `bin/LEDGER_WRITES.md`.

This ensures every closed session has a consistent shape in the archive. The shared scaffold contract (slug generation, folder structure) is documented in `sessions/schema.yaml`. Both init and check implement independently but follow the same rules.

---

## Shutdown Sequence (CLOSE and RESTART both run this)

Phases executed in order. (v2: added S-1 and S-0.5; v3: added S-2 capture-first; v4: added Gate G0 + delegated persistence)

### Gate G0: Teardown Confirmation — RUNS FIRST (v4)

**Teardown is its own explicit decision. It is never a side effect of an earlier option.** Before anything below runs (capture, archive, ledger write, branch switch), confirm the user actually wants to close.

**When the gate is auto-satisfied (skip the prompt):** the user reached this sequence by selecting a clean, teardown-only option at the Phase 1e triage — its label was exactly "Close it down", "Restart fresh", or "Hand off + close" with nothing else bundled in. That selection IS the confirmation; proceed to S-2.

**When the gate MUST prompt:** the path here came through any option that bundled ongoing work with closing (a composite like "do it now, then close"), or through `--close` issued while OPEN branches were still unresolved, or you are at all unsure how teardown was authorized. In those cases, **call the `AskUserQuestion` tool** before proceeding:

```json
{
  "questions": [{
    "question": "Ready to close {slug}? This will capture knowledge to the bibliothèque, archive the session folder, mark it closed in the ledger, and switch touched repos back to dev.",
    "header": "Teardown",
    "multiSelect": false,
    "options": [
      {"label": "Close it down (Recommended)", "description": "Run the full shutdown now."},
      {"label": "Not yet — keep working", "description": "Abort teardown. Return to the session; nothing is archived."},
      {"label": "Bookmark + pause", "description": "Persist a checkpoint, leave the session active. No teardown."}
    ]
  }]
}
```

Only "Close it down" proceeds to Phase S-2. Anything else aborts the teardown: do NOT capture, archive, write the ledger, or switch branches. The cost of one extra confirm is trivial; a surprise teardown is not. **When in doubt, prompt.**

> **Delegation (volume control, v4).** The deterministic file I/O in this sequence — S-1 (write `intent-tree.md`), the S0 file move + ledger patch *after the orchestrator has computed the idempotency/collision decisions below*, and S1 (state files) — should be bundled into a **single subagent task** (Sonnet) that executes the concrete operations and returns a one-line manifest. Show only that one line; do not narrate each write. The orchestrator keeps the *decisions* (G0 confirm, S0 idempotency/collision/lock logic, the S1 git AskUserQuestion) and hands the subagent only unconditional, pre-decided operations to execute. Capture (S-2) stays in the orchestrator — it needs full conversation context. The subagent performs the ledger patch by invoking the **`ledger` helper** (Bash), not the Write tool — the helper is the only sanctioned writer (a PreToolUse hook blocks hand-edits). The helper's own operationalize gate enforces capture; it passes because S-2 already ran and stamped the manifest.

### Phase S-2: Capture (Operationalize) — RUNS FIRST (v3)

**Capture before you tear anything down.** This phase runs before ledger update, archival, and state persistence, so knowledge is on disk before the session ceases to exist.

Invoke the **`gab-operationalize`** skill (via the `Skill` tool — this is the `/operationalize` command) and wait for completion. It mines THIS conversation, writes nuggets through to the bibliothèque inbox, and stamps `last_run`. Even if every nugget was already captured at an earlier checkpoint, the run still stamps `last_run` — that fresh stamp is what the close gate reads.

> ⚠️ **Use `gab-operationalize`, NOT `operationalize-audit`.** They are near-twins and easy to confuse. `gab-operationalize` (command `/operationalize`) mines the *current session* and routes to the inbox — this is the one close needs. `operationalize-audit` (command `/operationalize-audit`) only *reviews the backlog* of past captures and does NOT capture this session — running it does not satisfy this phase, and the hardened gate will reject it (no inbox file produced).

This is not optional and it is not a judgment call. The mechanical backstop (`session-close-operationalize-guard.sh`) **blocks the Phase S0 ledger write** unless `last_run` is fresh AND the session's manifest references a bibliothèque inbox file that exists on disk (proof `gab-operationalize` actually routed knowledge, not just that a stamp was written). A skipped or wrong-skill capture cannot reach a closed session regardless of reasoning. Run it.

**Volume (v4):** at close, surface only a one-line capture summary (e.g. `Captured 3 nuggets → inbox/2026-06-10-foo.md`). The nuggets are written to disk; do not echo their contents into the transcript.

### Phase S-1: Intent Tree Persistence (v2)

Persist the reconstructed intent tree to disk for cross-session analysis.

**File location:** `sessions/archive/{slug}/intent-tree.md` (the slug comes from the active session or from retroactive init above).

**File format:** Per `sessions/schema.yaml` `intent_tree_format`:

```markdown
---
session_slug: {slug}
intent: "{root intent from tree}"
org: {detected from CWD}
created: {session start timestamp, from state.yaml or ledger}
closed: {now, ISO timestamp}
verdict: {CLOSE | RESTART | ABANDON}
node_counts:
  done: {count}
  open: {count}
  abandoned: {count}
  handoff: {count}
  ticket: {count}
efficiency_estimate: {N}%
context_health: {fresh | aging | compacted}
handoffs_generated: [{list of handoff filenames created this session}]
tickets_referenced: [{list of Jira keys from tree nodes}]
---

## Intent Tree

{Full ASCII tree from Phase 1a-visual, exactly as rendered}

## Open Branches at Close

{List of nodes still OPEN at close time, with their handoff file paths if handoffs were generated.
If all branches resolved: "None — all branches resolved before close."}

## Session Timeline
- Started: {timestamp}
- Closed: {timestamp}
- Duration: {calculated human-readable, e.g., "2h 15m"}
- Compactions: {count, 0 if none detected}
```

Create the directory if needed (`mkdir -p sessions/archive/{slug}/`). If the archive folder already exists (e.g., from a previous close attempt), overwrite the intent-tree.md.

### Phase S-0.5: Auto Report-Back (v2)

If this session originated from a handoff (detected in the pre-check via `sessions/ledger.yaml` `started_from_handoff` field), invoke `/session:report-back` automatically. No user confirmation needed. The handoff contract demands a structured completion report so the parent session can resume intelligently.

If the session did NOT originate from a handoff, skip this phase silently.

### Phase S0: Update Ledger and Archive Session

This phase is **idempotent and collision-safe**. Sessions close in parallel terminals that share one ledger and one folder namespace; a bare `mv` and a blind ledger overwrite corrupt that shared state. Compute these checks FIRST, in the orchestrator, before handing any operation to the persistence subagent.

**Pre-flight checks (orchestrator decides; never delegate these):**

1. **Already-closed → no-op.** Read this `{slug}`'s ledger entry. If its status is already `closed`/`abandoned` AND `sessions/archive/done/{slug}/` (or `archive/abandoned/{slug}/`) already exists on disk, this session was already archived (an earlier or parallel close beat you to it). Do **not** move, do **not** re-flip status, do **not** clobber the archive copy. Log `Already closed — idempotent no-op` and skip straight to Phase S1. This is the case the "pragmatic close" was hand-working around; it is now the defined behavior.

2. **Awaiting-handoff safety.** Handoff prompts normally live in the shared `sessions/active/prompts/`, but if any prompt file inside *this session's* folder has `status: awaiting_initiation`, **relocate it to `sessions/active/prompts/` BEFORE the move** so archiving never buries a still-pickup-able handoff. Note each relocation in the report.

3. **Destination-exists guard (genuine collision).** If the archive destination already exists but the ledger does **not** mark this session closed (a real slug collision, not an already-done close), do **not** overwrite. Move to a suffixed path `sessions/archive/done/{slug}-{YYYYMMDD-HHmm}/` instead and flag the collision in the report. `mv` must never clobber an existing archive directory — use `test -e` (or `mv -n` and verify) first.

**Ledger write (via the helper — its flock replaces the old optimistic-lock dance):**
Never hand-edit `sessions/ledger.yaml` (a PreToolUse hook blocks it). The helper takes the lock, re-reads, validates, journals, and bumps `version`+`modified` atomically, so a stale-copy overwrite is impossible even under a parallel close. Reference: `bin/LEDGER_WRITES.md`.
1. If this session's entry already exists (normal init'd session): `... update --section sessions --key {slug} --set status=closed --set closed={ISO}` (use `status=abandoned` for terminal drift).
2. If the session was never init'd (retroactive scaffold at close): `... append --section sessions --json '{"slug":"{slug}","intent":"...","org":"<org>","status":"closed","created":"{ISO}","closed":"{ISO}"}'`.
3. Any completed handoffs to flip in the same close: fold them into a single `batch` call (see `bin/LEDGER_WRITES.md` → Batch) so the header bumps once.

**Move the session folder** (skip entirely if pre-flight check 1 hit the no-op, or if no folder exists in legacy mode):
- **CLOSE:** `test -e sessions/archive/done/{slug} || mv sessions/active/{slug}/ sessions/archive/done/{slug}/` (collision → suffixed path per check 3)
- **ABANDONED:** same pattern into `sessions/archive/abandoned/{slug}/`

### Phase S1: Persist State

**Identify all repos touched during this session.** Check every repo you navigated to, modified files in, or ran commands against. For each, run `git status`.

Categorize uncommitted changes:
- **Session-created:** You wrote or modified these during this session
- **Pre-existing:** Dirty state from before the session started
- **Unknown:** Can't determine origin

**For session-created uncommitted changes:**
1. Show `git diff --stat` to the user
2. Propose a commit message
3. **Call the `AskUserQuestion` tool** per repo:

```json
{
  "questions": [{
    "question": "Uncommitted changes in {repo}. What should we do?",
    "header": "Git",
    "multiSelect": false,
    "options": [
      {"label": "Commit (Recommended)", "description": "Commit with message: '{proposed message}'"},
      {"label": "Leave as-is", "description": "Keep uncommitted. Next session sees them as dirty state."},
      {"label": "Stash", "description": "Stash changes so the repo is clean but work is preserved."}
    ]
  }]
}
```

Pre-existing or unknown changes: mention they exist, do not touch them.

**Write state files:**

If a **ticket context** exists (ticket folder, branch with ticket ID):
- Update `STATUS_SNAPSHOT.yaml` with current progress
- Update `jira/ac.yaml` if ACs were worked on
- Write session summary to `reports/status/session-check-{YYYY-MM-DD}.md`:
  ```markdown
  ---
  session_date: {date}
  intent: {original intent}
  outcome: {what was accomplished}
  verdict: {CLOSE | RESTART}
  drift: {none | description}
  repos_touched: [{list}]
  ---
  ## What was done
  {bullet points}
  ## What remains
  {bullet points, or "Nothing — work complete."}
  ## Decisions made
  {with rationale}
  ## Pickup instructions
  {What the next session should do first}
  ```

If a **plan file** exists: update it. Mark completed steps, note resume point.

If **no ticket context:** write `SESSION_STATE.md` in the primary working directory.

**Multi-repo sweep:** for sessions spanning multiple repos, persist state in each. The session summary in project-management lists ALL repos and their state.

### Phase S2: Operationalize — ALREADY DONE in Phase S-2 (v3)

Capture now runs **first** (Phase S-2, top of this sequence) so knowledge is persisted before any teardown, and so the close gate can verify it. Do not run `/operationalize` again here. This phase is retained only as a marker; the work happened at S-2.

### Phase S3: Librarian

Invoke `/bibliotheque-librarian` to process pending inbox entries (including anything Phase S-2 produced).

Wait for completion. Fold its result into the S4 one-liner (`Librarian: processed N` or `inbox empty`); do not reproduce its full processing log in the transcript.

### Phase S4: Report

**Keep this short — the full record already lives on disk.** Do NOT re-render the intent tree here; it was written to `intent-tree.md` (Phase S-1) and shown earlier at triage. The close report is a confirmation, not a recap. Aim for ≤8 lines. Use a one-line capture/librarian summary, not the nugget dump.

```
**Session {closed | handed off} — {slug}** (ledger v{N})

{1-line outcome}
Persisted: {N files, M commits} · Captured: {N nuggets → inbox} · Librarian: {processed N | inbox empty}
Loose ends: {1-2 items, or "none"}
Next: {CLOSE: "complete" or "remaining in {path}"} · {RESTART: "paste restart prompt / point at {path}"}
```

If the user wants detail, it is one `cat` away at the archived `intent-tree.md` and the session summary. Offer the path; do not pre-expand it.

### Phase S5: Repo Branch Cleanup

Switch touched repos back to dev so the next session starts clean.

**For each repo under `~/Developer/grp-beklever-com/` that was touched during this session:**

1. Run `git -C {repo} branch --show-current` to see what branch it's on
2. If the branch is NOT dev/main/master (i.e., it's still on a feature branch):
   - Check if the branch was pushed: `git -C {repo} branch -r | grep {branch}`
   - If pushed (MR was created): `git -C {repo} checkout dev && git -C {repo} pull origin dev`
   - If NOT pushed (work still in progress): leave it alone, note it in the report
3. Report which repos were switched back

**Detection method:** Check repos you navigated to, ran `git` commands in, or modified files in during this session. Also check repos mentioned in commits from this session's work.

```
## Repo Cleanup
| Repo | Branch | Action |
|------|--------|--------|
| {repo} | {branch} → dev | Switched (branch was pushed) |
| {repo} | {branch} | Left (unpushed work in progress) |
```

If a repo has uncommitted changes, do NOT checkout dev. Leave it and note it as "dirty, left as-is."

### Phase S6: Clear

Tell the user:

> Session wrapped. Run `/clear`, then `/session-initialize` or `/pickup` to start fresh.
