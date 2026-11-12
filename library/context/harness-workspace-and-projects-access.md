# Harness workspace selection and GitHub Projects access

Use this when selecting an editor around the shared harness or when GitHub CLI can manage issues but cannot add them to Projects.

## Workspace requirements

Gabriel uses Herdr for session management. The missing workspace needs code navigation, a persistent system architecture view and code-review context while retaining the existing harness and Claude/Codex subscriptions. API-key support alone does not prove subscription reuse. A free editor does not prove free inference or parity with installed CLI hooks, skills and MCP configuration.

The research recommends a VS Code/LikeC4 pilot, with Theia and Zed as alternatives. This remains a proposal: no workspace was installed and no harness compatibility was tested. The sourced comparison and acceptance plan live in [issue #623](https://github.com/gabriel-amyot/klever-project-management/issues/623). Keep product architecture in its owning repositories; the editor displays that source rather than owning a duplicate record.

## GitHub CLI Projects scope

When a stored OAuth token has repository access but a Projects operation reports missing scope, use `gh auth refresh --hostname github.com --scopes project`. The account holder completes the browser authorization. Verify with `gh project list --owner gabriel-amyot`, then verify the issue's actual Project membership after adding it.

In the 2026-11-04 session, Gabriel completed this refresh, Project enumeration succeeded, and #623 was added to [Project 1](https://github.com/users/gabriel-amyot/projects/1). This is historical verification, not a permanent credential-health claim.

Source: visual-harbor, thread 01a1a724-00ad-74e2-aa21-22693499c9d1. [Permission-repair receipt](https://github.com/gabriel-amyot/klever-project-management/issues/623#issuecomment-6634761406).
