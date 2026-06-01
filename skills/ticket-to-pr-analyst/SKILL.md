---
name: ticket-to-pr-analyst
description: Use when starting work on a Jira ticket and need structured spec analysis before design or implementation. Invoke with ticket key argument (e.g., KTP-123). Supports implementation tickets, stories, bugs, and spikes. Stage 1 of the Ticket-to-PR Pipeline.
nav:
  bay: plan
  when: "Structured spec analysis before design or implementation. Stage 1 of Ticket-to-PR Pipeline."
  when_not: "Full pipeline (use /dark-factory). Quick estimation (use /estimate)."
---

# Ticket-to-PR Analyst (Stage 1)

**POC v1.1.** Self-improving via run journal. After each run, the user reads `analyst/run-journal.vN.md`, improves this skill, and bumps the version if the change is non-trivial.

## Invocation

```
/ticket-to-pr-analyst <TICKET-KEY>
```

Arguments: a single Jira ticket key (e.g., `KTP-499`, `SPV-123`).

## Org Resolution

Parse the project prefix from the ticket key (text before the hyphen). Map to org:

| Prefix | Org | Jira `--org` | PM Root |
|--------|-----|--------------|---------|
| KTP, INS | klever | klever | `~/Developer/grp-beklever-com/project-management` |
| SPV | supervisrai | supervisrai | `~/Developer/supervisr-ai/project-management` |
| PER | personal | n/a | `~/Developer/gabriel-amyot/project-management` |

Unknown prefix: read `~/.claude/library/context/workspace-map.yaml` and ask the user.

## Process

### Step 1: Materialize Ticket

**Ticket folder:** `<PM_ROOT>/tickets/<PREFIX>/<TICKET-KEY>/`

