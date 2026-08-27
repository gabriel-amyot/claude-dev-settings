Configurations
- add any localy available AGENTS.md, agents.md or GEMINI.md to your context.
- **Skip generated mirrors.** An AGENTS.md whose first line is `<!-- generated-mirror-of-claude-md -->` is a verbatim copy of a CLAUDE.md you have already loaded. Do NOT load it. Loading both doubles the context cost for zero new information.

# Organizations

| Org | Root |
|-----|------|
| Personal | `~/Developer/gabriel-amyot` |
| Klever | `~/Developer/grp-beklever-com` |
| Supervisr.ai | `~/Developer/supervisr-ai` |
| Origin8 | `~/Developer/origin8` (legacy → managed from Supervisr.ai) |

When navigating between projects, starting work on a ticket, or when user mentions a specific org/project, read `~/.claude/library/context/workspace-map.yaml` for full paths and conventions.

# Org Isolation
- **Scope all queries to the current org.** Determine the active org from the current working directory using the Organizations table above. Only pass the matching `--org` flag to Jira, only read repos under that org's root, and only present data from that org. "The company," "big picture," "what's happening" all mean the current org, never all orgs.
- **Cross-org queries require explicit user request.** If the user says "across all orgs," "including Klever," or switches directories, then and only then expand scope. Never infer cross-org intent from an ambiguous prompt.
- **Subagent dispatch must include org constraint.** When dispatching subagents for Jira, git, or file operations, explicitly pass the resolved org name and instruct the subagent to query only that org.

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
- **ALWAYS render MR / PR / Jira references as clickable links — every time, in every output (chat, tables, reports, docs, external posts). No exceptions.** Never write a bare `!131`, `KTP-951`, or `#267`. Format: `[!131](<full MR/PR URL>)`, `[KTP-951](https://beklever.atlassian.net/browse/KTP-951)`. Jira base: `https://beklever.atlassian.net/browse/<KEY>` (Klever) / `https://origin8cares.atlassian.net/browse/<KEY>` (Supervisr). GitLab MR: `<project web_url>/-/merge_requests/<iid>`. GitHub PR: `<repo url>/pull/<n>`. If the URL is unknown, fetch it before emitting the reference; do not fall back to a bare number.
- **Skills use `Skill` tool. Agents use `Agent` tool.** Any `plugin:skill` colon-named thing (e.g. `agent-browser:dogfood`, `ralph-loop:ralph-loop`) goes through the `Skill` tool. Only names from the Agent tool's registered agent list go in `Agent` `subagent_type`. Wrong tool = instant error + wasted tokens.
- **Never rely on the exit status of a piped git command.** A pipe reports the LAST command's status, so `git push | tee log` looks successful even when the push failed. Pipe read-only queries freely (`git log | head`). Run a mutation (`push`, `commit`, `tag`, `fetch`, `merge`, `rebase`, `reset`) unpiped so a failure is visible.
- When only incomplete or contradictory instructions/context is available, read the README.md.
- Do not reflexively agree when challenged. Hold your position if you believe it's correct and explain why. If you genuinely change your mind, state what specific new information changed it — not just that the user pushed back. Be critical and constructive. The goal is for optimal contribution.
- When given feedback mid-build, capture it as notes first. Do not reflexively tear down or discard the ideas already built. Take the notes, then decide what actually changes.
- Never correct Gabriel's English or grammar. He is not a native speaker and does not want language coaching. Read through typos and phrasing to the intent; do not teach English.
- **No dashes as separators.** Never use em-dash, hyphens, or double-hyphens to join sentences. Use periods, commas, or conjunctions instead.
- **Never rewrite git history.** No `git push --force`, `git rebase` on shared branches, `git reset --hard` to before pushed commits, `git commit --amend` on pushed commits, or any other history-rewriting operation. This is absolute, even if the user approves it. If the user insists, provide the exact command with full context (branch, remote, paths) for them to run manually. You will not execute it.

# Mechanical Backstops

