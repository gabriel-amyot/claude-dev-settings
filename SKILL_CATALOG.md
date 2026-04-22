# Skill & Agent Catalog

Quick reference for what to use when. Organized by intent.

---

## I want to review code

| Intent | Tool | Type |
|--------|------|------|
| Review my own PR/MR before shipping | `/pr-review` | skill (wraps pr-review-toolkit) |
| Deep multi-agent review (standalone) | `/pr-review-toolkit:review-pr` | plugin |
| Review teammates' GitHub PRs | `colleague-review` | agent |
| Quick standards check mid-dev (Supervisr) | `/supervisr-review` | skill |
| Challenge test validity | `/test-adversarial` | skill |
| Challenge ideas/work/design decisions | `/challenge` | skill |

## I want to ship

| Intent | Tool | Type |
|--------|------|------|
| Full pipeline (validate → review → release → deploy → Jira) | `supervisr-ship` | agent |
| Just validate (compile, tests, AC) | `/supervisr-validate` | skill |
| Just tag + build + schema publish | `/supervisr-release` | skill |
| Pre-ship readiness across all services in epic | `/pre-ship-check` | skill |

## I want to check ticket quality

| Intent | Tool | Type |
|--------|------|------|
| AC health check (is this ticket ready?) | `ticket-scan` | agent |
| Full quality cascade (Leo → Winston → Amelia) | `story-quality-gate` | agent |
| Close sprint tickets with evidence | `/sprint-close` | skill |
| Aggregate test gaps from closed tickets | `/spillover-scan` | skill |

## I want to test

| Intent | Tool | Type |
|--------|------|------|
| Run local harness manually | `/test-harness` | skill |
| Autonomous local testing loop (Docker) | `night-crawl` via `/ralph-loop` | agent |
| Autonomous cloud testing loop (GCP dev) | `dev-crawl` via `/ralph-loop` | agent |
| Challenge test validity (false positives) | `/test-adversarial` | skill |

## I want to go autonomous

| Intent | Tool | Type |
|--------|------|------|
| Full ticket lifecycle (intake → ship) | `supervisr-autopilot` | agent |
| Local test + fix loop | `night-crawl` via `/ralph-loop` | agent |
| Cloud deploy + fix loop | `dev-crawl` via `/ralph-loop` | agent |
| Iteration wrapper for any agent | `/ralph-loop` | plugin |
| Pre-flight before autonomous run | `/pre-flight` | skill |
| Validate ralph-loop setup | `/ralph-loop-preflight` | skill |

## I want to communicate

| Intent | Tool | Type |
|--------|------|------|
| Search Slack, reply, check unread | `/slack` | skill |
| Post to PR/Jira/Slack (safe pipeline) | `/post-comment` | skill |
| Watch PR channel for new PRs | `/slack-pr-listener` | skill |
| Post PR comments with BMAD debate | `/agent-debate-review` | skill |

## I want to manage tickets

| Intent | Tool | Type |
|--------|------|------|
| Query/create/transition Jira tickets | `/jira` | skill |
| Create batch of tickets (epic + stories) | `/create-tickets` | skill |
| Scaffold ticket folder locally | `/ticket-init` | skill |
| Pick up a ticket (fetch context + clarity gate) | `pickup-ticket` | agent |
| Generate STATUS_SNAPSHOT.yaml | `/status-index` | skill |
| Archive completed ticket | `/archive` | skill |

## I want to manage docs

| Intent | Tool | Type |
|--------|------|------|
| Index a folder (generate INDEX.md) | `/index-context` | skill |
| Full doc coherence audit | `/agent-os:audit-docs` | skill |
| Check DAC repo CLAUDE.md coverage | `/mb-doc-housekeeping` | skill |
| Push an architectural decision (ADR) | `/push-adr` | skill |
| Refresh Bibliothèque from Notion | `/bibliotheque-refresh` | skill |
| Search across all knowledge layers | `/tribal-knowledge` | skill |

## I want to manage infrastructure

| Intent | Tool | Type |
|--------|------|------|
| Query GCP (logs, Datastore, Cloud Run) | `/gcloud` | skill |
| Access GitLab repos (Klever, Origin8 infra) | `/gitlab` | skill |
| Deactivate/reactivate Origin8 services | `/supervisr-service-manager` | skill |
| Reset dev environment data | `/dev-reset` | skill |
| Validate repo links | `/validate-repo-links` | skill |

## I want to plan / brainstorm

| Intent | Tool | Type |
|--------|------|------|
| BMAD party (interactive, you participate) | `bmad-party` | agent |
| BMAD party (autonomous, no interaction) | `bmad-party-autopilot` | agent |
| Post-mortem / debrief | `/bmad-debrief` | skill |
| PR response sweep (batch reply to reviews) | `pr-response-sweep` | agent |
| Research-driven PR response | `review-responder` | agent |

## Workflow modes

| Intent | Tool | Type |
|--------|------|------|
| Switch to Lean workflow | `/lean` | command |
| Switch to TDD workflow | `/tdd` | command |
| Morning brief from transcript | `/morning-brief` | skill |
| Extract tribal knowledge into skills | `/gab-operationalize` | skill |
| Estimate ticket implementation | `/estimate` | command |

## Peon Ping (fitness)

| Intent | Tool | Type |
|--------|------|------|
| Log exercise reps | `/peon-ping-log` | skill |
| Toggle sounds on/off | `/peon-ping-toggle` | skill |
| Change voice pack | `/peon-ping-use` | skill |
| Change config (volume, rotation) | `/peon-ping-config` | skill |

---

## Platform Routing Rules

| Org | Code Repos | Infra/IaC | CI/CD | Tickets |
|-----|-----------|-----------|-------|---------|
| Supervisr.AI | GitHub | GitLab (DAC/IAC) | GitLab CI (on tag push) | Jira (SPV-*) |
| Klever | GitLab | GitLab (DAC/IAC) | GitLab CI | Jira (KTP-*, INS-*) |
| Origin8 | GitHub (legacy) | GitLab (DAC/IAC) | GitLab CI | Jira (legacy) |

**Rule:** Never use GitHub for Klever infra. Never use GitLab for Supervisr app repos.

---

## Natural Language Quick Reference

| You say... | Tool triggered |
|------------|---------------|
| "ship it" / "let's release" / "ready to ship" | supervisr-ship agent |
| "review my PR" / "check my changes" / "before I push" | /pr-review |
| "check this ticket" / "is this ready?" / "review the AC" | ticket-scan agent |
| "pick up KTP-xxx" / "start working on" / "continue on" | pickup-ticket agent |
| "wrap up the sprint" / "close tickets" | /sprint-close |
| "what should I work on" / "what's on my plate" | /jira |
| "check what's failing" / "any errors in dev" | /gcloud |
| "challenge this" / "devil's advocate" / "stress test my idea" | /challenge |
| "go autonomous" / "work overnight" / "night crawl" | night-crawl via /ralph-loop |
| "search slack for" / "check my DMs" | /slack |
| "post a comment on" / "reply to the PR" | /post-comment |
| "index this folder" / "update the docs" | /index-context |
| "scaffold this ticket" / "init ticket folder" | /ticket-init |
| "archive this ticket" / "clean up completed work" | /archive |