If the folder has no `jira/` subfolder, fetch it:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py fetch <TICKET-KEY> --output-dir <PM_ROOT>/tickets/<PREFIX>/ --org <ORG>
```

Then read the materialized data:
- `jira/description.md` for the full description
- `jira/ticket.yaml` for metadata (type, labels, parent, children, status)
- `jira/ac/index.yaml` for any existing AC from Jira (may not exist)

Also fetch full details for richer analysis:
```bash
cd ~/.claude/skills/jira && python3 jira_skill.py get <TICKET-KEY> --full --org <ORG>
```

### Step 2: Check Existing Versions

Look for `analyst/acceptance_criteria.v*.json` in the ticket folder.
- If found: next version = max(existing N) + 1.
- If none: version = 1.

### Step 3: Assess Spec Quality

**PASS requires ALL three:**
1. Description longer than one sentence.
2. At least one identifiable code area, feature, or behavior (explicit or inferable from context).
3. Stakeholder intent is inferable (what they want, not just that they want something).

**Spike adaptation:** "Identifiable code area" includes system areas under investigation (e.g., "investigate Placer API" references the analytics/measurement area).

**Calibration:** A well-titled ticket with a paragraph of description and clear intent should PASS even without formal AC. Only FAIL genuinely underspecified tickets (e.g., title-only, vague one-liners with no actionable intent).

**If FAIL:**
- Write `acceptance_criteria.vN.json` with `spec_quality: "FAIL"`, populated `fail_reason`, empty `acceptance_criteria` array.
- Do NOT write `affected_repos` or `assumptions` files.
- Suggest posting a Jira comment requesting clarification (do not post automatically).
- Skip to Step 8 (run journal).

### Step 4: Extract or Infer Acceptance Criteria

**Ticket has explicit AC:** Extract each as a numbered, testable, independent item.

**No explicit AC:** Infer from:
- Ticket description and title
- Epic context (parent ticket, if available)
- Codebase context (read relevant repo CLAUDE.md files, scan referenced code areas)
- For each inferred AC, create a corresponding entry in Step 6 (assumptions)

**For spikes:** ACs describe research deliverables, not code changes.
- Example: "AC1: Document API rate limits and pricing tiers"
- Example: "AC2: Produce a comparison matrix of candidate approaches with tradeoffs"

**Per AC, produce:**
- `id`: "AC1", "AC2", etc.
- `description`: Testable, independent statement. Outcomes, not tasks.
- `category`: `ui` | `backend` | `fullstack` | `infra` | `data`

### Step 4.5: Existing Implementation Audit (Brownfield Awareness)

**Purpose:** Prevent greenfield bias. Before producing ACs, verify whether the feature already has a partial or full implementation in the codebase. The analyst must document what was searched before making any assumption about UI placement, routes, pages, or service structure.

**For frontend tickets:**
- Grep the affected frontend repo(s) for existing routes, pages, or components that serve the backend endpoint the ticket describes.
- Grep for route definitions referencing relevant keywords from the ticket title and description (e.g., feature name, noun objects).
- Grep for component filenames and navigation constants that might indicate an existing page.

```bash
# Example searches (adapt patterns to the ticket's domain):
grep -r "/<feature-keyword>" <frontend-repo>/src --include="*.ts" --include="*.tsx" -l
grep -r "feature-keyword" <frontend-repo>/src/routes --include="*.ts" -l
grep -r "featureKeyword" <frontend-repo>/src/components -l
```

**For backend tickets:**
- Grep affected backend repo(s) for existing controllers or services handling the same data path (URL segments, entity names).
- Grep for the specific endpoint path fragments mentioned or implied by the ticket.

```bash
# Example searches:
grep -r "/api/feature-keyword" <backend-repo>/src --include="*.java" --include="*.py" -l
grep -r "FeatureKeywordController\|FeatureKeywordService" <backend-repo>/src -l
```

**Classification decision:**
- `modification`: Default. Use when any existing implementation is found (a page, route, controller, or component serving the same concern). Every assumption about routes, nav items, permissions, and page structure must be validated against what already exists, not invented from scratch.
- `creation`: Use only when searches return no results AND there is no adjacent implementation that could be extended. Requires explicit evidence (search commands run + zero results).

**Record the classification** in `acceptance_criteria.vN.json` as `brownfield_classification` at the ticket level.

**Every assumption that references UI placement, route paths, page structure, or nav items MUST include an `evidence_searched` field** listing the exact search commands run before making the assumption. An assumption without `evidence_searched` on a UI placement claim is invalid.

### Step 5: Re-run Gate (version > 1 only)

If version > 1:
1. Read the latest existing `analyst/acceptance_criteria.v*.json`.
2. Compare the new AC list to the existing one semantically.
3. If identical: log a warning, print "ACs unchanged, skipping." Do NOT write new files. Stop.
4. If different: proceed. Set `change_note` to describe what changed.

### Step 6: Identify Affected Repos

Read `~/.claude/library/context/workspace-map.yaml` for the org's repo inventory. For each candidate:
- Read the repo's `CLAUDE.md` (if present) for context on what it contains.
- Match against AC descriptions and ticket context.
- Include only repos genuinely affected. Do not list the entire org.

**Per repo, produce:** `name`, `path` (absolute), `type` (`frontend` | `backend` | `infra` | `shared`), `reason`.

**For spikes:** Repos are "under investigation." Mark the reason accordingly.

### Step 7: Document Assumptions

Record everything unclear, inferred, or assumed:
- `id`: "ASM1", "ASM2", etc.
- `unknown`: What was unclear in the ticket.
- `assumption`: What was assumed.
- `reasoning`: Why this assumption was made.
- `alternatives_considered`: Other interpretations considered (array, may be empty).

If nothing was assumed, write an empty `assumptions` array.

**Key rule:** If you inferred an AC, you made an assumption. Record it.

### Step 8: Write Outputs

Create `analyst/` subfolder if it does not exist:
```bash
mkdir -p <TICKET_FOLDER>/analyst
```

Generate run_id: `analyst-<TICKET-KEY>-<ISO-timestamp>` (e.g., `analyst-KTP-499-2026-05-19T143000Z`).

Write three JSON files using the Write tool:
- `analyst/acceptance_criteria.v<N>.json`
- `analyst/affected_repos.v<N>.json`
- `analyst/assumptions.v<N>.json`

Schemas are defined in the Output Schemas section below.

### Step 9: Write Run Journal & Print Summary

Write `analyst/run-journal.v<N>.md` using the template in the Run Journal section below.

Then print a summary to the user:
```
Analyst complete for <TICKET-KEY> (v<N>)
  Spec quality: PASS/FAIL
  ACs: <count> (<extracted|inferred|mixed>)
  Repos: <count>
  Assumptions: <count>
  Output: <ticket-folder>/analyst/
  Journal: analyst/run-journal.v<N>.md ← read this and improve the skill
