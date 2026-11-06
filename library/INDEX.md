# Bibliothèque — User-Level Knowledge Library

Cross-org operational knowledge: tools, workflows, standards, and patterns that apply regardless of which organization you're working in. This is the global layer. Org-specific domain knowledge lives in each org's own Bibliothèque (see pointers below).

Start with this INDEX, then read selectively. Each section links to its files with one-line descriptions and load triggers.

---

## Org-Level Bibliothèques

| Org | Entry Point | Scope |
|-----|-------------|-------|
| Klever | `~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/INDEX.md` | Ad-tech, DSPs, vendors, Klever products, stack, BQ schemas, people, operations |
| Supervisr.AI | `~/Developer/supervisr-ai/project-management/documentation/bibliotheque/INDEX.md` | Lead lifecycle, EQS, compliance, dreampipe, Supervisr stack, operations |

When a question is org-specific (Klever ad-tech, Supervisr lead pipeline), read the org bibliothèque. When it's about tooling, workflows, or cross-cutting standards, read here.

---

## context/ — On-Demand Context Files

Loaded by trigger from `~/.claude/CLAUDE.md`. Never bulk-load; read only when the trigger matches.

### Development Workflow

| File | Trigger | Description |
|------|---------|-------------|
| [shipping-workflow.md](context/shipping-workflow.md) | Tagging, shipping, deploying, MRs, CI/CD | Tag, build, deploy, MR workflow across orgs |
| [java-standards.md](context/java-standards.md) | Writing/reviewing Java code | Mockito, testing, enforcement standards |
| [schema-validation-gate.md](context/schema-validation-gate.md) | Before wiring any BQ adapter | Verify actual BQ schema before coding |
| [documentation-standards-quick-ref.md](context/documentation-standards-quick-ref.md) | Writing/reviewing ADRs, placing docs | Three-layer doc model, ADR placement, migration checklist |

### Agent Operations

