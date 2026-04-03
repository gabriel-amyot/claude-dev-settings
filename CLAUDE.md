Configurations
- add any localy available AGENTS.md, agents.md or GEMINI.md to your context.

# Organizations

| Org | Root |
|-----|------|
| Personal | `~/Developer/gabriel-amyot` |
| Klever | `~/Developer/grp-beklever-com` |
| Supervisr.ai | `~/Developer/supervisr-ai` |
| Origin8 | `~/Developer/origin8` (legacy → managed from Supervisr.ai) |

When navigating between projects, starting work on a ticket, or when user mentions a specific org/project, read `~/.claude/library/context/workspace-map.yaml` for full paths and conventions.

# Context Engineering
- **Progressive disclosure.** Index → metadata → selective read. Never bulk-load.
- **Recursive INDEX.md.** Every document folder needs one. Read the index, pick selectively, never read all files.
- **Metadata before content.** Explore via filenames, folder structure, and indexes before reading full files.
- **Every write requires an index update.** Update the nearest INDEX.md after creating or modifying a document.
- **Library writes follow the Librarian Protocol.** When adding files to `library/`: (1) name as `{domain}-{purpose}-{key-concepts}.md`, (2) place in the correct section, (3) update that section's `INDEX.md`, (4) add to `library/CATALOG.md` Topic Cross-Reference if cross-cutting. Read `library/CATALOG.md` before shelving new knowledge.
- **Distill, don't accumulate.** Write summaries to disk between phases. Index them. Never carry raw material across sessions.
- **All context is on-demand** except CLAUDE.md files (auto-loaded). Everything else: load when the task requires it.
- **Persist state before compaction.** Write SESSION_STATE.md to the working or ticket directory at logical boundaries and before compaction. Include: current goal, progress, decisions with rationale, constraints, blockers, modified files. Read it back after compaction before continuing.
- **Delegate deep work to subagents.** Research, exploration, and large reads go to subagents that return condensed summaries (1-2k tokens). Keep the orchestrator's context clean for decision-making.

For the full framework (compaction strategies, note-taking patterns, subagent architecture), see the On-Demand Context table.

# Data Stays on Disk, Not in Context
- **Never load, scrape, or paste large datasets into the conversation.** If the user asks to analyze a CSV, scrape a website, query an API, parse logs, or process any bulk data, generate a self-contained script (Python, Bash, Node, etc.) that the user can run locally. Write the script to disk using the Write tool.
- **This applies to:** CSV/JSON/XML files, database query results, web scraping output, API response dumps, log files, spreadsheet contents, and any data larger than ~50 lines.
- **The script should:** read the source data, perform the requested analysis/transformation, and write results to an output file. Include clear instructions for how to run it.
- **Why:** Loading raw data into context burns tokens fast, hits limits, and provides no lasting value. A script is reusable, shareable, and costs zero tokens to execute.
- **Exception:** Small lookups (a few rows, a single API response under ~50 lines) that directly answer a question can be loaded into context. When in doubt, script it.

# Core Rules
- Never pipe git commands. Run them sequentially (e.g., `git fetch` then `git status`, not `git fetch && git status`).
- When only incomplete or contradictory instructions/context is available, read the README.md.
- Do not reflexively agree when challenged. Hold your position if you believe it's correct and explain why. If you genuinely change your mind, state what specific new information changed it — not just that the user pushed back. Be critical and constructive. The goal is for optimal contribution.
- **No dashes as separators.** Never use em-dash, hyphens, or double-hyphens to join sentences. Use periods, commas, or conjunctions instead.
- **Never rewrite git history.** No `git push --force`, `git rebase` on shared branches, `git reset --hard` to before pushed commits, `git commit --amend` on pushed commits, or any other history-rewriting operation. This is absolute, even if the user approves it. If the user insists, provide the exact command with full context (branch, remote, paths) for them to run manually. You will not execute it.

# BMAD Workflows
- No directory constraints. BMAD workflows run from wherever you are (typically project-management). Don't invent execution context requirements. If unsure, ask.

