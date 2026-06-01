---
name: batch-skill-pipeline
description: Batch-create skills from approved proposals in ~/.claude/skill-proposals/. Trigger: "build all skills", "batch create skills", "create the skills", "build proposals", "skill pipeline", "build the Tier N skills", "build approved skills".
nav:
  bay: ops
  when: "Batch-create skills from approved proposals in skill-proposals/."
  when_not: "Creating a single skill (use skill-creator:skill-creator)."
---

# Batch Skill Pipeline

Turn a backlog of approved proposals into deployed skills in one pass. Dispatches parallel Sonnet subagents (one per proposal), validates each result structurally, gates on user review, then archives built proposals.

**Usage:**
```
/batch-skill-pipeline                   # List all proposals, user picks which to build
/batch-skill-pipeline --all             # Build every proposal in the inbox
/batch-skill-pipeline --file 2026-04-25-foo.md 2026-04-25-bar.md   # Build specific files
```

---

## Step 1: Inventory Proposals

List everything in `~/.claude/skill-proposals/` (excluding `archive/`).

For each file, read it and extract:
- Proposal name (from `# Skill Proposal: {name}` heading)
- Trigger phrase(s)
- Scope (global / org / repo-local)
- Draft Steps count

Present as a table:

```
| # | File                                  | Skill Name             | Scope  | Steps |
|---|---------------------------------------|------------------------|--------|-------|
| 1 | 2026-04-25-batch-skill-pipeline.md    | batch-skill-pipeline   | global | 6     |
| 2 | 2026-04-25-gateway-400-triage.md      | gateway-400-triage     | global | 4     |
...
```

If `--all` was passed, proceed to Step 2 with the full list. Otherwise, ask:

> "Which proposals should I build? Enter numbers (e.g., 1,3,5), a range (e.g., 1-5), or type 'all'."

Wait for the user's answer before continuing.

---

## Step 2: Read the Format Reference

Before dispatching subagents, read:
- `~/.claude/skills/gab-operationalize/SKILL.md` — canonical meta-skill format reference

Extract the YAML frontmatter format and structural conventions. Bundle these into each subagent's prompt so they produce consistent output without needing to read it themselves.

---

## Step 3: Build Skills (Orchestrator Writes, Subagents Research)

**CRITICAL SANDBOX CONSTRAINT (learned 2026-04-27):** Subagents CANNOT write to `~/.claude/skills/`. The sandbox restricts them to the project working directory. Pre-creating directories does not help. The Write tool itself is denied.

**Effective pattern:** Subagents research (read proposals, read reference skills, draft content). The ORCHESTRATOR writes all SKILL.md files from the main thread.

For each selected proposal:
1. Read the proposal file
2. Read one existing skill with a similar pattern for format reference
3. Pre-create the directory: `mkdir -p ~/.claude/skills/{skill-name}`
4. Write the SKILL.md directly from the orchestrator thread

Process up to 5 proposals in parallel using parallel Write tool calls from the orchestrator. For batches > 5, dispatch Sonnet subagents to read proposals and draft content to `/tmp/skill-drafts/{name}.md`, then the orchestrator copies to `~/.claude/skills/{name}/SKILL.md`.

Each SKILL.md must include:

**Subagent prompt template:**

```
You are building a new Claude Code skill from an approved proposal.

## Proposal
{full proposal text}

## SKILL.md Format
{format reference from gab-operationalize/SKILL.md}

## Output path
~/.claude/skills/{skill-name}/SKILL.md

## Instructions
1. Read the proposal carefully. Understand the trigger, scope, and draft steps.
2. Write a complete SKILL.md at the output path with:
   - YAML frontmatter: name + description (under 200 chars, includes trigger phrases)
   - Title and 1-2 sentence purpose statement
   - Usage block (slash command variants with flags if applicable)
   - Numbered steps with enough detail to execute without guessing
   - Error recovery section if the skill has failure modes
3. After writing, verify the file exists and run the structural checklist below.
4. Return a JSON result: {"skill": "{name}", "path": "{path}", "status": "PASS|FAIL", "checks": {...}, "notes": "..."}

## Structural Checklist
- [ ] frontmatter has both `name` and `description` fields
- [ ] description is under 200 characters
- [ ] description includes at least one trigger phrase from the proposal
- [ ] file has a top-level H1 heading
- [ ] file has at least one step or phase
- [ ] no placeholder text left unfilled (e.g., "{TODO}", "TBD", "PLACEHOLDER")
- [ ] if proposal mentions subagents: model guidance (Sonnet for execution) is present
- [ ] if proposal mentions file writes: INDEX.md update instruction is present
```

