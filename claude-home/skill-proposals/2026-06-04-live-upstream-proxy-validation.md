# Skill Proposal: live-upstream-proxy-validation
Date: 2026-06-04
Source: KTP-756 Goldfish DOOH proxy (keen-falcon)

## Trigger
A ticket whose deliverable is a backend proxy to a live external API (Goldfish, Placer, etc.), when
mocked tests are green but the live contract is unverified — or post-merge validation of such an endpoint.

## Scope
org (Klever); generalizable.

## Draft Steps
1. Build + boot the service locally with real creds (or open the dev IAP tunnel via gcp-connect.sh →
   localhost:port → dev backend).
2. Curl the new endpoint(s) through the running service against the LIVE upstream; capture real payloads.
3. Compare the backend-received body to what curl/docs show — specifically field CASING and field
   population (the snake_case-vs-camelCase class of bug). Flag any all-null multi-word fields.
4. Add a regression guard: a unit/integration test using the real upstream shape (not the doc shape),
   plus an e2e script that asserts field population, not just HTTP 200.
5. Verify graceful-degradation + caching/retry against the repo's conventions.
6. Tear down the tunnel; record evidence in the ticket's qa/ folder.

## Notes
This is the concrete answer to "green mocks, broken live." Pairs with the dark-factory hardening items
(live-upstream proof + QA verify_status code_proven|live_proven).
