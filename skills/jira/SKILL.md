---
name: jira
description: Access and query Jira issues. List issues assigned to you, get issue details, search with JQL, create new issues, and explore subtasks and epics. Use this skill whenever the user mentions Jira tickets, asks about their backlog, wants to fetch or create tickets, check what's assigned to them, look up a ticket key (like KTP-115 or INS-226), search for issues, add comments, transition ticket status, or asks "what's new for me" or "what should I work on". Also trigger when the user says "fetch ticket", "pull in the ticket", "create a story/bug/task", "check comments on", or references any Jira project key.
---

# Jira Skill

## Multi-Organization Support

This skill supports multiple Jira organizations with automatic detection based on your current working directory.

**Organizations**:
- **Klever**: Detected when working in `/Users/gabrielamyot/Developer/grp-beklever-com`
- **Supervisr AI**: Detected when working in `/Users/gabrielamyot/Developer/supervisr-ai`
- **Default**: Supervisr AI (when working outside organization directories)

**Setup** (one-time):
```bash
# Add organizations (already configured in jira_config.json)
~/.claude-shared-config/skills/jira/jira_config_setup.py add klever \
  https://beklever.atlassian.net gamyot@beklever.com \
  /Users/gabrielamyot/Developer/grp-beklever-com INS

~/.claude-shared-config/skills/jira/jira_config_setup.py add supervisrai \
  https://origin8cares.atlassian.net gamyot@origin8cares.com \
  /Users/gabrielamyot/Developer/supervisr-ai

# Configure API tokens (stored securely in macOS Keychain)
~/.claude-shared-config/skills/jira/jira_config_setup.py configure klever
~/.claude-shared-config/skills/jira/jira_config_setup.py configure supervisrai

# Set default organization
~/.claude-shared-config/skills/jira/jira_config_setup.py default supervisrai
```

**How it works**:
- The skill detects your organization by matching `$PWD` against configured paths
- Displays a disclaimer showing which organization was detected
- Use `--skip-disclaimer` to suppress the disclaimer message
- Use `--org ORG_NAME` to manually override auto-detection

**List configured organizations**:
```bash
~/.claude-shared-config/skills/jira/jira_config_setup.py list
```

## Agent Rules

**Before using this skill, read and follow the rules in [JIRA_AGENT_RULES.md](./JIRA_AGENT_RULES.md).** Key constraints:
- Never transition tickets to Done/Closed without explicit human confirmation
- All comments must include the `[automated]` attribution header
- Be honest about what has and has not been validated

## Instructions

Use this skill to interact with Jira issues through simple CLI commands. All commands return JSON data.

