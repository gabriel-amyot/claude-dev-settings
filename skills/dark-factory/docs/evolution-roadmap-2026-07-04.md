# Dark Factory — Evolution Roadmap (panel synthesis, 2026-07-04)

**Status:** APPROVED by Gab 2026-07-05, with amendments:
1. Roadmap accepted ("i like it").
2. **Phase 3 (headless) pulled forward and BUILT** (0.9.4, 2026-07-05). Gab also asked for an
   autopilot-design explainer with mermaid via crit (delivered same session).
3. **Phase 1 validation ticket CHANGED: NOT KTP-853.** Proxi is Hermes — a different thing, intra-work
   + AI-agent themed but a one-off, not the repeating python-service shape. Validation is instead a
   **retro-run of the ai-insight-blurbs work (KTP-821 producer)**: the harness branches from the
   pre-implementation commit and re-builds it through the python belt, then diffs against what
   actually shipped. HARD CONSTRAINT from Gab: **never touch the grp-cfg/* repos** (single `main`
   branch, unacceptable blast radius) — the eval scopes to the app repo only.

## Phase 1 validation mechanics (retro-run / time-travel eval — design note)

- Pin `baseline_ref` = the parent commit of the first KTP-821 implementation commit on the target app
  repo. Implement builds in a worktree branched from that SHA; review/QA diff against `baseline_ref`,
  not the dev tip.
- Push only a clearly-named throwaway eval branch (`KTP-821-factory-eval-<date>`) — feature branches
  do not auto-deploy; delete it after scoring. **No MR, no Jira post, no CFG/DAC repo writes.**
- Honest caveat (contamination): ADR-003 live-verify and the brownfield check look at the CURRENT
  world (the BQ table now exists; dev tip contains the shipped implementation). Eval mode must remap
  "origin/dev" to `baseline_ref` in the concierge/grill/review prompts, and some live-data asymmetry
  is unavoidable — acceptable for an eval, must be listed in the score's deductions.
- Scoring: diff the factory's output vs the shipped implementation (structure, tests, the tracer-bullet
  entry point Sisi's generator drops behind) + the standard run telemetry. This doubles as the
  factory's FIRST run-level e2e eval.
**Inputs:** `month-learnings-2026-07-04.md` (Stage-3 findings) + three panel position papers
(Winston/architecture, PO/value, PM/roadmap) produced in the 2026-07-04 self-evolve session.
**Already shipped in that session:** the 0.9.3 self-evolve pass (see CHANGELOG).

## Panel verdicts (where they agreed)

1. **Python/CrewAI belt is the #1 build.** Three deploy tickets of identical shape waited all
   month (KTP-688 / KTP-735 / KTP-853). It is a BELT under ADR-002 (tools only), so cheap.
2. **Full-stack fan-out (0.10.0) is parked.** Detection shipped; execution is the quarter's
   shiny object. Hand-splitting works. Winston adds a hard constraint: fan-out must not ship
   before the integrity gate (it widens exactly the cross-repo blast radius the gate closes).
3. **BQ/SQL/Dataform is a FLOOR, not a belt** (ADR-002's own boundary example). Highest
   per-room cost. Parked behind everything; do not smuggle it in as a belt.
4. **Eval work is folded, not standalone.** Two load-bearing fixtures first: the KTP-677
   integrity fixture (a re-run must BLOCK) and the KTP-870 behavioral-parity template (≥90%
   vs reference set). The FeatureBench-style benchmark waits until those exist. Cost
   telemetry (prediction #3, never measured) co-delivers with the integrity phase.
5. **R6 lights-out autonomy stays cut.** No containment/governance infra. Ceiling remains
   human at the bookends; headless mode buys a clean gate-EXIT, never auto-merge.

## Panel disagreements (chaired resolution)

- **Where headless sits.** PO: #2 (the multiplier). PM: Phase 4 (needs work to run). Winston:
  parallel anytime (depends on nothing). RESOLUTION: schedule as Phase 3 but explicitly
  parallelizable, and hard-gated on Gab approving the autopilot design (he has not, yet).
- **Integrity gate priority.** PO ranks it 5th on frequency; PM makes it Phase 2 on severity.
  RESOLUTION: Phase 2. It is the only KTP-677-class guard, its architecture is already LOCKED,
  and Winston's sequencing rule (gate before fan-out) makes it a prerequisite for later scale.

## Architecture classifications (Winston, adopted)

| Candidate | Kind | Key design decision |
|---|---|---|
| Python/CrewAI | **Belt** (`python-crewai`) + a new behavioral proof lane | C1: concierge classifies ACs `behavioral` (like `visual`); tester proof = reference-set parity + LLM judge with threshold, kept SEPARATE from the deterministic TDD RED lane. Never force behavioral tests into RED commits. |
| Cloud validation | **Room** + main-loop split | C2: subagent phase emits a validation PLAN + deploy-identity verdict with per-code-ref `[VERIFIED against dev@sha]`/`[UNVERIFIED]` stamps; new terminal `NEEDS_CLOUD_VALIDATE` hands the live drive (gcloud/ui-probe/auth) to the main loop, mirroring `NEEDS_VISUAL_VERIFY`. |
| System-integrity gate | **Room** (Thread A) | Per locked design: Integrity phase + JS verdict + main-loop git backstop; build the room as Thread B's future home (findings schema extensible to behavioral/additive types; agent-OS check advisory-dormant). |
| Headless / gate-as-handoff | **Interface** (thin spine change) | `headless: true` arg converts AWAITING_HUMAN into a clean `GATE_WRITTEN`-style exit + `type: gate` handoff + decision_file; re-entry reads answered decisions; no AskUserQuestion downstream. Protocol already designed in ADR-004 v2.2. |
| Full-stack fan-out | **Composition** (main-loop + parallel()) | C3: each fan-out agent self-manages a worktree in its TARGET repo; `isolation:'worktree'` is a backstop only (spike-proven insufficient). PARKED. |
| BQ/SQL/Dataform | **Floor** (R4) | PARKED behind Phase 4. |
| Eval harness | **Meta** (measurement) | Folded: two fixtures + cost telemetry. |

## The roadmap (solo, ~15% capacity; fewer phases finished fully)

| Phase | What | Entry | Exit / validation | Value |
|---|---|---|---|---|
| **0 (done)** | 0.9.3 self-evolve: observability → code gates | — | node --check + 34 eval cases green | Retro loop closes fully |
| **1** | `python-crewai` belt (service leg) + behavioral AC lane spec + KTP-870 parity fixture | A live deploy ticket available | **Retro-run of ai-insight-blurbs (KTP-821 producer) from its pre-implementation commit reaches READY_TO_SHIP through the belt** (see mechanics above; CFG repos excluded); belt_tools telemetry recorded | Unblocks the agent-service queue; widest coverage gain per effort; doubles as the first run-level e2e eval |
| **2** | Integrity gate: design session closes Q4–Q13 → build room + KTP-677 executable fixture + cost telemetry | Design session held; fixture captured | **Re-run of KTP-677 BLOCKS** (the fixture is a living eval) | Closes the only incident class every gate missed |
| **3** | Headless / gate-as-handoff interface — **BUILT 2026-07-05 (0.9.4)**, approved by Gab | ~~approval~~ given | One headless run parks at a gate, exits clean, resumes idempotently from decision_file (**live validation still owed**) | Cuts attended minutes/ticket; the multiplier |
| **4** | Cloud-validation room (read-only diagnosis + NEEDS_CLOUD_VALIDATE) | Phase 1 shipped (needs deployed services to validate); PO quality bar wired | **Factory validates the ai-insight-blurbs loop end-to-end in dev** with stamped code-refs, zero manual pass | Absorbs the biggest manual toil; retires the KTP-688 incident class |
| Parked | Full-stack fan-out (after gate), BQ floor, FeatureBench, R6 | — | — | Do-nothing cost logged in PM paper |

**Dependency notes:** Phases 1 and 2 are independent (belt vs room) — a slip in one is absorbed by
pulling the other forward. Phase 4 hard-depends on Phase 1. Phase 3 depends only on approval.

## PO trust bar for Phase 4 (non-negotiable)

Cloud validation is the one evolution that, built badly, ends delegation (it makes outward claims
about deployed systems — the KTP-688 burn). Before it ships: deploy-identity probe is the mandatory
first step; confidence is an OUTPUT of the probe (HIGH only on VERIFIED); every escaping code-ref
carries its stamp; no external post without real proof. If the bar can't be met, it ships as an
internal evidence-gatherer with a human posting.

## North-star fit

Phase 2 builds the Integrity room that R9 (spec-integrity engine) grows into — seam kept open.
Phases 1/4 widen work-kinds and evidence reach. Phase 3 moves toward "runs longer without Gab"
without touching the autonomy ceiling. Nothing here violates ADR-001/002/003.
