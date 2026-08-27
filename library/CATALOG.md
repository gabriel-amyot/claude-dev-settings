# Bibliothèque Catalog — User Level

Last updated: 2026-08-03

Entry point: [INDEX.md](INDEX.md)

## Org-Level Bibliothèques

| Org | Path | Glossary | Sections |
|-----|------|----------|----------|
| Klever | `~/Developer/grp-beklever-com/project-management/documentation/bibliotheque/` | 107 terms | domain, vendors, product, stack, operations, people, maps-proximity, sops, development |
| Supervisr.AI | `~/Developer/supervisr-ai/project-management/documentation/bibliotheque/` | Yes | domain, vendors, product, stack, operations, people |

## context/ — On-demand context files for agent sessions

| File | Purpose | Load Trigger |
|------|---------|-------------|
| shipping-workflow.md | Tag, build, deploy, MR workflow | Tagging, shipping, deploying, merge requests, CI/CD |
| java-standards.md | Mockito, testing, enforcement standards | Writing or reviewing Java code |
| context-engineering.md | Compaction, note-taking, subagent architecture | Long-running agents, compaction, context limits |
| claude-md-authoring.md | DRY principle, satellite files, section ownership | Editing any CLAUDE.md file |
| tools-catalog.md | Which tool produces which artifact | Creating PRDs, tickets, contracts, changelogs, ADRs |
| swarm-diagnostics.md | Multi-service debugging, parallel investigation | Complex multi-service debugging, blocker triage |
| stakeholder-response-pattern.md | Check Jira, post via `/post-comment` | Stakeholder asks about feature business logic |
| schema-validation-gate.md | Verify BQ schema before coding | Before wiring any BQ adapter |
| ticket-quality-standards.md | AC writing, closure protocols, bug fix standards | Creating tickets, writing AC, reviewing quality |
| security-audit-claude-code-config.md | Priority fixes, permission audit findings | Security hardening, credential rotation |
| pr-panic-protocol.md | 3-lookup rule, invariant flagging | User expresses alarm about PR contamination/security/data loss |
| jira-skill-gotchas.md | Org slugs, subcommands, ADF format, header rule | Running `jira_skill.py` |
| retell-api-v2-reference.md | Pagination, broken filters, response format | Calling Retell AI API |
| eqs-graphql-reference.md | Field names, filter syntax, comparators | Querying EQS GraphQL |
| cloud-run-iam-diagnosis.md | IAM vs app auth, audit logs, smoke tests | Cloud Run 403/401 diagnosis |
| apollo-gateway-architecture.md | Subgraph URLs, DNS TXT env vars | Apollo Router managed federation |
| long-running-process-pattern.md | Nohup launcher, tool timeout limits | Running multi-hour jobs |
| python-http-client-egress-gotchas.md | `httpx` `trust_env`, loopback resolution | Claiming a request stays local; writing a localhost security check |
| harness-self-management.md | Cost config, transcript mining, batch API, local-plugin cache-sync gotcha | Improving the harness |
| harness-architecture-textbook.md | Whole-harness map + deploy-identity subsystem deconstructed; reusable mermaid diagrams D1–D9; weaknesses/constraints/trade-offs self-documented | "How does my harness work", subsystem/hook-lifecycle diagrams, deploy-identity, harness onboarding |
| vendor-api-contract-validation.md | 5-gate defense for vendor API parsing (anti-hallucination) | Writing vendor API parsing, spike completion, debugging all-null vendor metrics |
| klever-infra-access.md | Cloud Identity group model, Marc-André gate | Granting GCP/GitLab access at Klever |
| klever-api-credentials.md | Auth patterns, key storage (no values) | Using Placer API, adding API integrations |
| documentation-standards-quick-ref.md | Three-layer doc model, ADR placement, migration checklist | Writing/reviewing ADRs, placing docs |
| nextjs-cloudflare-static-export.md | CF Pages `npx next build` skips npm prebuild hooks; generate artifacts from next.config; verify with prod build command; CF API deploy diagnosis | Next.js static export on Cloudflare Pages, "works locally not in prod" build artifacts, missing search-index/sitemap |
| workspace-map.yaml | Org roots, repo paths, harness locations | Navigating orgs/projects, starting tickets |
| worktree-fleet-ops.md | Worktree from a PM cwd (target code repo with `git -C`); `~/.gitconfig` lock contention in parallel fleets (retry, deferred structural fix) | Creating worktrees from project-management, gitconfig lock errors in fleets |
| browser-automation-sops.md | Google Drive upload recipe (New>File-upload injection, `file_upload` against ref, zip-multi-folder-first); transient 529 fallback | Uploading to Drive via claude-in-chrome, transient 529 on browser tools |
| claude-code-session-crash-forensics.md | Transcript mtime clustering as a crash signal; filter to `entrypoint == "cli"`; resolve by session ID once touched | Building crash-recovery tooling on Claude Code session transcripts |
| llm-tool-design-safety-patterns.md | Split read-only discovery from the one side-effecting action; never collapse multiple candidates into "the one" | Designing an LLM-driven CLI/tool with a side-effecting action |
| macos-terminal-automation-gotchas.md | Ghostty single-instance behavior, keystroke drop on long strings, `activate`-frontmost race, Accessibility permission target | Driving Ghostty or another single-instance macOS terminal app via `open`/AppleScript |
| zsh-dotfiles-double-sourcing-gotcha.md | `.zshenv` sourcing `.zshrc` directly runs it twice, once before `.zprofile` sets up PATH | Intermittent `command not found: brew` in `.zshrc`, zsh startup order issues |
| mcp-server-scoping-and-isolation.md | Local-scope MCP registration loads everywhere; `--strict-mcp-config` for true isolation; per-directory trust approval separate from OAuth; `!`-prefix shell cannot launch interactive `claude` | Scoping an MCP server to one project, isolating a heavy MCP server to a headless batch process |

