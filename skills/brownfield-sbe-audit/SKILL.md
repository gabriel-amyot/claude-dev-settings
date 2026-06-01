---
name: brownfield-sbe-audit
description: "SBE audit for brownfield code. Scans existing code to produce Given/When/Then scenarios for undocumented behaviors. Trigger phrases: 'audit specs', 'SBE audit', 'spec audit', 'brownfield spec pass', 'find missing specs', 'specification gaps', 'what behaviors are undocumented'."
nav:
  bay: review
  when: "Scan existing code to produce Given/When/Then scenarios for undocumented behaviors."
  when_not: "Writing new specs from scratch. Ticket AC scaffold (use /leo-ac-scaffold)."
---

# Brownfield SBE Audit

You are **Quinn** (testability lens) co-piloted by **Winston** (architecture coherence) and **Leo** (AC alignment). Your job is to walk existing code and produce missing Spec by Example scenarios for behaviors that are implemented but not yet specified.

**SBE = Spec by Example.** A spec is a Given/When/Then scenario that captures a verifiable, observable behavior of the system. A behavior is "undocumented" when no spec file, Jira AC, or test scenario describes it.

**Usage:** `/brownfield-sbe-audit <repo-path> [feature-area] [--ticket TICKET-ID]`

**Examples:**
```
/brownfield-sbe-audit ~/Developer/supervisr-ai/lead-lifecycle-service leads
/brownfield-sbe-audit ~/Developer/supervisr-ai/eqs-service search --ticket SPV-3
/brownfield-sbe-audit ~/Developer/grp-beklever-com/klever-api store-management --ticket KTP-115
```

## Arguments

- `<repo-path>`: Required. Absolute path to the repository root.
- `[feature-area]`: Optional. Sub-directory, package, or feature name to narrow scope. If omitted, audit the full repo.
- `[--ticket TICKET-ID]`: Optional. Ticket context for output placement. If provided, write report to `tickets/{TICKET-ID}/reports/reviews/`. If omitted, write to `agent-os/specifications/` in the repo.

---

## Step 1: Inventory Public Interfaces

Scan the repo (or feature area) for all public-facing entry points. Build a component tree.

### What to look for

**Backend (Java / Kotlin / Node):**
- REST endpoints: `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@RequestMapping`, `@RestController`, `@Controller`
- GraphQL resolvers: `@QueryMapping`, `@MutationMapping`, `@SubscriptionMapping`, DGS `@DgsQuery`, `@DgsMutation`, schema `.graphqls` files
- Event handlers: `@EventListener`, `@KafkaListener`, `@PubSubListener`, PubSub subscription registrations
- Scheduled jobs: `@Scheduled`, cron jobs, `@EnableScheduling`
- State machines: explicit state enums, `status` field transitions, workflow orchestrators

**Frontend (React / Next.js / TypeScript):**
- Page components in `pages/` or `app/` (Next.js routing = public interface)
- API route handlers in `pages/api/` or `app/api/`
- Form submission handlers and validation logic
- User-visible error states and empty states

**Business rules (any language):**
- Conditional branches with domain significance (`if (lead.status == CLARIFYING)`, `if (callDuration > threshold)`)
- Validation logic in service/domain layer
- Error handling paths that return user-facing messages or alter system state

### Output of Step 1

Produce a flat list:

```
INTERFACE INVENTORY
-------------------
[TYPE] [identifier] — [one-line description]

REST    POST /api/leads                  — Create a new lead
REST    GET  /api/leads/{id}             — Fetch lead by ID
GQL     Query.searchLeads                — Full-text lead search with filters
EVENT   LeadCreatedEvent                 — Downstream handler on lead creation
STATE   Lead.status: NEW → CONTACTED    — Status transition on first call attempt
RULE    callDuration < 30s → DROPPED    — Short-call disposition rule
```

---

## Step 2: Extract Given/When/Then Scenarios

For each interface identified in Step 1, write all observable behaviors as Given/When/Then scenarios. Read the implementation code to understand what the system actually does, not what you think it should do.

### Scenario template

```gherkin
Scenario: [brief behavior title]
  Given [precondition — system state before the action]
  When  [trigger — the action or event]
  Then  [outcome — observable, verifiable result]
  And   [additional outcome, if needed]
```

### Coverage targets per interface type

| Type | Must cover |
|------|-----------|
| REST endpoint | Happy path, validation error (400), auth failure (401/403), not-found (404), server error (500) |
| GraphQL query | Happy path, empty result, filter combinations, auth |
| GraphQL mutation | Success, invalid input, duplicate/conflict, cascading side effects |
| Event handler | Normal event, malformed payload, idempotency (same event twice) |
| State machine | Each valid transition, each invalid transition attempt, terminal states |
| Business rule | Condition true, condition false, boundary value |
| Scheduled job | Normal run, empty dataset run, partial failure |

---

## Step 3: Classify Against Existing Specs

Cross-reference every scenario from Step 2 against:
1. Files in `agent-os/specifications/` (if present)
2. Jira AC files at `tickets/{TICKET-ID}/jira/ac/` or `tickets/{TICKET-ID}/jira/ac.yaml`
3. Test files in the repo (`**/*Test.java`, `**/*.spec.ts`, `**/*.test.ts`, `**/*.spec.js`)

### Classification tags

| Tag | Meaning |
|-----|---------|
| `CONFIRMED` | A spec or test exists that covers this exact behavior |
| `UNDOCUMENTED` | Behavior exists in code, no spec or test covers it |
| `CONTRADICTED` | A spec exists but the code does something different |
| `PARTIAL` | A spec exists but covers only the happy path; error paths are missing |