# Development Workflow
- **Secrets never committed.** When touching a repo's `.gitignore`, ensure `*.token`, `*.secret`, `.env`, and any credential files are listed. Before committing, verify no secrets are staged. If a secret file exists untracked, add the pattern to `.gitignore` before doing anything else.
- **Clean repo gate (new session).** At the start of a new session, before writing any code to a repo: `git fetch origin` then verify no unstaged/uncommitted changes exist. If the working tree is dirty, stop and ask the user how to proceed (stash, commit, or discard). Within a continuing session, in-progress uncommitted work is expected and fine.
- Before starting a feature or bug fix in a git repo:
	- Check if the branch is clean and up to date
	- If on a feature branch (not dev/main/master), recommend switching back to the main branch (contextual: some repos use `dev`, most use `main` or `master`)
	- Propose: switch to main branch → pull origin → create a new branch for the fix/feature
- **Branch naming:** `{TICKET-ID}-short-description` — e.g., `SPV-23-datastore-adapter-lenient-types`. No `fix/`, `feature/`, `chore/` prefixes. No folder-style separators.
- Assume feature flags will be used for any complex feature implementation — wire up from the start with fallback to legacy behavior when disabled.
- **NEVER commit documentation to repo** — put implementation summaries, design docs, analysis in `project-management/tickets/{ticket-or-branch-name}/`
- **Don't touch what you don't understand.** If you see something unfamiliar in the codebase (a config field, an input variable, a file you didn't create), do NOT delete or modify it. Ask the user first.
- **You don't own other people's code.** Other engineers contribute to these repos. Respect their work. If something looks wrong but was added by someone else, flag it — don't silently change it.
- **After pushing a new branch to GitLab:** Always create an MR immediately. No exceptions confirmed by user.
- **Long-running agent sessions (>30 min):** Create WIP commits at logical boundaries (per AC or per logical unit). Uncommitted code dies with the context window.
- **Scope agent sessions to 2-3 ACs max.** Break larger work into sequential sessions: research/docs first, then code, then review. Each session reads the previous session's distilled output, not raw source material.
- **Separate research from coding.** Session A produces docs/plans (committed). Session B reads the plan and writes code. Session C reviews. This prevents context explosion from reading large architecture docs AND writing code in the same session.

# Spec Fidelity (Learned from SPV-3: searchLeads incident)
- **Never add endpoints, APIs, or interfaces not explicitly covered in the spec.** If the spec says Query X lives on Service A, do not also add Query X to Service B for convenience. Read the architecture spec before adding any new public interface.
- **Never modify the spec to justify a code change.** If the code you want to write contradicts the spec, STOP.
  - **Interactive mode:** Ask the user whether the spec or the code intent is correct.
  - **Headless/overnight mode:** Spawn an Opus architect agent and a contrarian reviewer agent. Spend tokens analyzing the conflict. If their conclusion is "the spec needs to change," park the task with a written rationale in `tickets/{ID}/reports/status/` and move on to the next non-dependent task. Do NOT commit spec changes autonomously.
- **Hacks for validation are OK, commits are not.** If you need a temporary endpoint to test something (e.g., peek inside an opaque service), you may create it locally and run tests against it. But do NOT commit it. If the hack reveals a real need, document it as a proposal in `tickets/{ID}/reports/architecture/` for user review.
- **ADR-023** codifies this for the dreampipe pattern specifically: source-of-truth services must not expose search/list queries that duplicate EQS's role.

# Autonomous Mode & Crawls
When the user wants to run autonomously, do a night crawl, or any iterative agent loop, follow this protocol:

1. **Identify the agent** (behavior): `night-crawl` (plan+fix+review), `dev-crawl` (deploy+verify+diagnose)
2. **Identify the harness** (environment): `local-harness`, `rnd-harness`, `dev-harness`. Ask if ambiguous.
3. **Run pre-flight:** `/pre-flight --profile {harness}`
4. **Launch:** `/ralph-loop {agent} {ticket} --completion-promise "{PROMISE}" --max-iterations {N}`

Natural language triggers and what to do:
- "go autonomous" / "work overnight" / "night crawl" → night-crawl agent, ask which harness
- "run against dev" / "deploy to dev" → dev-crawl agent + dev-harness
- "run against rnd" / "test on rnd" → agent + rnd-harness
- "run locally" / "local harness" → agent + local-harness
- "ralph loop on X" → ask which agent and harness if not obvious from context

Harness profiles: `~/.claude/crawl-profiles/{local,rnd,dev}-harness.yaml`
Do NOT quote the prompt in `/ralph-loop`. Example: `/ralph-loop night-crawl SPV-3 --max-iterations 7`

# Jira Subagent Org Detection
- When spawning haiku subagents to run `jira_skill.py`, always pass `--org {org}` (e.g., `--org klever`). Subagents `cd` to the skill directory (`~/.claude/skills/jira/`), which is outside the org auto-detection path. Without the flag, queries hit the wrong Jira instance. Learned from 2026-03-31 sprint closure session.

# Ralph Loop Multi-Terminal Conflicts
- `.claude/ralph-loop.local.md` is per-repo, not per-session. Two terminals in the same repo will fight over it. When a stop hook feeds a task from another session (wrong ticket, wrong completion promise), do NOT start working on it. Check the ralph-loop file, confirm it's stale or from another terminal, and `rm .claude/ralph-loop.local.md` to break the cycle. Never delete blindly without reading the file first. Learned from 2026-04-01: KTP-329 loop bled into KTP-430 session via shared file.

# Architecture Discovery During Crawls
- When a night crawl plan says "implement X" but code investigation reveals the architecture already handles the intent differently, do NOT force the planned change. Instead: (1) document the finding, (2) verify the existing behavior satisfies the AC, (3) create a tentative ADR in `documentation/architecture/adr/` (or the repo's `agent-os/architecture/adr/`) for the user to confirm. The ADR should capture: what the plan said, what the code actually does, why the existing approach is sufficient (or not), and the Phase 2 risk if applicable. The user must confirm the ADR before it's considered accepted. Learned from KTP-430 AC-4: plan said "add OR CHANNEL = 'UNKNOWN' to WHERE clause" but real-data queries already bypass channel filtering entirely.

# Pre-existing Test Failures in Crawls
- When running tests after code changes reveals failures that predate your changes (stale assertions, UnnecessaryStubbing from Mockito strict mode, etc.), fix them as part of the crawl. Attribute clearly in the commit message: "Fixed pre-existing test bug: [description]." Do not leave pre-existing failures unresolved as they mask whether your changes introduced regressions. Learned from KTP-430 crawl: StatePerformanceBigQueryAdapterTest had stale "United States" assertion and 3 adapter tests had UnnecessaryStubbing errors predating the crawl.

# Ticket References (Learned from SPV-69 session)
- **Never use internal/made-up task names in external-facing content** (commits, PRs, Jira comments, Slack). Always use the real Jira ticket key (e.g., SPV-69, not "A-3").
- Internal shorthand (A-1, A-2, B-3, etc.) from planning docs is for internal context only. Before referencing a task externally, look up the Jira key using the `/jira` skill.
- If no Jira ticket exists for the work, propose creating one before committing or posting.

# External Posts (PR comments, Jira comments, Slack)
Never generate or post externally visible content inline. All external posts go through `/post-comment`.
Protocol: write draft to disk, invoke `/post-comment`, agent renders via template, previews full content, waits for explicit approval, posts, logs to audit trail.

This applies to: GitHub PR comments/replies, Jira comments/ticket updates, Slack messages, GitLab MR comments, and any external API that writes content others can see. No exceptions, even if a plan was previously approved.

- **Never mention autonomous tooling externally.** Night-crawls, dev-crawls, ralph-loops, agent sessions, subagent orchestration, and any autonomous tooling are internal implementation details. In standups, 3Ps, Jira comments, Slack messages, PRs, and any team-visible content, present outcomes only. Say "verified adapter wiring, added unit tests" not "night-crawl agent session completed overnight."

# Shipping Safeguards
- Do NOT run GitLab pipelines from Claude in PROD nor UAD (Exception DEV, you can in DEV)
- Do NOT update GitLab CI/CD variables from Claude  in PROD nor UAD (Exception DEV, you can in DEV)
- Do NOT run terraform plan/apply
- Commits and tags push; CI/CD picks up automatically
- **IAM/Auth changes require human gate (Learned from EQS permit-all incident 2026-03-16).** Any change to `allUsers`, `permitAll()`, `iam_public_access`, invoker bindings, OAuth security filters, or M2M scope modifications on shared environments (Dev, UAT, Prod) MUST be surfaced to the user as a blocking proposal before committing. Present the exact diff, explain why you believe it's necessary, and wait for explicit approval. Do not proceed until the user reviews and confirms. R&D-BAC1 is exempt (isolated, tear-down-after). Auth failures (403/401) on shared environments are blockers to document and escalate, not obstacles to work around.

When tagging, shipping, deploying, creating merge requests, or working with CI/CD, read `~/.claude/library/context/shipping-workflow.md` for the full workflow.

# Creating New Skills & Agents
- When creating a new agent (`~/.claude/agents/`), always: (1) identify the pipeline gap it fills (what feeds in, what it feeds into), (2) read existing templates/formats it must consume or produce, (3) update MEMORY.md with the agent's role and pipeline position, (4) update the skills-and-agents-index if one exists for the project.
- Agent output format must match what downstream tools expect. Design from the consumer backwards.
- After creating any skill or agent, check if a decision/design questions document exists and mark questions as answered.

# Ticket Closure & Bug Fix Protocols
- **Never close a ticket without adversarial review and evidence-backed closing comment.**
- Full procedures (adversarial gate, coverage classifications, bug fix protocol) in `~/.claude/library/context/ticket-quality-standards.md`.

# Code Style Preferences
- Code should be self-documenting. Name variables and methods intuitively. If explanation is truly needed, use `log.debug()` instead of comments.
- **Keep methods small and focused** — extract helper methods. Boolean helpers should read like questions: `isStaleWebhook()`, `hasPermission()`, `shouldRetry()`.
- No comment cruft — a well-named method is better than a comment.

When writing or reviewing Java code, read `~/.claude/library/context/java-standards.md` for Mockito, testing, and enforcement standards.

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
| Navigating orgs/projects, starting tickets | `~/.claude/library/context/workspace-map.yaml` |
| Tagging, shipping, deploying, merge requests, CI/CD, PR reviews | `~/.claude/library/context/shipping-workflow.md` |
| Writing/reviewing Java code | `~/.claude/library/context/java-standards.md` |
| Using Gemini CLI or analyzing large codebases | `~/.claude/library/context/gemini-cli-reference.md` |
| Creating PRDs, tickets, contracts, changelogs, ADRs | `~/.claude/library/context/tools-catalog.md` |
| Initializing tickets, organizing ticket folders, file placement | Project-level `documentation/process/ticket-initialization-guide.md` |
| Understanding domain terms, system capabilities, service catalog | Project-level `documentation/bibliotheque/INDEX.md` |
| Creating tickets, writing AC, defining stories, reviewing ticket quality | `~/.claude/library/context/ticket-quality-standards.md` |
| Editing any CLAUDE.md file (auto-injected by hook) | `~/.claude/library/context/claude-md-authoring.md` |
| Long-running agents, compaction, context limits, agent drift | `~/.claude/library/context/context-engineering.md` |
| Complex multi-service debugging, parallel investigation, blocker triage | `~/.claude/library/context/swarm-diagnostics.md` |
| Security hardening, credential rotation, permission audit | `~/.claude/library/context/security-audit-claude-code-config.md` |
