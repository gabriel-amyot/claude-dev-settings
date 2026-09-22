# Skill Proposal: jira-structure-writes
Date: 2026-08-26
Source: Powers MCP ticket consolidation (session vivid-jackal)

## Trigger

Any ticket-restructure task that needs to change a ticket's **shape** rather than its text:
convert Sub-task ↔ Story, re-parent a ticket, set or move an epic link, or bulk-move a family of
tickets under a new epic. Also fires when an agent has just discovered a ticket set cannot be
pointed or sprinted because it is Sub-tasks.

## Scope

Extension of the existing `_meta/skills/jira/jira_skill.py` (Klever + Supervisr), not a new skill.

## Problem it solves

`jira_skill.py update` writes only `description`, `summary`, `assignee`. A restructure that needs
`parent`, epic link, or `issuetype` has no CLI path, so the agent either hand-rolls an importlib
hack against `mod.jira` (fragile, undocumented) or hands the work back to the human for UI clicks.

On 2026-08-26 this split one restructure across two actors: the agent did all content, the human
was told to do the type conversion by hand. The conversion was then skipped entirely, leaving four
tickets unpointable and unsprintable.

## Draft Steps

1. Add `update --parent KEY` — sets `fields.parent`. Already proven to work via the library:
   `issue.update(fields={"parent": {"key": "KTP-3"}})`.
2. Add `update --epic KEY` — resolves the project's epic-link custom field (varies per instance;
   probe `customfield_10014` / `10008` / `10011`) and falls back to `parent` on team-managed
   projects, where epic link IS parent.
3. Add `convert --type Story|Sub-task --parent KEY` — issue-type conversion. **Verify feasibility
   first:** the REST API may reject Sub-task→Story without a parent reassignment, and some
   instances require the UI. If the API refuses, the command should say so and print the exact UI
   steps rather than failing opaquely.
4. Add `epic-children KEY` — resolve the true epic of any issue by walking `parent` upward, so an
   agent stops misreading a Sub-task's empty `epic_key` as "not under an epic."
5. Guard: refuse a bulk restructure without `--confirm`, and print the before/after tree first.

## Verification note

Step 1 is proven. Steps 2 and 3 are **unverified** — build them behind a probe that reports what the
instance actually supports before claiming the capability exists.
