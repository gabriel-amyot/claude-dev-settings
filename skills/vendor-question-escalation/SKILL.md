---
name: vendor-question-escalation
description: Drafts focused, binary vendor questions when a blocker requires external confirmation. Triggered by "ask the vendor", "email Nick", "check with [external person]", or when a blocker is tagged as "vendor response needed."
---

# Vendor Question Escalation

When a blocker depends on a vendor's answer, the only thing that matters is getting that answer fast. Vendors respond quickly to clear, direct questions. They go quiet when they have to parse architecture debates to find what you're actually asking.

This skill drafts vendor-facing messages. It strips everything that belongs inside the team and surfaces only the three things a vendor can act on: what you tested, what you observed, and what you need confirmed.

---

## When to Use This Skill

Use this skill when any of the following are true:

- Internal research contradicts vendor documentation and the discrepancy blocks a go/no-go decision.
- A task is tagged with "vendor response needed" or a similar blocker label.
- The user says any of: "ask the vendor", "email [name]", "check with [external contact]", "we need to confirm with [vendor]", "reach out to support".
- A technical assumption cannot be validated without vendor access (API behavior, undocumented limits, data availability, licensing terms).

Do not use this skill for internal escalations, team-to-team clarifications, or questions that can be answered by reading documentation more carefully.

---

## What This Skill Produces

A draft message ready for the user to review. The draft contains:

1. A subject line that names the product and states the question in one line.
2. A minimal greeting.
3. A two-to-three sentence context block — only what the vendor must know to understand the question.
4. Up to three numbered questions, each phrased as binary (yes/no, A or B, confirmed or not).
5. A brief "What we tried" section: factual, no architecture discussion.
6. A clean sign-off.

See `templates/vendor-email.md` for the full template.

---

## Step-by-Step Procedure

### Step 1: Identify the binary questions

Before writing anything, identify the exact questions that unblock progress. Apply this test to each candidate question:

- Can a vendor engineer answer it in two sentences or fewer?
- Is the answer a binary outcome (yes/no, A/B, supported/not supported)?
- Does the answer directly unblock a decision?

If the answer to all three is yes, include it. If not, it is internal analysis and belongs in your ticket notes, not in the vendor message.

**Maximum: three questions.** If you have more than three, rank by dependency. A question that blocks all other questions goes first. Questions that only matter if the first answer is "yes" can wait for a follow-up.

### Step 2: Strip internal context

Everything that stays inside the team:

- Ticket references (KTP-130, SPV-165, etc.)
- Internal tool names (EQS, LLS, DAC, ERS, Apollo Router, etc.)
- Team member names
- Architecture debates ("we considered X but Y because Z")
- Implementation details ("we're using a federated GraphQL gateway with...")
- Business logic explanations
- Rationale for why you need the answer

The vendor does not need to understand your system to answer a precise question. Internal context is noise that delays their response.

### Step 3: Write the context block

Two to three sentences maximum. Include only:

- What product/API/feature you are working with.
- The specific behavior or capability you are trying to use.
- Any relevant version, tier, or access level if it affects the answer.

Do not explain why you need it. Do not mention your architecture. Do not reference your stack.

**Good context block:**
> We are integrating with the Placer.ai Visits API (commercial tier) and evaluating whether polygon-based queries are supported in the v2 endpoint.

**Bad context block:**
> We're building a location intelligence layer on top of our existing EQS GraphQL service. We've been going back and forth on whether to use Placer or TTD for the POI data and the federated query model we use means we need polygon support at the API level, not client-side.

### Step 4: Write the questions

Each question must be:

- **Numbered.** Start at 1.
- **Binary or enumerable.** The vendor can answer with yes/no, a version number, a specific value, or a short list.
- **Self-contained.** Each question includes enough context to be understood without the others.
- **No leading.** Do not embed your preferred answer or expected outcome.

**Good questions:**
> 1. Does the v2 Visits endpoint support polygon-based geographic queries, or is it limited to radius-based queries?
> 2. Are polygon queries available on the commercial tier, or do they require an enterprise plan?
> 3. Is there a documented rate limit for polygon queries distinct from the general endpoint rate limit?

**Bad questions:**
> 1. We assumed polygon support was included based on the docs but when we tested it we got a 400 error — is that expected or are we doing something wrong? (Not binary. Embeds assumption. Requires vendor to diagnose your implementation.)
> 2. We need polygon support for our architecture to work — can you confirm it's available? (Includes internal pressure. Not a clean yes/no framing.)
> 3. What's the rate limit? (Too vague. No context for which endpoint, tier, or query type.)

