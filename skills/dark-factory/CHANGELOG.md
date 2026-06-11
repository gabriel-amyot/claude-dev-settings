# Dark Factory v2 — Changelog

Every SKILL.md / workflow.js / contract change bumps the version and adds an entry.

## 0.9.1 (2026-06-10)

**Concierge-only / dry-run mode — run the front gate across a whole sprint to review tickets, with zero
risk of trickling into design or any code work.**

For a Sprint 6 review pass that runs the concierge on every ticket and stops. `args.concierge_only: true`
(alias `dry_run: true`): immediately after the concierge phase records, the workflow returns a uniform
`CONCIERGE_ONLY_COMPLETE` carrying the full findings (spec_quality, needs_human, ac_count, `acs`
[visual/logic + fixture], repos, tool_belt, prereqs_ok, open_questions, summary) — as DATA, not as an
`AWAITING_HUMAN` pause. The return sits BEFORE the spec-quality / needs-human / belt early-returns, so a
review gets one consistent shape per ticket regardless of verdict, and the run can never reach design.
Retro is skipped for this state (a review pass is not scored). Additive + arg-gated: default runs are
byte-identical. (workflow.js + SKILL.md.)

## 0.9.0 (2026-06-09)

**Visual-AC gate — stop discovering at QA that rendered-UI ACs can't be auto-verified; gate on it up
front, and ship code-complete UI tickets to a render step instead of a surprise HALT.**

The 0.8.0 TDD gate ran clean in production (KTP-759/788, `trustworthy: true`), but those runs — and
KTP-728/758 before them — all `HALT_PRESHIP` on the *same* root cause: a rendered-UI AC can't be visually
verified from a headless QA subagent, found only at QA after burning implement+review+QA. Reframe:
"couldn't auto-verify the UI" is not "failed" — a UI ticket with proven logic + clean build + clean review
is code-complete and needs a render/eyeball, not a blocked branch.