```

## Output Schemas

### acceptance_criteria.vN.json

```json
{
  "version": 1,
  "produced_at": "2026-05-19T14:30:00Z",
  "produced_by_run_id": "analyst-KTP-499-2026-05-19T143000Z",
  "spec_quality": "PASS",
  "fail_reason": null,
  "change_note": "Initial analysis",
  "brownfield_classification": "modification",
  "acceptance_criteria": [
    {
      "id": "AC1",
      "description": "Testable, independent outcome statement",
      "category": "backend"
    }
  ]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| version | int >= 1 | yes | |
| produced_at | ISO 8601 UTC | yes | |
| produced_by_run_id | string | yes | |
| spec_quality | "PASS" or "FAIL" | yes | |
| fail_reason | string or null | yes when FAIL | Why the ticket failed quality gate |
| change_note | string | no | What changed from previous version, or "Initial analysis" |
| brownfield_classification | "modification" or "creation" | yes | Set in Step 4.5. "modification" is the default; "creation" requires search evidence |
| acceptance_criteria | array | yes | May be empty on FAIL |
| acceptance_criteria[].id | string | yes | "AC1", "AC2", etc. |
| acceptance_criteria[].description | string | yes | Testable, independent |
| acceptance_criteria[].category | enum | yes | ui, backend, fullstack, infra, data |

### affected_repos.vN.json

```json
{
  "version": 1,
  "produced_at": "2026-05-19T14:30:00Z",
  "produced_by_run_id": "analyst-KTP-499-2026-05-19T143000Z",
  "repos": [
    {
      "name": "user-management-backend",
      "path": "/Users/gabrielamyot/Developer/grp-beklever-com/user-management-backend",
      "type": "backend",
      "reason": "Contains the store API endpoint referenced in AC1"
    }
  ]
}
```

| Field | Type | Required |
|-------|------|----------|
| version | int >= 1 | yes |
| produced_at | ISO 8601 UTC | yes |
| produced_by_run_id | string | yes |
| repos | array | yes |
| repos[].name | string | yes |
| repos[].path | string (absolute) | yes |
| repos[].type | enum: frontend, backend, infra, shared | yes |
| repos[].reason | string | yes |

### assumptions.vN.json

```json
{
  "version": 1,
  "produced_at": "2026-05-19T14:30:00Z",
  "produced_by_run_id": "analyst-KTP-499-2026-05-19T143000Z",
  "posted_to_jira": false,
  "assumptions": [
    {
      "id": "ASM1",
      "unknown": "Whether the export should include archived records",
      "assumption": "Export includes only active records",
      "reasoning": "Most export features default to active-only; ticket does not mention archived data",
      "alternatives_considered": ["Include all records with an archive flag column"],
      "classification": "modification",
      "evidence_searched": []
    },
    {
      "id": "ASM2",
      "unknown": "Where in the UI the new view should be surfaced",
      "assumption": "Feature is added to the existing /proximity-chatbot page, not a new route",
      "reasoning": "Codebase audit (Step 4.5) found an existing page serving the same backend endpoint",
      "alternatives_considered": ["New standalone route /market-research"],
      "classification": "modification",
      "evidence_searched": [
        "grep -r 'chatbot' src/routes --include='*.ts' -l",
        "grep -r '/proximity-chatbot' src --include='*.tsx' -l"
      ]
    }
  ]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| version | int >= 1 | yes | |
| produced_at | ISO 8601 UTC | yes | |
| produced_by_run_id | string | yes | |
| posted_to_jira | boolean | yes | |
| assumptions | array (may be empty) | yes | |
| assumptions[].id | string | yes | |
| assumptions[].unknown | string | yes | |
| assumptions[].assumption | string | yes | |
| assumptions[].reasoning | string | yes | |
| assumptions[].alternatives_considered | array of strings | no | |
| assumptions[].classification | "modification" or "creation" | yes | Inherited from Step 4.5 brownfield classification |
| assumptions[].evidence_searched | array of strings | yes for UI placement claims | List of exact search commands run before making this assumption. Empty array is acceptable only for non-UI-placement assumptions |

## Run Journal Template

```markdown
# Run Journal: <TICKET-KEY> v<N>

**Date:** <YYYY-MM-DD>
**Skill version:** POC v1.1
**Run ID:** <run_id>
**Ticket type:** <Story|Bug|Task|Spike|Epic|Sub-task>
**Spec quality:** <PASS|FAIL>

## What Worked Well
- (list concrete things that went smoothly)

## What Was Brittle
- (steps that almost failed, required workarounds, or felt fragile)

## What I Had to Guess At
- (information not in the ticket or codebase that I inferred without confidence)

## What Instructions Were Unclear
- (parts of this skill's SKILL.md that were ambiguous, contradictory, or missing)

## What I Wish I Had Been Told
- (context that would have made the analysis better or faster)

## Proposed Improvements to This Skill
- (specific, actionable changes to SKILL.md with reasoning)

## Execution Notes
- Jira fetch: <success|failure, data completeness notes>
- Brownfield classification: <modification|creation> — searches run: <list commands>
- Existing implementation found: <yes/no — describe what was found or confirm absence>
- Repos scanned: <list with outcome per repo>
- Time-intensive steps: <which steps took disproportionate effort>
- Errors encountered: <any tool failures or unexpected states>
```

**Be brutally honest.** The journal exists to surface friction. Diplomatic vagueness defeats its purpose.

## Common Mistakes

- **Tasks instead of outcomes.** "Update the config file" is a task. "System reads configuration from the new path" is a testable outcome.
- **Listing every repo.** Only include genuinely affected repos, not the whole org inventory.
- **Silent inference.** If you inferred an AC, you made an assumption. It must appear in `assumptions.vN.json`.
- **Skipping the journal.** The run journal IS the feedback mechanism. Without it, this POC cannot improve.
- **Over-aggressive FAIL.** A ticket with a solid paragraph and clear intent should PASS even without formal AC bullets. FAIL is for genuinely underspecified work.
- **Greenfield bias.** Never invent a new route, page, or nav item from a ticket that describes behavior without specifying UI placement. Run Step 4.5 first. If an existing page or route already serves the backend endpoint, classify as `modification` and wire into what exists. KTP-713 invented ASM1 ("/market-research route") and ASM4 ("dedicated page with own map instance") when the existing /proximity-chatbot page already served the endpoint.
- **Assumption without evidence.** Any assumption touching UI placement, route paths, or page structure that lacks `evidence_searched` is invalid. The analyst must document the actual grep commands run before claiming nothing exists.
