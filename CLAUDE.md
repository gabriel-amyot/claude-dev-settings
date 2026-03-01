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
- When only incomplete or contradictory instructions/context is available, read the README.md.
- Do not reflexively agree when challenged. Hold your position if you believe it's correct and explain why. If you genuinely change your mind, state what specific new information changed it — not just that the user pushed back. Be critical and constructive. The goal is for optimal contribution.
- **No dash separators at all.** Never use em-dash (—), hyphens (-), or double-hyphens (--) as sentence separators. They feel alien. Use natural conversational language instead: periods, commas, conjunctions. Example: "I heard you on this, and here's why" instead of "I heard you on this - here's why".

# Development Workflow
- Before starting a feature or bug fix in a git repo:
	- Check if the branch is clean and up to date
	- If on a feature branch (not dev/main/master), recommend switching back to the main branch (contextual: some repos use `dev`, most use `main` or `master`)
	- Propose: switch to main branch → pull origin → create a new branch for the fix/feature
- **Branch naming:** `{TICKET-ID}-short-description` — e.g., `SPV-23-datastore-adapter-lenient-types`. No `fix/`, `feature/`, `chore/` prefixes. No folder-style separators.
- Assume feature flags will be used for any complex feature implementation — wire up from the start with fallback to legacy behavior when disabled.
- **NEVER commit documentation to repo** — put implementation summaries, design docs, analysis in `project-management/tickets/{ticket-or-branch-name}/`
- **Don't touch what you don't understand.** If you see something unfamiliar in the codebase (a config field, an input variable, a file you didn't create), do NOT delete or modify it. Ask the user first.
- **You don't own other people's code.** Other engineers contribute to these repos. Respect their work. If something looks wrong but was added by someone else, flag it — don't silently change it.
- **Long-running agent sessions (>30 min):** Create WIP commits at logical boundaries (per AC or per logical unit). Uncommitted code dies with the context window.
- **Scope agent sessions to 2-3 ACs max.** Break larger work into sequential sessions: research/docs first, then code, then review. Each session reads the previous session's distilled output, not raw source material.
- **Separate research from coding.** Session A produces docs/plans (committed). Session B reads the plan and writes code. Session C reviews. This prevents context explosion from reading large architecture docs AND writing code in the same session.

# Autonomous Mode
When the user explicitly opts out of human gates ("don't ask questions until done", "go autonomous", "work overnight"), follow these guardrails:
- **Status reports:** Write progress snapshots to `tickets/{ID}/reports/status/` at each meaningful milestone (not every iteration, but every phase gate).
- **WIP commits:** Commit at logical boundaries. Uncommitted code dies with the context window.
- **Context management:** Compact at 85% context utilization. After compaction, reload the plan file and any front-loader docs (README, STATUS_SNAPSHOT) to restore working context.
- **Diagnose-fix loop:** Budget 5-7 iterations max. Each iteration targets one specific blocker. If stuck after budget, write a status report with what's blocked and stop.
- **Multi-agent model assignment:** Haiku for straightforward coding tasks. Sonnet for QA, diagnostics, and code review. Opus for architecture supervision and integration decisions.
- **Adversarial gate:** After all tests pass, run `/adversarial-review` before declaring phase complete. A green suite is not proof of correctness until a reviewer has challenged it.

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

# File Handling

## Reading .pptx Files
When asked to read or analyze a `.pptx` file:
1. Unzip it to `/tmp/` using Python's `zipfile` module
2. Slides are stored as images in `ppt/media/` (e.g., `Slide-1-image-1.png`)
3. Read each image using the Read tool to see slide content visually
- Text in `.pptx` slides is often embedded in images, not extractable as text directly

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
