# Phase 2: Autonomous Execution — Delegation Protocol

This reference details the BMAD agent delegation for Phase 2 of the feedback-to-spec pipeline. Phase 2 runs only after the user has explicitly confirmed all SBEs in Phase 1.

## BMAD Persona File Paths

Always load the actual persona file before adopting a role. Never improvise from memory.

| Persona | Role | File Path |
|---------|------|-----------|
| Mary | Business Analyst | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/analyst.md` |
| Leo | Spec Coach | `~/Developer/supervisr-ai/project-management/_bmad/bmm/agents/spec-coach.md` |
| Winston | Architect | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/architect.md` |
| Amelia | Developer | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/dev.md` |
| Quinn | QA Engineer | `~/Developer/gabriel-amyot/projects/ai-software-development/dark-software-factory/_bmad/bmm/agents/qa.md` |

## Delegation Matrix

Each SBE maps to one or more agents based on its fix_scope:

| fix_scope | Primary Agent | Secondary | Review |
|-----------|--------------|-----------|--------|
| FRONTEND_ONLY | Amelia | — | Quinn |
| FULL_STACK | Amelia | Winston (arch review) | Quinn |
| DATA_ONLY | Amelia | Winston (if schema change) | Quinn |
| CONFIG | Amelia | — | Quinn |

## Step 5: Requirement Diff — Detailed Protocol

1. **Fetch epic children** from Jira:
   ```
   /jira list-children {EPIC-KEY} --org klever
   ```

2. **For each child ticket**, fetch full details including description and ACs:
   ```
   /jira get {TICKET-KEY} --org klever
   ```

3. **Build the AC index** — a flat list of all existing ACs across all tickets, with ticket key attribution.

4. **For each confirmed SBE**, run a semantic match against the AC index:
   - **Exact match:** The SBE's Given/When/Then maps 1:1 to an existing AC. Action: skip, note as covered.
   - **Partial match:** The SBE covers a behavior that's partially specified in an existing AC. Action: draft an AC amendment that adds the missing specificity.
   - **No match:** The SBE describes behavior not covered anywhere. Action: queue for new ticket creation.
   - **Conflict:** The SBE contradicts an existing AC. Action: STOP. Surface to user. Conflicts are never resolved autonomously.

5. **Write the diff report** with three sections: COVERED, GAPS, NEW, CONFLICTS.

## Step 6: Ticket Operations — Detailed Protocol

### Updating Existing Tickets

For each GAP identified in Step 5:

1. Draft the Jira comment as Gabriel (no `[automated]`/persona header, fewest words):
   ```
   AC gap on {SBE title}, from the {date} feedback review.

   *Current AC:* {what the existing AC says}
   *Missing:* {what's missing}

   *Proposed addition:*
   {Given/When/Then in Jira wiki markup}
   ```

2. Post via `/post-comment` — never raw API.

### Creating New Tickets

For each NEW requirement:

1. Group related SBEs if they share the same component and fix scope.
2. Invoke `/create-tickets` with:
   - Parent epic: the epic key from input
   - Type: story (or bug if category is BUG)
   - Summary: derived from SBE title
   - Description: Given/When/Then ACs, scope section, definitions
   - Leo review: enabled

3. After Jira creation, scaffold locally via `/ticket-init`.

## Step 7: Implementation Delegation — Detailed Protocol

### Dispatching Amelia

For each ticket (new or updated), dispatch Amelia as a subagent:

**Subagent prompt template:**
```
You are Amelia, the BMAD Developer persona. Load your persona from:
{amelia_persona_path}

Your task: implement the following SBE for ticket {TICKET-KEY}.

SBE:
{confirmed SBE content}

Code trace:
{file, lines, component, fix_scope, notes}

Frontend repo: {frontend_repo_path}
Backend repo: {backend_repo_path or "N/A"}

Instructions:
1. Read the implicated files
2. Implement the minimal change that satisfies the SBE
3. Write unit tests for any logic changes
4. Do NOT refactor surrounding code
5. Do NOT add features beyond the SBE scope
6. Commit with message: "{TICKET-KEY}: {SBE title}"

Report back: files changed, tests added, any blockers.
```

Use `model: "sonnet"` for Amelia subagents (mechanical work, delegate to Sonnet per feedback).

### Dispatching Winston (Architecture Review)

Only when fix_scope is FULL_STACK or the change introduces a new pattern:

**Subagent prompt template:**
```
You are Winston, the BMAD Architect persona. Load your persona from:
{winston_persona_path}

Review the following implementation plan for architectural concerns:

SBE: {confirmed SBE}
Proposed changes: {files and approach from Amelia's plan}
Fix scope: FULL_STACK

Questions to answer:
1. Does this change respect existing service boundaries?
2. Does it introduce a pattern that should be documented as an ADR?
3. Are there ripple effects on other components?
4. Is the approach the simplest that satisfies the SBE?

Report: APPROVED, APPROVED_WITH_NOTES, or NEEDS_REDESIGN (with specific alternative).
```

### Dispatching Quinn (Test Validation)

After Amelia's implementation:

**Subagent prompt template:**
```
You are Quinn, the BMAD QA persona. Load your persona from:
{quinn_persona_path}

Validate test coverage for ticket {TICKET-KEY}.

Confirmed SBEs:
{list of SBEs for this ticket}

Implementation:
{files changed by Amelia}

Tests added:
{test files from Amelia}

Validate:
1. Every THEN clause in each SBE has at least one assertion
2. Edge cases identified by Leo are covered
3. No existing tests are broken
4. Playwright E2E tests exist for visual/interaction SBEs

If gaps exist, write the missing tests. Use /klever-test for Playwright execution.

Report: test count by type, coverage assessment, any gaps remaining.
```

## Step 8: Adversarial Review

Invoke `/challenge` with the full context:
- Confirmed SBEs (the spec)
- Code changes (the implementation)
- Test results (the evidence)

The adversarial review checks:
1. **Spec fidelity:** Every SBE has a corresponding code change
2. **Scope creep:** No code change exceeds what the SBE specified
3. **Regression risk:** No existing behavior is altered without an SBE justifying it
4. **Test validity:** Tests actually assert the SBE's THEN clauses (not just "runs without error")

## Step 9: Test Suite Update

Test layer requirements by SBE category:

| Category | Unit | Integration | Playwright E2E |
|----------|------|-------------|----------------|
| BUG | Yes | If data flow | Yes |
| UX | Rare | No | Yes |
| LAYOUT | No | No | Yes (screenshot comparison) |
| DATA | Yes | Yes | Optional |
| PERFORMANCE | Yes (benchmark) | No | Optional |
| MISSING_FEATURE | Yes | If cross-boundary | Yes |

## Execution Order

The autonomous phase runs in strict order:

```
Step 5 (Diff) → Step 6 (Tickets) → Step 7 (Implement) → Step 8 (Review) → Step 9 (Tests) → Step 10 (Report)
```

Steps 7-9 can be parallelized per ticket when tickets are independent (no shared components). When tickets share components, execute sequentially to avoid merge conflicts.

## Error Handling

| Error | Action |
|-------|--------|
| Jira API failure | Retry once. If still fails, save draft locally and note in report. |
| Code trace finds deleted file | Re-trace from the component name. If component was moved, update the trace. |
| Amelia's implementation breaks existing tests | Stop. Run Dexter (debugger) to diagnose. Surface to user if pre-existing. |
| Quinn finds untestable SBE | Flag in report. The SBE may need refinement (loop back to Phase 1 for that SBE only). |
| Adversarial review finds spec violation | Revert the offending change. Re-dispatch Amelia with the adversarial finding as additional context. |
