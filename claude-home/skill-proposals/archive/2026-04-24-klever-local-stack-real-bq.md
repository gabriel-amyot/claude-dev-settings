# Skill Proposal: klever-local-stack-real-bq
Date: 2026-04-24
Source: KTP-130 test hardening session

## Trigger
"start local stack with real data", "test against dev BQ", "full local e2e"

## Scope
org (Klever)

## Problem
The existing `klever-local-stack` skill starts services but doesn't handle:
- 1Password CLI key fetch + caching
- BQ project/dataset overrides for real data
- Docker MySQL with `--lower-case-table-names=1`
- Liquibase component 9 pre-insert workaround
- UM seed data ID mismatch awareness

## Draft Steps
1. Check Docker running, start MySQL with correct flags
2. Pre-insert component 9 if fresh DB
3. Start UM with `--spring.liquibase.contexts=local`
4. Fetch Placer key from 1Password (cache to /tmp)
5. Start proximity-report with BQ project override + Placer key
6. Start frontend
7. Health check all services
8. Report: which advertiser IDs match BQ (warn about seed data mismatches)