Use `model: "sonnet"` for all subagents. Run all in background (up to 5 at a time).

---

## Step 4: Collect Results and Structural Grades

As each subagent completes, read its returned JSON. Build a results table:

```
| Skill                  | Path                                          | Status | Notes                  |
|------------------------|-----------------------------------------------|--------|------------------------|
| gateway-400-triage     | ~/.claude/skills/gateway-400-triage/SKILL.md  | PASS   |                        |
| epic-reorganization    | ~/.claude/skills/epic-reorganization/SKILL.md | FAIL   | description > 200 chars |
```

For any FAIL:
1. Read the written SKILL.md to see what the subagent produced
2. Fix the specific failing check inline (do not re-dispatch a new subagent for minor fixes)
3. Update the table row to PASS with a note: "fixed: {what}"

Do NOT proceed to Step 5 if any skill remains in FAIL state.

---

## Step 5: User Review Gate

Present all newly built skills for review:

```
Built {N} skills:

1. gateway-400-triage
   Description: "Diagnose Apollo Gateway 400 errors. Trigger: 'gateway 400', 'Apollo gateway error', 'router returns 400'."
   Path: ~/.claude/skills/gateway-400-triage/SKILL.md

2. epic-reorganization
   Description: "Reorganize Jira epics and sub-tickets. Trigger: 'reorganize epics', 'restructure tickets', 'epic cleanup'."
   Path: ~/.claude/skills/epic-reorganization/SKILL.md
...

Do these look right? Type 'ship it' to archive proposals and register skills, 'hold {name}' to exclude one, or 'edit {name}: {instruction}' to request a change.
```

Wait for explicit approval before archiving. A response of "ship it", "looks good", "yes", or "all good" counts as approval. Do not auto-proceed on silence.

---

## Step 6: Archive Built Proposals

For each approved skill, move its source proposal to `~/.claude/skill-proposals/archive/`:

```bash
mv ~/.claude/skill-proposals/{original-filename}.md ~/.claude/skill-proposals/archive/{original-filename}.md
```

Run moves sequentially. After all moves, verify the archive directory contains the expected files.

Do NOT archive proposals for skills that were held or excluded by the user. Leave those in the inbox.

---

## Step 7: Report

Final summary:

```
Batch Skill Pipeline — complete

Built and deployed ({N} skills):
  - {skill-name} → ~/.claude/skills/{skill-name}/SKILL.md
  ...

Archived proposals:
  - ~/.claude/skill-proposals/archive/{filename}.md
  ...

Held (not archived):
  - {skill-name} — reason: user held for editing
  ...

Skills are immediately available. Invoke with /{skill-name} or via the Skill tool.
```

---

## Key Rules

- **Never build a skill from a proposal with no trigger phrase.** If the proposal's "Trigger" section is empty or vague, ask the user before dispatching.
- **Max 5 concurrent subagents.** Dispatch in batches. Wait for each batch to complete before starting the next.
- **Structural checks are gates, not suggestions.** Every check in the checklist must pass before archiving.
- **User approval is required before archiving.** Silent continuation is not approval.
- **Each subagent writes one skill.** Do not dispatch one subagent to build multiple skills. Parallel but independent.
- **The archive is permanent.** Do not move proposals to archive unless the skill file was verified to exist on disk after the subagent wrote it.
- **Held skills stay in the inbox.** They are not failures. The user may build them later or modify the proposal first.

---

## Error Recovery

**Subagent times out or fails:** Do not retry automatically. Note the skill as FAIL in the results table with "subagent timeout/error." After all other skills complete, report the failure to the user and offer to retry just that one.

**SKILL.md written but structurally invalid (unfixable inline):** Mark as FAIL, leave the file in place, do not archive the proposal. Show the user the file path and the failing check so they can inspect manually.

**Archive directory does not exist:** Create it before moving any files: write a placeholder or use the Write tool to create `~/.claude/skill-proposals/archive/.keep` if needed.

**More than 10 proposals selected:** Warn the user this will take multiple batches and confirm before starting. Estimate: ~2-3 minutes per batch of 5.
