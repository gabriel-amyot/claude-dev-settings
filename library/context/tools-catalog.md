# Tools Catalog — Document Types and Creation Tools

On-demand context: load when creating PRDs, tickets, contracts, changelogs, or ADRs.

## Document Type → Skill/Tool Mapping

| Document Type | Skill/Command | Output Location |
|---|---|---|
| PRD | `/create-prd` | `tickets/{TICKET-ID}/reports/architecture/` |
| Jira tickets (epics, stories) | `/create-tickets` | Jira (remote) + local `tickets/{ID}/` |
| ADR | `/push-adr` | `{repo}/agent-os/architecture/adr/` (repo-specific) or `documentation/architecture/adr/` (cross-cutting) |
| Story quality review | `/story-quality-gate` agent | `tickets/{TICKET-ID}/reports/reviews/` |
| Adversarial review | `/adversarial-review` | `tickets/{TICKET-ID}/reports/reviews/` |
| Implementation estimate | `/estimate` | `tickets/{TICKET-ID}/reports/architecture/` |
| Task breakdown | `/generate-tasks` | `tickets/{TICKET-ID}/` |
| STATUS_SNAPSHOT.yaml | `/status-index` | `tickets/{TICKET-ID}/STATUS_SNAPSHOT.yaml` |
| Sprint close evidence | `/sprint-close` | `tickets/{EPIC}/reports/status/` |
| Ticket scaffold | `/ticket-init` | `tickets/{TICKET-ID}/` (README, STATUS_SNAPSHOT, reports/) |
| INDEX.md | `/index-context` | Nearest directory |
| Bibliotheque refresh | `/bibliotheque-refresh` | `documentation/bibliotheque/` |

## Navigator

| Need | Skill | What It Does |
|---|---|---|
| Don't know which skill to use | `/floor-manager` | Recommends the right tool based on intent and context. 7 bays, 3-layer catalog. |
| BMAD workflow guidance | `/bmad-help` | Step-by-step BMAD workflow navigator (53-row CSV catalog). |
| Harness health check | `/harness-audit` | Adversarial audit of skills, agents, hooks, proposals. Detects drift. |

## When to Create ADRs

| Create ADR | Don't Create ADR |
|---|---|
| Chose between architectural patterns | Implementation details |
| Selected core technology | Tactical code choices |
| Changed fundamental data model | Bug fixes |
| Security/compliance decision | Minor refactoring |

## When to Update Contracts

| Update | Don't Update |
|---|---|
| API endpoints added/modified/removed | Internal implementation changes |
| Data entity fields change | Changes not affecting interfaces |
| Frontend-backend interface shifts | |

## Contract files location
`documentation/architecture/contracts/`

## Promotion Rules
Before closing any ticket: promote ADRs to `documentation/architecture/adr/`, update global `DECISIONS_LOG.md`, verify docs reflect implemented state.
