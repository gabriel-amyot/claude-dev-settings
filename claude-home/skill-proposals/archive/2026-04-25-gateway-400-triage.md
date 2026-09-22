# Skill Proposal: gateway-400-triage
Date: 2026-04-25
Source: SPV-165 session 2 debugging spiral

## Trigger
When debugging HTTP 400 from Apollo Gateway (Supervisr), or when an overnight crawl reports 400 errors from gateway calls.

## Scope
org (Supervisr)

## Draft Steps
1. **Check parameters first** — Are all required GraphQL arguments passed? Look for null values in non-nullable fields (`FilterQueryValue!`, `String!`). This is the #1 cause.
2. **Check data types** — Are numeric fields receiving strings? (e.g., epoch millis vs ISO dates)
3. **Reproduce from curl** — Send the exact same GraphQL request from curl to the gateway. If curl gets 200 but Cloud Run gets 400, THEN investigate networking.
4. **Check M2M credentials** — Read the secret from Secret Manager, test oauthToken mutation with exact credentials.
5. **Only then investigate infrastructure** — VPC routing, Cloud Armor, CSRF, router.yaml headers.

## Rationale
This session spent ~15 minutes investigating URLs, WebClient vs MonoGraphQLClient, Cloud Run networking, and domain-mapped vs direct URLs. The root cause was a missing parameter. A 30-second parameter check would have found it.
