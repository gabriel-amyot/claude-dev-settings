# Skill Proposal: gitlab skill — `recent` + generic API passthrough

Date: 2026-06-22
Source: Proxi / BI-Agent repo discovery session (Klever)

## Problem

The `gitlab` skill has no way to answer "what repo was created recently?" or "list all repos
for project X across naming aliases" or "is this repo empty / what's its default branch"
without either cloning or hand-writing a `python3 -c "import gitlab_skill ..."` one-liner.
This session needed exactly that (find the repo created "yesterday") and fell back to importing
the module directly.

## Trigger

"what repo was created yesterday/recently", "find all repos related to <project>", "is repo X
empty", "what's repo X's default branch", "list newest GitLab projects".

## Scope

Enhancement to the existing `gitlab` skill (`~/.claude-shared-config/skills/gitlab/`). NOT a new
skill — add subcommands. Org-aware like the rest of the skill.

## Draft Steps

1. Add `recent [--limit N] [--type iac|dac|app]` — calls `/projects?order_by=created_at&sort=desc`,
   prints `created_at | id | default_branch | empty | path_with_namespace`, optional path-substring
   filter for repo type.
2. Add `api <endpoint> [--param k=v ...]` — thin authenticated passthrough to GitLab API v4
   (reuses `_init` + `api_request`), so any read endpoint is reachable without a one-liner.
3. Make `search` first-class (already exists in API; surface it) so alias lookups
   (`biag`, `proexp`) are a documented command.
4. Document the empty-repo check (`/projects/:id` → `empty_repo`) as the pre-flight before
   treating a no-files clone as a failure.
