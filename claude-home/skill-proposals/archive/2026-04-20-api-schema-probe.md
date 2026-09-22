# Skill Proposal: api-schema-probe
Date: 2026-04-20
Source: KTP-522 Goldfish API spike

## Trigger
When integrating with an undocumented or poorly documented REST API where the schema isn't publicly available and you need to reverse-engineer the expected request format.

## Scope
global (any org, any API)

## Draft Steps
1. **Auth probe:** Send request with invalid credentials to confirm auth mechanism works (expect 401/403)
2. **Field discovery:** Send empty body, then add one field at a time. Watch for error message changes (422 text shifting = field accepted)
3. **Value format discovery:** For each discovered field, try common formats (string, int, nested object, array) and watch for error changes (422 → 500 means value format wrong but field name right)
4. **Document findings:** Produce a structured report: confirmed fields, inferred types, unknown formats, blocker classification
5. **Generate reusable script:** Output a Python/curl script that captures the working request shape for re-validation after vendor fixes issues