### Step 5: Write the "What we tried" section

This section is optional but recommended when you observed specific behavior (an error code, an unexpected response, a discrepancy between documentation and behavior). Keep it to three bullet points or fewer.

Include:
- The endpoint or feature tested.
- What was sent (request type, parameters, relevant values — no internal system names).
- What was observed (response code, error message, behavior).

Do not include:
- Why you expected a different result.
- Architecture context.
- Internal ticket references.

**Good "What we tried":**
> - Called `POST /v2/visits/query` with a GeoJSON polygon in the `region` field.
> - Received HTTP 400 with message: `"region type 'Polygon' not supported"`.
> - Confirmed API key is active and tier is commercial.

**Bad "What we tried":**
> We spent two days in our test harness trying to get this to work and the EQS pre-flight kept rejecting the polygon format. We tried radius first (that worked) but our architecture requires polygon for the KTP-130 use case. The DAC pipeline runs fine but the API just won't accept polygons.

### Step 6: Review before presenting

Before presenting the draft to the user, apply this checklist:

- [ ] Subject line names the product and states the question in one line.
- [ ] No internal ticket references anywhere in the message.
- [ ] No internal tool, service, or system names.
- [ ] No team member names (yours or internal).
- [ ] Context block is three sentences or fewer.
- [ ] Three questions or fewer, each binary or enumerable.
- [ ] "What we tried" is factual with no architecture discussion.
- [ ] Total message length: under 300 words.

If any check fails, fix it before presenting.

### Step 7: Present and route for approval

Present the full draft to the user. Do not send it.

If the target is a Jira comment or an external ticketing system, route through `/post-comment`. The `/post-comment` skill renders via template, previews the full content, waits for explicit approval, posts, and logs to the audit trail.

If the target is email, present the draft inline. The user copies it manually or approves before you take any action.

**Never post externally without explicit user approval.** This is a hard rule.

---

## Anti-Patterns Cheat Sheet

| What you have | What to do |
|---|---|
| Internal ticket number | Remove it. |
| Internal service name (EQS, LLS, DAC) | Remove or replace with generic description ("our data layer") only if necessary for context. |
| Your architecture rationale | Remove it. |
| "We need this for X use case" | Remove it. Vendors don't need to know your use case. |
| More than three questions | Cut to the three most blocking. Park the rest. |
| A question that requires the vendor to diagnose your code | Rephrase as a capability question: "does this feature exist" not "why doesn't this work for us". |
| A question with your preferred answer embedded | Rephrase as neutral. "Is X supported?" not "X is supported, right?" |
| Team member names | Remove. |

---

## Template Reference

The email template is at `templates/vendor-email.md`. Use it as the structural skeleton for the draft. Fill in the product name, context, questions, and "what we tried" section from the analysis above.

---

## Example: Before and After

### Before (first draft, stripped from internal session)

> Hi Nick,
>
> We're working on KTP-130 and we've been trying to integrate Placer's Visits API into our EQS pre-flight layer. Our DAC pipeline runs the polygon query through our federated gateway but we're getting a 400 back from the v2 endpoint. We assumed polygon support was included in the commercial tier based on the docs page but we're not sure if this is a tier issue or an API limitation.
>
> A few questions:
> 1. Is polygon support included in our plan?
> 2. Why are we getting 400s?
> 3. What's the rate limit?
> 4. Is there a sandbox environment?
> 5. What version should we be using?
>
> Thanks

### After (using this skill)

> Subject: Placer Visits API: polygon query support and rate limits
>
> Hi Nick,
>
> We're integrating with the Placer Visits API (commercial tier) and need to confirm two capabilities before proceeding.
>
> **Questions:**
> 1. Does the v2 Visits endpoint support polygon-based geographic queries, or is it restricted to radius queries?
> 2. If polygon queries are supported, is there a rate limit distinct from the general endpoint rate limit?
>
> **What we tried:**
> - Called `POST /v2/visits/query` with a GeoJSON polygon in the `region` field.
> - Received HTTP 400: `"region type 'Polygon' not supported"`.
> - Confirmed API key active, tier is commercial.
>
> Thanks,
> Gabriel

The second version got a same-day response. The first version would have required a follow-up to clarify what was actually being asked.
