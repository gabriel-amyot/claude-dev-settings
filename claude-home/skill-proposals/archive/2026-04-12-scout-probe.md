# Skill Proposal: scout-probe
Status: BUILT (2026-04-21 — functional test: PARTIAL)
Date: 2026-04-12
Source: SPV-92 reconciliation debugging session

## Trigger
When a mutation/API claims "success" but observable state doesn't change. When debugging pipeline operations that touch multiple services (LLS, ERS, EQS, retell-service). When you need a controlled experiment against a live environment.

## Scope
org (Supervisr) — reusable across any service pipeline

## Draft Steps
1. **Extract** one real record from the source system (Retell, ERS, etc.)
2. **Create** one entity in the target system with matching identifiers (phone, UUID, etc.)
3. **Verify baseline** state via read path (EQS, LLS direct, etc.)
4. **Execute** the operation under test for that single record
5. **Compare** before/after state, emit PASS/FAIL verdict with full evidence

## Key Design Decisions
- Always use real data from the source (not synthetic), so the operation processes it identically to production
- Query through the same read path the UI/consumers use (EQS via Gateway, not Datastore direct)
- Account for materialization delays (EQS poll-retry)
- Script should be self-contained: one file, sources auth-helper.sh, prints verdict
- Leave scout entity in place (one record is harmless, deletion adds complexity)

## Existing Implementation
`tickets/SPV-92/tools/scout-reconciliation-probe.py` is the first instance. Generalize the pattern.
