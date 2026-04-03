---
name: status-index
description: Generate STATUS_SNAPSHOT.yaml for any ticket using acceptance-criteria-weighted completion. Supports recursive indexing from leaf tickets up to epics with progressive disclosure.
---

# Status Index Skill

Generate or refresh `STATUS_SNAPSHOT.yaml` for a ticket or epic.

**Usage:** `/status-index <ticket-path> [--dry-run] [--push-jira]`

**Examples:**
```
/status-index SPV-3/SPV-8        # Index single leaf ticket
/status-index SPV-3              # Index entire epic (recursive, bottom-up)
/status-index SPV-3 --dry-run    # Preview without writing files
/status-index SPV-3 --push-jira  # Index + post status comment to Jira
/status-index SPV-3/SPV-8 --push-jira  # Index leaf + post to its Jira ticket
```

## Arguments

`$ARGUMENTS` is the ticket path relative to the `tickets/` directory in the current project-management folder.

Parse arguments:
- **ticket_path**: First argument (required). E.g., `SPV-3/SPV-8` or `SPV-3`
- **--dry-run**: If present, print the generated YAML to stdout instead of writing to file
- **--push-jira**: If present, post a formatted status comment to the Jira ticket after indexing

Resolve the full path: `{project-management-root}/tickets/{ticket_path}`

If the path doesn't exist, error and stop.

## Algorithm

### Step 1: Determine Ticket Type

Check if the ticket directory has sub-ticket directories (directories matching pattern `SPV-*`, `MVP-*`, or any `{PREFIX}-{NUMBER}` pattern).

- **Has sub-ticket dirs** → Parent/Epic ticket → go to Step 3
- **No sub-ticket dirs** → Leaf ticket → go to Step 2

### Step 2: Index Leaf Ticket

Read the following sources (in order of priority):

#### 2a. Read `jira/ac/index.yaml` (required for completion calculation)

Path: `{ticket_path}/jira/ac/index.yaml`

If this file doesn't exist:
- Warn: "No jira/ac/index.yaml found for {ticket}. Cannot calculate AC-weighted completion."
- Fall back to looking for completion info in existing STATUS_SNAPSHOT.yaml or README.md
- Set `completion: null` and add a note that AC data is missing

From `ac.yaml`, extract:
- `story_points` (default: 1 if not specified)
- Each criterion's `status` and `points` (default points: 1 if not specified)
- Calculate: `completion = sum(points where status=done) / sum(all points) * 100`

Status values for AC items: `done`, `in_progress`, `pending_validation`, `not_started`, `blocked`

#### 2b. Read deployment state and reconcile ac.yaml

Check these sources for deployment info:
1. Parent's `REPO_MAPPING.yaml` — look for this ticket's service mapping
2. Existing `STATUS_SNAPSHOT.yaml` — preserve deployment info if present
3. If a `repo` field exists, try `git` commands to get branch/tag info (best effort):
   - `git -C {repo_path} tag --sort=-v:refname | head -1` for latest tag
   - `git -C {repo_path} branch --show-current` for current branch
   - `git -C {repo_path} status --short` for working tree state

**Auto-correct ac/index.yaml when deployment state is fresher:**
If an AC item's description references a version (e.g., `0.0.8-dev`) and git shows a newer tag (e.g., `0.0.10-dev`):
- Update the `status` field in `jira/ac/index.yaml` for that AC
- If deployed at latest tag, mark `done`; if not, mark `blocked`
- Log: "Updated ac/index.yaml: AC-{N} version {old} → {new}"

