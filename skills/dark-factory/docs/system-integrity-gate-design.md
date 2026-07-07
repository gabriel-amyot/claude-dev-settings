# Dark Factory — System-Integrity / AC-Regression Gate (design, grill in progress)

**Status:** design in progress (grill-with-docs session, 2026-06-15). Core architecture LOCKED;
placement + scan mechanics OPEN. A formal **ADR-004** will be written once the design tree resolves.
**Owner decision-maker:** Gab. **Drives:** backlog item-0 in
`project-management/sessions/active/prompts/2026-06-12-dark-factory-improvement-backlog.md`;
origin spec `…/dark-factory-system-integrity-gate.md`.

---

## Motivating incident (the canonical acceptance fixture)

KTP-677 ("remove dead feature code", AC-4) swept `ProximityTableConfig.getSummaryPerformanceTable()`
as dead code. **Every existing factory gate passed it green** (grill, AC review, TDD ledger, QA suite
GREEN 459 tests, Spring context clean-start). It would have shipped. It was **not** dead:

- `POST /reports/summary/performance` is live and **frontend-consumed** (`app-front-portal`
  `app/api/map/reports/[reportType]/route.ts` maps `summary-performance`).
- `SummaryPerformanceBigQueryAdapter:45` reads `getZipPerformanceTable()` — a **latent bug** (wrong
  accessor) — so `getSummaryPerformanceTable()` has **zero callers at dev HEAD** → a naive "who calls
  this?" returns 0 → it *looks* dead.
- **KTP-678** (in flight) is the ticket that repoints the adapter back to `getSummaryPerformanceTable()`.
  Another in-flight ticket was actively reviving the "dead" symbol.

Milder second instance, same run: KTP-677 AC-2 deletes a subset of `/geography/*` that **KTP-725**
(further along) deletes wholesale → overlap, not contradiction.

## The invariant the factory is missing

Every existing gate answers *"does this change satisfy THIS ticket's ACs?"* None answers *"is the
surrounding system still coherent — does this change break **previously-accepted** behavior?"*
High-level intent (Gab): **the system keeps working as-is.** A ticket's change must not break prior
ACs, documented capabilities, or live consumers.

## Scope boundary — this is THREAD A (build now)

This gate is the **structural** half: *"does removing/changing this symbol break an existing
consumer?"* (code-level: grep consumers + scan in-flight branches). It catches the KTP-677 *structural*
case and is buildable now because it needs no system spec. It deliberately **does NOT** cover:
- **`additive` spec evolution** — adding a capability is structurally safe, but it changes the system
  spec (must be recorded intentionally).
- **behavioral regression** — same signature, different result (e.g. KTP-677's adapter silently
  reading the wrong table). Structurally invisible.

Both belong to **Thread B — the spec-integrity engine** (`spec-integrity-engine-northstar.md`,
roadmap R9), a separate, prerequisite-gated design. Thread A builds the **Integrity room** that
Thread B later grows into; build A leaving that seam clean.

## Terminology (sharpened in the grill)

- **Blast radius** — everything that depends on a symbol/surface a change deletes or alters:
  cross-repo consumers, in-flight branches, documented specs.
- **Destructive premise** — the ticket's *intent* is to remove/change something load-bearing.
  Knowable **pre-code** from the ticket/plan. KTP-677 was this class.
- **Destructive implementation** — the premise is fine, but the actual *diff* breaks something.
  Knowable only **post-code** from the diff.
- **In-flight collision** — another open (unmerged) branch/ticket adds or uses the symbol this change
  removes (KTP-678).
- **"Looks-unused-is-latent-bug"** — a symbol reads as dead (0 callers) only because a bug elsewhere
  calls the wrong thing; a sibling ticket fixing that bug revives it.

---

## LOCKED decisions

- **D1 — Both gates, shared scanner, START first.** A **START** pre-flight (pre-code, fail-fast on a
  destructive premise) AND an **END** gate (post-build, fail-closed, diff-based). One shared
  blast-radius scanner, two call sites. START is implemented first (Gab).
