# Dark Factory — Month-of-Operations Learnings (2026-06-04 → 07-04)

**Status:** Stage-3 distillation from the 2026-07-04 self-evolve session. Sources: 17 run
telemetry yamls (06-09→06-22), ~30 session transcripts, sessions/ledger.yaml, autopilot ADR-004,
factory design docs. Feeds the Winston/PO/PM panel and the roadmap proposal. Facts below cite their
source class; anything marked HYPOTHESIS needs verification before build.

## 1. Where the factory stands (verified)

- 0.9.3 as of today (self-evolve pass applied: observability items promoted from prose to
  schema/gate — see CHANGELOG 0.9.3).
- 4 belts racked: `java`, `scripting`, `frontend`, `terraform-dac-infra` (terraform belt never yet
  exercised by a live run).
- 17 runs in the last month: 3 READY_TO_SHIP, 2 NEEDS_VISUAL_VERIFY (new escape hatch works),
  7 HALT_AGENT_SKIPPED (one transient batch fault, now diagnosable), rest honest halts.
- Predictions: #1 (gates kill compliance failures) CONFIRMED; #2 (gates cannot kill
  reasoning failures) CONFIRMED in predicted direction; #3 (cost ±20%) NEVER MEASURED.
- The retro auto-improve loop HALF-closes: mechanical improvements land within days;
  observability/audit items recur until promoted to code. Design rule going forward: **an
  improvement is applied only when it is a schema field or a JS gate.**

## 2. Work the factory could NOT take this month (the demand signal)

| Work-kind | Evidence | Today's outcome |
|---|---|---|
| Python/CrewAI agent services (BI agent KTP-688, Media Plan KTP-735, Proxi KTP-853) | 3 deploy tickets, same shape: FastAPI/Uvicorn + CrewAI pipeline + FastMCP + AG-UI SSE on COS | Never routed to factory |
| AI-agent behavioral work (hallucinated BQ tables → retry storm; fix = Literal-constrained tool args, max_iter caps) | 06-29 sessions | Hand-debugged in main loop |
| BigQuery/SQL/Dataform | SKILL when_not excludes SQL; data ACs cap PARTIAL "no BQ assertion" | Excluded |
| Full-stack tickets | 0.9.2 detects, cannot build (fan-out spec 0.10.0 unbuilt) | Split by hand |
| Cloud e2e validation (ai-insight-blurbs: Scheduler → CloudRun Fn → Vertex/Gemini → BQ partition → Java API → FE panel) | KTP-821/739; validation loop 100% manual today | Human does deploy-identity, gcloud logs, IAM checks, live turn |

## 3. Recurring manual interventions (absorption candidates)

1. Ship tail: /klever-mr, Jira evidence comments, transition, post-merge validate — every run.
2. Live UI proof via ui-probe — always deferred to a human pass.
3. Deploy-identity + IAM verification (gcloud describe, get-iam-policy) — every cloud ticket.
4. Cross-env config/secrets wiring (the DOOH prod outage was a missing prod property, masked by
   a resilience contract returning empty-200).
5. Dev nightly-down (20:00 ET) guard injected by hand into every overnight prompt.
6. Spec-question posting: Leo drafts, disk-parks, never reaches Jira (3 dead dispatches) —
   0.9.3 adds the front-gate triage; the POSTING leg still needs the main loop/autopilot.

## 4. Incidents a factory gate could have prevented

- **KTP-677 over-deletion** — passed every gate while deleting a symbol an in-flight sibling
  branch consumed. → the designed-but-unbuilt System-Integrity gate (Thread A; LOCKED
  architecture, OPEN scan mechanics Q4–Q13; canonical fixture: re-run KTP-677 must BLOCK).
- **KTP-688 deploy-identity** — read `main`, deployed is `dev` (93 commits apart); wrong
  line-refs handed to a code owner. → /deploy-identity probe exists as a skill + hooks, but is
  NOT a factory phase; any future cloud-validation room must make the probe its first step and
  carry VERIFIED/UNVERIFIED stamps on every code-ref that leaves the run.
- **False blockers from stale checkouts** (KTP-728 ×2, KTP-762, KTP-792's false "blocked by
  KTP-791") — partially killed by ADR-003 live-verify + 0.9.3 assumption-audit discipline; the
  class survives wherever an agent asserts without `git show origin/dev:`.

## 5. Evals: what exists, what's missing

- EXISTS: 2 mutation-checked harnesses over real gate functions (tdd-gate 16 cases,
  visual-readiness 18 cases); belt_tools Retro telemetry block (proposed, unwired); run
  telemetry corpus (30 runs) with 2 scores per run.
- MISSING: belt-selection/concierge eval; integrity-gate fixture (KTP-677) as an executable
  eval; run-level e2e eval (validation today = "run one real ticket"); cost telemetry
  (prediction #3); FeatureBench/NoCode-bench style benchmark Gab asked for (06-09, 06-29);
  behavioral parity harness pattern from KTP-870 (cloud LLM ≥90% vs reference set) — the
  template for judging AI-agent work-type output.
- Pending ledger handoffs: dark-factory-eval-harness, harness-taxonomy, local-harness-fix.

## 6. gcloud integration status

Present for PROOF (terraform belt QA asserts live resources; concierge ADR-003 live-verify).
ABSENT for DEBUGGING (no contract/phase reads Cloud Logging/COS serial logs to diagnose a
failing deployed service; nightly-down awareness is manual). A cloud-validation room would be
new surface, not an extension of the terraform belt.

## 7. Autopilot (parallel workstream — design NOT yet 100% approved by Gab)

ADR-004 accepted (07-03) as gate+scheduler; execution today is a generic inline agent, NOT
dark-factory. The gate-as-handoff protocol (headless factory hits a human gate → writes a
`type: gate` handoff + decision_file, exits clean; human answers at pickup; idempotent re-entry)
is DESIGNED but not adopted by the factory. What the factory must expose for safe headless use:
(a) a headless arg that converts AWAITING_HUMAN into a clean machine-readable gate-exit,
(b) decision_file consumption on re-entry, (c) never AskUserQuestion downstream. Explicitly a
Stage-4 proposal — no wiring without Gab's approval.

## 8. North-star alignment check

North star (R9): a spec-integrity engine — reliable system spec, upstream collision discernment,
intentional spec change, regression against spec. Progressive autonomy (R6) is capped until
containment/governance infra exists; ceiling stays human-at-the-bookends. Every proposal in the
roadmap must (i) widen the range of work-kinds (belts), (ii) deepen trustworthy evidence
(gates/evals), or (iii) extend reach toward cloud validation — while keeping ADR-001/002/003
boundaries: gates are code; a belt swaps tools only; claims are live-verified.
