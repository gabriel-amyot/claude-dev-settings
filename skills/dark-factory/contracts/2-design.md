# Contract 2 — Design

Produce a **tactical implementation plan**. Not architecture (settled before the factory runs). Map
each acceptance criterion to specific files, functions, and tests. Work-type-agnostic — stack
specifics (build/test commands, module scoping) come from the run's tool belt, not this contract.

Adapted from the old skill's Phase 2 (DESIGN).

## Inputs

- The absolute ticket-folder path is in your prompt. Read the concierge's outputs from
  `<ticket_folder>/analyst/` (AC list, affected repos, assumptions).
- Honor any human decisions stated in your prompt exactly.

## Steps

1. For each affected repo: read its `CLAUDE.md`, grep the code areas the ACs reference, and confirm
   the stack/tooling from the run's tool belt (`toolcrib/<belt>.md`).
   **Use the VERIFIED schema facts.** Column names, counts, and table/view existence come from the
   `VERIFIED` entries the concierge pinned into `analyst/assumptions.json` (live-schema preflight,
   ADR-003). Do NOT re-derive a column list from a local checkout or memory. If a column you need is not
   in the VERIFIED set, that is a gap to surface in `notes`, not to guess.
2. For each AC, specify: files to create/modify, functions/methods, test files + approach.
3. **Brownfield gate.** Before proposing any new route/endpoint/controller/component, search for an
   existing implementation of the same behavior. Before finalizing each AC mapping, ask yourself: *is
   there an existing function I should modify rather than a new one I should create?* Do NOT create
   parallel artifacts when modifying existing code satisfies the AC. (KTP-713 lesson.)
4. **Write test specifications** per AC (specs, not bodies — Phase 4 writes bodies):
   - Baseline test (existing behavior, backward-compat): signature + expected assertion.
   - New-behavior test: signature + **the expected RED assertion** — the specific assertion that must
     fail before the code exists (Phase 4 gates on a RED that fails for this reason, not a compile error).
   - Adversarial test: an edge case the AC does not mention (null, empty, old call signature).
   - **No-unit-surface ACs:** if an AC is pure-render with no extractable logic (e.g. "the layer renders",
     "the toggle shows/hides" on the frontend belt), say so here and mark it for `not_applicable` unit RED
     — its proof is the belt's method (live visual validation), not a unit test. Do not invent a unit spec
     just to have one.
5. **Module scoping:** if the run's tool belt defines module scoping (e.g. multi-module builds), pick
   the target module(s) from the AC file paths per the belt's guidance.

## Output

Write `<ticket_folder>/design/impl-plan.md` (NOT committed to the code repo).

## Return

- `status`: pass | partial | stuck  (use `stuck` only if the plan cannot be formed — e.g. ACs map to
  nothing buildable)
- `summary`: what the plan covers
- `artifacts`: paths written
- `notes`: anything the next phases must know
