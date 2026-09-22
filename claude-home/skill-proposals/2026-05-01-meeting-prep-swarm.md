# Skill Proposal: meeting-prep-swarm
Date: 2026-05-01
Source: Map architecture research session (March 31)

## Trigger
When preparing for a strategic alignment meeting, scoping session, or sprint prep where multiple stakeholders have opinions and context is spread across Slack, Jira, Notion, git, and local docs.

## Scope
org (Klever, could generalize to global)

## Draft Steps
1. User provides meeting topic, key people, decision to be made, and known context locations
2. Skill spawns parallel research agents: codebase analysis, Slack mining (per person), Notion/doc search, web competitive research, architecture patterns
3. Each agent returns a structured 1-2K word summary
4. Skill synthesizes into a "Reality Folder": options matrix, data feasibility, risk analysis, known unknowns, talking points
5. Writes all outputs to `general/meetings/YYYY-MM-DD-{topic}-reality-folder.md` with source index
6. Optionally produces an "Ideas Goldmine" doc if multiple team members have contributed ideas
