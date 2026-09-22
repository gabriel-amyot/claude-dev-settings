# Skill Proposal: External API Spike Validation
Date: 2026-04-20
Source: KTP-522 Goldfish Ads API spike

## Trigger
When running a spike/validation ticket against an unknown external API. "validate API", "API spike", "test API credentials", "explore API".

## Scope
Global (any org, any external API)

## Draft Steps
1. Auth check: send invalid key, confirm 401/403. Send valid key to known endpoint.
2. Parent path probe: GET the parent resource path before trying sub-paths. Read error messages for parameter hints.
3. Discovery endpoints: probe /v2/types, /v2/publishers, /v2/status, etc. Map the API shape.
4. Adjacent variants: if POST /resource/by-X fails, try GET /resource with query params. Try different HTTP methods.
5. Error message reading: 422 messages often describe the correct format. 500 means auth passed, business logic crashed. 404 = wrong path. 410 = deprecated version.
6. Save working payloads immediately. Document non-working endpoints with exact error.
7. Never declare BLOCKED after one endpoint variant. Explore at least 3 adjacent paths first.