- **Corrected premise:** a too-pessimistic v1 spec said visual proof was "structurally impossible
  autonomously." It conflated *dev* verification (IAP + nightly-off) with *all* verification. Localhost has
  no IAP wall and the Playwright suite already drives the local stack headlessly. So local-stack rendering
  is the **primary** path; human eyeball is the fallback. The real irreducible blocker is **fixtures**
  (unseeded data, e.g. KTP-788's Canadian FSA store), not browser access.
- **`dark-factory.workflow.js`:**
  - `CONCIERGE_SCHEMA` gains per-AC `acs: [{id, ac_kind: visual|logic, fixture}]`. A `visual` AC with
    `fixture: 'missing'` is a front-gate `needs_human` (a stack can't conjure unseeded data).
  - `QA_SCHEMA.per_ac` gains `visual_pending` — a rendered-UI AC whose logic is proven and only the live
    screenshot is missing.
  - `classifyQaGap()` (`all_pass` | `visual_only` | `real_gap`) + `preShipBlockers()` now takes the gap:
    a `visual_only` gap does NOT block; a `real_gap` does. New terminal state **`NEEDS_VISUAL_VERIFY`**
    (ShipPrep still runs, branch pushed) hands the render step to the main loop with `visual_acs` + the
    `next_steps`. Concierge prompt classifies + raises the missing-fixture question up front.
- **Two-tier verification, by substrate:** skills are unreliable inside Workflow subagents (ADR-001), so
  the QA subagent proves everything *without* a browser; the **main loop** (where skills + the local stack
  work) does the render: `/klever-local-stack` → `ui-probe`/`/klever-test` against `localhost:3000` →
  promote to READY_TO_SHIP with screenshots, or fall to **`READY_FOR_VISUAL_QA`** (MR flagged for a human
  eyeball) when the stack/fixture/browser can't render. `HALT_PRESHIP` stays for real blockers only.
- **Contracts:** `1-concierge.md` (step 3b: visual/logic + fixture classification, missing-fixture
  front-gate halt), `6-qa.md` (mark `visual_pending` for proven-logic rendered-UI ACs).
- **`tests/visual-readiness.test.mjs`** — 14 cases over the real `classifyQaGap` + `preShipBlockers`
  (extracted verbatim), mutation-checked (dropping the `visual_pending` requirement lets a real FAIL slip
  into `visual_only`, caught).
- **Deferred (in the spec):** typecheck-noise split, deferred-hardening capture for dropped LOW/MEDIUM
  findings, AC-vs-implementation mechanism-drift gate, an auto-seed fixture library.

## 0.8.0 (2026-06-05)

**Promoted red-green-refactor from prose into an un-skippable, artifact-backed gate — the one factory
discipline that was still self-certified.**

An audit of 9 past runs (`runs/*.yaml`) found TDD adherence was *invisible and fabricable*: not one run
recorded a test written first or seen failing. The contract said "RED first"; nothing proved it. Per
ADR-001 ("gates are code, not prose"), that self-cert is exactly what the factory exists to eliminate.

- **`dark-factory.workflow.js`** (+128/−9):
  - `IMPLEMENT_SCHEMA` gains a required `ac_tdd[]` ledger — per AC: `kind`, `red{artifact,commit,failed,
    right_reason}`, `green{commit,passed,suite_green}`, `exempt`.
  - `QA_SCHEMA.per_ac` gains `red_verified` (`true|false|exempt`).
  - **`tddViolations()`** — layer-1 structural gate: every non-exempt AC needs `red.failed +
    red.right_reason + red.artifact` and `green.passed`; every `done` AC must carry a ledger entry (no
    dodge-by-omission). Exemptions must match `not_applicable(<why>)` / `infra_blocked(<why>)`.
  - **`tddVerifiedCap()`** — layer-2: caps a PASS AC to PARTIAL when QA could not re-verify its RED.
  - Wired into Implement (`HALT_TDD_GATE`), each Fix round (completeness off — a fix re-reports only what
    it touched), and QA's capped verdict.
  - `tdd_gate_mode` arg: `warn` (cap + telemetry, no halt) for the soft-launch trial; default `halt`.
- **Two-layer design (why):** the Workflow spine is a pure JS sandbox (no fs/git), so it can only check
  the self-reported `ac_tdd` shape. QA — a fresh agent on the branch — supplies ground truth by diffing
  the **test-only RED commit** (`git show --stat`) and re-running it to confirm it fails. The test-only
  commit is the forgery-resistance core: you cannot fake "I did TDD" without it.
- **Contracts:** `4-implement.md` (stub-then-assert RED, test-only RED commit, per-AC `tdd/AC-<N>.md`
  ledger, structured exemptions), `6-qa.md` (re-verify the RED commit → `red_verified`), `2-design.md`
  (test specs state the expected RED assertion; flag no-unit-surface ACs).
- **Belts:** `java` (stub signature → assertion failure, not compile error), `scripting` (stub fn →
  pytest assertion, not ImportError), `frontend` (extractable pure logic → Playwright pure-fn RED;
  pure-render ACs → honest `not_applicable`, proof stays the ui-probe screenshot — no fake unit tests).
- **Decisions (locked):** D1 test-only RED commit + QA re-verify · D2 strict stub-then-assert, no
  compile-error RED on any belt · D3 `infra_blocked` exempts only execution-verify, not unit RED · D4
  soft-launch one `warn` trial, then `halt`.
- **`tests/tdd-gate.test.mjs`** — first test harness in the skill: 16 cases over the real gate functions
  (extracted verbatim, not reimplemented), mutation-checked to confirm the RED check is load-bearing.

## 0.7.0 (2026-06-04)

**Racked the `frontend` belt — the factory can now run Next.js / React / TypeScript / Mapbox GL UI
tickets, not just Java services and side-effect scripts.**

A frontend deliverable (e.g. KTP-758, a Measurement Map DOOH pin layer) previously halted at the
concierge with `BLOCKED_UNSUPPORTED_FLOOR` — the crib only racked `java` and `scripting`. Per ADR-002 a
belt swaps tools only, so this is purely a new loadout, no new floor logic.

- **`toolcrib/frontend.md`**: build/tester loadout for rendered-UI work. Tooling validated against
  `grp-app/grp-frontend/app-front-portal` (Next 15 / React 19 / TS 5 / Mapbox GL / Playwright), not
  guessed. Corrections vs the originating handoff's proposed loadout: the repo ships **no jest/vitest**
  (Playwright is the only runner, so there is no component-unit socket to equip — flagged as the belt's
  weakest point); typecheck is the repo's `lint:types` script (`tsc --noEmit --skipLibCheck`), not a
  bare `tsc`; added a `:3000` auth-port note. execute-verify = `next build` + a `next dev` boot smoke
  (frontend analog of the java belt's "Started in N seconds"); proof = live AC validation with
  screenshots via `ui-probe` (preferred, reuses Gab's authed Chrome) / agent-browser / Playwright,
  code-reading is never a PASS; data-source-down → `infra_blocked(...)`, never fabricate API data.
- **`SUPPORTED_BELTS`** in `dark-factory.workflow.js` → `['java','scripting','frontend']`. This is the
  functional gate; the prose registries (`toolcrib/INDEX.md`, `SKILL.md`, `contracts/INDEX.md`,
  `docs/tooling.md`) were updated to match.
- **Each tool in the belt carries a "Why these tools" rationale** (the alternative it beat and why), so
  a future loadout revision edits a decision rather than re-guessing.
- **Belt-tuning telemetry proposal**: the belt documents a `belt_tools` block (per-tool ran / outcome /
  caused_deduction / evidence) as a proposed addition to the Retro contract (`9-retro`), plus the three
  questions an aggregated rollup should answer (which tool drives deductions; how often the missing unit
  socket is skipped; recurring `infra_blocked` dependencies). Not yet wired into contract 9 — the belt
  is the motivating case; capturing it structurally at Retro time is the next-upgrade hook.
- `node --check dark-factory.workflow.js` clean. SKILL.md version → 0.7.0.

## 0.6.0 (2026-06-03)

**Bounded fix loop — per-AC resilience harvested from v1 + sprint-crawl.**

Before: a review CRITICAL terminated the run (`BLOCKED_REVIEW_CRITICAL`) on the first pass. Now the
workflow bounces back to a targeted fix and re-reviews, up to 2 rounds, before halting. This brings v2
in line with v1's "Quinn attacks → Amelia fixes" loop and sprint-crawl's review→implement revert,
without breaking the segregated-review or ADR-002 spine boundaries.

- New `Fix` phase in the workflow + meta: on `review.criticals_open > 0`, dispatch a fix agent
  (`readContract('4-implement')` in FIX MODE) scoped to ONLY the open CRITICAL findings — no new scope,
  no unrelated refactors — in its own worktree; it fixes, re-runs affected tests, and pushes the branch.
  A fresh segregated reviewer then re-reviews the updated branch.
- Bounded at `MAX_FIX_ROUNDS = 2`. A CRITICAL that survives both rounds still returns
  `BLOCKED_REVIEW_CRITICAL` (now carrying `fix_rounds`). A round that fails to push returns the new
  `HALT_FIX_NOT_PUSHED`.
- Review prompt factored into a reused `reviewPrompt` const (identical fresh reviewer each round; the
  branch differs because the fix pushed). `node --check` clean.
- Design context: harvested from the sprint-crawl analysis (`docs/harvest-from-sprint-crawl.md`). The
  full per-AC restructure (iterate implement→review→QA per AC with persisted per-AC verdicts) remains a
  roadmap item; this is the spine-safe increment.

## 0.5.0 (2026-06-03)

**Hardened from the first live trial (KTP-728 + KTP-699 retros). Front gate's relationship to truth is
the headline — see `docs/hardening-spec-0.5.0.md` and ADR-003.**

The trial proved the JS gates work (`HALT_PRESHIP`, `BLOCKED_SPEC_QUALITY` both fired correctly). The
dominant cost was upstream: a concierge **false data-layer blocker** from a stale local checkout (two
abandoned runs) — a reasoning/staleness failure the substrate cannot catch. 0.5.0 fixes that, and
promotes two patterns flagged in BOTH retros (schema preflight; structured findings). Built blind —
generic rules only, no KTP-728/699 specifics in the spine or shared contracts (ADR-002 boundary holds).

- **Concierge live-verifies every data-layer claim (ADR-003)** [contract 1]: any blocker asserting a
  table/view/column/count/serving-path is verified live (`bq show --schema`/`bq ls`/`bq query`;
  `git show origin/dev:<path>`) before it is emitted; a stale local tree is not evidence. Every blocker
  carries a one-line assumption audit. No live access → mark `unverified` + flag, never assert.
- **Live-schema preflight** [contract 1 writes → contract 2 reads]: concierge pins exact column
  count + names into `analyst/assumptions.json` marked `VERIFIED`; design reads those rather than
  re-deriving from a checkout. Kills the F4 "no COUNTRY column" / "22-vs-20 columns" errors.
- **New brand ⇒ new advertiser id** [contract 1]: a fabricated/new brand must not reuse an existing
  demo-advertiser entity; the id must be unused in BOTH the perf tables AND the demo-agency registry.
- **Backend-gated sub-ACs flagged/split at the gate** [contract 1]: a sub-criterion depending on
  un-landed backend work is named as deferred (or the AC is split) at the concierge, not discovered at
  HALT_PRESHIP.
- **Structured artifacts on disk** [contracts 5 + 6]: review writes `review/findings.json` on every run
  (even at `criticals:0`); QA writes `qa/result.yaml` with a real `test_ref` (command + output path).
  A PARTIAL is now auditable without re-deriving from a raw diff.
- **Resume path fixed** [workflow.js + SKILL.md]: on `resumeFromRunId` with `humanDecisions`, the
  decisions are folded into the concierge prompt — busting the resume cache so the concierge **re-runs
  live** and re-reads the ticket, instead of replaying its stale needs_human verdict.
  `BLOCKED_NEEDS_HUMAN_AGAIN` now means a genuinely new/unanswered blocker remains.
- **Bucketed ticket-folder guard** [contract 1]: `ticket_folder` must resolve under
  `<PM_ROOT>/tickets/<PREFIX>/<EPIC-or-no-epic>/<TICKET>/` and never the PM root; stop and fix if it
  would land at root or a non-`tickets/` child.
- SKILL.md version → 0.5.0; references ADR-003 + the hardening spec. `node --check` clean.

## 0.4.1 (2026-06-02)

**Stack-agnostic hardening — no Java or ticket specifics in the factory itself.**

- Removed all Java/Spring/Maven specifics from the spine (concierge prompt) and the shared contracts
  (1 concierge, 2 design, 6 QA, 7 ship, 8 validate, 9 retro). They now defer to the run's tool belt.
  Java build/test/execute tooling lives only in `toolcrib/java.md` (multi-module Maven note moved there).
- Concierge now **discovers** belts by reading the new `toolcrib/INDEX.md` + each belt's `detect` rule,
  instead of the spine naming/​describing belts.
- Removed every KTP-728 mention from the operational files (spine, contracts, toolcrib, SKILL, CHANGELOG).
  Only `docs/` (the design archive that documents the build-blind rule) retains historical references.
- Belt ids (`java`, `scripting`) remain named in the registry/catalog — that's the rack's contents, not
  stack logic in a shared room.

## 0.4.0 (2026-06-02)

**Multi-work-type via tool belts (ADR-002). Scripting floor added so the factory can run side-effect
script tickets, not just Java services.**

Triggered by the first live trial (a scripting ticket): it halted honestly at the concierge
because validation was hardwired to `mvn spring-boot:run`. That halt = the anti-fake design working.

- ADR-002: one **blueprint** (the spine) + swappable **tool belts** from a **tool crib**, NOT
  duplicated floors. Corrected vocabulary against the Minions source (blueprint = the state machine;
  tool crib = curated tools per task). Concierge stays; dispatcher + spec/architect-persona loop
  parked to the refining phase (`docs/second-floor-refining-notes.md`).
- `toolcrib/java.md` + `toolcrib/scripting.md`: per-work-type build/tester loadouts.
- Concierge (contract 1 + schema) classifies the work-type and returns `tool_belt`; workflow halts
  `BLOCKED_UNSUPPORTED_FLOOR` when no belt is racked (then rack one + confirm with human).
- Implement (contract 4) + QA (contract 6) rewritten belt-aware: they read the run's tool belt for
  compile/execute-verify/proof instead of assuming Java/Maven. Generalized proof of work =
  "run the deliverable on declared inputs, assert the declared expected output."
- Ship-prep (contract 7) honors the belt's `has_version_file` (skips version bump for repos without
  one). Workflow `readContract` injects the belt path into every phase prompt.
- SKILL.md updated (no longer "backend/Java only"). Syntax verified.

## 0.3.0 (2026-06-02)

**Instrumentation migrated from v1: per-phase confidence + a Retro auto-improve phase.**

- Every phase now returns soft `confidence` (0-100) + `confidence_deductions` (signal, not a gate),
  injected via a shared blurb appended to every phase prompt. Schemas allow the fields.
- New final **Retro** phase (`contracts/9-retro.md`): runs on every terminal outcome (success or
  halt), scores the run twice /100 (task_confidence + factory_fitness) with every lost point
  accounted for, lists red flags, proposes concrete next-run improvements, and writes telemetry to
  `runs/` plus a next-run improvement handoff. AWAITING_HUMAN pauses skip Retro (they resume).
- Pipeline refactored into `runPipeline()` + a `trace` of per-phase status/confidence fed to Retro.
- Added `runs/` directory. Bumped to 0.3.0.

## 0.2.0 (2026-06-02)

**Adversarial-cascade + prompt-specialist fixes; back-half restructure from verified Workflow API.**

Reviews: adversarial-cascade (Quinn + Codex-framed) and an independent prompt-engineering specialist.
API behavior verified via claude-code-guide. Full triage in `docs/review-findings-v0.1.0.md`.

Code (workflow.js):
- Null-guard every `agent()` return (skip → `HALT_AGENT_SKIPPED`).
- Enforce `status:'stuck'` halts for design, grill, implement, ship-prep (previously swallowed).
- Add missing `phase('Design')`.
- `capQaVerdict`: canonicalize `execution_verified` to string, drop dead boolean check, warn on
  unrecognised values. Add `evidenceCappedOverall` (a PASS AC with no code_ref+test_ref caps to PARTIAL).
- `preShipBlockers`: execution gate now explicitly rejects `infra_blocked`/`false`/missing, and
  requires the branch to have been pushed.
- Resume loop guard: `BLOCKED_NEEDS_HUMAN_AGAIN` instead of re-looping the concierge.
- Schema tightening: required `repos`, `ticket_folder`, `summary` (concierge); `minimum:0` on
  `criticals_open`/`ac_count`; `minLength:1` on `branch`; pattern on `execution_verified`; `notes` added
  to PHASE_SCHEMA.
- Remove unused `ticketFolder` arg; concierge now RESOLVES and returns `ticket_folder`; absolute
  contracts path (no `~`).

Structure (from verified API limits):
- Skills not callable inside a workflow agent → **Ship is code-prep only**; MR + Jira + transition move
  to the main loop. New terminal state `READY_TO_SHIP`.
- Sibling agents can't see each other's worktree → **Implement pushes the feature branch**; Review/QA/
  Ship-prep run with `isolation:'worktree'` and fetch+checkout it; Implement also writes a diff artifact.
- Single worktree owner: removed `git worktree add` from contract 4 (runtime owns it).
- No native wait → **Validate removed from the auto-run**; main loop runs it post-merge.

Contracts: all 8 updated — concierge returns `ticket_folder` + example open_question; design/grill add
reason-before-file + artifact paths; implement pushes branch + writes diff + dependent-AC stuck;
review defines `demonstrated` + severity rubric + fetch/checkout; qa adds Inputs + example row +
evidence rule; ship-prep is prep-only; validate is a post-merge main-loop step.

## 0.1.0 (2026-06-01)

Initial seed build: workflow spine + 8 backend-floor contracts + SKILL.md. Never run.
