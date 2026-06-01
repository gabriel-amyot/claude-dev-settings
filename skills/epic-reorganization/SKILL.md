---
name: epic-reorganization
description: Split, reorganize, or re-parent Jira tickets across epics. Use when user says "split epic", "reorganize tickets", "move tickets to new epic", "re-parent tickets", or "epic split". Creates new epics in Jira, re-parents selected tickets, creates local ticket folders, updates REPO_MAPPING and STATUS_SNAPSHOT. Previews all changes before executing.
nav:
  bay: plan
  when: "Split, reorganize, or re-parent Jira tickets across epics."
  when_not: "Creating new tickets from scratch (use /create-tickets). Archiving (use /archive)."
---

# Epic Reorganization Skill

Automates splitting or reorganizing Jira epics: creates new epics, re-parents tickets in Jira, restructures local `tickets/` folders, and updates index files. Covers any org (SPV, KTP, etc.).

**Usage:** `/epic-reorganization <EPIC-ID> [--ac <ticket-list>] [--dry-run]`

**Examples:**
```
/epic-reorganization KTP-115
/epic-reorganization SPV-3 --dry-run
/epic-reorganization KTP-115 --ac "KTP-200,KTP-201,KTP-202 → KTP-NEW-EPIC"
```

## Arguments

- `<EPIC-ID>`: Required. The source epic to split or reorganize (e.g., KTP-115, SPV-3).
- `--ac <mapping>`: Optional. Explicit ticket-to-epic mapping, bypasses the classification interview.
- `--dry-run`: Optional. Preview all changes without executing any Jira API calls or folder moves.

---

## Step 0: Detect org and working directory

Resolve the org and project-management root before doing anything else.

```
If PWD contains /grp-beklever-com → org = klever, jira_org_flag = "--org klever"
If PWD contains /supervisr-ai    → org = supervisrai, jira_org_flag = "--org supervisrai"
Else                             → check jira_config.json default; fall back to supervisrai
```

All subsequent `jira_skill.py` calls must include `jira_org_flag`.

Resolve `PM_ROOT`:
- If PWD is inside a `project-management/` subtree, walk up to find it.
- Otherwise default to `~/Developer/{org}/project-management/`.

---

## Step 1: Fetch the source epic and all children

```bash
cd ~/.claude/skills/jira
python3 jira_skill.py get <EPIC-ID> --full <jira_org_flag>
python3 jira_skill.py search "parentEpic = <EPIC-ID> ORDER BY created ASC" --max 200 <jira_org_flag>
```

Collect: key, summary, status, assignee, sprint for every child ticket.

Also check the local folder:
```
<PM_ROOT>/tickets/<EPIC-ID>/
```
List all sub-ticket folders found locally. Note any tickets present locally but not in Jira (orphans) and vice versa.

### Hierarchy Constraints (gate check)

Before proposing any nested structure in Step 2, verify Jira hierarchy constraints:

- **Epic cannot nest under Epic** (company-managed projects). Jira flat hierarchy: Epic → Story → Sub-task only.
- **Story cannot parent Story.** Only Epic can be a parent of Story.
- **Sub-task cannot exist outside a Story parent.**
- **Fallback:** When nesting seems natural but hierarchy forbids it (e.g., grouping related stories under a "tracker" story), use a flat epic with **labels** for logical grouping instead. Document the label convention in the epic's INDEX.md.

If the user requests a structure that violates these constraints, explain the limitation and propose the label-based alternative before proceeding.

---

## Step 2: Classify tickets into groups (interview)

Skip this step if `--ac` mapping was provided.

Present the full ticket list to the user grouped by inferred category:

```
Source epic: KTP-115 — "<epic summary>"
Children (18 tickets):

  Active / In Progress (5):
    KTP-200  [In Progress]  "Implement X"
    KTP-201  [In Progress]  "Implement Y"
    ...

  Refinement / To Do (6):
    KTP-210  [To Do]  "Design Z"
    ...

  Done / Historical (7):
    KTP-220  [Done]  "Shipped A"
    ...

Proposed groupings (edit before confirming):
  New Epic A: KTP-200, KTP-201, KTP-210 → "<suggested name>"
  New Epic B: KTP-202, KTP-211          → "<suggested name>"
  Stay in <EPIC-ID>: KTP-220 ... (historical/done — leave in original)
```

