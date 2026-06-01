---
name: api-spike
description: "Structured external API spike for undocumented or poorly documented APIs. Four phases: auth probe, shape discovery, schema reverse engineering, documentation. Trigger: 'API spike', 'validate API', 'test API credentials', 'explore API', 'reverse-engineer this API'. Global scope. Input: base URL + credentials. Returns: API surface map + schema docs in ticket folder."
nav:
  bay: plan
  when: "Structured spike on undocumented or poorly documented external API."
  when_not: "API already documented. Vendor docs exist (use /vendor-api-ingest to save them)."
---

# API Spike

Systematic exploration of undocumented or poorly documented external APIs.

## Prerequisites

- Base URL for the API
- Credentials (API key, Bearer token, or Basic auth). NEVER store credentials in output files. Reference env vars.
- A ticket context for output (e.g., KTP-131 for Goldfish Ads)

## Phase 1: Auth Probe

**Goal:** Confirm auth mechanism and that credentials work.

1. Send a request with INVALID credentials to a likely endpoint:
```bash
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer INVALID" <base_url>/v1/status
```
Expected: 401 or 403. This confirms the auth check is active.

2. Send VALID credentials:
```bash
curl -s -w "\n%{http_code}" -H "Authorization: Bearer $API_TOKEN" <base_url>/v1/status
```
Expected: 200 or 204. If 500: auth passed but server crashed (explore further, don't declare BLOCKED).

3. Document:
- Auth type (API key header, Bearer, Basic, OAuth)
- Header name (Authorization, X-API-Key, etc.)
- Token format (JWT, opaque string, etc.)

## Phase 2: API Shape Discovery

**Goal:** Map the API surface.

1. Start with parent resource paths:
```bash
curl -s -H "Authorization: Bearer $API_TOKEN" <base_url>/v1/ | python3 -m json.tool
curl -s -H "Authorization: Bearer $API_TOKEN" <base_url>/v2/ | python3 -m json.tool
```

2. Probe common discovery endpoints:
- `/v1/types`, `/v1/status`, `/v1/publishers`, `/v1/info`
- `/v2/types`, `/v2/status`, `/v2/campaigns`

3. For each path, record: HTTP method, status code, response shape (or error).

4. Try adjacent variants when something fails:
- POST fails? Try GET with query params
- `/resource/by-X` fails? Try `/resource?x=VALUE`
- 404? Try without trailing slash, different version prefix

5. Build a surface map table:

```
| Method | Path | Status | Response Shape | Notes |
|--------|------|--------|----------------|-------|
| GET | /v1/types | 200 | [{id, name}] | Lists all types |
| POST | /v1/campaigns | 422 | {error: "..."} | Requires body |
| GET | /v2/status | 410 | - | Deprecated |
```

## Phase 3: Schema Reverse Engineering

**Goal:** Discover request/response schemas for key endpoints.

1. Send empty body to writable endpoints:
```bash
curl -s -X POST -H "Authorization: Bearer $API_TOKEN" -H "Content-Type: application/json" -d '{}' <base_url>/v1/resource
```
Read the error message for required fields.

2. Add one field at a time. Watch for error message changes:
- 422 text shifts = field was accepted, next field now required
- 422 to 500 = field name is right but value format is wrong
- 204 = empty data, not an error
- 410 = deprecated version

3. For each discovered field, try common formats:
- String: `"field": "test"`
- Integer: `"field": 1`
- Boolean: `"field": true`
- Array: `"field": [1]`
- Nested: `"field": {"sub": "value"}`

4. Document the discovered schema with types and constraints.

## Phase 4: Document and Report

Write output to: `tickets/{PREFIX}/{TICKET-ID}/reports/architecture/{vendor}-api-surface-{date}.md`

Include:
1. **Auth method** and header format
2. **API surface map** (the table from Phase 2)
3. **Request/response schemas** for key endpoints
4. **Error codes** observed (with example messages)
5. **Undocumented behaviors** (rate limits, pagination quirks, deprecation hints)
6. **Blocking gaps** (endpoints that exist but return no useful data, required fields with no documentation)

## Safety Rules

- NEVER store credentials in skill output. Use `$ENV_VAR` references.
- Use `curl --fail-with-body` to capture error response bodies
- Use `curl -s` (silent) to avoid progress bars in output
- All output goes to ticket folder, never project root
- If an endpoint returns 500 repeatedly, note it but continue (don't declare BLOCKED)
- Rate limit yourself: add 1-second delays between requests if the API shows signs of throttling