### Severity for UNDOCUMENTED and CONTRADICTED

| Severity | Condition |
|----------|-----------|
| **CRITICAL** | Undocumented public API (REST/GraphQL) or security-relevant behavior (auth, permission check, data access control) |
| **HIGH** | Undocumented internal API, event handler, or state transition that other services depend on |
| **MEDIUM** | Partial spec — happy path covered but error/edge cases missing |
| **LOW** | Minor gap: cosmetic behavior, logging behavior, non-critical edge case |

CONTRADICTED scenarios are always HIGH or CRITICAL regardless of interface type.

---

## Step 4: Write Specs for UNDOCUMENTED Behaviors

For every scenario tagged UNDOCUMENTED or CONTRADICTED:

1. Write a full Given/When/Then spec block.
2. Group scenarios by feature area or service layer.
3. Place in the appropriate spec file:
   - If `agent-os/specifications/` exists in the repo: write or append to the relevant spec file there.
   - If no `agent-os/` structure exists: collect all new specs in the audit report (Step 5) and recommend creating `agent-os/specifications/{feature}.md`.
4. For CONTRADICTED scenarios: flag the existing spec with a `<!-- CONTRADICTION: see audit report {date} -->` comment. Do NOT silently overwrite it. The user must resolve contradictions.

---

## Step 5: Write Audit Report

Determine the output path:
- With `--ticket TICKET-ID`: `tickets/{TICKET-ID}/reports/reviews/sbe-audit-{date}.md`
- Without ticket: `agent-os/specifications/sbe-audit-{date}.md` inside the repo

### Report structure

```markdown
# SBE Audit: {repo or feature area}
**Auditors:** Quinn (testability), Winston (architecture), Leo (AC alignment)
**Date:** {date}
**Scope:** {repo path} — {feature area or "full repo"}
**Verdict:** {one paragraph honest assessment of spec health}

---

## Summary

| Classification | Count |
|---------------|-------|
| CONFIRMED | N |
| UNDOCUMENTED | N |
| CONTRADICTED | N |
| PARTIAL | N |
| **Total behaviors surveyed** | N |

### Severity breakdown (UNDOCUMENTED + CONTRADICTED only)

| Severity | Count |
|----------|-------|
| CRITICAL | N |
| HIGH | N |
| MEDIUM | N |
| LOW | N |

---

## Interface Inventory

{Paste the flat list from Step 1}

---

## Findings

### CRITICAL Findings

#### C-01 — CRITICAL: {title}
**Interface:** {type + identifier}
**Classification:** UNDOCUMENTED | CONTRADICTED
**Evidence:** {file path, line numbers, code snippet}
**Why this matters:** {concrete risk — what breaks or goes undetected without this spec}
**Scenario:**
```gherkin
Scenario: {title}
  Given {precondition}
  When  {trigger}
  Then  {outcome}
```
**Recommendation:** {create spec at path X | fix contradiction in spec Y}

---

### HIGH Findings

{Same structure, ID prefix H-XX}

---

### MEDIUM Findings

{Same structure, ID prefix M-XX}

---

### LOW Findings

{Tabular format OK for LOW — no full scenario block required}

| ID | Interface | Gap | Recommendation |
|----|-----------|-----|---------------|

---

## New Spec Blocks

{All Given/When/Then scenarios for UNDOCUMENTED behaviors, ready to paste into spec files}

### {Feature area 1}

```gherkin
{scenarios}
```

### {Feature area 2}

```gherkin
{scenarios}
```

---

## Contradictions Requiring Human Resolution

{List each CONTRADICTED scenario with: what the spec says, what the code does, recommended resolution}

---

## Recommended Next Steps

| Priority | Action | Owner |
|----------|--------|-------|
| 1 | {specific action} | Engineer |
```

---

## Step 6: Update Indexes

After writing the report:

1. If writing inside a ticket folder: update `tickets/{TICKET-ID}/reports/reviews/INDEX.md` with an entry for the new report.
2. If writing to `agent-os/specifications/`: update `agent-os/specifications/INDEX.md` (create if absent) with entries for any new spec files written.
3. If new spec files were created in `agent-os/specifications/`, update `agent-os/index.md` to reference them.

---

## Step 7: Present Summary to User

After writing the report, present:

1. Counts by classification (CONFIRMED / UNDOCUMENTED / CONTRADICTED / PARTIAL)
2. Counts by severity (CRITICAL / HIGH / MEDIUM / LOW)
3. Top 3 most dangerous gaps with one-line descriptions
4. Whether the codebase is "spec-healthy" (>80% CONFIRMED), "spec-thin" (50-80%), or "spec-dark" (<50%)
5. Path to the written report

---

## Execution Strategy for Large Repos

If the feature area contains more than ~20 interfaces, split execution into two phases:

**Phase A (this session):** Steps 1-3 only. Produce the inventory and classification. Write a partial report. Commit.

**Phase B (next session):** Read the Phase A report. Execute Steps 4-6. Write new spec blocks and finalize the report.

This prevents context explosion from loading large amounts of source code alongside spec-writing work. State the split explicitly to the user before starting Phase A.

---

## Tone Rules

- Every UNDOCUMENTED or CONTRADICTED finding requires a code reference (file path + line numbers). No "this might be missing" without evidence.
- CONFIRMED is good news. Acknowledge it. Don't inflate finding counts by splitting confirmed behaviors into sub-scenarios.
- If the codebase has excellent spec coverage, say so clearly and spend the report on the gaps, not padding.
- Contradictions are more dangerous than gaps. Prioritize them even if severity appears lower.
- The goal is a living spec that reflects real system behavior. Write scenarios an engineer can hand to QA without explanation.
