# Skill Proposal: claude-md-schema-check
Date: 2026-11-06
Source: app-front-portal CLAUDE.md audit (session indigo-lantern)

## Trigger
"check this CLAUDE.md", "lint the repo CLAUDE.md", before a CLAUDE.md, AGENTS.md or docs/ change ships in a
Klever repo, or when onboarding a repo to the agent standard.

## Scope
Org (Klever). Lives in `app-agent-skills` so colleagues get it in their own harness. CI enforcement later through
a `grp-includes` include, after team alignment.

## Draft Steps
1. Run the lint (`repo-claude-md-lint.py --repo . [--ref origin/dev] [--file proposed]`) against schema v1.
2. For each pointer the change adds or keeps, grep the destination doc for contradicting terms (stale-destination check).
3. Check the AGENTS.md / CLAUDE.md mirror shape, so Codex sees the same rulebook.
4. Report the violations by rule ID with a fix for each. Never edit CLAUDE.md without approval.

Prototype and schema: `project-management/general/harness/2026-11-04-portal-claude-md-index/`.
