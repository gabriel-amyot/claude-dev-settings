# Skill Proposal: post-deploy-smoke
Date: 2026-05-20
Source: KTP-669 Winston harness recommendations (Rec 2)

## Trigger
After merge to dev on a Klever backend repo, or when user says "smoke test dev", "verify deploy", "check if dev is working".

## Scope
Org-scoped (Klever initially). Extensible to Supervisr.

## Draft Steps
1. Wait for Cloud Run revision to become serving (poll /actuator/health, max 3 min)
2. Swagger schema assertion: fetch /v3/api-docs, verify key endpoints and parameters exist via JSON path checks
3. Data path probe: call one real endpoint with known-good parameters from smoke-test-config.yaml
4. Multi-entity pass-if-any rule: probe multiple entity IDs, pass if any returns non-null metric
5. Report PASS/FAIL to the deploying session or Gabriel's inbox

## Notes
Dev environment only. UAT/prod are human-initiated per shipping safeguards. Catches both stale Docker images (Swagger assertion) and parsing failures (data path probe). The smoke-test-config.yaml lists endpoints, expected fields, and entity IDs per vendor.