Ask: "Does this grouping look right? Rename the proposed epics and adjust ticket assignments, then say 'confirmed'."

Do NOT proceed until the user explicitly confirms the grouping.

---

## Step 3: Preview all changes (always, even without --dry-run)

Before executing anything, print the full change manifest:

```
PREVIEW — Changes that will be executed:
=========================================

Jira operations:
  [CREATE] New Epic: "<name>" (project: KTP) → will receive key KTP-???
  [CREATE] New Epic: "<name>" (project: KTP) → will receive key KTP-???
  [RE-PARENT] KTP-200 → KTP-NEW-1
  [RE-PARENT] KTP-201 → KTP-NEW-1
  [RE-PARENT] KTP-202 → KTP-NEW-2
  [LINK] KTP-115 "Work item split" ← KTP-NEW-1
  [LINK] KTP-115 "Work item split" ← KTP-NEW-2

Local folder operations:
  [CREATE] tickets/KTP/KTP-NEW-1/         (new epic folder)
  [CREATE] tickets/KTP/KTP-NEW-1/KTP-200/ (copy from tickets/KTP/KTP-115/KTP-200/)
  [CREATE] tickets/KTP/KTP-NEW-1/KTP-201/
  [CREATE] tickets/KTP/KTP-NEW-2/
  [CREATE] tickets/KTP/KTP-NEW-2/KTP-202/
  [MOVE]   tickets/KTP/KTP-115/KTP-200/ → tickets/KTP/KTP-NEW-1/KTP-200/
  [MOVE]   tickets/KTP/KTP-115/KTP-201/ → tickets/KTP/KTP-NEW-1/KTP-201/
  [MOVE]   tickets/KTP/KTP-115/KTP-202/ → tickets/KTP/KTP-NEW-2/KTP-202/
  [KEEP]   tickets/KTP/KTP-115/KTP-220/ (historical — not moved)
  [UPDATE] tickets/KTP/KTP-115/REPO_MAPPING.yaml (remove moved tickets)
  [UPDATE] tickets/KTP/KTP-115/STATUS_SNAPSHOT.yaml
  [UPDATE] tickets/KTP/KTP-NEW-1/INDEX.md (generated)
  [UPDATE] tickets/KTP/KTP-NEW-2/INDEX.md (generated)

Rollback plan:
  - Jira creates are not reversible; moved tickets can be re-parented back to KTP-115
  - Local folder moves are reversible; original paths are preserved until Jira step succeeds
```

If `--dry-run` was passed, stop here and report "Dry run complete. No changes made."

Otherwise ask: "Ready to execute? Type 'go' to proceed or 'cancel' to abort."

Do NOT execute without explicit "go" or equivalent affirmative.

---

## Step 4: Execute Jira operations

Execute in this order. Stop and rollback on any failure (see Step 7).

### 4a. Create new epics

For each new epic:
```bash
cd ~/.claude/skills/jira
python3 jira_skill.py create \
  --summary "<epic name>" \
  --type Epic \
  --project <PROJECT> \
  --description "<description from user confirmation>" \
  <jira_org_flag>
```

Capture the new key returned (e.g., `KTP-558`). Store as `NEW_EPIC_KEY`.

### 4b. Re-parent tickets

For each ticket being moved, run in parallel batches of up to 5:
```bash
cd ~/.claude/skills/jira
python3 jira_skill.py update <TICKET-KEY> --parent <NEW_EPIC_KEY> <jira_org_flag>
```

Wait for each batch to complete before starting the next. Log success/failure per ticket.

### 4c. Add split links

For each new epic:
```bash
cd ~/.claude/skills/jira
# Use the search/metadata commands to confirm the link type name for this org
python3 jira_skill.py search "issue = <EPIC-ID>" --full <jira_org_flag>
```

Create issue links via the Jira REST API directly:

```bash
# Get the auth token
JIRA_TOKEN=$(security find-generic-password -s "claude-jira" -a "jira_klever" -w 2>/dev/null)

# Create issue link
curl -s -X POST "https://beklever.atlassian.net/rest/api/3/issueLink" \
  -H "Authorization: Basic $JIRA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": { "name": "Work item split" },
    "inwardIssue": { "key": "<NEW_EPIC_KEY>" },
    "outwardIssue": { "key": "<SOURCE_EPIC_ID>" }
  }'
```

