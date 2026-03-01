---
name: gab-operationalize
description: Review chat history to identify repeatable procedures, then codify them as skills, agents, CLAUDE.md instructions, or README updates at the right scope level (repo, org, or user).
---

# Operationalize Skill

Turn ad-hoc Claude sessions into reusable, permanent knowledge. After a productive session where you taught Claude a workflow (tagging, deploying, testing, reviewing, etc.), invoke this skill to extract that knowledge and install it where future sessions will find it automatically.

**Usage:** `/operationalize [hint]`

**Examples:**
```
/operationalize                          # Scan full chat history, propose what to codify
/operationalize tagging and deployment   # Focus extraction on tagging/deployment procedures
/operationalize "testing workflow"       # Focus on testing-related procedures
```

## Arguments

`$ARGUMENTS` is an optional hint to focus the extraction. If empty, scan the full conversation.

## Execution: 4 Phases

You MUST execute these phases sequentially. Do NOT skip the user confirmation steps.

---

### Phase 1: Mine the Conversation

Review the entire chat history (or the hinted topic) and extract:

1. **Procedures** — Step-by-step sequences the user taught you (e.g., "first fetch, then rebase, then tag with `-dev` suffix, then push tag")
2. **Rules & Constraints** — Guardrails the user specified (e.g., "never run terraform apply", "always use `-dev` tags", "run tests before tagging")
3. **Decision Points** — Places where the user made a choice and explained why (e.g., "we use Cloud Run, not Cloud Functions, because...")
4. **Error Recovery** — How failures were handled (e.g., "if tests fail, fix and re-run, don't skip")
5. **Tool/Service Interactions** — External tools invoked and how (e.g., GitLab CI/CD, Jira, specific CLI commands)
6. **Context Dependencies** — What context was needed to perform the work (repo structure, config files, environment variables)

**Output format for presenting to user:**

```
## Procedures Found

### 1. [Procedure Name]
**Trigger:** When does this get invoked?
**Steps:**
1. Step one
2. Step two
...
**Rules:**
- Constraint A
- Constraint B
**Error handling:**
- If X fails, do Y

### 2. [Procedure Name]
...

## Implicit Knowledge Found
- [Things you inferred from context that should be documented]
```

Present this to the user using `AskUserQuestion`:
- "I found N procedures in this session. Which ones should I operationalize?"
- Options: list each procedure name, plus "All of them"
- `multiSelect: true`

---

### Phase 2: Design the Artifact

For each selected procedure, determine the best artifact type:

| Artifact Type | Best When | Example |
|---|---|---|
| **CLAUDE.md section** | Simple rules, constraints, preferences that apply broadly | "Never run terraform apply in DAC repos" |
| **README.md update** | Repo-specific developer workflow that humans also need | "How to tag and deploy this service" |
| **Skill** (slash command) | Multi-step interactive procedure with decision points | `/ship` — tag, test, deploy pipeline |
| **Agent** | Complex autonomous workflow requiring specific tools/model | `supervisr-ship` — full release orchestration |
| **Command** | Simple prompt template that delegates to existing tools | `/deploy-checklist` — pre-deployment verification |

**Decision logic:**
1. Is it just rules/preferences with no interactive steps? → **CLAUDE.md section**
2. Is it a procedure humans should also follow without Claude? → **README.md update** (+ optionally CLAUDE.md)
3. Is it a repeatable multi-step workflow with user interaction? → **Skill**
4. Is it a complex autonomous workflow that should run with minimal supervision? → **Agent**
5. Is it a simple prompt that kicks off a workflow? → **Command**

Present the proposal to the user:

```
## Proposal: [Procedure Name]

**Artifact type:** Skill
**Name:** `deploy-service`
**Why this type:** This is a multi-step interactive procedure (tag → test → deploy) with decision points (test failure handling) and guardrails (pre-tag checklist).

**Functionality:**
- Pre-flight checks (clean branch, up-to-date with origin)
- Tagging with version bump logic
- Test execution with retry on failure
- Deployment trigger via GitLab CI/CD

**Example invocations:**
```
/deploy-service                    # Full workflow
/deploy-service --skip-tests       # Skip test phase (if user explicitly wants)
/deploy-service --dry-run          # Preview what would happen
```

**Alternative considered:** CLAUDE.md section — but this has too many interactive steps and decision points for static instructions.
```

Then ask the user to confirm or iterate on the design.

---

### Phase 3: Choose Installation Level

Ask the user where to install using `AskUserQuestion`:

**Question:** "At what level should this be installed?"

| Level | Path | When to Use |
|---|---|---|
| **Repo-local** | `.claude/` in the target repo | Procedure is specific to one repository |
| **Org-level** | Project-management or shared config scoped to one org | Procedure applies to all repos in an org (e.g., all Supervisr repos) |
| **User-global** | `~/.claude/` (symlinked to `~/.claude-shared-config/`) | Procedure applies across all your projects |

Options:
1. **Repo-local** — "Only for this specific repository"
2. **Org-level** — "For all repos in this organization (e.g., Supervisr, Klever)"
3. **User-global** — "For all my projects everywhere"

If repo-local is selected, ask which repo (or infer from conversation context).

**Path resolution:**