| File | Trigger | Description |
|------|---------|-------------|
| [context-engineering.md](context/context-engineering.md) | Long-running agents, compaction, context limits | Compaction strategies, note-taking, subagent architecture |
| [claude-md-authoring.md](context/claude-md-authoring.md) | Editing any CLAUDE.md file | DRY principle, satellite files, section ownership |
| [harness-self-management.md](context/harness-self-management.md) | Improving the harness, transcript mining, cost monitoring | Self-management ideas, batch API, cost optimization |
| [claude-config-filesystem-topology.md](context/claude-config-filesystem-topology.md) | Editing any file under `~/.claude/` | `~/.claude/CLAUDE.md`/hooks/skills are symlinks into `~/.claude-shared-config` (resolve before Edit/Write); `library/` and `plugins/local-marketplace/` are real, untracked directories |
| [long-running-process-pattern.md](context/long-running-process-pattern.md) | Running multi-hour jobs from Claude Code | Nohup launcher scripts, tool timeout limits |
| [tools-catalog.md](context/tools-catalog.md) | Creating PRDs, tickets, contracts, changelogs, ADRs | Which tool produces which artifact |
| [swarm-diagnostics.md](context/swarm-diagnostics.md) | Complex multi-service debugging | Parallel investigation, blocker triage |
| [ALIASES.md](ALIASES.md) | **Retrieval index (SILVER).** Every file in `context/` has a row. `bibliotheque-recall.sh` matches your prompt against it and injects the pointer automatically. Replaced the On-Demand Context table that used to sit in CLAUDE.md. | Add a row when you add a context file |
| [deploy-identity-gate.md](context/deploy-identity-gate.md) | Any claim about DEPLOYED code | Probe the deploy branch, stamp the citation, falsify on pushback |
| [autonomous-crawl-rules.md](context/autonomous-crawl-rules.md) | Starting an unattended crawl or ralph-loop | Proven-code rule, mid-crawl ADRs, WIP hygiene |
| [protected-module-change-isolation.md](context/protected-module-change-isolation.md) | Writing or reviewing a "never touch module X" guardrail | A blanket prohibition expires when reuse turns symmetric; a diff-shape rule blocks the good case; fence by packaging (one MR, reviewed alone, counted) plus one narrow no-internal-refactors rule |
| [data-mutation-safety.md](context/data-mutation-safety.md) | Scripts that mutate datastore or DB records | Backup procedure, Datastore upsert drops fields |
| [worktree-fleet-ops.md](context/worktree-fleet-ops.md) | Creating a worktree from a project-management cwd; `could not lock config file ~/.gitconfig` in parallel fleets | Target code repo explicitly (`git -C`); gitconfig lock = transient contention, retry |
| [browser-automation-sops.md](context/browser-automation-sops.md) | Uploading files to Google Drive via claude-in-chrome; transient 529 on `find` | New>File-upload injects the input, `file_upload` against ref, zip-multi-folder-first; 529 = retry then screenshot+click |
| [session-lifecycle-skills.md](context/session-lifecycle-skills.md) | Session management, handoffs, pickup, session-check, intent tracking | Five skills, one ledger: /session-initialize, /handoff, /pickup, /report-back, /session-check |
| [harness-architecture-textbook.md](context/harness-architecture-textbook.md) | "Harness architecture", "how does my harness work", subsystem/hook-lifecycle diagrams, deploy-identity | Didactic textbook of the whole harness + deploy-identity subsystem deconstructed; reusable mermaid diagrams D1–D9; self-documents weaknesses, constraints, trade-offs |
| [hermes-agent-platform-mechanics.md](context/hermes-agent-platform-mechanics.md) | Standing up / operating a Nous hermes-agent (profiles, gateway, cron, kanban bus, model/GBrain, heartbeat & ingestion patterns) | Hermes profile↔gateway↔cron mechanics, no-MCP kanban coordination, LiteLLM→Vertex bridge, keep-alive heartbeat + ingest-flat-embed-later patterns; node-binary gotcha |
| [claude-code-session-crash-forensics.md](context/claude-code-session-crash-forensics.md) | Building crash-recovery tooling on Claude Code session transcripts, detecting a crash from session history | Transcript mtime clustering as a crash signal; filter to `entrypoint == "cli"`; resolve by session ID, not by time window, once a session has been touched |
| [llm-tool-design-safety-patterns.md](context/llm-tool-design-safety-patterns.md) | Designing a CLI or tool an LLM will drive on a human's behalf, especially one with a side-effecting action | Split read-only discovery from the one side-effecting action; never collapse multiple real candidates into "the one" |
| [python-http-client-egress-gotchas.md](context/python-http-client-egress-gotchas.md) | Claiming a request cannot leave the machine; loopback/localhost security checks | `httpx` trusts `HTTP_PROXY` unless `trust_env=False`, so a "local only" claim is false by default; `localhost` is a name an `/etc/hosts` entry can move — resolve and check every address, fail closed, and unify the predicate across checks |
| [mcp-server-scoping-and-isolation.md](context/mcp-server-scoping-and-isolation.md) | Scoping an MCP server to one project, isolating a heavy MCP server to a headless batch process | Local-scope registration loads everywhere despite `.mcp.json`; `--strict-mcp-config` is the real isolation mechanism; per-directory trust approval is separate from OAuth; `!`-prefix shell cannot launch interactive `claude` |

### Personal Tooling & Automation

| File | Trigger | Description |
|------|---------|-------------|
| [macos-terminal-automation-gotchas.md](context/macos-terminal-automation-gotchas.md) | Driving Ghostty (or another single-instance macOS terminal app) via `open` or AppleScript keystroke injection | Ghostty single-instance behavior, keystroke drop on long strings, `activate`-frontmost race condition, Accessibility permission target |
| [macos-disk-reclaim-measurement-traps.md](context/macos-disk-reclaim-measurement-traps.md) | Running `/disk-management` or any macOS disk-space cleanup, sizing deletion candidates for `AskUserQuestion` | `df -h /` hides real usage on APFS (read `/System/Volumes/Data`), `brew cleanup --prune=all` vs plain cleanup, size the exact deletion target not its parent, `vm_bundles`/`stremio-cache` live outside `Caches/`, `Caches/` vs `Application Support/` for browser data |
| [zsh-dotfiles-double-sourcing-gotcha.md](context/zsh-dotfiles-double-sourcing-gotcha.md) | Intermittent `command not found: brew` in `.zshrc`, diagnosing zsh startup order issues | `.zshenv` sourcing `.zshrc` directly runs it twice, once before `.zprofile` sets up PATH |

### Jira & Ticketing