If the link type "Work item split" does not exist in this org, fall back to "Relates". If REST API auth fails (IAP blocks direct API on Klever), surface as manual step:

```
Manual step required: Add "Work item split" links in Jira:
  KTP-115 → KTP-558 (new epic A)
  Navigate to KTP-115 → Link → "is split by" → KTP-558
```

---

## Step 5: Execute local folder operations

Only after all Jira re-parenting succeeds (Step 4b complete with no failures).

### 5a. Create new epic folders

For each new epic, scaffold using `/ticket-init`:
```
/ticket-init <NEW_EPIC_KEY>
```

If ticket-init is unavailable, manually create:
```
tickets/<ORG>/<NEW_EPIC_KEY>/
├── INDEX.md
├── STATUS_SNAPSHOT.yaml
└── reports/
    ├── architecture/
    ├── implementation/
    ├── reviews/
    └── status/
```

Populate `INDEX.md` with the new epic's title and a link to Jira.
Populate `STATUS_SNAPSHOT.yaml` with:
```yaml
ticket: <NEW_EPIC_KEY>
epic: null
title: "<epic summary>"
status: in_progress
completion: 0
last_indexed: <ISO timestamp>
split_from: <SOURCE_EPIC_ID>
```

### 5b. Move sub-ticket folders

For each ticket being re-parented:
```
Move: tickets/<ORG>/<SOURCE_EPIC>/<TICKET-KEY>/
  To: tickets/<ORG>/<NEW_EPIC_KEY>/<TICKET-KEY>/
```

If the sub-ticket folder does not exist locally, skip silently (not an error).

After moving, update the sub-ticket's `STATUS_SNAPSHOT.yaml` if it exists:
```yaml
epic: <NEW_EPIC_KEY>   # was <SOURCE_EPIC_ID>
```

### 5c. Update source epic's REPO_MAPPING.yaml

Read `tickets/<ORG>/<SOURCE_EPIC>/REPO_MAPPING.yaml`. Remove any entries that exclusively served the moved tickets. Add a `split_off` section:
```yaml
split_off:
  - epic: <NEW_EPIC_KEY>
    tickets: [<TICKET-KEY>, ...]
    date: <YYYY-MM-DD>
```

### 5d. Update source epic's STATUS_SNAPSHOT.yaml

Recalculate completion based on remaining tickets. Add:
```yaml
reorganized: true
last_reorganization: <ISO timestamp>
new_epics: [<NEW_EPIC_KEY>, ...]
```

### 5e. Fetch new epics to disk

For each new epic, fetch from Jira to populate `jira/` folder:
```bash
cd ~/.claude/skills/jira
python3 jira_skill.py fetch <NEW_EPIC_KEY> --output-dir <PM_ROOT>/tickets/<ORG>/<NEW_EPIC_KEY> --depth 2 <jira_org_flag>
```

### 5f. Update INDEX.md files

For every folder created or modified:
1. Read or create `INDEX.md`
2. Add/update a navigation table listing all sub-tickets with their status
3. Add links to new sibling epics if this is the source epic's INDEX.md

---

## Step 6: Verify

After all operations complete, run a verification pass:

```bash
cd ~/.claude/skills/jira
# Confirm each moved ticket now shows correct parent
python3 jira_skill.py get <TICKET-KEY> --full <jira_org_flag>
```

Sample 2-3 moved tickets. Confirm `parentEpic` field equals `NEW_EPIC_KEY`.

Also verify local folders:
- New epic folder exists with INDEX.md and STATUS_SNAPSHOT.yaml
- Moved ticket folders are under new epic, not old

Report:
```
Verification results:
  Jira: KTP-200 parent = KTP-558 ✓
  Jira: KTP-201 parent = KTP-558 ✓
  Jira: KTP-202 parent = KTP-559 ✓
  Local: tickets/KTP/KTP-558/ exists ✓
  Local: tickets/KTP/KTP-558/KTP-200/ exists ✓
```

---

