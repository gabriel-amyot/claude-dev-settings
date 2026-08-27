# Vendor API Contract Validation — Harness Gates

On-demand context: load when writing code that parses a vendor/external API response, onboarding a new vendor API, reviewing vendor integration code, or completing a spike that explored vendor endpoints.

**Origin:** KTP-669 failure chain (2026-05-19). Agent hallucinated Placer API field names during a spike, fabricated test fixtures to match, and the null-safe architecture concealed total data loss for 18 days. 21 unit tests passed. 0 caught the bug. A human curling the real API did.
**Full RCA + detailed recommendations:** `~/Developer/grp-beklever-com/project-management/tickets/KTP/KTP-559/KTP-669/reports/reviews/dexter-rca-placer-parsing-2026-05-19.md` and `reports/architecture/winston-harness-recommendations-2026-05-19.md`

---

## The Anti-Pattern: Circular Validation

Agent writes parsing code with guessed field names → agent writes test fixtures matching the guessed names → tests pass → code ships → real API returns different field names → parser returns null → null-safe architecture renders dashes → nobody notices.

**Diagnostic signature:** Plausible camelCase field names (`avgDwellTime`, `visitsByHours`) that are English expansions of the endpoint's purpose, not the vendor's actual naming convention (`average`, `estimatedFoottraffic`). This is how LLMs hallucinate API schemas from natural-language descriptions.

---

## Five Gates (defense-in-depth, no single gate is sufficient)

### Gate 1: Spike Must Probe the Real API (prevents at origin)

When writing parsing code for a vendor endpoint during a spike:
1. **curl the endpoint first** and save the full response to `tickets/{SPIKE-ID}/reports/api-probes/{endpoint-slug}.json`
2. Write parsing code against the recorded response, not from imagination
3. If the API is unreachable (missing credentials, rate limits, sandbox unavailable), **mark the spike as incomplete**. "Tests pass" is not evidence of correctness.

Spike completion report must include:
- curl command + HTTP status for each endpoint
- Recorded response JSON per endpoint
- Field name mapping table: code field → API field → line number
- Parse validation: evidence that recorded response produces non-null output

**This is the only gate with a human review checkpoint.** All others are mechanical and can be circumvented.

### Gate 2: Recorded-Response Fixtures (catches at test time)

Every vendor API endpoint the backend calls must have a recorded-response fixture at `src/test/resources/vendor/{vendor-name}/{endpoint-slug}-response.json`. Each endpoint gets its own file. **Never reuse a single fixture across multiple endpoints** (the `stubAllPlacerCalls()` anti-pattern).

Unit tests must:
- Load the endpoint-specific recorded fixture
- Parse it through the production parsing method
- Assert output fields are non-null and structurally valid

**Staleness gap:** Fixtures are point-in-time snapshots. If the vendor changes their API, stale fixtures still pass while live calls fail. Mitigation: the post-deploy smoke test (Gate 4) catches drift in the deployed environment. Fixtures prevent hallucination at dev time; smoke tests catch drift at deploy time.

### Gate 3: Circular Validation Lint (weak signal, defense-in-depth)

A pre-commit lint flags:
- Shared stub methods returning identical JSON for multiple vendor endpoints
- Same fixture file loaded by tests for different endpoints
- Missing provenance annotation (`// Recorded from {Vendor} API: {method} {url} on {date}`)

**Honest limitation:** This lint is trivially satisfied by renaming methods or fabricating provenance comments. It catches laziness, not deliberate hallucination. Only meaningful when paired with Gate 2 (mandatory captured fixtures).

### Gate 4: Post-Deploy Smoke Test (catches after deploy)

After merge to dev:
1. Wait for Cloud Run revision to become serving
2. **Schema assertion:** Fetch `/v3/api-docs` and verify key endpoints/parameters exist
3. **Data path probe:** Call one real endpoint with known-good parameters, assert at least one metric is non-null

Use multiple entity IDs with a pass-if-any-returns-data rule to absorb individual entity churn.

**Scope:** Dev only. UAT/prod are human-initiated. This catches stale Docker images AND parsing failures that produce all-null.

### Gate 5: Null Cascade Canary (runtime detection)

When assembling a response for a mapped vendor entity:
- **Total null:** All vendor-sourced metrics null → `WARN store_metrics_all_null`
- **Disproportionate null:** 1 of N endpoints returns data but the rest are null → `WARN store_metrics_mostly_null`

Suppression: new entities (mapped within 7 days) skip the canary to avoid alert fatigue.

The disproportionate canary catches the actual production symptom from KTP-669: one parser worked, six were broken.

---

## When This Context Applies

Load this file when:
- Writing or reviewing code that parses any external/vendor API response
- Completing or reviewing a spike that explored vendor API endpoints
- Onboarding a new vendor (Placer, Goldfish, Retell, or any future vendor)
- Debugging "all values are null/dashes" in a vendor data integration
- An agent writes a `stubAll*Calls()` or reuses a single mock fixture across endpoints

---

## Key Principle

**Never write parsing code from a description of what the API returns. Write it from a recording of what the API returns.** The gap between "returns average dwell duration" (documentation) and `"average": 48` (actual field name) is where hallucination lives.
