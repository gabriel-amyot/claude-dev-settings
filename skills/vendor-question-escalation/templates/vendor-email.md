# Vendor Email Template

---

## Subject Line

```
{PRODUCT}: {1-line question summary}
```

Examples:
- `Placer Visits API: polygon query support and rate limits`
- `Auth0 M2M: token scope inheritance for nested organizations`
- `Mapbox Tiling Service: concurrent upload limits on standard plan`

Keep it under 60 characters. Name the product first. State the question, not the context.

---

## Message Body

```
Hi {Name / Support Team},

{CONTEXT — 2-3 sentences max. What product, what feature, what you need confirmed. Nothing else.}

Questions:
1. {Binary question — yes/no, A/B, or short enumerable answer.}
2. {Binary question — yes/no, A/B, or short enumerable answer.}
3. {Binary question — yes/no, A/B, or short enumerable answer.}

What we tried:
- {Endpoint or feature tested.}
- {What was sent — request type, parameters, observed behavior.}
- {Response received — HTTP code, error message, or specific output.}

Thanks,
{Name}
{Title, if relevant}
```

---

## Field Rules

### {CONTEXT}

- **Length:** 2-3 sentences. Hard limit.
- **Include:** Product name, API version or tier, feature being tested.
- **Exclude:** Internal system names, ticket references, team names, architecture rationale, your use case.

**Good:**
> We are integrating with the Auth0 Management API (M2M, developer plan) and need to confirm how token scopes are inherited when using nested organizations.

**Bad:**
> We're building the LLS-to-EQS auth bridge in our federated gateway and the DAC pipeline keeps failing because the M2M scopes don't seem to propagate through the org hierarchy. Our SPV-100 ticket is blocked on this.

---

### {Questions}

- **Maximum:** 3 questions. If you have more, cut to the three most blocking.
- **Format:** Numbered. One sentence each.
- **Type:** Binary (yes/no), enumerable (list of options), or specific value (rate limit, max, version).
- **Not allowed:** Open-ended questions, diagnostic requests, questions that embed your architecture.

**Good:**
> 1. Does the v2 endpoint support OAuth 2.0 client credentials flow, or is it restricted to authorization code?
> 2. Is the 429 rate limit documented anywhere for the commercial tier?

**Bad:**
> 1. We're getting a 403 on our gateway — can you help us debug it? (Diagnostic, not binary.)
> 2. How does auth work? (Too open-ended.)
> 3. We assumed this was included, right? (Leading question.)

---

### {What we tried}

- **Optional.** Include only when you observed specific behavior worth sharing.
- **Length:** 3 bullets maximum.
- **Content:** Endpoint called, inputs used, output observed.
- **Not allowed:** Architecture context, internal system references, rationale for the test.

**Good:**
```
What we tried:
- Called POST /v2/visits/query with a GeoJSON polygon in the `region` field.
- Received HTTP 400: "region type 'Polygon' not supported".
- Confirmed API key is active and account tier is commercial.
```

**Bad:**
```
What we tried:
- Our EQS layer sends the polygon through our federated GraphQL gateway to the Placer endpoint.
- The DAC pipeline runs the pre-flight which calls the API and gets a 400 back.
- We've been trying for two days and the KTP-130 ticket is blocked until we know if this is supported.
```

---

## Anti-Pattern Quick Reference

Strip these before sending:

| Anti-pattern | Replace with |
|---|---|
| Internal ticket number (KTP-130, SPV-165) | Nothing. Remove entirely. |
| Internal service names (EQS, LLS, DAC, ERS) | Remove or use generic ("our API layer") only if essential to the question. |
| Team member names | Remove. |
| "We need this for X use case" | Remove. |
| Architecture rationale ("we chose X because Y") | Remove. |
| More than 3 questions | Cut to top 3 by blocking priority. |
| A question asking the vendor to debug your code | Rephrase as: "Is X supported?" |
| Phrases like "we assumed", "we expected", "this should work" | Remove. State only what you observed. |

---

## Routing

This template produces a **draft only**.

- If posting to Jira, GitLab, or an external ticketing system: route through `/post-comment`.
- If sending as email: present draft to user for copy-paste. Do not send autonomously.
- Never post externally without explicit user approval.
