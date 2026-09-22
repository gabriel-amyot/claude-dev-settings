# Skill Proposal: dataform-trigger-monitor
Date: 2026-05-27
Source: KTP-680 Dark Factory session — manual Dataform trigger + monitoring

## Trigger
When deploying Dataform pipeline changes: after merge to dev, need to compile, trigger by tag, and validate execution succeeded. Also useful for manual re-runs (e.g., proximity full refresh).

## Scope
org (Klever only, Dataform Cloud is Klever-specific infra)

## Draft Steps
1. Compile from specified branch (default: dev) via Dataform API
2. Verify compilation has 0 errors
3. Trigger workflow invocation with specified tag (default: all) and optional full refresh flag
4. Poll invocation status until SUCCEEDED/FAILED (15s interval, 5min timeout)
5. If SUCCEEDED: run phase 2 validation if `tests/changes/{ticket}/` exists
6. If FAILED: print failure reason and suggest rollback steps