- **D2 — Intent.** The gate enforces *"current change must not break previously-accepted behavior /
  the system keeps working as-is"* — explicitly broader than the ticket's own ACs.
- **D3 — Shape (Q1).** Built as the **three-layer pattern** the factory already uses, NOT a pure-spine
  gate (the spine is a pure JS sandbox — no fs, no git — so it cannot grep repos or run git):
  1. a new **agent phase** (`Integrity`) runs the real blast-radius scan and returns a structured
     verdict (`PASS | BLOCK | WARN`) + `findings[]` (symbol → dependent → evidence);
  2. a thin **JS verdict-check** in the spine halts on `BLOCK` → new terminal state
     **`BLOCKED_SYSTEM_INTEGRITY`**;
  3. a **main-loop deterministic git/grep backstop** re-runs it for real before the MR opens
     (mirrors `tdd_red_audit`) — the one non-LLM confirmation.
  Inherits the existing anti-fabrication property (separate agent + real-git backstop).
- **D4 — END placement.** A new dedicated **`Integrity` phase after QA, before ShipPrep**: its own
  fresh agent in its own worktree (like Review/QA), fetches the pushed branch, scans the *real diff*.
  Fail-closed → `BLOCKED_SYSTEM_INTEGRITY`. *(locked, open to final confirm during build)*
- **D5 — START placement (Q2 → a).** The **Concierge** sets a coarse per-AC flag (`touches/deletes a
  public surface: yes/no`); the real blast-radius **scan runs in the Grill** (it already interrogates
  the plan against the codebase with git, and it is still pre-code). A live consumer / in-flight
  reviver found at Grill halts before any code is written.
- **D6 — AC risk classification (Q2.5/Q3 → resolved).** The Concierge sets a per-AC enum
  `surface_impact: none | additive | signature_change | deletion`. **`deletion` + `signature_change`
  = high-risk → the Grill scans them.** `additive` + `none` = **skip the structural scan** (safe for
  *structural* breakage — adding a symbol/endpoint/field breaks no existing consumer). **Conservative
  default:** undeterminable → high-risk (over-scan beats missing a destructive premise). **No
  concierge-side target list** — the Grill resolves the exact symbols/paths to scan from the *plan*
  (keeps the concierge simple; dropped the earlier `surface_targets` companion as needless density).
  NOTE: `additive` being "safe" here is ONLY about structural breakage; an additive change still
  *evolves the system spec* — that, and behavioral regression, are **Thread B** (see Scope boundary).

## OPEN decisions (remaining grill tree)
- **Q3 — RESOLVED → D6.** Per-AC `surface_impact` enum; deletion/signature_change scan, additive/none
  skip, conservative default; no concierge-side target list (Grill resolves from the plan).
- **Q4** — the **surface set** to scan: public/exported methods, HTTP endpoint paths, response DTO
  fields, BQ table/column refs?
- **Q5** — in-flight branch scan mechanics: `git branch -r --no-merged origin/dev` + grep each for the
  symbol; which branches in scope; `git merge-tree` for conflicts?
- **Q6** — cross-repo consumer scan scope: which sibling repos (`app-front-portal`, chatbot/agent-hub,
  `app-proximity-explorer`); fixed config vs derived manifest?
- **Q7** — the "looks-unused-is-latent-bug" check: heuristic flag + escalate vs attempt auto-detect.
- **Q8** — agent-OS / spec-fidelity (**Gap 2**): code-level scans are PRIMARY/blocking now; agent-OS
  spec check is **advisory** until the `app-proximity-report` agent-OS backfill (separate work item),
  then promoted to blocking.
- **Q9** — `BLOCK` vs `WARN` semantics: in-flight + live consumer = `BLOCK`; two tickets deleting the
  same surface = `WARN` + sequence.
