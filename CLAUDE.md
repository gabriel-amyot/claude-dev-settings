Configurations
- add any localy available AGENTS.md, agents.md or GEMINI.md to your context.

# Organizations

| Org | Root |
|-----|------|
| Personal | `~/Developer/gabriel-amyot` |
| Klever | `~/Developer/grp-beklever-com` |
| Supervisr.ai | `~/Developer/supervisr-ai` |
| Origin8 | `~/Developer/origin8` (legacy → managed from Supervisr.ai) |

When navigating between projects, starting work on a ticket, or when user mentions a specific org/project, read `~/.claude/context/workspace-map.yaml` for full paths and conventions.

# Core Rules
- Never pipe git commands. Run them sequentially (e.g., `git fetch` then `git status`, not `git fetch && git status`).
- Before running a project, read the README.md first.
- Sycophancy is prohibited. Be critical and constructive.

# Development Workflow
- Before starting a feature or bug fix in a git repo:
	- Check if the branch is clean and up to date
	- If on a feature branch (not dev/main/master), recommend switching back to the main branch (contextual: some repos use `dev`, most use `main` or `master`)
	- Propose: switch to main branch → pull origin → create a new branch for the fix/feature
- Assume feature flags will be used for any complex feature implementation — wire up from the start with fallback to legacy behavior when disabled.
- **NEVER commit documentation to repo** — put implementation summaries, design docs, analysis in `project-management/tickets/{ticket-or-branch-name}/`
- **Don't touch what you don't understand.** If you see something unfamiliar in the codebase (a config field, an input variable, a file you didn't create), do NOT delete or modify it. Ask the user first.
- **You don't own other people's code.** Other engineers contribute to these repos. Respect their work. If something looks wrong but was added by someone else, flag it — don't silently change it.

# Shipping Safeguards
- Do NOT run GitLab pipelines from Claude
- Do NOT update GitLab CI/CD variables from Claude
- Do NOT run terraform plan/apply
- Commits and tags push; CI/CD picks up automatically

When tagging, shipping, deploying, creating merge requests, or working with CI/CD, read `~/.claude/context/shipping-workflow.md` for the full workflow.

# Code Style Preferences
- Code should be self-documenting. Name variables and methods intuitively. If explanation is truly needed, use `log.debug()` instead of comments.
- **Keep methods small and focused** — extract helper methods. Boolean helpers should read like questions: `isStaleWebhook()`, `hasPermission()`, `shouldRetry()`.
- No comment cruft — a well-named method is better than a comment.

When writing or reviewing Java code, read `~/.claude/context/java-standards.md` for Mockito, testing, and enforcement standards.

# On-Demand Context Files

Load these via `Read` when the context calls for it:

| Trigger | File |
|---------|------|
| Navigating orgs/projects, starting tickets | `~/.claude/context/workspace-map.yaml` |
| Tagging, shipping, deploying, merge requests, CI/CD, PR reviews | `~/.claude/context/shipping-workflow.md` |
| Writing/reviewing Java code | `~/.claude/context/java-standards.md` |
| Using Gemini CLI or analyzing large codebases | `~/.claude/context/gemini-cli-reference.md` |
| Creating PRDs, tickets, contracts, changelogs, ADRs | `~/.claude/context/tools-catalog.md` |
| Initializing tickets, organizing ticket folders, file placement | `~/.claude/context/ticket-initialization.md` |
