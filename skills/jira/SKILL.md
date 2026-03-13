---
name: jira
description: Access and query Jira issues. List issues assigned to you, get issue details, search with JQL, create new issues, and explore subtasks and epics.
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
├── README.md                   # Summary: status, assignee, links, AC checklist, child list
└── jira/
    ├── ticket.yaml             # Full metadata: parent, children (with local_path refs), links
    ├── description.md          # Verbatim Jira description
    ├── ac.yaml                 # Extracted acceptance criteria (omitted if none found)
    └── comments/               # Only created if comments exist
        ├── index.yaml          # Comment index: author, date, 100-char preview
        └── comment-001-*.md    # One file per comment
```

**Behaviour:**
- `--depth 1` (default): fetches the ticket only, lists children in `ticket.yaml` and `README.md` but does not recurse
- `--depth 2`: fetches ticket + all children one level deep
- `--depth N`: recurses N levels (use carefully on large epics)
- `README.md` is **not overwritten** if it already exists (preserves manual edits)
- All other `jira/` files are always refreshed on re-fetch
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