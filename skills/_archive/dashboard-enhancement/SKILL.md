---
name: dashboard-enhancement
description: Turn UI/UX feedback into a structured, multi-phase implementation pipeline. Explores target components and dependencies, creates specs and ticket folders with ACs, writes ADRs for non-trivial decisions, implements tickets in dependency order using the project's design system, writes Playwright E2E tests, updates documentation, and verifies the build. Triggers on "enhance the dashboard", "fix the UX on X tab", "polish the UI", "implement this plan for the dashboard", "turn this feedback into tickets", "upgrade the X tab". Input is user feedback about a dashboard feature. Output is a fully implemented, tested, documented enhancement.
user_invocable: true
nav:
  bay: build
  when: "Turn UI/UX feedback into structured implementation pipeline with specs and tickets."
  when_not: "Backend-only changes. No UI/UX feedback to process."
  personas: [amelia]
---

# Dashboard Enhancement Pipeline

End-to-end pipeline for turning UI/UX feedback into shipped dashboard improvements. Takes raw user feedback about a Mission Control Dashboard feature and drives it through exploration, specification, architecture, implementation, testing, documentation, and verification.

**Usage:** `/dashboard-enhancement [target]`

**Examples:**
```
/dashboard-enhancement housekeeper tab     # Enhance the Housekeeper tab
/dashboard-enhancement agents panel        # Improve the Agents panel
/dashboard-enhancement graph view          # Polish the WikiGraph visualization
/dashboard-enhancement                     # Interactive: ask what to enhance
```

## Trigger Phrases

- "enhance the dashboard", "enhance the X tab"
- "fix the UX on X", "polish the UI"
- "these tooltips are raw", "the contrast is bad"
- "implement this plan for the dashboard"
- "turn this feedback into tickets"
- "upgrade the X tab", "improve the X panel"
- "I have feedback about the dashboard"
- `/dashboard-enhancement [target]`

---

## Project Paths

| Component | Path |
|-----------|------|
| Frontend root | `~/Developer/gabriel-amyot/projects/mission-control-dashboard/frontend/` |
| Components | `frontend/src/components/` |
| UI primitives | `frontend/src/components/ui/` |
| Meta tabs | `frontend/src/components/meta/` |
| Housekeeper panes | `frontend/src/components/meta/housekeeper/` |
| Backend root | `~/Developer/gabriel-amyot/projects/mission-control-dashboard/backend/` |
| Backend routers | `backend/routers/` |
| E2E tests | `frontend/e2e/` |
| Housekeeper project | `~/Developer/gabriel-amyot/projects/housekeeper/` |
| Tickets | `~/Developer/gabriel-amyot/project-management/tickets/PER/` |
| Docs | `~/Developer/gabriel-amyot/project-management/documentation/bibliotheque/` |

---

## Design System Reference

All implementations MUST use the existing design tokens and reusable components. Do not invent new color classes or bypass the component library.

### Reusable UI Components

| Component | File | Purpose |
|-----------|------|---------|
| `Tooltip` | `ui/Tooltip.jsx` | Hover tooltip (NOT native `title` attribute). Use for any explanatory hover text. |
| `Modal` | `ui/Modal.jsx` | Dialog with Escape key dismissal and backdrop click. Use for confirmations, detail views, forms. |
| `Card` | `ui/Card.jsx` | `bg-slate-deck` card wrapper. Base container for dashboard sections. |
| `WikiGraph` | `WikiGraph.jsx` | `react-force-graph-2d` visualization. Use for knowledge graph, dependency graphs, relationship views. |
| `StatusPill` | `StatusPill.jsx` | Colored status indicator. Use for lifecycle states (active, idle, error, pending). |
| `ErrorBoundary` | `ui/ErrorBoundary.jsx` | React error boundary wrapper. Wrap new panes in this. |
| `ProseContent` | `ui/ProseContent.jsx` | Markdown-rendered prose block. |

### Design Tokens

| Token | Class | Use |
|-------|-------|-----|
| Primary text | `text-chalk` or `text-signal-white` | Headings, primary labels |
| Secondary text | `text-smoke` | Descriptions, timestamps, secondary info |
| Muted text | `text-smoke/60` | Tertiary, placeholder |
| Hover background | `bg-ash/40` | Interactive row/card hover states |
| Card background | `bg-slate-deck` | Card and panel backgrounds |
| Label typography | `typo-label` | Small caps labels, section headers |
| Monospace | `typo-mono` | Code, file paths, IDs |
| Info icon | lucide `Info` at size 9-10 | Inline help indicators next to labels |

### Contrast Rules

- Never use `text-gray-400` or similar low-contrast grays on dark backgrounds. Use `text-smoke` minimum.
- Interactive elements must have visible hover state (`bg-ash/40` or equivalent).
- Status indicators use `StatusPill`, not raw colored text.
- Section labels use `typo-label` class, not raw `text-xs text-gray-500`.

---

## Phase Pipeline

Execute phases in order. Phases with independent sub-tasks can use parallel subagents.

### Phase 0: Explore

**Goal:** Understand the current state of the target feature before proposing changes.