Hooks enforce many rules in this file. They are defense-in-depth, never a substitute: each has known gaps, and **a hook that does not fire is not permission**. Which hook covers which rule, and where the gaps are: `~/.claude/library/context/mechanical-backstops.md`.

---

# Inline Review with Crit
- **Recommend `/crit:crit` before committing to a plan or a large diff.** When you finish a written plan, or when a diff is large enough that scanning it inline is error-prone (roughly 100+ changed lines or 5+ files), proactively suggest running `/crit:crit` so the human can leave inline comments in the browser and you address them in a loop. Recommend, don't force: a one-line change or a quick answer doesn't need it.
- The crit CLI must be installed (`brew install crit`); the plugin ships only the skill. If `crit` returns `command not found`, surface that and stop rather than guessing an install path.

# BMAD Workflows
- No directory constraints. BMAD workflows run from wherever you are (typically project-management). Don't invent execution context requirements. If unsure, ask.

# Development Workflow
- **Secrets never committed.** When touching a repo's `.gitignore`, ensure `*.token`, `*.secret`, `.env`, and any credential files are listed. Before committing, verify no secrets are staged. If a secret file exists untracked, add the pattern to `.gitignore` before doing anything else.
- **Clean repo gate (new session).** At the start of a new session, before writing any code to a repo: `git fetch origin` then verify no unstaged/uncommitted changes exist. If the working tree is dirty, stop and ask the user how to proceed (stash, commit, or discard). Within a continuing session, in-progress uncommitted work is expected and fine.
- **Fetch-before-read gate (reasoning about deployed code).** Before drawing any conclusion from local repo code that reflects a deployed environment: `git fetch` (sequential, never piped), then `git rev-list --count HEAD..origin/<default-branch>`. If the count is > 0 the checkout is stale — sync, or read `origin/<branch>:path`, BEFORE concluding. This applies to READS, not just edits. Derived knowledge docs (bibliothèque, ADRs, handoffs) that assert what deployed code does are hypotheses, not ground truth. Detail and the KTP-781 write-up: `~/.claude/library/context/deploy-identity-gate.md`.
- **Deploy-identity gate (staleness is not the same as which branch deploys).** `git rev-list HEAD..origin/main = 0` proves "my main is current". It does NOT prove "main is what deploys." Some repos invert the DAC norm: `app-agent-hub` has `main` as default but `dev` deploys. Before any claim about DEPLOYED code, run `/deploy-identity`. Confidence is an OUTPUT of that probe, never self-asserted: HIGH only on `VERIFIED`. Code-location claims that leave your context carry the stamp `[VERIFIED against dev@<sha>]` or `[UNVERIFIED — read on main, deploy=dev]`. A challenge from a code owner is a falsification trigger, not a prompt for more confirming evidence. Full procedure and stamps: `~/.claude/library/context/deploy-identity-gate.md`.
- **A diagnosis is a hypothesis until it is stamped.** In any RCA, status, or handoff doc: an unverified finding files under an "Open Questions / Unverified" heading. A `Verdict:` line is permitted only with a `verified_against: <commit-or-query>` stamp. This applies to every diagnosis doc, not only deployed-code ones. Unstamped verdicts get read as fact by the next agent.
- Before starting a feature or bug fix in a git repo:
	- Check if the branch is clean and up to date
	- If on a feature branch (not dev/main/master), recommend switching back to the main branch (contextual: some repos use `dev`, most use `main` or `master`)
	- Propose: switch to main branch → pull origin → create a new branch for the fix/feature