- **Repo-local skill:** `{repo}/.claude/skills/{skill-name}/SKILL.md`
- **Repo-local agent:** `{repo}/.claude/agents/{agent-name}.md`
- **Repo-local CLAUDE.md:** `{repo}/CLAUDE.md` (append section) or `{repo}/.claude/CLAUDE.md`
- **Org-level:** Depends on org structure — for Supervisr: `~/Developer/supervisr-ai/project-management/tools/` or shared config
- **User-global skill:** `~/.claude-shared-config/skills/{skill-name}/SKILL.md`
- **User-global agent:** `~/.claude-shared-config/agents/{agent-name}.md`
- **User-global CLAUDE.md:** `~/.claude/CLAUDE.md` (append section)

---

### Phase 4: Generate and Install

Based on confirmed design and level:

1. **Generate the artifact** following the conventions of its type:
   - Skills: YAML frontmatter + detailed Markdown instructions (see existing skills for pattern)
   - Agents: YAML frontmatter (name, description, tools, model) + persona + instructions
   - CLAUDE.md: Well-structured section with clear headings
   - README.md: Developer-friendly documentation

2. **Show the full artifact to the user** before writing. Let them review and request changes.

3. **Write the file(s)** to the correct location.

4. **Propose progressive disclosure updates:**
   - If a skill/agent was created, propose adding a brief reference in the relevant CLAUDE.md so Claude knows when to suggest it
   - If repo-local, propose updating the repo's README.md with a "Workflows" or "Development" section describing available automations
   - If there's a related CLAUDE.md at a higher level, propose adding a one-liner pointer

5. **Summary:** Print what was created, where it lives, and how to invoke it.

```
## Installed

| Artifact | Path | Invoke |
|---|---|---|
| Skill: `deploy-service` | `~/.claude/skills/deploy-service/SKILL.md` | `/deploy-service` |
| CLAUDE.md update | `~/Developer/supervisr-ai/.../CLAUDE.md` | Auto-loaded |

**Next session:** Just say `/deploy-service` and Claude will know the full procedure.
```

---

## Memory Mode

**Usage:** `/operationalize --memory [hint]`

**Examples:**
```
/operationalize --memory                     # Extract reusable facts from session into persistent docs
/operationalize --memory "deployment flow"   # Focus memory extraction on deployment-related knowledge
```

`--memory` shifts the skill from "create a new artifact" to "extract and persist facts into existing documentation." Same Phase 1 extraction logic, different output target.

### Phase 1: Mine Facts

Same as standard Phase 1, but optimize for **atomic facts** rather than full procedures:

1. **Decisions made** — architectural choices, tool selections, trade-offs evaluated
2. **Patterns confirmed** — coding conventions, naming patterns, file placement rules
3. **Gotchas discovered** — things that didn't work, surprising behaviors, platform limitations
4. **Corrections applied** — wrong assumptions that were fixed during the session
5. **Preferences expressed** — user's stated preferences for workflow, style, tooling

For each fact, classify:
- **NEW** — not found in any existing documentation
- **MUTATE** — updates or refines something already documented
- **SKIP** — already documented accurately

Present the classified list to the user with `AskUserQuestion` (multiSelect). Only NEW and MUTATE items should be selected by default.

### Phase 2: Identify Target

Infer the target repo or project from conversation context (what repo was being discussed, what org the work belongs to).

Ask the user where to write using `AskUserQuestion`:
- **In-repo docs** — e.g., `{repo}/docs/decisions/`, `{repo}/agent-os/`
- **Shared config** — `~/.claude-shared-config/docs/`
- **Custom path** — user specifies

If the user selects in-repo docs, confirm the specific subfolder. If the target file doesn't exist yet, confirm the filename before creating it.

### Phase 3: Diff and Merge

For each selected fact:

1. Read the target file (if it exists)
2. For **NEW** items: append with a date tag `(YYYY-MM-DD)`
3. For **MUTATE** items: show the existing entry and proposed replacement side-by-side, ask user to confirm
4. For items that conflict with existing content: flag the conflict explicitly, don't silently overwrite

### Phase 4: Write and Confirm

1. Show the full proposed changes (diff-style) before writing
2. Write the updated file
3. Print summary: what was added, what was mutated, what was skipped

### Phase 5: Promote Check

After writing, check if any extracted facts should also live at a higher durability level:

- Fact in a docs file → should it also be in CLAUDE.md?
- Fact in a repo doc → should it also be in shared-config?
- Decision → should it be a formal ADR?

Propose promotions but don't auto-execute. Let the user decide.

---

## Guidelines

- **Don't over-engineer.** If a CLAUDE.md section is sufficient, don't create a skill. Simpler is better.
- **Preserve the user's voice.** The extracted rules should reflect what the user actually said, not a sanitized version.
- **Be specific, not generic.** "Tag format is `x.y.z-dev`" is better than "follow semantic versioning."
- **Include error paths.** The most valuable knowledge is often what to do when things go wrong.
- **Reference existing skills.** If the procedure uses existing skills (e.g., `/gitlab`, `/jira`), reference them rather than reimplementing.
- **Respect the CLAUDE.md hierarchy.** User-global instructions in `~/.claude/CLAUDE.md`, project instructions in repo CLAUDE.md. Don't duplicate.
- **Ask, don't assume.** When in doubt about scope, level, or naming — ask the user.
