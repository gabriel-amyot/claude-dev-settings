# Archive

Historical artifacts. Retired agent definitions, plugin snapshots, test cases. Kept for pattern mining and reference, not active use.

## Sections

### retired-agents/ — Agent definitions no longer in production
Code-reviewer variants superseded by `pr-review-toolkit` plugin agents. The orchestrator pattern influenced `supervisr-review`.

| File | Summary |
|------|---------|
| `code-reviewer-general-expert.md` | General expert reviewer: quality, security, best practices |
| `code-reviewer-architect-scalability.md` | Principal engineer: architecture, scalability, maintainability |
| `code-reviewer-frontend-react-typescript.md` | Frontend specialist: React, TypeScript components, UI logic |
| `code-reviewer-team-lead-mentorship.md` | Team lead: dynamics, onboarding, mentorship focus |
| `code-reviewer-security-vulnerabilities.md` | Security specialist: vulnerabilities, auth patterns, data handling |
| `code-reviewer-devops-infrastructure.md` | DevOps: infrastructure, deployment, monitoring, CI/CD |
| `code-reviewer-team-orchestrator.md` | Meta-reviewer: dispatches to all specialized reviewers above |
| `typescript-error-fixer-systematic.md` | TypeScript compiler and ESLint systematic resolution |

### superpowers-plugin/ — Snapshot of the superpowers Claude Code plugin
Plugin config, hooks, scripts, test cases, and tutorials. The skill content has been extracted to `practices/`.

| File | Summary |
|------|---------|
| `README.md` | Plugin overview: features, installation, usage |
| `RELEASE-NOTES.md` | Version history across multiple releases (451 lines) |
| `supervisr-autopilot-guide.md` | Autopilot agent complete guide: 10-phase architecture (642 lines) |
| `code-reviewer-agent.md` | Plugin's code reviewer agent definition |
| `using-superpowers-tutorial.md` | Tutorial for using the superpowers plugin |
| `plugin.json` | Plugin manifest |
| `marketplace.json` | Marketplace listing metadata |
| `hooks.json` | Hook configuration |
| `session-start.sh` | Session initialization hook script |
| `initialize-skills.sh` | Skill loading script |
| `INSTALL.md` | Installation guide |
| `superpowers-bootstrap.md` | Bootstrap configuration |
| `systematic-debugging-creation-log.md` | Debugging skill iteration history |
| `test-cases/` | 4 test scenarios for systematic debugging skill |
| `examples/` | Example CLAUDE.md for skill validation |
| `commands/` | 3 command stubs (write-plan, execute-plan, brainstorm) |