## inbox/ — Unindexed nuggets pending promotion

| File | Contents | Promote to |
|------|----------|------------|
| 2026-04-17-leo-ac-scaffolding-session.md | Jira mention format, scope-clarification template fix, Amal question scope, CONVERSION_NAME domain knowledge | jira-skill-gotchas.md, project-management CLAUDE.md, Klever bibliothèque |
| 2026-04-21-debugging-persona-research-prompt.md | Gemini Deep Research prompt for BMAD debugging persona, BMAD persona anatomy analysis | New BMAD persona file + skill-proposals/2026-04-21-debugging-agent.md |

---

## Topic Cross-Reference

- **Harness architecture / hooks / subsystems:** `harness-architecture-textbook.md` (whole-harness map D1, deploy-identity deconstructed, weaknesses + fixes), `harness-self-management.md` (cost/self-management), `claude-md-authoring.md` (CLAUDE.md cascade)
- **Deploy-identity / which-branch-deploys / wrong-branch claims:** `harness-architecture-textbook.md` (Ch 3) + KTP-688 ticket artifacts (`tickets/KTP/KTP-374/KTP-688/reports/`)
- **PR review / adversarial review:** `pr-panic-protocol.md` (panic flow), `ticket-quality-standards.md` (closure protocols)
- **Jira workflows:** `jira-skill-gotchas.md` (skill usage), project-level memory entries (sprint moves, closing comments, transitions, deadline mode)
- **Harness cost + self-management:** `harness-self-management.md` (ideas A/B/C), skill proposals in `~/.claude/skill-proposals/`
- **Vendor API contract integrity:** `vendor-api-contract-validation.md` (5-gate defense), Klever incident detail at `~/Developer/grp-beklever-com/project-management/tickets/KTP/KTP-559/KTP-669/reports/architecture/winston-harness-recommendations-2026-05-19.md`
- **Dark Factory pipeline:** Klever Bibliothèque → `development/dark-factory/` (lessons, ADRs, specs). Skill: `~/.claude/skills/dark-factory/SKILL.md`
- **Klever domain:** Klever Bibliothèque → ad-tech, DSPs, BQ schemas, products, people
- **Supervisr domain:** Supervisr Bibliothèque → lead lifecycle, EQS, compliance, dreampipe
- **Personal tooling / macOS automation:** `macos-terminal-automation-gotchas.md` (Ghostty, AppleScript keystroke injection), `zsh-dotfiles-double-sourcing-gotcha.md` (zsh startup order)
- **LLM tool/agent design patterns:** `llm-tool-design-safety-patterns.md` (discovery vs. side-effecting action, candidate listing), `claude-code-session-crash-forensics.md` (transcript-mtime crash detection)
- **MCP server configuration:** `mcp-server-scoping-and-isolation.md` (local-scope leak, `--strict-mcp-config`, per-directory trust approval)
