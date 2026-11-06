# Context Files — Fallback Index

Retrieval normally happens automatically: `bibliotheque-recall.sh` matches your prompt
against `../ALIASES.md` and injects the pointer. This list is the fallback for when
nothing surfaces and you need to browse.

Generated from `../ALIASES.md`. Every file has a row.

| file | when to load |
|---|---|
| `INDEX.md` | Understanding domain terms, system capabilities, service catalog |
| `apollo-gateway-architecture.md` | Apollo Gateway routing, subgraph URLs, managed federation |
| `autonomous-crawl-rules.md` | Starting a night-crawl, dev-crawl, sprint-crawl, or ralph-loop |
| `browser-automation-sops.md` | Uploading files to Google Drive via claude-in-chrome, transient 529 on browser tools |
| `claude-code-session-crash-forensics.md` | claude code crashed, recover a lost session, transcript mtime, resume after crash |
| `claude-md-authoring.md` | Editing any CLAUDE.md file (auto-injected by hook) |
| `cloud-run-iam-diagnosis.md` | Cloud Run 403/401 diagnosis, IAM audit logs, smoke tests |
| `context-engineering.md` | Long-running agents, compaction, context limits, agent drift |
| `data-mutation-safety.md` | Writing a script that mutates datastore or database records |
| `deploy-identity-gate.md` | Any claim about DEPLOYED code, which branch deploys, code-owner pushback, **writing an RCA / diagnosis / verdict doc** |
| `documentation-standards-quick-ref.md` | Writing/reviewing ADRs, placing docs, migrating agent-os/, doc standards |
| `eqs-graphql-reference.md` | Querying EQS GraphQL (field names, filter syntax, comparators) |
| `git-history-verification.md` | Writing PR bodies, asserting code history ("X was deleted", "X never existed"), reviewing agent-written PR descriptions |
| `harness-architecture-textbook.md` | how the harness is wired, harness subsystems, onboarding to the harness design |
| `harness-self-management.md` | Improving the harness, transcript mining, auto cost monitoring, batch API for crawls |
| `hermes-agent-platform-mechanics.md` | hermes agent runtime, nous hermes, gravel first-responder, local agent install |
| `java-standards.md` | Writing/reviewing Java code |
| `jira-skill-gotchas.md` | Running `jira_skill.py` (subcommands, org slugs, comment rules, deadline mode) |
| `klever-api-credentials.md` | which klever api key, credential names, where a vendor key lives |
| `klever-infra-access.md` | Granting GCP or GitLab access to a new Klever user |
| `llm-tool-design-safety-patterns.md` | designing a side-effecting CLI an agent will drive, tool safety patterns, destructive tool guard |
| `long-running-process-pattern.md` | Running multi-hour jobs, nohup patterns, tool timeout limits |
| `macos-terminal-automation-gotchas.md` | applescript keystroke injection, driving ghostty or terminal from a script, macos open command |
| `mcp-server-scoping-and-isolation.md` | mcp server scope, project vs user mcp, isolating an mcp server |
| `nextjs-cloudflare-static-export.md` | Next.js static export on Cloudflare Pages, build artifact 404s in prod ("works locally not in prod"), `npx next build` skips npm prebuild hooks, diagnosing CF Pages deploys |
| `pr-panic-protocol.md` | User expresses alarm/PTSD about a PR, contamination, security, data loss |
| `python-http-client-egress-gotchas.md` | request cannot leave the machine, python http egress, offline claim, requests urllib proxy |
| `react-force-graph-gotchas.md` | Using react-force-graph-2d, ResizeObserver + canvas loops, wikilink parsing |
| `retell-api-v2-reference.md` | Calling Retell AI API (pagination, filters, response format) |
| `schema-validation-gate.md` | wiring a bigquery adapter, verify bq schema, column names and nullability before coding |
| `security-audit-claude-code-config.md` | Security hardening, credential rotation, permission audit |
| `session-lifecycle-skills.md` | Session management, handoffs, pickup, intent tracking, cross-session continuity |
| `shipping-workflow.md` | Tagging, shipping, deploying, merge requests, CI/CD, PR reviews |
| `stakeholder-response-pattern.md` | stakeholder asked about a feature, answering a spec question, david or amal question |
| `swarm-diagnostics.md` | Complex multi-service debugging, parallel investigation, blocker triage |
| `ticket-quality-standards.md` | Creating tickets, writing AC, defining stories, reviewing ticket quality |
| `tools-catalog.md` | Creating PRDs, tickets, contracts, changelogs, ADRs |
| `vendor-api-contract-validation.md` | Writing/reviewing vendor API parsing code, spike completion for vendor endpoints, debugging all-null vendor metrics, onboarding new vendor API |
| `workspace-map.yaml` | Navigating orgs/projects, starting tickets |
| `worktree-fleet-ops.md` | Creating a worktree from a project-management cwd, `could not lock config file ~/.gitconfig` in parallel fleets |
| `zsh-dotfiles-double-sourcing-gotcha.md` | shell startup errors, zshenv sourcing zshrc, dotfiles run twice, intermittent terminal error |
| `mechanical-backstops.md` | which hook enforces which rule, hook coverage and gaps |
