# Frontend: Playwright Regression Tests

Runs the Playwright Test suite in `app-front-portal/e2e/`. Zero Claude token cost during execution.

## Specs Available

Located at `~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal/e2e/`:

| Spec file | What it tests |
|-----------|--------------|
| `admin-permissions.spec.ts` | Permission management UI |
| `bulk-grant-modal.spec.ts` | Bulk permission grant flow |
| `new-user-modal.spec.ts` | User creation modal |
| `scope-editor.spec.ts` | Permission scope editing |
| `visitor-flow-lines.spec.ts` | KTP-130 flow line rendering |
| `fixtures.ts` | Shared test fixtures |

## Run Commands

```bash
cd ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal

# Full suite
npm run test:e2e 2>&1

# Specific spec
npx playwright test --grep "<pattern>" 2>&1

# Headed mode (visual debugging)
npx playwright test --headed 2>&1

# UI mode (interactive)
npm run test:e2e:ui
```

## Parse Results

From stdout, extract: total, passed, failed, skipped, duration.

## Handle Failures

```bash
# Check for failure screenshots
ls -la ~/Developer/grp-beklever-com/grp-app/grp-frontend/app-front-portal/test-results/ 2>/dev/null
```

Classify each failure: **test bug** vs **infrastructure** (500 errors, timeouts = infrastructure).

## Report Format

If ticket context exists, write to: `tickets/{PREFIX}/{TICKET-ID}/reports/reviews/e2e-regression-{YYYY-MM-DD}.md`

```markdown
# E2E Regression Report
**Date:** {date}
**Duration:** {Xs}

## Summary
| Status | Count |
|--------|-------|
| PASS | N |
| FAIL | N |
| SKIP | N |

## Failures
### {test name}
**File:** e2e/{spec}.spec.ts:{line}
**Error:** {message}
**Classification:** test bug | infrastructure
```

Suggest `npx playwright show-report` for interactive HTML report on failures.