- **Main worktree stays clean.** All code edits happen in git worktrees, never in the main checkout. On a block: `git fetch origin`, then invoke `superpowers:using-git-worktrees`. `project-management/` is exempt.
- **Branch naming:** `{TICKET-ID}-short-description` — e.g., `SPV-23-datastore-adapter-lenient-types`. No `fix/`, `feature/`, `chore/` prefixes. No folder-style separators.
- **Commit messages must contain why and what.** First line: `{TICKET-ID}: {short imperative what}`. Body: why this change exists (problem/ask), then what changed (outcome, not file list). MR descriptions are built from commits, so each commit must be self-explanatory.
- Assume feature flags will be used for any complex feature implementation — wire up from the start with fallback to legacy behavior when disabled.
- **NEVER commit documentation to repo** — put implementation summaries, design docs, analysis in `project-management/tickets/{ticket-or-branch-name}/`
- **Don't touch what you don't understand.** If you see something unfamiliar in the codebase (a config field, an input variable, a file you didn't create), do NOT delete or modify it. Ask the user first.
- **You don't own other people's code.** Other engineers contribute to these repos. Respect their work. If something looks wrong but was added by someone else, flag it — don't silently change it.
- **After pushing a new branch to GitLab:** Always create an MR immediately. No exceptions confirmed by user.
- **DAC repos: `dev` is the default branch.** Push changes to `dev` only. To promote to `uat` or `main`, create a merge request. Never push directly to `main` or `uat` on DAC repos. Before pushing, verify the default branch with `git branch -r | grep HEAD`. See [[dac-workflow]].
- **Datasophia terraform registry nightly downtime.** `cicd.prod.datasophia.com` goes down ~11 PM to 5 AM ET every night. All DAC pipelines fail with "Error accessing remote module registry" during this window. Do NOT retry in a loop. Schedule DAC deploys before 11 PM or leave for morning. See [[ci-cd-patterns]].
- **Long-running agent sessions (>30 min):** Create WIP commits at logical boundaries (per AC or per logical unit). Uncommitted code dies with the context window.
- **Subagent outputs must be committed immediately.** When a subagent writes files (CLAUDE.md, agent-os/, docs/), verify they exist on disk AND commit them before claiming "done." Untracked files are wiped by `git clean`, `git checkout`, or repo switches. See [[session-file-wipe]].
- **Scope agent sessions to 2-3 ACs max.** Break larger work into sequential sessions: research/docs first, then code, then review. Each session reads the previous session's distilled output, not raw source material.
- **Separate research from coding.** Session A produces docs/plans (committed). Session B reads the plan and writes code. Session C reviews. This prevents context explosion from reading large architecture docs AND writing code in the same session.

# Spec Fidelity
- **Never add endpoints, APIs, or interfaces not explicitly covered in the spec.** If the spec says Query X lives on Service A, do not also add Query X to Service B for convenience. Read the architecture spec before adding any new public interface.
- **Never modify the spec to justify a code change.** If the code you want to write contradicts the spec, STOP.
  - **Interactive mode:** Ask the user whether the spec or the code intent is correct.
  - **Headless/overnight mode:** Spawn an Opus architect agent and a contrarian reviewer agent. Spend tokens analyzing the conflict. If their conclusion is "the spec needs to change," park the task with a written rationale in `tickets/{ID}/reports/status/` and move on to the next non-dependent task. Do NOT commit spec changes autonomously.
- **Hacks for validation are OK, commits are not.** If you need a temporary endpoint to test something (e.g., peek inside an opaque service), you may create it locally and run tests against it. But do NOT commit it. If the hack reveals a real need, document it as a proposal in `tickets/{ID}/reports/architecture/` for user review.
- **ADR-023** codifies this for the dreampipe pattern specifically: source-of-truth services must not expose search/list queries that duplicate EQS's role.

# Git History Claims
- **Never assert "X never existed" in external content without `git log -S` proof.** Load `~/.claude/library/context/git-history-verification.md` before writing or reviewing any PR body that makes historical claims about code.

# Autonomous Mode & The Factory Family

Three tools cover ticket-to-dev automation. They are **different modes, not three versions of one thing.** Pick by shape of work.

| Tool | Substrate | Use it for |
|------|-----------|-----------|
| **dark-factory** (`/dark-factory KTP-XXX`) | Workflow-tool script, JS gates (un-skippable), human concierge front gate, tool belts (java/scripting), segregated review + bounded fix loop + QA in worktrees, Retro telemetry. Terminal state `READY_TO_SHIP`; main loop does MR+Jira+validate. | **Single ticket, interactive/gated.** The default for one well-specified ticket where you want a human decision point at the front. (Formerly "dark-factory v2".) |
| **Sprint Factory** (`/sprint-factory`, formerly "dark-factory v1") | Prose orchestration + agent dispatch. Multi-ticket DAG: flat list (auto-dep-checked) or plan-file with YAML dependency graph → topological tiers → parallel dispatch → inter-tier gates → integration tests. Idempotent rerun (reconciles from Jira + ledger). | **Multi-ticket / epic.** When tickets have dependencies and you want tiered parallel execution. Conducts each ticket through `/dark-factory` via handoffs. |
| **sprint-crawl** (`/sprint-crawl KTP-XXX`) | Agent + sprint-harness Bash hooks (phase-gate, stop-guard, context-reinject, audit-trail). Per-AC, resumable across context death. | **Overnight-autonomous, single ticket, per-AC.** When you'll lose the session (sleep, long run) and need hook-enforced resilience. Wrap in ralph-loop for persistence. |

**Triggers** ("go autonomous", "work overnight", "run this ticket", "one-shot this"): for an unattended overnight single ticket → `sprint-crawl` (+ ralph-loop). For an interactive single ticket → `/dark-factory`. For a dependency-linked set → `/sprint-factory`.

**Overnight with ralph-loop:**
```
/ralph-loop:ralph-loop "sprint-crawl KTP-XXX" --completion-promise "ALL_ACS_DONE" --max-iterations 10
```

**When NOT to use any of them:** Spikes, quick bug fixes, research tasks, tickets without clear ACs.

**Legacy agents** (night-crawl, dev-crawl) remain for Supervisr-specific infra work (deploy+verify against GCP dev).

# Jira Skill
- Always pass `--org {klever|supervisrai}` when running `jira_skill.py` from outside the org path. For gotchas (slug list, subcommand names, `[automated]` header rule, deadline mode), load `~/.claude/library/context/jira-skill-gotchas.md`.

# Autonomous Crawls

Rules that apply only inside a night-crawl, dev-crawl, sprint-crawl, or ralph-loop live in `~/.claude/library/context/autonomous-crawl-rules.md`. Load it before starting any unattended run. It covers: never replacing proven code on an unverified hypothesis, handling architecture discovered mid-crawl, fixing pre-existing test failures, spec conflicts in headless mode, ralph-loop multi-terminal conflicts, and WIP-commit hygiene.

# Ticket References
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
- **DAC repos: merge-forward model.** DAC repos on GitLab have three branches reflecting environments: `dev`, `uat`, `main` (prod). Each branch auto-deploys on push. ALL changes go to `dev` first. Promotion is manual forward-merge: dev → uat → main. Agents NEVER push to `main` or `uat` on DAC repos. Before any `git push` on a repo whose path contains `grp-dac`, verify the target branch is `dev`. If not, STOP. Hotfixes to uat/main are always human-initiated. See [[dac-workflow]].
- **Pipeline retry circuit breaker.** If a CI/CD pipeline fails with the same error 3 consecutive times, stop retrying. Document the infrastructure blocker and exit the loop. Never trigger more than 5 pipelines for the same commit in a single session. Registry outages, build infra failures, and network errors are not transient, they last hours. See [[ci-cd-patterns]].
- **IAM/Auth changes require human gate.** Any change to `allUsers`, `permitAll()`, `iam_public_access`, invoker bindings, OAuth security filters, or M2M scope modifications on shared environments (Dev, UAT, Prod) MUST be surfaced to the user as a blocking proposal before committing. Present the exact diff, explain why you believe it's necessary, and wait for explicit approval. Do not proceed until the user reviews and confirms. R&D-BAC1 is exempt (isolated, tear-down-after). Auth failures (403/401) on shared environments are blockers to document and escalate, not obstacles to work around. See [[klever-grant-user-resource-access]].

- **Every data mutation script must back up before writing.** Any script that writes, updates, or deletes datastore or database entities MUST first read and save the affected records to a local JSON backup at `tickets/{TICKET-ID}/data/backups/` with a timestamped filename. Never inside a service repo. One line changed equals one line backed up. No exceptions, even for "idempotent" operations. If you cannot back up, stop and ask the user.
- **A Datastore `upsert` replaces the whole entity.** Any property missing from the payload is silently deleted. Read the full entity first and include ALL fields, or use a patch operation instead.
- Backup paths, filename convention, and both incident write-ups: `~/.claude/library/context/data-mutation-safety.md`.

When tagging, shipping, deploying, creating merge requests, or working with CI/CD, read `~/.claude/library/context/shipping-workflow.md` for the full workflow.

# Creating New Skills & Agents

Design from the consumer backwards: identify the pipeline gap the thing fills, read the formats it must consume and produce, then build. Update `MEMORY.md` and any skills index with its pipeline position.

**Every new SKILL.md needs a `nav:` block** in its frontmatter (bays: `build`, `fix`, `review`, `ship`, `plan`, `know`, `ops`) with `when:` and `when_not:`. Copy the shape from an existing SKILL.md.

Full procedure: the `write-a-skill` and `skill-creator` skills.

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

# Bibliothèque — User-Level Knowledge Library

Cross-org operational knowledge lives in `~/.claude/library/`. Entry point: `~/.claude/library/INDEX.md`. Org-specific domain knowledge lives in each org's own Bibliothèque:
- **Klever:** `~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/INDEX.md`
- **Supervisr.AI:** `~/Developer/supervisr-ai/project-management/documentation/bibliotheque/INDEX.md`

**Library-first is ambient, not on-request.** Labeling an org mechanism "UNVERIFIED"/unknown is an epistemic claim, and it is false if the bibliothèque already documents it — the user must never serve as the retrieval layer for your own knowledge base. Before declaring any org-system mechanism unknown, mapping a system's topology, or dispatching a discovery probe: check the org bibliothèque's `INDEX.md` + `ALIASES.md` (or `bibliotheque-librarian` query mode). Every system-investigation subagent prompt carries a `Library:` line — cited doc paths + what they establish, or `Library: silent (checked INDEX/ALIASES for <topic>)`; what the library establishes is context to hand over, not a question to re-probe. See [[bibliotheque-ambient-consultation]].

## On-Demand Context Files

Not listed here. `~/.claude/library/ALIASES.md` indexes every file in `~/.claude/library/context/`, and the `bibliotheque-recall.sh` hook matches your prompt against it and injects the pointer for you. Adding a row there costs nothing at load time; listing them here costs every session.

If nothing surfaces and you still need a file, read `~/.claude/library/INDEX.md`.

# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

# Writing Style — STE Anti-Slop (applies to ALL output to Gabriel)

Write in the ASD-STE100 mechanical subset. This is the default voice for every response, not a mode to invoke. It cuts the six AI-slop patterns: synonym rotation, hedging, frozen verbs, marketing adjectives, run-ons, and phrasal verbs.

- One idea per sentence. Max 20 words for steps, 25 for prose. Split run-ons.
- Active voice. Use a verb for an action ("analyze", not "perform an analysis of").
- One name for one thing. Do not rotate synonyms (user / customer / client).
- No phrasal verbs: "start" not "spin up", "contact" not "reach out", "review" not "dive into".
- No marketing adjectives: seamless, robust, powerful, cutting-edge, next-generation.
- No hedges: "it is important to note", "this may potentially".
- No semicolons or run-ons. Write two sentences.
- Keep articles (a, an, the). This is the one point where STE diverges from `/caveman`: caveman drops articles to compress, STE keeps them to remove ambiguity. Use caveman for internal token cutting, STE for clarity.
- Em-dash stays allowed only as a heading label (existing rule); never as a sentence separator.

**This is guidance for conversation. On-disk external artifacts are enforced mechanically** by `~/.claude-shared-config/tools/ste_lint.py` (scored per 100 words), wired into post-comment, klever-mr, klever-3ps, and bibliotheque-librarian. See `~/.claude-shared-config/docs/specs/2026-07-30-ste-anti-slop-design.md`.
