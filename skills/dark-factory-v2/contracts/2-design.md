# Contract 2 — Design

Produce a **tactical implementation plan**. Not architecture (that is settled before the factory
runs). Map each acceptance criterion to specific files, functions, and tests. Backend/Java floor.

Adapted from the old skill's Phase 2 (DESIGN).

## Inputs

- The concierge's AC list and affected repos (from `analyst/`).
- Any human decisions passed into the run (honor them exactly).

## Steps

1. For each affected repo: read its `CLAUDE.md`, scan the code areas referenced by the ACs (grep
   for the relevant classes, endpoints, controllers, validators), confirm the stack (Java/Maven).
2. For each AC, specify:
   - Files to create or modify.
   - Functions/methods to add or change.
   - Test files and the test approach.
3. **Brownfield gate.** Before proposing any new route, endpoint, controller, or component, search
   the codebase for an existing implementation serving the same behavior. Do NOT create parallel
   artifacts when modifying existing code satisfies the AC. (KTP-713 lesson: a new page was invented
   when one already existed.)
4. **Write mandatory test specifications** for each AC — these are specs, not bodies (Phase 4 writes
   the bodies). For each AC include:
   - Baseline test (existing behavior, for backward-compat): signature + expected assertion.
   - New-behavior test: signature + expected assertion targeting the actual change.
   - Adversarial test: an edge case the AC does not mention (null, empty, old call signature).
5. **Multi-module Maven:** if `pom.xml` has `<modules>`, identify the target module(s) from the
   AC file paths and scope all `mvn` commands to those modules (`mvn compile -pl <module>`).

## Output

Write `design/impl-plan.md` to the ticket folder (NOT committed to the code repo).

## Return

- `status`: pass | partial | stuck
- `summary`: what the plan covers
- `artifacts`: paths written
- `notes`: anything the next phases must know