- **Q10** — fail-closed semantics: scan inconclusive / agent error → default `BLOCK` (require override).
- **Q11** — override mechanism: an explicit, **logged** human override (never silent), like
  `humanDecisions`.
- **Q12** — shared-scanner division: START runs on *planned* targets (ticket/plan), END on the *real
  diff*. Confirm one engine, two inputs.
- **Q13** — acceptance test: two-level — a unit test on the JS verdict function (synthetic findings,
  mirroring `tests/tdd-gate.test.mjs`) + a **live re-run of KTP-677** that MUST `BLOCK`.

## Cross-cutting idea — crit-as-default human review + standard review-doc format

Raised by Gab (2026-06-15): make the factory **open `/crit:crit` by default** whenever a phase produces
a **doc / plan / diff for human review**, with a **standard doc format** so the human-feedback surface
is consistent. Bigger than this gate (touches every human-gated phase) — tracked as its own backlog
item; first concrete instance is the integrity-gate BLOCK report (see Q11 override).

- **Where it runs:** NOT inside a workflow phase — verified constraint: skills are unreliable in-agent
  and there is no wait primitive (that is *why* human gates are handled by the MAIN LOOP via
  `AWAITING_HUMAN`). So crit runs in the **main loop**, at hand-back boundaries: `AWAITING_HUMAN`
  (concierge decision packet), the design-plan review, **`BLOCKED_SYSTEM_INTEGRITY`** (blast-radius
  report → override), `NEEDS_VISUAL_VERIFY`, and the pre-MR diff.
- **Not a blanket replacement for `AskUserQuestion`:** crit fits a markup-able **doc/plan/diff/live
  page**; discrete decisions (e.g. UM-gate yes/no) stay `AskUserQuestion`. Rule: reviewable artifact
  → crit; discrete choice → AskUserQuestion.
- **Standard review-doc format:** each human-review artifact = markdown with stable sections
  (Summary · Decisions-needed [+options] · Evidence/diff · stable anchors), so crit attaches
  predictably and the resume maps comments → answers. Aligns with the global CLAUDE.md crit rule
  (recommend crit before committing to a plan or a large diff).
- **Cautious / manual mode (Gab, 2026-06-16):** crit-on-the-design-doc is **mode-gated, not always-on.**
  For big / risky / cross-repo architecture or huge work, run the factory in a "cautious" mode where —
  after the architect (Design phase) produces the design doc AND it has been reviewed + all fixes
  applied — the design doc is routed to a **human crit review before Implement**. A new optional
  pre-code human gate, triggered by a risk classification (cross-repo, large, architecture-class), off
  by default for routine single-repo tickets. Complements the integrity START gate (both are pre-code
  catches for a destructive/architecture-breaking premise). Ties to roadmap R1 (targeted design rigor)
  + `second-floor-refining-notes.md` (architect persona in the loop).

## Acceptance fixture (canonical)

Re-running the KTP-677 branch through the gate **MUST `BLOCK`** on the `getSummaryPerformanceTable`
deletion (in-flight KTP-678 + live frontend consumer) and **`WARN`** on the `/geography/*` overlap
with KTP-725.

## Build order

START first (Gab) → END second. v1 = code-level scans (cross-repo consumer + in-flight branch);
agent-OS spec-fidelity advisory until the proximity-report agent-OS backfill (Gap 2). Regression guard
mirrors `tests/tdd-gate.test.mjs`.

## Cross-references

- Origin handoff + spec: `project-management/sessions/active/prompts/dark-factory-system-integrity-gate.md`
- Improvement backlog (item-0): `…/2026-06-12-dark-factory-improvement-backlog.md`
- Existing three-layer gate pattern: spine `tddViolations()` (layer 1) + QA `red_verified` (layer 2) +
  main-loop `tdd_red_audit` (backstop), in `dark-factory.workflow.js`.
- `docs/adr/ADR-002-blueprints-not-floors.md` (belt vs floor — informs whether deletion-handling is a
  belt tweak or new logic).
