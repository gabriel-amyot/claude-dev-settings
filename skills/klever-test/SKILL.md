---
name: klever-test
description: "Klever testing hub for suite and evidence testing: Playwright regression, backend API e2e, AC validation, proximity 14-UC suite, UX dogfood, and the sprint proof runner. Use when the user says 'run the e2e/regression suite', 'run the backend tests', 'generate proof', 'sprint proof', 'AC evidence', 'prove the sprint', or wants Jira-ready test artifacts for a ticket or sprint. For LIVE UI inspection or debugging against the running app — 'test/validate/QA the UI', 'why isn't the UI updating', 'the button/spinner does nothing', 'read the live React state/DOM/console', 'inspect the running app' — use the ui-probe skill instead; the frontend AC-validation and proximity modes here delegate live execution to ui-probe. Playwright regression and UX dogfood remain available here on request."
user_invocable: true
nav:
  bay: review
  when: "Suite & evidence testing: Playwright regression, backend API e2e, AC validation, proximity suite, dogfood, proof runner. Live UI inspection delegates to ui-probe."
  when_not: "Live UI inspection/debugging against the running app (use ui-probe). Non-Klever testing. Adversarial code review (use /adversarial-cascade)."
  personas: [quinn]
  org: [klever]
---

# Klever Test Hub

Single entry point for Klever testing. Pick the right test type, then load the detailed procedure from the sub-file.

**Usage:** `/klever-test [type] [args]`

## Default routing — live UI goes to ui-probe

For **live UI inspection or debugging against the running app** (the portal on dev or localhost) — "test/validate/QA the UI", "why isn't it updating", "the button does nothing", "read the live React state/DOM/console" — the default is the **`ui-probe`** skill, not this hub. It attaches to the user's authenticated Chrome and returns runtime ground truth (DOM, props/state, console, network timing) without the auth dance that the agent-browser and Playwright-MCP paths struggle with. The frontend AC-validation (mode 2) and proximity-suite (mode 3) modes below **delegate their live execution to `ui-probe`**.

This hub still owns suite runs, evidence, and on-request tools: the Playwright regression suite, backend API e2e, the sprint proof runner, and the UX dogfood persona. Those are picked explicitly — use them when the user asks for them by name.

## Menu

When invoked without arguments, present this menu and ask the user which option:

| # | Type | What it does | Tool | Sub-file to read |
|---|------|-------------|------|-----------------|
| 1 | **Frontend: Playwright Regression** | Runs the Playwright e2e spec suite (`npm run test:e2e`). Zero Claude token cost during execution. | Playwright Test runner | [frontend-playwright.md](frontend-playwright.md) |
| 2 | **Frontend: AC Validation** | Validates a specific ticket's acceptance criteria via browser automation. Screenshots for evidence. | Agent Browser CLI | [frontend-ac-validation.md](frontend-ac-validation.md) |
| 3 | **Frontend: Proximity 14-UC Suite** | Targeted UI test for the Proximity Map feature. 14 use cases including flow lines, layers, filters. | Agent Browser CLI / Chrome MCP | [frontend-proximity-suite.md](frontend-proximity-suite.md) |
| 4 | **Frontend: UX Dogfood (Sally)** | First-user walkthrough with Sally persona. Finds what looks broken or confusing. Severity-rated report. | Chrome MCP | [frontend-ux-dogfood.md](frontend-ux-dogfood.md) |
| 5 | **Backend: API E2E Tests** | Runs Python scripts that call proximity-report endpoints with assertions. 22 tests total. | Python (`python3`) | [backend-api-tests.md](backend-api-tests.md) |
| 6 | **Sprint Proof Runner** | Generates per-ticket proof artifacts (screenshots, API logs, unit test results, grep checks) in Jira wiki markup. AC-driven: maps every acceptance criterion to a test layer and produces evidence. Covers full sprint or single ticket. | run-proof.sh | [proof-runner.md](proof-runner.md) |

## Auto-Selection Heuristics

If the user provides context, skip the menu:

| User says | Auto-select |
|-----------|------------|
| "test/validate/QA the UI", "why isn't the UI updating", "the button/spinner does nothing", "read the live React state/DOM/console", "inspect the running app", "the map is blank live" | **ui-probe** (live runtime inspection — hand off, don't run a mode here) |
| "run e2e tests", "regression", "run playwright" | #1 Frontend: Playwright |
| "validate AC for KTP-XXX", "verify acceptance criteria" | #2 Frontend: AC Validation (delegates live execution to ui-probe) |
| "proximity test", "run the 14 use cases", "test flow lines" | #3 Frontend: Proximity Suite (delegates live execution to ui-probe) |
| "dogfood", "Sally look at this", "UX review", "how does it look" | #4 Frontend: UX Dogfood |
| "test the backend", "test the API", "run backend tests" | #5 Backend: API E2E |
| "generate proof", "proof artifacts", "sprint proof", "AC evidence", "proof for KTP-XXX", "prove the sprint", "test the sprint", "run proof", "ticket proof" | #6 Sprint Proof Runner |

## Autonomous Agent Usage

When an agent needs to test as part of a crawl or autonomous session:
1. Load this skill via `Skill` tool
2. Determine which test type matches the current task
3. Read the relevant sub-file using the `Read` tool on the path shown in the menu
4. Follow the sub-file's procedure

## Preflight Checks (ALL test types)

Every test type requires services to be running. Previous failures were caused by missing backends (HTTP 500s), not browser or test tooling.

```bash
# Frontend (port 3001 or 3000)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 2>/dev/null || \
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000

# Proximity backend (port 8097)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8097/actuator/health

# UM backend (port 8090)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/actuator/health

# MySQL container
docker ps --filter name=klever-mysql-local --format "{{.Status}}"
```

If any fail: report which services are down. Suggest `/klever-local-stack`. Do NOT proceed.

For dev environment: check nightly schedule (off after 20:00 EDT). If 000/timeout, use local mode.

## Common Failure Patterns

| Symptom | Cause | Fix |
|---------|-------|-----|
| HTTP 500 on `/api/map/*` | Backend not running | `/klever-local-stack` |
| Map blank | Mapbox token expired | Check `.env.local` |
| 0 locations | Missing seed data | `/um-local-seed` |
| Dev returns 000 | Nightly shutdown | Use local mode |
| Flow lines absent | Placer key expired | Refresh via 1Password CLI |

## Browser Tool Selection

| Tool | When to use | Token cost |
|------|------------|------------|
| **ui-probe (Chrome MCP)** | **Default for live UI inspection/debugging — attaches to the user's authenticated Chrome, no auth dance.** AC validation and proximity suite delegate here. | MEDIUM |
| Playwright Test | Regression suite (runs independently, no auth needed) | ZERO |
| Chrome MCP (dogfood) | UX dogfood persona — opinion/severity pass, not fact-finding | MEDIUM-HIGH |
| Agent Browser CLI | On request only; struggles with Klever IAP. Prefer ui-probe for live work. | LOW |
