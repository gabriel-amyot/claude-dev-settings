# When NOT to Use Autonomous Ticket Ship

This skill is for **additive, reversible** work shipped as a surprise MR. If any condition below applies, STOP and tell the user why this mode is inappropriate.

## Hard Blockers (never proceed)

### Destructive Changes
- Database migrations that drop columns, tables, or alter constraints destructively
- Data deletes, bulk updates, or schema alterations that cannot be undone with a revert commit
- Removing existing endpoints, contracts, or public interfaces

### IAM / Auth / Security on Shared Environments
- Any change to `allUsers`, `permitAll()`, `iam_public_access`, invoker bindings
- OAuth security filter modifications, M2M scope changes
- Auth0 tenant configuration changes
- Adding or removing permission checks on shared environments (Dev, UAT, Prod)
- Exception: R&D-BAC1 (isolated, tear-down-after) is exempt

### Data Mutations Without Backup
- Any script that writes, updates, or deletes datastore/database entities must first backup affected records to `tickets/{TICKET-ID}/data/backups/` with a timestamped filename
- If you cannot back up (no read access), stop and ask the user
- This mode does not support data mutation scripts. Use interactive mode with explicit user oversight.

### Pipeline / CI-CD Changes
- Never modify `.gitlab-ci.yml` on a feature branch without checking `git diff origin/dev -- .gitlab-ci.yml` (feature branches overwrite dev's CI config on merge)
- Never change CI/CD variables on prod or UAT
- Never run terraform plan/apply
- Never trigger more than 5 pipelines for the same commit in a single session

### Infrastructure Changes
- Cloud Run service configuration (env vars, scaling, IAM bindings)
- Secret Manager provisioning
- Terraform state modifications
- DNS, load balancer, or networking changes

## Soft Blockers (redirect to a better tool)

### Tickets Without Clear AC
If the ticket lacks concrete acceptance criteria (Given/When/Then or equivalent observable outcomes), this mode cannot scaffold `ac-tracking.yaml`. Redirect to `/leo-ac-scaffold` first, then return.

### Open-Ended Research or Spikes
This mode requires scoped ACs to commit against. For investigation work, use `/sprint-crawl` or run a research session.

### User Wants Progress Updates, Not a Polished MR
If the user wants visibility into incremental progress (e.g., "work on this and keep me posted"), use `/sprint-crawl` or `/ralph-loop` instead. This skill is specifically for the "disappear, ship, hand off a polished MR" pattern.

### Multi-Sprint Epics
This skill handles a single ticket with bounded ACs. For multi-ticket execution across an epic, orchestrate multiple invocations or use `/sprint-crawl` per ticket.

## Source

Derived from:
- `CLAUDE.md` Shipping Safeguards section
- `CLAUDE.md` IAM/Auth changes require human gate (EQS permit-all incident 2026-03-16)
- `CLAUDE.md` Every data mutation script must backup (SPV-141 data loss incident 2026-04-13)
- `CLAUDE.md` Pipeline retry circuit breaker (SPV-165 nightcrawl 2026-04-21)
- `CLAUDE.md` Feature branches that modify .gitlab-ci.yml (Klever development workflow)
- SOP `autonomous-ticket-ship.md` "When NOT to Use" section