**Reconciliation rules:**
- Only auto-correct version references in AC descriptions, not arbitrary text
- Version pattern to match: semver-like strings (e.g., `0.0.8-dev`, `1.2.3`, `0.0.14-dev`)
- Compare against: latest git tag for the mapped repo
- To check deployed version: use `gcloud run services describe` if the service is mapped in REPO_MAPPING (best effort, don't fail if gcloud is unavailable)

#### 2c. Read INDEX.md (optional, for title/context)

Extract ticket title and any blocker/dependency info mentioned.

#### 2d. Generate STATUS_SNAPSHOT.yaml

Write to `{ticket_path}/STATUS_SNAPSHOT.yaml`:

```yaml
ticket: {TICKET-ID}
parent: {PARENT-ID}  # from directory structure, omit if top-level
title: {title from jira/ticket.yaml or README.md or ac.yaml}
status: {derived from AC: done if 100%, in_progress if >0%, not_started if 0%}
assignee: {from jira/ticket.yaml or existing snapshot}
story_points: {from ac.yaml}
completion: {calculated percentage, 1 decimal}
last_indexed: {current ISO timestamp}

ac_summary:
  total: {count of criteria}
  done: {count where status=done}
  in_progress: {count where status=in_progress}
  pending_validation: {count where status=pending_validation}
  not_started: {count where status=not_started}
  blocked: {count where status=blocked}
  completed_points: {sum of points where status=done}
  total_points: {sum of all points}

# Only include deployment section if deployment info is available
deployment:
  service: {cloud run service name}
  deployed_version: {current deployed version}
  latest_tag: {latest git tag}

# Only include blockers if any exist
blockers:
  - {blocker description, include ticket reference if applicable}

# Only include next_actions if actionable items exist
next_actions:
  - {concrete next step}
```

**Keep it lean.** Target 40-60 lines. Omit empty sections entirely (don't write `blockers: []`).

### Step 3: Index Parent/Epic (Recursive)

#### 3a. Identify sub-tickets

List all sub-ticket directories (matching ticket ID patterns).

#### 3b. Recurse into each sub-ticket

For each sub-ticket directory, run this same algorithm (Step 1 → 2 or 3).

**Process leaf tickets first, then nested parents, bottom-up.**

#### 3c. Read each child's STATUS_SNAPSHOT.yaml

After recursion, each child should have a fresh `STATUS_SNAPSHOT.yaml`. Read them all.

#### 3d. Calculate epic-level completion

**Formula:** Weighted average by story points.

```
epic_completion = sum(child.completion * child.story_points) / sum(child.story_points)
```

If a child has `completion: null` (missing AC data), use its existing completion percentage from the snapshot, or exclude it from the weighted calculation and note it.

#### 3e. Generate parent STATUS_SNAPSHOT.yaml

```yaml
epic: {EPIC-ID}
title: {epic title from README.md}
completion: {weighted average, 1 decimal}
last_indexed: {current ISO timestamp}

sub_tickets:
  {CHILD-ID}:
    title: {child title}
    status: {child status}
    completion: {child completion}
    story_points: {child story points}
    snapshot: ./{CHILD-ID}/STATUS_SNAPSHOT.yaml
    blocker: {first blocker from child, if any — one line only}

  # ... repeat for each child, sorted by ticket ID

# Only epic-wide blockers — DO NOT repeat individual child blockers verbatim
# Synthesize: if multiple children share the same blocker, mention it once
critical_blockers:
  - {synthesized blocker affecting multiple children or the epic overall}

# Only include if risks exist
risks:
  - {risk description}
```

**Progressive disclosure rules:**
- Parent NEVER repeats full child context — only: title, status, completion, story points, snapshot path, and one-line blocker (if any)
- If 3 children are all blocked by the same thing, the parent mentions it ONCE in `critical_blockers`
- Parent links to child snapshots via relative path (`./SPV-8/STATUS_SNAPSHOT.yaml`)
- Target 40-80 lines for the parent snapshot

### Step 4: Output

If `--dry-run`:
- Print the generated YAML to stdout
- Print "DRY RUN — no files written"

If not dry-run:
- Write the file
- Print summary: "Indexed {ticket}: completion={X}%, {N} blockers"
- If recursive, print summary for each indexed ticket

### Step 5: Push to Jira (`--push-jira`)

Only runs if `--push-jira` flag is present. Runs AFTER indexing is complete.

**For leaf tickets:** Post a single comment to the ticket's Jira issue.

**For epics (recursive):** Post a comment to the EPIC's Jira issue only (not each sub-ticket). The epic comment includes the sub-ticket summary table.

#### 5a. Resolve Jira ticket key

The ticket ID from the directory name (e.g., `SPV-22`) IS the Jira key. If jira/ticket.yaml exists, use its `key` field instead.

#### 5b. Format the comment

**Leaf ticket comment format:**
```
[automated] Status Index Update — {DATE}

Completion: {completion}% ({done}/{total} AC done)
Status: {status}
Story Points: {story_points}

Acceptance Criteria:
{for each AC}
- [{status_icon}] AC-{N}: {description} ({status})
{end for}

{if blockers}
Blockers:
{for each blocker}
- {blocker}
{end for}
{end if}

{if next_actions}
Next Actions:
{for each action}
- {action}
{end for}
{end if}

{if deployment}
Deployment: {service} @ {deployed_version} (latest tag: {latest_tag})
{end if}
```

Status icons: done=✅, in_progress=🔄, pending_validation=⏳, not_started=⬜, blocked=🚫

**Epic comment format:**
```
[automated] Epic Status Index Update — {DATE}

Epic Completion: {completion}%

| Ticket | Title | Status | Completion | SP | Blocker |
|--------|-------|--------|------------|-----|---------|
{for each sub-ticket}
| {ID} | {title} | {status} | {completion}% | {sp} | {blocker or —} |
{end for}

{if critical_blockers}
Critical Blockers:
{for each blocker}
- {blocker}
{end for}
{end if}

{if risks}
Risks:
{for each risk}
- {risk}
{end for}
{end if}
```

#### 5c. Post the comment

Use the jira skill's add-comment command:
```bash
python3 ~/.claude-shared-config/skills/jira/jira_skill.py add-comment {JIRA_KEY} --comment "{formatted_comment}"
```

**Rules (from JIRA_AGENT_RULES.md):**
- Always prefix with `[automated]`
- No emojis in prose text (status icons in the AC list are OK — they're data indicators, not decoration)
- Be honest: say "code complete" not "integration complete"; say "deployed to dev" not "deployed and working"
- Never transition tickets — only post comments

#### 5d. Log result

Print: "Posted status comment to {JIRA_KEY}"
If the post fails, warn but don't fail the entire indexing operation.

## Error Handling

- **Missing `jira/ac.yaml`**: Warn, set completion to null, continue
- **Missing sub-ticket directory**: Skip with warning
- **Missing README.md**: Use ticket ID as title
- **Circular references**: Should not happen with directory-based nesting, but guard against infinite recursion (max depth: 5)

## Important Notes

- This skill READS `jira/ac/index.yaml` and MAY UPDATE individual `jira/ac/ac-NNN.md` status fields when deployment state is fresher. It never creates the ac/ folder from scratch — that comes from Jira (via `/jira` skill). The `index.yaml` is always refreshed on re-fetch; `ac-NNN.md` files are write-once (agent scratchpad).
- The generated `STATUS_SNAPSHOT.yaml` replaces any existing one at that path.
- Deployment info is best-effort — preserved from existing snapshots or REPO_MAPPING.yaml.
- Timestamps use ISO 8601 format with timezone (e.g., `2026-02-16T18:00:00Z`).
