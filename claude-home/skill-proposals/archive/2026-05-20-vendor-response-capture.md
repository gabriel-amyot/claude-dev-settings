# Skill Proposal: vendor-response-capture
Date: 2026-05-20
Source: KTP-669 Winston harness recommendations (Rec 1)

## Trigger
When an agent writes parsing code for a vendor API endpoint during a spike or implementation ticket, or when user says "capture vendor response", "record API response", "save fixture from API".

## Scope
Global (any org with vendor API integrations). First implementation targets Klever/Placer.

## Draft Steps
1. Accept vendor name, endpoint URL, HTTP method, request body, and auth header source (1Password path or env var)
2. Execute curl probe with credentials, capture full response
3. Strip volatile fields (timestamps, request IDs, trace headers) while preserving structure and field names
4. Write response to `src/test/resources/vendor/{vendor}/{endpoint-slug}-response.json`
5. Add provenance comment to the fixture file header: `// Recorded from {vendor} API: {method} {url} on {date}`
6. Commit the fixture with message citing source endpoint and date

## Notes
Analogous to `/bq-schema-preflight` but for vendor REST APIs. Prevents the KTP-669 hallucination pattern where agents guess field names from descriptions instead of recordings. The fixture becomes both the contract test source and living documentation.