**Default behavior**: `list` returns only your open issues (excludes Done and Won't Do statuses) with minimal data (key, summary, status).

**Progressive data discovery**: Use the `--full` flag only when you need complete issue details to avoid wasting tokens.

**Available commands**:
- `fetch KEY [--output-dir DIR] [--depth N]` - **Materialize a ticket to disk** (see below)
- `list [--status STATUS] [--project KEY] [--max N] [--full]` - List issues
- `get KEY [--full]` - Get single issue details
- `subtasks KEY` - List subtasks of an issue
- `epic KEY` - Get parent epic of an issue
- `comments KEY` - Get all comments for an issue
- `description KEY` - Get raw description (verbatim)
- `metadata KEY` - Get all metadata (assignee, reporter, labels, links, etc.)
- `attachments KEY` - Get all attachments for an issue
- `download-attachment URL FILENAME [--output-dir DIR]` - Download an attachment
- `upload-attachment KEY FILEPATH` - Upload a local file as an attachment to an issue
- `search JQL [--max N] [--full]` - Raw JQL search
- `create --summary SUMMARY --type TYPE --project PROJECT [--description DESC] [--assignee USER] [--labels LABEL1,LABEL2] [--parent KEY]` - Create new issue (use --parent to create sub-tasks)
- `add-comment KEY --comment "BODY"` - Add a comment to an issue
- `delete-comment KEY --comment-id ID` - Delete a comment from an issue
- `transition KEY STATUS` - Transition issue to a new status
- `transitions KEY` - List available transitions for an issue
- `update KEY [--description DESC] [--summary SUMMARY] [--assignee USER] [--labels LABEL1,LABEL2] [--parent KEY]` - Update issue fields

## fetch — Materialize a Ticket to Disk

The `fetch` command is the standard way to pull a Jira ticket into the local project-management folder. It writes a consistent folder structure so every fetched ticket looks the same, regardless of org or project.

```bash
# Fetch a single ticket into current directory
cd ~/.claude/skills/jira && python3 jira_skill.py fetch KTP-100

# Fetch into a specific folder
cd ~/.claude/skills/jira && python3 jira_skill.py fetch KTP-100 --output-dir ./tickets

# Fetch an epic + all its children (depth 2)
cd ~/.claude/skills/jira && python3 jira_skill.py fetch KTP-115 --output-dir ./tickets --depth 2
```

**Output structure per ticket:**
```
KEY/
└── jira/
    ├── ticket.yaml             # Full metadata: parent, children (with local_path refs), links
    ├── description.md          # Verbatim Jira description
    ├── ac/                     # Only created if AC found
    │   ├── index.yaml          # All ACs with status (always refreshed on re-fetch)
    │   └── ac-NNN.md           # Per-AC scratchpad (write-once, preserved on re-fetch)
    └── comments/               # Only created if comments exist
        ├── index.yaml          # Comment index: author, date, preview, acknowledged, triage_task
        └── comment-001-*.md    # One file per comment
```
INDEX.md, STATUS_SNAPSHOT.yaml, and plan/ are owned by the pickup-ticket agent, not this script.

**Behaviour:**
- `--depth 1` (default): fetches the ticket only, lists children in `ticket.yaml` and `README.md` but does not recurse
- `--depth 2`: fetches ticket + all children one level deep
- `--depth N`: recurses N levels (use carefully on large epics)
- `INDEX.md` and `STATUS_SNAPSHOT.yaml` are owned by pickup-ticket — not written by this script
- `jira/ac/index.yaml` and `jira/comments/index.yaml` are always refreshed on re-fetch
- `jira/ac/ac-NNN.md` files are write-once — never overwritten (agent scratchpad preserved)
- AC extraction looks for headers: `Acceptance Criteria`, `AC:`, `Definition of Done`, `DoD:`

## Examples

List your open issues (compact output):
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py list
```

Get full details of a specific issue:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py get INS-226 --full
```

List your TO DO items in the INS project:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py list --status "TO DO" --project INS
```

Search for bugs in a project:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py search "project = INS AND type = Bug"
```

Create a new bug:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py create --summary "Bug: Login page broken" --type Bug --project INS --description "Login not working on mobile" --labels "bug,urgent"
```

Create a task assigned to someone:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py create --summary "Update documentation" --type Task --project INS --assignee gamyot@beklever.com
```

Create a sub-task under a parent issue:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py create --summary "Implement login API" --type Sub-task --project INS --parent INS-204
```

List subtasks of an issue:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py subtasks INS-204
```

Get the parent epic of an issue:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py epic INS-226
```

## Delegation to Haiku

All Jira API calls should be delegated to Haiku subagents. Jira operations are I/O-bound (network calls, JSON parsing) and do not require deep reasoning. Delegating to Haiku saves tokens on the orchestrator while keeping response times fast.

**Pattern:** Spawn a Haiku subagent with `model: "haiku"` for any `jira_skill.py` invocation. The subagent runs the command, parses the output, and returns a concise summary. The orchestrator (Opus/Sonnet) handles interpretation, decision-making, and user communication.

**Exception:** The `create` command requires the orchestrator to run the AC quality gate (Rule 6) and human gate (Rule 0) before delegating the actual API call.

## Create Command: Inline AC Quality Gate

Before creating any ticket, you must run the AC quality gate from [JIRA_AGENT_RULES.md](./JIRA_AGENT_RULES.md) Rule 6:

1. **Read the description template** at `~/.claude-shared-config/skills/templates/jira-ticket-description.md` before drafting. Follow its formatting rules exactly (Given/When/Then ACs, numbered lists, definitions at bottom).
2. Draft the ticket in story format: "As a [role], I want [capability], so that [benefit]"
3. Include at least 2 spec-based acceptance criteria using the Given/When/Then format from the template
4. Show the full draft to the user and wait for explicit confirmation (Rule 0)
5. If ACs are missing or task-based, flag them with a suggested rewrite before asking for confirmation

This gate is mandatory. The user can override with "create it anyway" but the agent must always present the quality check first.

## Post-Creation: Leo AC Scan

After creating or updating tickets with acceptance criteria, proactively suggest running a Leo AC scan:

- Spawn the `leo-ac-scan` agent on the newly created tickets
- Leo reviews ACs for: vague language, task-list ACs (not observable outcomes), actor-perspective gaps, missing coverage
- Present Leo's findings to the user, then incorporate approved fixes into both Jira and local files

This is not a hard gate. The user can skip it. But always offer it after creating tickets with ACs.

## Fetch Diff Workflow (Re-fetch)

When the user asks to check for updates on an already-fetched ticket:

1. **Check local state first.** Read the existing `jira/ticket.yaml` and `jira/comments/index.yaml` to understand what you already have
2. **Re-fetch from Jira.** Run `fetch` again (it refreshes `jira/ac/index.yaml` and `jira/comments/index.yaml` while preserving `ac-NNN.md` scratchpads)
3. **Diff and summarize.** Compare the refreshed indexes against what was there before. Surface:
   - New or changed comments (especially those with `acknowledged: false`)
   - AC status changes
   - Status transitions
   - New subtasks or links
4. **Present a human-readable summary**, not raw YAML diffs

## My Updates Workflow

When the user asks "what's new for me", "what should I work on", or "check my board":

1. Run `list` (no `--full`) to get open issues assigned to the user
2. Present a scannable summary: ticket key, summary, status, grouped by project
3. If the user wants more detail on a specific ticket, use `get KEY --full` or `fetch` as appropriate
4. Keep the initial response concise. The user can drill down on demand.