| File | Trigger | Description |
|------|---------|-------------|
| [jira-skill-gotchas.md](context/jira-skill-gotchas.md) | Running `jira_skill.py` | Org slugs, subcommand names, ADF format, comment rules, deadline mode |
| [ticket-quality-standards.md](context/ticket-quality-standards.md) | Creating tickets, writing AC, reviewing quality | AC writing, closure protocols, bug fix standards |
| [stakeholder-response-pattern.md](context/stakeholder-response-pattern.md) | Stakeholder asks about feature business logic | Check Jira first, post via `/post-comment` |

### Security & Access

| File | Trigger | Description |
|------|---------|-------------|
| [security-audit-claude-code-config.md](context/security-audit-claude-code-config.md) | Security hardening, credential rotation | Priority fixes, permission audit findings |
| [klever-infra-access.md](context/klever-infra-access.md) | Granting GCP/GitLab access to Klever user | Cloud Identity group model, Marc-André gate |
| [klever-api-credentials.md](context/klever-api-credentials.md) | Using Placer API, adding new API integrations | Auth patterns, key storage. NO actual key values |
| [pr-panic-protocol.md](context/pr-panic-protocol.md) | User expresses alarm about a PR | 3-lookup rule, branch-names-lie, invariant flagging |

### Service-Specific References

| File | Trigger | Description |
|------|---------|-------------|
| [eqs-graphql-reference.md](context/eqs-graphql-reference.md) | Querying EQS GraphQL | Field names, filter syntax, comparators |
| [apollo-gateway-architecture.md](context/apollo-gateway-architecture.md) | Apollo Router managed federation | Subgraph URLs, DNS TXT env vars |
| [cloud-run-iam-diagnosis.md](context/cloud-run-iam-diagnosis.md) | Cloud Run 403/401 diagnosis | IAM vs app auth, audit logs, smoke tests |
| [retell-api-v2-reference.md](context/retell-api-v2-reference.md) | Calling Retell AI API | Pagination, broken filters, response format |

---

## inbox/ — Unindexed Nuggets Pending Promotion

| File | Contents |
|------|----------|
| [2026-04-17-leo-ac-scaffolding-session.md](inbox/2026-04-17-leo-ac-scaffolding-session.md) | Jira mention format, scope-clarification template fix, Amal question scope, CONVERSION_NAME domain knowledge |
| [2026-04-21-debugging-persona-research-prompt.md](inbox/2026-04-21-debugging-persona-research-prompt.md) | Gemini Deep Research prompt for BMAD debugging persona + BMAD anatomy reference for build phase |
| [2026-04-21-dexter-persona-deep-research.md](inbox/2026-04-21-dexter-persona-deep-research.md) | Full Gemini research results: methodologies, cognitive biases, activation steps, voice design, anti-patterns |

---

## Quick Answers

| Question | Where to look |
|----------|---------------|
| How do I ship a Supervisr service? | [shipping-workflow.md](context/shipping-workflow.md) |
| How do I post a Jira comment from a script? | [jira-skill-gotchas.md](context/jira-skill-gotchas.md) (ADF format, org slugs) |
| What Java testing standards apply? | [java-standards.md](context/java-standards.md) |
| How do I grant someone GCP access at Klever? | [klever-infra-access.md](context/klever-infra-access.md) |
| Where does domain knowledge for Klever live? | Klever Bibliothèque (see Org-Level pointer above) |
| Where does domain knowledge for Supervisr live? | Supervisr Bibliothèque (see Org-Level pointer above) |

---

## Meta

| | |
|---|---|
| **Scope** | Cross-org tools, workflows, standards |
| **Philosophy** | Progressive disclosure: this INDEX → file read on trigger |
| **Update cadence** | Nuggets land in `inbox/`, promote on review |

---

## Sections carried from the versioned library

Present only in the versioned copy before the 2026-08-27 merge.

- `architecture/` — 10 page(s)
- `archive/` — 32 page(s)
- `context/` — 3 page(s)
- `inbox/` — 1 page(s)
- `operations/` — 10 page(s)
- `practices/` — 29 page(s)
- `process/` — 4 page(s)
- `research/` — 12 page(s)
- `LOG.md`
- `SCHEMA.md`
- `WIKI_REGISTRY.yaml`

A `-legacy` suffix marks a page whose filename collided with a different document during the merge. Both were kept; they need curation, not deletion.