1. **Identify the target.** Parse user feedback to determine which tab, pane, or component needs enhancement. If ambiguous, ask.

2. **Read the component tree.** Starting from the target component, read:
   - The main tab file (e.g., `HousekeeperTab.jsx`)
   - All pane files it renders (e.g., `housekeeper/DashboardPane.jsx`, `ProposalsPane.jsx`)
   - Any shared components it imports from `ui/`
   - The backend router that serves its data (e.g., `routers/housekeeper.py`)

3. **Read data sources.** Trace where the data originates:
   - Backend router endpoints and their data readers
   - Any upstream project files (e.g., housekeeper YAML configs, agent definitions)
   - Mock data or spec files if they exist

4. **Catalog current issues.** Map user feedback to specific code locations:
   - Which lines produce the raw tooltips?
   - Which components lack interactivity?
   - Where are contrast problems?
   - What functionality is missing?

5. **Identify dependency order.** Determine which fixes are prerequisites for others:
   - Foundation work (design tokens, shared helpers) comes first
   - Data model changes before UI that depends on them
   - Backend endpoints before frontend that consumes them

**Output:** A structured assessment written to `tickets/PER/{EPIC-ID}/exploration-report.md` with:
- Component tree map
- Issue-to-code mapping
- Dependency graph
- Proposed ticket decomposition

---

### Phase 1: Spec and Tickets

**Goal:** Create a structured ticket plan with acceptance criteria.

1. **Update spec/roadmap mock data** if it exists. Check:
   - `frontend/src/mock/` or `frontend/src/data/` for mock data files
   - Any `SPEC.md` or `ROADMAP.md` in the project root
   - Housekeeper project config files that define capabilities

2. **Create an epic ticket folder:**
   ```
   tickets/PER/{EPIC-ID}/
   ├── INDEX.md
   ├── STATUS_SNAPSHOT.yaml
   └── {TICKET-ID}/
       ├── INDEX.md
       └── ac.md
   ```

3. **Write acceptance criteria** for each ticket. Use Given/When/Then format:
   ```
   AC-1: Given the user hovers over a status indicator,
         When the tooltip appears,
         Then it shows a human-readable description (not raw enum values)
   ```

4. **Order tickets by dependency.** Typical ordering for dashboard enhancements:
   - UX Foundation (design tokens, shared helpers, contrast fixes)
   - Data layer (new backend endpoints, data transformations)
   - Core feature panes (the main new/improved UI components)
   - Interactivity (approve/reject workflows, CRUD operations)
   - Visualization (graph views, charts)
   - Polish (animations, loading states, empty states, final contrast pass)

**Gate:** Present the ticket plan to the user. Wait for confirmation before proceeding.

---

### Phase 2: Architecture Decisions

**Goal:** Document non-trivial architectural decisions as ADRs.

Write ADRs when the enhancement involves any of:
- New control plane patterns (e.g., agent lifecycle management via YAML)
- New data flow patterns (e.g., backend aggregating from multiple sources)
- Component decomposition strategy (e.g., splitting a monolithic tab into pane files)
- New shared abstractions (e.g., a reusable approval workflow component)

**ADR location:** `tickets/PER/{EPIC-ID}/architecture/` or the project's `docs/adr/` directory.

**ADR format:**
```markdown
# ADR-NNN: {Title}

## Status
Accepted

## Context
{Why this decision was needed}

## Decision
{What was decided}

## Consequences
{Trade-offs, what this enables, what it constrains}
```

**Skip this phase** if the enhancement is purely cosmetic (contrast fixes, tooltip text changes, label updates). Not every enhancement needs ADRs.

---

### Phase 3: Implement

**Goal:** Execute tickets in dependency order.

#### Implementation Rules

1. **One ticket at a time, in dependency order.** Do not jump ahead.

2. **Decompose into pane files.** Large tab components should be split:
   ```
   meta/housekeeper/
   ├── DashboardPane.jsx    # Summary stats, health indicators
   ├── ProposalsPane.jsx    # List + approve/reject workflow
   ├── AgentsPane.jsx       # Agent cards with detail modal
   ├── ArchitecturePane.jsx # Knowledge graph visualization
   └── helpers.js           # Shared formatting, data transforms
   ```

3. **Use existing UI components.** Before building anything custom:
   - Check if `Tooltip`, `Modal`, `Card`, `StatusPill`, `WikiGraph` already do what you need
   - Extend existing components rather than duplicating
   - Import from `../ui/` or `../../` as appropriate

4. **Backend endpoints follow existing patterns.** Read an existing router (e.g., `routers/agents.py`) to match:
   - FastAPI router structure
   - Response format conventions
   - Error handling patterns
   - Registration in `main.py`

5. **Helpers file for formatting logic.** Extract into `helpers.js`:
   - Status label mappings (enum to human-readable)
   - Tooltip content generators
   - Date/time formatting
   - Filtering and sorting logic

6. **Contrast and typography adherence.** Every new element must use design tokens from the reference table above. Run a visual check: if any text is below `text-smoke` contrast on the dark background, fix it.