## Step 7: Rollback plan

If any Jira operation fails (Step 4), stop immediately and report what succeeded and what failed.

**Jira rollback:**
- For each ticket that was successfully re-parented: re-run `jira_skill.py update <TICKET-KEY> --parent <SOURCE_EPIC_ID>`
- Newly created epics cannot be auto-deleted via the skill. Surface the keys to the user: "Please delete KTP-558 manually in Jira if this epic is no longer needed."

**Local rollback:**
- Local folder moves are safe to reverse because the source epic folder was not deleted.
- If sub-ticket folders were moved before Jira failed, move them back.

Always report the rollback state explicitly:
```
Rollback complete:
  Reverted: KTP-200 → KTP-115 ✓
  Reverted: KTP-201 → KTP-115 ✓
  Manual action needed: Delete KTP-558 in Jira (empty epic)
  Local folders: no changes made (Jira step failed before folder moves)
```

---

## Step 8: Final report

```
Epic reorganization complete.
===============================

Source epic: KTP-115 — "Original Epic Name"
  Remaining tickets: 7 (historical/done, kept in place)

New epic KTP-558 — "Phase 1 Active Work"
  Tickets moved: KTP-200, KTP-201, KTP-210 (5 total)
  Local folder: tickets/KTP/KTP-558/

New epic KTP-559 — "Phase 2 Refinements"
  Tickets moved: KTP-202, KTP-211 (2 total)
  Local folder: tickets/KTP/KTP-559/

Manual follow-up:
  [ ] Add "Work item split" links in Jira (KTP-115 → KTP-558, KTP-559)
  [ ] Update sprint assignments in Jira if needed
  [ ] Update DECISIONS_LOG.md with split rationale
  [ ] Commit local folder changes

Files modified:
  tickets/KTP/KTP-115/REPO_MAPPING.yaml
  tickets/KTP/KTP-115/STATUS_SNAPSHOT.yaml
  tickets/KTP/KTP-115/INDEX.md
  tickets/KTP/KTP-558/ (new)
  tickets/KTP/KTP-559/ (new)
```

---

## Safety rules

1. Never execute without showing the preview (Step 3) and receiving explicit confirmation.
2. Never re-parent tickets the user did not explicitly include in the grouping.
3. Never delete the source epic, its folder, or historical/done sub-ticket folders.
4. Never move tickets that are marked Done into a new epic. Done tickets stay with the original epic.
5. If a sub-ticket folder does not exist locally, skip silently. Do not fabricate folders.
6. IAM / auth changes (if any epic touches DAC repos) are human-gated. Surface to user, do not auto-apply.
7. Never run `git commit` or `git push` automatically. Always list modified files and ask the user to commit.
8. **Type changes (Epic ↔ Story) require manual Jira UI action.** The Jira REST API does not support changing issue type in company-managed projects. When the reorganization plan requires demoting an Epic to a Story (or vice versa), flag it explicitly as a human action item in the final report. Do NOT attempt to automate it.

---

## Integration with other skills

- **`/jira`**: All Jira API calls go through the jira skill. Do not call the Jira REST API directly except for `createIssueLink` (not yet in the skill).
- **`/ticket-init`**: Use to scaffold new epic folders in Step 5a.
- **`/status-index`**: After folder moves complete, run `/status-index <SOURCE_EPIC_ID>` and `/status-index <NEW_EPIC_KEY>` to regenerate STATUS_SNAPSHOT.yaml with accurate AC-weighted completion.
- **`/index-context`**: Run on any folder whose INDEX.md was updated to verify completeness.

---

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `update --parent` returns 400 | Ticket type cannot have an Epic as parent | Use Epic Link field instead: `--epic-link <KEY>` |
| Moved ticket still shows old epic in Jira | Jira propagation lag | Wait 30 seconds and re-verify |
| Local folder not found for a ticket | Ticket was never locally fetched | Skip move. Run `jira fetch <KEY>` post-reorganization |
| New epic key not returned | Jira create succeeded but output parsing failed | Run `jira search "project = KTP AND summary ~ '<name>'"` to find the key |
| `customfield_10014` (Epic Link) not updating | Different Jira field name in this org | Check `jira get <TICKET> --full` for the actual parent epic field name |
