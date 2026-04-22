---
name: create-tickets
description: Create Jira tickets (epics, stories, spikes) with proper formatting, AC quality gate, local scaffolding, and optional Leo review. Use when the user wants to create multiple related tickets, plan an epic with children, or batch-create stories/spikes. Triggers on "create tickets", "create an epic with stories", "plan the tickets", "set up the Jira tickets", "scaffold tickets for this work". Input: epic description or list of stories with AC. Returns: created Jira keys and local scaffold paths.
---

# Create Tickets

End-to-end ticket creation pipeline: draft, review, create in Jira, scaffold locally, and optionally run Leo AC scan.

**Usage:** `/create-tickets [hint]`

**Examples:**
```
/create-tickets                              # Interactive: ask what to create
/create-tickets auth0 cleanup epic           # Create epic + children for auth0 cleanup
/create-tickets SPV spike for X              # Create a spike ticket
```

## Pipeline Steps

Execute these steps in order. Do not skip the user confirmation gates.

### Step 1: Gather Requirements

Ask the user what they need:
- What type? Epic, story, spike, bug, task
- If epic: what children? (stories, spikes, sub-tasks)
- What project? (default: infer from current working directory via Jira skill org detection)
- Any parent epic to attach to?

If the user already described what they want (e.g., in the hint or prior conversation), skip straight to drafting.

### Step 2: Read the Template

**Mandatory.** Before drafting any ticket description, read:
```
~/.claude-shared-config/skills/templates/jira-ticket-description.md
```

Follow its rules exactly:
- User story as first line
- `## Scope`, `## Investigation Approach` (spikes only), `## Acceptance Criteria`, `## Definitions` (at bottom)
- ACs as numbered list with Given/When/Then format and short titles
- No long definitions inside ACs
- No em-dashes anywhere

### Step 3: Draft All Tickets

Draft every ticket in the batch. For each ticket, include:
- Summary (title)
- Type
- Parent (if applicable)
- Full description following the template format

Present the full batch to the user for review. Wait for explicit confirmation before creating anything.

### Step 4: Create in Jira

Create tickets in dependency order:
1. Epic first (if creating one)
2. Children with `--parent` referencing the epic key

Use the `/jira` skill's `create` command for each ticket. The description is passed via `--description`.

### Step 5: Scaffold Locally

After Jira creation, scaffold local folders using `/ticket-init`:
- Epic gets: INDEX.md, STATUS_SNAPSHOT.yaml, REPO_MAPPING.yaml, reports/ tree
- Children get: INDEX.md, STATUS_SNAPSHOT.yaml, jira/ac/, plan/, reports/ tree
- Children are created as subdirectories of the epic folder

Update the relevant ticket index (e.g., NON-SPV3-INDEX.md or parent epic's INDEX.md) with entries for the new tickets.

### Step 6: Leo AC Scan (Optional)

After creation, offer to run a Leo AC scan on the new tickets:

"Want me to run Leo (spec coach) to adversarially review the ACs?"

If the user accepts:
1. Spawn the `leo-ac-scan` agent on the new ticket keys
2. Present findings (PASS/FLAG/WARN per AC)
3. If fixes are needed, draft the corrections and show to the user
4. On approval, update both Jira descriptions and local INDEX.md files

If the user declines, skip.

### Step 7: Summary

Print a summary table:

```
| Key | Type | Summary |
|-----|------|---------|
| SPV-113 | Epic | Origin8 Stack Deprecation |
| SPV-114 | Spike | Auth0 investigation |

Local folders scaffolded at: tickets/SPV-113/
Leo AC scan: [completed / skipped]
```

## Rules

1. **Always read the template** (Step 2) before drafting. No exceptions.
2. **User confirms before Jira writes.** Show the full draft, wait for "go ahead."
3. **Epic first, children second.** Create in dependency order so `--parent` works.
4. **Local scaffolding is not optional.** Every Jira ticket gets a local folder.
5. **Leo scan is optional but always offered.**
6. **No em-dashes.** Not in titles, descriptions, ACs, or local files.