7. **Interactive elements need feedback.** Every clickable element needs:
   - Hover state (minimum `bg-ash/40`)
   - Loading state for async operations
   - Error state with user-friendly message
   - Empty state when no data

#### Parallel Execution

Independent tickets can run in parallel via subagents. Typical parallelism:
- After UX Foundation is done: Proposals workflow + Agent detail can run in parallel
- After both are done: Agent management + Knowledge graph can run in parallel

When dispatching parallel work, each subagent receives:
- The ticket's AC file
- The design system reference (from this skill)
- The component tree context from Phase 0
- The specific pane file(s) they own

#### Commit Strategy

- One commit per ticket (or per AC if the ticket is large)
- Message format: `PER-{N}: {short imperative description}`
- Include the "why" in the commit body

---

### Phase 4: Test

**Goal:** Write Playwright E2E tests with mocked API routes.

1. **Read existing test files** in `frontend/e2e/` to match conventions:
   - How routes are mocked (`page.route()`)
   - How assertions are structured
   - Test naming patterns

2. **Write tests for each new pane/feature:**
   ```javascript
   test('housekeeper proposals pane shows approve/reject buttons', async ({ page }) => {
     await page.route('**/api/housekeeper/proposals', route =>
       route.fulfill({ json: mockProposals })
     );
     await page.goto('/');
     // Navigate to the target tab
     // Assert the new UI elements exist and function
   });
   ```

3. **Test categories:**
   - **Render tests:** Component mounts with mock data, correct elements visible
   - **Interaction tests:** Click approve, modal opens, confirm action
   - **Empty state tests:** No data returns empty state message
   - **Tooltip tests:** Hover shows human-readable text, not raw values
   - **Navigation tests:** Tab switching, pane switching, deep links

4. **Mock data strategy:** Define mock data objects at the top of the test file that match the backend response format. Cover edge cases: empty arrays, null fields, long strings, special characters.

---

### Phase 5: Document

**Goal:** Update project documentation with new workflows and capabilities.

1. **Bibliotheque updates.** If the enhancement adds significant new capability (e.g., agent lifecycle management, proposal approval workflow), add or update entries in:
   - `documentation/bibliotheque/` under the appropriate section
   - Follow the wiki schema (YAML frontmatter, wikilinks, aliases)

2. **Component documentation.** If new shared components were created, document their props and usage in a comment block or companion file.

3. **README updates.** If the project README references dashboard capabilities, update it to reflect new features.

4. **Housekeeper project docs.** If the enhancement changed how the housekeeper agent works or what data it exposes, update docs in the housekeeper project.

---

### Phase 6: Verify

**Goal:** Confirm the build passes and new features work.

1. **Frontend build check:**
   ```bash
   cd ~/Developer/gabriel-amyot/projects/mission-control-dashboard/frontend
   npx vite build
   ```
   Fix any import errors, missing dependencies, or build warnings.

2. **Backend import check:**
   ```bash
   cd ~/Developer/gabriel-amyot/projects/mission-control-dashboard/backend
   python -c "from routers import {new_router}; print('OK')"
   ```
   Verify new routers import cleanly and register correctly.

3. **E2E test run:**
   ```bash
   cd ~/Developer/gabriel-amyot/projects/mission-control-dashboard/frontend
   npx playwright test e2e/{test_file}.spec.js
   ```

4. **API endpoint validation** (if new backend routes were added):
   ```bash
   cd ~/Developer/gabriel-amyot/projects/mission-control-dashboard/backend
   uvicorn main:app --port 8100 &
   curl -s http://localhost:8100/api/{new_endpoint} | python -m json.tool
   ```

5. **Visual spot check.** If `agent-browser` is available, navigate to the dashboard and verify the enhanced tab renders correctly with real or mock data.

---

## Rules

1. **Always explore before proposing.** Phase 0 is not optional. Read existing code before suggesting changes.
2. **User confirms the ticket plan.** Present the full decomposition after Phase 1. Wait for "go ahead."
3. **Design system compliance.** Every new element uses the tokens and components listed in the Design System Reference. No exceptions.
4. **No native title attributes.** All tooltips use the `Tooltip` component. `title="..."` is banned.
5. **No raw enum values in UI.** Every status, type, or category value must pass through a human-readable mapping in `helpers.js`.
6. **Pane decomposition for large tabs.** Any tab with more than 150 lines of JSX must be split into pane files.
7. **Backend router registration.** New routers must be imported and included in `main.py`. Verify with an import check.
8. **Test coverage for new panes.** Every new pane gets at least one render test and one interaction test.
9. **No em-dashes.** Not in code, comments, tickets, or documentation.
10. **Dependency order is sacred.** Never implement a ticket before its prerequisites are done.

---

## Learned From

- **PER-58 to PER-65 (2026-05-04):** Housekeeper Dashboard Enhancement. 8 tickets across UX foundation, proposals workflow, agent management, knowledge graph, and polish. Key patterns: pane decomposition for HousekeeperTab, helpers.js for status mappings, Tooltip component replacing native titles, Modal for agent detail and proposal approval, WikiGraph for architecture visualization. Parallel execution of independent tickets cut wall-clock time.
