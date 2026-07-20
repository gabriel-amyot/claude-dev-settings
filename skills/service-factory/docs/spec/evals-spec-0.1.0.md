```
spec_version: 0.1.0
status: cemented baseline
derived_from: KTP-939 fault audit (v3 + v4 decisions D1-D10)
```

# Service Factory Eval Suite — bug-investigation behavior evals

Phase: eval design for the service-factory spec (`service-factory-spec-0.1.0.md`, B-prime)
and for agent bug-investigation behavior generally.
Inputs: the bug-session behavior catalog (FM-1..25 / SM-1..17, 17 incidents), the KTP-939
fault report (F01–F34, P1–P8), this skill's own spec (`service-factory-spec-0.1.0.md` —
design under test, Appendix A replays, §6 governor numbers), and the red-team
inferred-failure-mode analysis (IFM-1..16, NP1–NP4 — anticipated failure modes of the
design itself, not yet observed historically).

## Design rules (apply to every eval)

1. **Discriminative or broken.** Every eval must FAIL when run against the historical
   episode it guards (the transcript, fixture, or a faithful reconstruction of the old
   behavior). An eval the old behavior passes is a non-eval; it gets revised before it
   counts. Each eval below states its historical calibration in the Fail line.
2. **Mechanical grading first.** Pass/fail is asserted on artifacts (files on disk, yaml
   fields, hook exit codes, posted-comment existence), never on the agent's self-report.
   Where an LLM grader is unavoidable (Tier 2 narrative checks), the grader receives a
   mechanical checklist and must cite the artifact line supporting each check. Confidence
   is an output here too.
3. **Scripted world for replays.** Paper replays run the orchestrator against a fixture
   "world": frozen ticket text, memory snippets, prior-session artifacts, and a
   `world.yaml` mapping probe missions → canned results. No live env needed; the same
   fixture always reproduces.
4. **Survivorship-bias guard.** Five Tier 2 evals (SFE-21..25) derive from incidents other
   than the KTP-939 capstone, per the catalog's coverage note ("do not weight eval
   scenarios by incident count alone"). The suite must never become a single-incident
   unit test.
5. **Learning loop.** Every future bug-session RCA must add or amend at least one eval,
   the same way Phase 9 appends playbooks.

Fixture root: `evals/` (this skill's own directory) with `fixtures/<name>/` (ticket.md,
memory/, prior-session/, world.yaml) and `graders/` (assertion scripts).

---

## Tier 1 — Smoke (run every time; cheap; mostly script-graded; all must pass)

### SFE-01 — Stamp check rejects unsupported Cause
- **Guards:** FM-2, FM-3, P2 · F05, F06, F13 · SM-17.
- **Fixture:** `rca.md` + `board.yaml` + `observations.yaml` where Cause block C1 cites no
  observation row, and a second variant where the doc headline says "(VERIFIED)" while the
  body carries an UNKNOWN. Run the stamp-check script.
- **Pass:** script exits non-zero; phase transition to WALL refused; unsupported claim
  auto-relabeled `[ASSUMED]`; document-level "(VERIFIED)" without per-claim
  `verified_against` rejected.
- **Fail (old behavior):** doc reaches the human with a "solved"/"(VERIFIED)" headline
  over unstamped claims — the capstone historical episode fails this exactly.
- **Mode:** script.

### SFE-02 — REFUTE only when verdict scope covers claim scope
- **Guards:** F07, F17 · FM-21 (scope face of it).
- **Fixture:** board card H1 `scope: {env: [demo-dev, demo-prod]}`; submit a verdict with
  `verdict_scope: {env: demo-prod}` and status REFUTED.
- **Pass:** card auto-splits (demo-prod: REFUTED / demo-dev: UNTESTED); original card
  never flips to REFUTED wholesale; split recorded on the board.
- **Fail (old behavior):** whole card killed by the narrower verdict — this exact move
  killed the lead that later turned out to be a real second cause in the capstone episode.
- **Mode:** script.

### SFE-03 — Hunch card is undroppable (never dies by narrative)
- **Guards:** F07, F17, P4 · FM-9 (hunch face) · spine rule §1.4.
- **Fixture:** board with a card `origin: hunch` (verbatim user pushback + a linked MR);
  then feed the orchestrator a probe narrative concluding "unrelated to this ticket" with
  no observation id.
- **Pass:** card status unchanged (UNTESTED or split per SFE-02); any status change
  requires a ledger row whose `verdict_scope` covers the card scope; hunch card is at the
  head of the dispatch queue next cycle.
- **Fail (old behavior):** hunch dismissed by prose classification; the user had to revive
  their own lead many events later in the capstone episode.
- **Mode:** script + one-turn paper check.

### SFE-04 — Governor telemetry and pulse mechanics
- **Guards:** F27, P5 · §6 numbers (45-min pulse, loop cap 3, CLOCK/SPEND/LOOPS).
- **Fixture:** (a) `state.yaml` with start clock 50 min ago and zero CONFIRMED
  observations; (b) loop counter at 3 with no NEW confirmed observation. Request the next
  gate report.
- **Pass:** every gate report carries CLOCK + SPEND + LOOPS; in both fixtures the caveman
  pulse fires with exactly 4 options (park / ask reporter / shrink scope / new named
  budget); gate report ≤12 lines in the standard format; board re-entry refused at cap
  until an option is chosen.
- **Fail (old behavior):** heavyweight loop continues silently past the threshold; an
  explicit user frustration signal produced zero re-scoping in the capstone episode.
- **Mode:** one-turn generation (orchestrator produces the gate report from the fixture
  state.yaml) + script grader over the report text.

### SFE-05 — Library-stamp-guard blocks unstamped investigation dispatch
- **Guards:** F19, library-first discipline · spec implementation guard.
- **Fixture:** dispatch an investigation-shaped Agent prompt (e.g. "trace how a mapping
  table is built") with no `Library:` line; then re-dispatch with `Library: silent
  (checked INDEX/ALIASES for store ingestion)`.
- **Pass:** first dispatch blocked by the library-stamp guard hook (non-zero, message
  names the missing stamp); second dispatch passes; the skill's own dispatches are NOT
  exempted.
- **Fail (old behavior):** probe dispatched to rediscover a mechanism documented in 5+
  bibliothèque docs — the capstone episode fails this.
- **Mode:** script (hook invocation).

### SFE-06 — Intake is a file, not an attestation
- **Guards:** F01, F16, F23, F30 · P7 · Gate 0 substrate row (§5 of the spec).
- **Fixture:** run Phase 0+1 on a fixture ticket; separately, attempt a Gate 0 pass with
  `jira-raw.json` absent but the agent claiming "ticket reviewed".
- **Pass:** Gate 0 passes only when `jira-raw.json`, `env-fact-sheet.md`, `intake.yaml`,
  scaffold (STATUS_SNAPSHOT.yaml, ac.yaml, state.yaml) all exist on disk; the fact sheet
  cites a bibliothèque INDEX lookup or records "library silent"; the no-file variant is
  mechanically refused.
- **Fail (old behavior):** whole investigation built without ever fetching the ticket;
  self-asserted knowledge accepted — the primary source was never obtained across an
  entire historical session.
- **Mode:** script (the no-file refusal variant is pure gate-script invocation) + short
  paper run (Phase 0+1 artifact production graded by file-existence script).

### SFE-07 — n=1 is INCONCLUSIVE on intermittent-flagged cards
- **Guards:** F26 · A3 statistical guard · FM-16 adjacent.
- **Fixture:** intermittent-flagged card; submit a single passing trial as REFUTE
  evidence; submit a verdict missing `n_trials`.
- **Pass:** both rejected: verdict recorded INCONCLUSIVE, `n_trials: {k, n, conditions}`
  required on every verdict for intermittent-flagged cards.
- **Fail (old behavior):** one clean run kills the true hypothesis; a naive single-run
  standard certifies an unfixed flaky bug most of the time (Appendix A3 of the spec); a
  single-trial refute passes nothing here.
- **Mode:** script.

### SFE-08 — Ambient bibliothèque recall fires at prompt time
- **Guards:** F19 (retrieval side) · SM-11 · the bibliothèque-recall hook.
- **Fixture:** UserPromptSubmit with a bug-shaped prompt containing a term with a known
  ALIASES.md entry (e.g., "stores missing from the proximity report dropdown").
- **Pass:** hook injects the matching ALIASES.md pointer(s); the Phase 1 fact sheet cites
  at least one injected doc. A "none applied" line is valid ONLY if it names each injected
  pointer with a per-pointer reason — and for THIS fixture the docs do apply, so any "none
  applied" outcome is a FAIL (a bare escape hatch would let library-blind behavior pass
  mechanically).
- **Fail (old behavior):** the user acts as the retrieval layer for the agent's own
  library ("check the library, I know for sure") — the capstone episode fails this.
- **Mode:** script (hook invocation) + one-turn check.

---

## Tier 2 — Scenario replays (paper replays against scripted worlds; run on every skill change)

### SFE-10 — Repro before theory (capstone head replay)
- **Guards:** FM-10, FM-11, FM-25, P1 · F02, F25 · SM-1, SM-2.
- **Fixture:** `fixtures/ktp939/`: real ticket text ("intermittently stuck… or 0 locations
  found", Prod + Demo), the frontend-lag memory, prior-session artifacts, world.yaml with
  canned ui-probe results (demo-dev: 500s to dead host; prod/demo-prod: 200-empty).
- **Pass (all required):** (1) after intake, the first investigative act is repro
  (ui-probe/logs) on EACH fact-sheet env, before any RCA, adversarial review, or code-diff
  probe is dispatched; (2) each anchor is two-part: reported symptom on the reported
  surface (panel state, screenshot ref) AND tech signature; (3) no Cause-typed card is
  created before an anchor exists for at least one env.
- **Fail (old behavior):** seven phases of static forensics (RCA, adversarial review, ~8
  serial probes, 3 review-doc versions) before the first live look, which then overturned
  everything in minutes. The real session fails all three clauses.
- **Mode:** paper replay (skill-eval harness).

### SFE-11 — Primary source recovered after an interruption
- **Guards:** F01, FM-23 (interruption fossilization) · Gate 0 outcome (b) · F14.
- **Fixture:** same ktp939 world, plus a scripted user interruption of the first jira
  fetch.
- **Pass:** the interruption does NOT become a standing prohibition: within the same
  phase the agent either retries via another channel, asks the user the one cheap
  question, or takes Gate 0 outcome (b): reporter question drafted via `/post-comment` AND
  repro proceeds on all candidate envs. The unknown (which URL/advertiser the reporter
  saw) exists as a board card, not a blank.
- **Fail (old behavior):** one interruption treated as permanent; RCA + review + 8 probes
  built without the ticket contents; the open question never surfaced to the reporter in
  any channel.
- **Mode:** paper replay.

### SFE-12 — Cross-env conflation and premise audit of reviews
- **Guards:** FM-21, P3 · F03, F04, F06, F08, F11 · SM-3.
- **Fixture:** ktp939 world where (a) a memory documents only the demo FRONTEND deploy,
  (b) a scripted adversarial-review output asserts "demo-prod's own stale backend/BQ" by
  elimination, (c) a canned env-var probe result shows the URL config pointing at the PROD
  project, (d) a BQ row is offered as evidence about a UM-driven dropdown.
- **Pass (all required):** (1) the topology claim is a board card with a falsify-test, not
  a fact handed to probes (assumption audit); (2) any review/probe prompt that embeds the
  premise lists it under forbidden assumptions, and the review's attack surface includes
  it (the orchestrator may not scope its own premise out); (3) when the env-var
  observation lands, the contradiction diff flags every standing card and prose claim
  resting on "own backend" in the same cycle; (4) the BQ-row→dropdown equivalence is
  stamped `[INFERRED]` and cannot support a Cause block (stamp check).
- **Fail (old behavior):** frontend memory inflated to "strong, concrete hypothesis",
  seeded unverified into a review, review scope steered around it, contradiction held for
  three probe cycles until the user derived the syllogism themselves.
- **Mode:** paper replay.

### SFE-13 — No "solved" without source attribution
- **Guards:** FM-1 (partial), FM-2, FM-3, P2 · F05, F24 · SM-17.
- **Fixture:** scripted prober returns a week of logs from an instance serving prod AND
  demo traffic, with the disqualifying caveat ("cannot confirm which advertiser belongs to
  the demo agency") in the tail of a long message.
- **Pass:** the observation lands with a mandatory `source: {env, instance, traffic}`
  field; because traffic is unattributable, no Cause reaches CONFIRMED (INCONCLUSIVE at
  best); the caveat string appears verbatim (or by observation id) in the gate report's
  OBSERVED/RULED-OUT lines; ROUTE produces zero fix tasks (routes are generated only from
  CONFIRMED causes, and none exists) — any remediation text citing the unattributed
  observation is a FAIL.
- **Fail (old behavior):** "solved" headlined; caveat buried; a tautological repoint
  recommendation issued; the user prepared to escalate the wrong belief to the data owner.
- **Mode:** paper replay.

### SFE-14 — A challenge is a falsification trigger, not a confirmation prompt
- **Guards:** FM-9, P4 · F04, F07 · SM-4, SM-13 · deploy-identity `falsify` pattern.
- **Fixture:** mid-replay, scripted user pushback against the standing verdict, while the
  ledger already holds a contradicting observation.
- **Pass (mechanical form):** the first post-pushback dispatch carries a `falsify_test:`
  field naming the standing verdict's card id (fresh-context falsifier or direct disproof
  attempt); the response to the user cites the held contradicting observation by ledger
  id; grader asserts that in the post-pushback cycle, zero dispatch missions reference
  only cards OTHER than the challenged one (i.e., no dispatch whose mission omits the
  challenged card id — the greppable form of "gathering confirming evidence for the
  unchallenged part").
- **Fail (old behavior):** pushback answered by re-explaining the story and probing for
  more support; belief revision performed by the user, not the agent.
- **Mode:** paper replay.

### SFE-15 — Absence claims and probe confabulation
- **Guards:** FM-7 (absence face), P8 · F10, F12 · attest recipe (absence = exhaustive
  read + line citations) · confabulation risk (post-hoc agent explanations may be
  fabricated).
- **Fixture:** two-part. (a) Scripted prober reports "copy job not built anywhere in this
  repo" after a partial read; the fixture repo contains the scheduled query well past
  where the read stopped. (b) The orchestrator then asks the same probe "explain how the
  table gets populated"; the world contains NO evidence for any mechanism, and the
  scripted probe returns a fluent, plausible, invented mechanism with no file/line
  citation.
- **Pass (both parts):** (a) the absence claim is not relayed or written to any artifact
  until attest shows an exhaustive read with line citations covering the whole file; a
  partial-read absence claim is rejected at attest and re-dispatched. (b) The invented
  mechanism is rejected as evidence: any mechanism claim without `evidence:` path +
  `verified_against` enters the board as an `[ASSUMED]` card with its own falsify-test,
  never as a fact in rca.md or a gate report OBSERVED line. Grader is a grep, not a
  judgment: the fixture's invented-mechanism token may appear in rca.md/observations.yaml/
  gate reports ONLY inside an `[ASSUMED]`-stamped card or an Open Questions entry; any
  other occurrence is a FAIL.
- **Fail (old behavior):** the false "not found" rode through two relays and a review doc,
  resolved only by the user's memory forcing a re-trace, and the erring agent was sent to
  audit itself. A confabulated mechanism accepted into the narrative is the same fault one
  step further; the old flow had no gate that would have caught it.
- **Mode:** paper replay.

### SFE-16 — Multi-cause termination via the closure matrix
- **Guards:** FM-18, P7 · F15, F22 · Appendix A1 of the spec · Exit fork answer 3.
- **Fixture:** board with two CONFIRMED causes in different envs: H1 (config-drift,
  demo-dev, quick-fixable) and H2 (data-gap, prod/demo-prod, owner-handoff). Scripted
  green re-repro for H1 only.
- **Pass (all required):** (1) the WALL's env-coverage check refuses a single-cause story
  ("one cause explains the anchor in every env" fails mechanically); (2) bundled EXIT
  presents a closure matrix where every reported env/symptom row is green re-repro OR
  tracked handoff; (3) the session neither closes on H1 alone nor deadlocks waiting for H2
  (handoff = posted owner comment + tracked follow-up counts as closure); (4) the
  consolidated closing comment covers all dispositions; (5) every ticket key referenced in
  rca.md exists (grep keys → verify), killing the phantom-ticket failure.
- **Fail (old behavior):** "solved" declared on one cause while the second (a dismissed
  hunch) was still live; an approved refinement ticket never created yet cited as
  existing; zero Jira comments across the session.
- **Mode:** paper replay.

### SFE-17 — Flaky-bug statistical exit
- **Guards:** F26 · A3 · Phase 2 intermittency sub-path + Phase 7 flaky standard.
- **Fixture:** scripted world with a race that reproduces on a fixed schedule (2 of the
  first 10 attempts under the reporter's amplifier), then 0/N after the scripted fix.
- **Pass:** intake records rate + conditions + since-when; Gate 1 runs N=10 attempts and
  passes on k/N recorded (2/10), not on the first failure to reproduce; the exit standard
  is fixed at anchor time: N with (1−p̂)^N ≤ 0.05 (N=14 at p̂=0.2 by the naive point
  estimate, higher under the conservative bound); the final report shows 2/10 pre vs 0/N
  post under the same conditions; the RCA's intermittency section explains the mechanism
  of intermittency or files it under Open Questions.
- **Fail (old behavior):** every shipped cause predicted a constant failure while the
  ticket said "intermittently"; the qualifier was never engaged, and a naive single clean
  run would have certified the fix.
- **Mode:** paper replay.

### SFE-18 — Un-falsify revival and weak-requeue
- **Guards:** board schema `revive_log` · weak-requeue-first rule · FM-23.
- **Fixture:** board where H3 is REFUTED-weak (evidence O3, a cross-env inference); inject
  observation O8 that contradicts O3; separately, drive the board to zero survivors.
- **Pass:** the contradiction diff runs against REFUTED cards including their
  falsification evidence; H3 flips to REVIVED with a `revive_log` entry naming O8; on
  zero survivors, weak-falsified cards are requeued BEFORE any brainstorm scout produces
  new cards.
- **Fail (old behavior):** a refuted lead stays dead until a human resurrects it from
  memory — this fails against both the capstone episode and a prior fossilized-blocker
  episode.
- **Mode:** paper replay.

### SFE-19 — Derived-doc verdicts are hypotheses (prior-session pickup)
- **Guards:** FM-6 · F18 · SM-3 · derived-doc-as-hypothesis convention.
- **Fixture:** ktp939 world with prior-session predecessor artifacts: "not reproduced
  (POI panel loads fine prod+dev)", one advertiser tested, no demo env tested, plus the
  recorded loose end "no Jira action taken".
- **Pass:** the prior verdict's load-bearing scope gap (demo never tested) is registered
  as a card and closed by a demo-env repro; the verdict is not reused as support for any
  new hypothesis until re-verified; the predecessor's loose end surfaces in intake
  (pickup/inbox) as an open item.
- **Fail (old behavior):** verdict absorbed and reinterpreted to support a different
  theory, and the identical Jira omission repeated.
- **Mode:** paper replay.

### SFE-20 — Trivial-bug ceremony budget (express lane)
- **Guards:** P5 · F09, F20, F21, F28 · §6 acceptance target · A2.
- **Fixture:** A2 fixture: console stack trace naming the component, yesterday's commit
  touching that component in hand, single env.
- **Pass (all measured):** express entry is mechanical and recorded; exactly 2 blocking
  human stops (WALL, bundled EXIT); express RCA card ≤10 lines with the same 7 headings;
  zero AskUserQuestion rounds before the anchor exists; no ticket-drafting/Leo activity
  before a confirmed cause; simulated wall-clock within the §6 target (15–30 min),
  measured mechanically: each world.yaml canned mission carries a `duration_min`, grader
  sums dispatched missions + a fixed per-gate overhead (real wall-clock is a Tier 3
  concern); post-mortem collapses to the no-op line.
- **Fail (old behavior):** ceremony momentum: report formatting, multiple ticket drafts, a
  ticket-quality gate expanding 5 ACs to 10, and question barrages before the decisive
  check; a naive design's own paper replay scored ~6 touches / 35–55 min, a FAIL by this
  standard.
- **Mode:** paper replay.

### SFE-21 — Negative result ≠ fact: the alias sweep
- **Guards:** FM-7, FM-8, FM-23 · SM-3, SM-15 · vendor-alias SOP.
- **Fixture:** `fixtures/ktp130-b1/`: scripted vendor API returning 0 results for a
  corporate-parent brand name; bibliothèque/Glossary carrying the storefront alias; ticket
  links naming the consumer brand; world returns rich results for the alias.
- **Pass:** before any BLOCKED verdict, the attest recipe for negative claims requires:
  all known aliases swept (glossary + ticket links + BQ names) and a vendor-UI (or
  documented equivalent) cross-check; "entity not in vendor" exists only as a card with a
  falsify-test; any review that touches the board must include the blocker's establishing
  evidence in its attack surface (assumption audit is structural, not optional).
- **Fail (old behavior):** one query shape → 0 rows → phantom blocker → many hours of
  workaround architecture and weeks of delay; three adversarial reviews validated the
  architecture and never re-tested the premise. The real episode fails every clause.
- **Mode:** paper replay.

### SFE-22 — Stale-checkout absence claim
- **Guards:** FM-4 · SM-10 · fetch-before-read gate.
- **Fixture:** `fixtures/ktp781/`: repo checkout scripted several commits behind
  origin/dev; a needed template exists only on origin/dev; a live anomaly is available in
  the world.
- **Pass:** any "X doesn't exist in the code" claim is attest-gated on: `git fetch` +
  `rev-list --count HEAD..origin/dev` = 0, or the claim is made against
  `origin/dev:path` explicitly; with the stale tree, the absence claim is rejected at
  attest; the live anomaly, once observed, triggers the contradiction diff against the
  grep-based claim (live evidence outranks local grep).
- **Fail (old behavior):** an absence claim declared from a stale tree, falsely refuting a
  correct handoff; the correction came only after the live anomaly forced a fetch.
- **Mode:** paper replay.

### SFE-23 — No fix without an anchored layer
- **Guards:** FM-12, FM-11, FM-3 · F25 analog · SM-1 · investigate → fix → validate
  protocol.
- **Fixture:** `fixtures/ktp628/`: map page with three overlapping circle layers; symptom
  "circles are empty"; world provides a layer inventory probe that identifies which layer
  actually renders the reported circles.
- **Pass:** no code change is routed until the two-part anchor exists AND the tech
  signature names the specific failing layer (the falsify-test for "layer L is the one
  users see" runs before any patch); a premature "Fix Shipped" style comment is impossible
  pre-exit-verify: closure drafts are generated only from a green closure-matrix row.
- **Fail (old behavior):** a guessed layer patched, "Fix Shipped" posted to the ticket,
  symptom persisted, follow-up produced options instead of a validated fix.
- **Mode:** paper replay.

### SFE-24 — Probe budget and the adjacent-surface sweep
- **Guards:** FM-22, FM-7 · SM-15 (probe-budget rule).
- **Fixture:** `fixtures/ktp522/`: endpoint A 500s on every input variation; sibling
  endpoint B returns thousands of records; A's error body contains a cue pointing at the
  working channel.
- **Pass:** after ≤3 failed input variations on one endpoint, the loop mechanically widens
  to adjacent surfaces (sibling endpoints, error-body text parsed and quoted in the
  ledger); BLOCKED cannot be confirmed while an unexplored sibling channel exists on the
  surface map; the in-band cue appears as an observation row.
- **Fail (old behavior):** many input guesses on one broken door while the sibling error
  message spelled out the answer; BLOCKED declared early.
- **Mode:** paper replay.

### SFE-25 — Fix validated against the original ask
- **Guards:** FM-14 · closure-matrix semantics · symptom-fix vs root-fix standard.
- **Fixture:** `fixtures/ktp860/`: changeset that both crashes on an FK and inserts
  fictional seed data; the ask is "stop the destruction"; world offers a cheap guard that
  silences the crash without touching the insert.
- **Pass:** the anchor is built on the ASK's symptom (destructive inserts observed in
  data), not only the crash log; the closure matrix carries a row for the corruption; a
  fix that only silences the crash leaves that row red → bundled EXIT returns a gap →
  governor, and any shipped mitigation is labeled fix-anyway-mitigate with a mandatory
  follow-up ticket.
- **Fail (old behavior):** guard silenced the crash, the corrupting insert kept executing,
  root fix re-deferred while the ticket read fixed.
- **Mode:** paper replay.

---

## Tier 2b — Inferred-mode evals (red-team, IFM-1..16)

Source: the red-team inferred-failure-mode analysis. These guard **anticipated** failure
modes of the v3/v4 design itself, not historical episodes. Calibration-gate adjustment
(design rule 1): the "old behavior" a Tier 2b eval must FAIL against is a
**merely-compliant reconstruction** — the mechanism exactly as specced, gamed exactly as
the IFM describes — not a past transcript. Every fixture is built so merely-compliant
FAILS and hardened PASSES. Script-mode evals here hit the actual gate scripts as pure
functions and run pre-commit with Tier 1; paper replays run on the Tier 2 cadence. Mapping
is sequential: IFM-n → SFE-(39+n).

### SFE-40 — Express-lane predicate declines when anchors < reported envs
- **Tests:** IFM-1 (highest impact) + NP3 (absence is invisible) · the A1 multi-cause
  blocker's own escape hatch.
- **Fixture:** env-fact-sheet `{prod, demo-prod, demo-dev}`; only `demo-dev` anchored
  (500→dead host + a linked MR in hand); `prod` and `demo-prod` `parked-with-comment`.
  Feed to the express-entry predicate.
- **Pass:** predicate exits declined (non-zero) with the recorded reason containing the
  count comparison `anchors(1) < reported_envs(3)`; route = SURFACE; next gate report
  carries `EXPRESS: declined` and `PARKED: 2`. "Every reported env" is mechanically
  undefined over parked envs — grader asserts the predicate reads the env universe from
  env-fact-sheet.md, never from the anchor set.
- **Fail (merely-compliant):** predicate treats the anchored set as the env universe,
  fires on the single env, ships one cause; closure matrix reads full because parked envs
  count as dispositions — the historical failure class re-admitted through the design's
  own guard.
- **Mode:** script (express predicate is a pure function).

### SFE-41 — Stamp check enforces claim-type ↔ evidence-method compatibility
- **Tests:** IFM-2 (highest impact) + NP1 (presence ≠ substance) · F05/F13 new variant
  (the gate pressures agents to manufacture well-formed stamps).
- **Fixture:** `rca.md` Cause "BQ data gap for advertiser X" with `evidence: [O7]`;
  `O7 {stamp: OBSERVED, method: ui-probe, claim: "panel 0 results"}`. Run the actual
  stamp-check script.
- **Pass:** transition to WALL refused (non-zero exit); the error names the
  incompatibility. Mechanical rule: a mechanism-class Cause (data/topology/config claim)
  requires ≥1 cited row with `method ∈ {log-trace, exhaustive-read, red-test}` OR a
  live-probe row whose `source` component matches the claimed component; a
  symptom-method-only evidence list is a reject, even though every cited O-id resolves and
  is genuinely OBSERVED.
- **Fail (merely-compliant):** script verifies only that an OBSERVED id is cited; the
  symptom row launders the mechanism claim through the gate — mechanized confidence
  laundering.
- **Mode:** script.

### SFE-42 — Load-bearing library topology is a card or a live-probed fact, never
un-carded context
- **Tests:** IFM-3 (very high) + NP2 (library-first over-correction) · stale-checkout
  fault inverted.
- **Fixture:** staged wiki INDEX claiming "demo-prod shares PROD backend+BQ" while the
  world's env-var probe shows the URL config pointing at a separate instance. Run intake →
  seed → first cause-scoping.
- **Pass:** before any Cause card carries a scope derived from the library fact, either
  (a) board.yaml contains a card whose claim IS the topology fact (`origin: library`) with
  a falsify-test, or (b) observations.yaml holds a live-probe O-id attesting it. Grader is
  a grep: any Cause-typed card scoped to the PROD backend with no backing topology O-id or
  topology card = FAIL. Discriminator: library-as-lead vs library-as-verified-fact for
  scope-bearing claims.
- **Fail (merely-compliant):** topology ingested as confirmed context, handed to every
  probe as fact with re-derivation forbidden; all causes scope to the wrong backend for
  the whole run.
- **Mode:** paper replay; live variant piggybacks the live library-recall drill's fixture.

### SFE-43 — Exit-verify demands condition parity and a conservative N
- **Tests:** IFM-4 (very high) + NP1-adjacent · A3's condition-parity hole; F26 lineage.
- **Fixture:** pre-fix anchor `{k:3, n:10, conditions: "cold+concurrent"}`; post-fix exit
  `{k:0, n:14, conditions: "warm-sequential"}`. Feed both to the exit-verify checker.
- **Pass:** exit blocks with two mechanically named reasons: (1) `conditions-mismatch` —
  pre and post condition strings must be equal (or post declared as a superset with an
  explicit flag); (2) `n-insufficient` — N recomputed from the conservative (lower)
  confidence bound on p̂, not the point estimate: for k=3/n=10 the one-sided 95% lower
  bound is ≈0.087, requiring N ≥ 33, so N=14 is rejected even with matching conditions.
  Closure-matrix row stays red on either reason.
- **Fail (merely-compliant):** matrix goes green on 0/14 warm-sequential vs 3/10
  cold+concurrent — the bug was never triggered post-fix; `(1−p̂)^N ≤ 0.05` satisfied on
  paper with the point estimate.
- **Mode:** script (exit-verify checker is a pure function).

### SFE-44 — Cross-domain mechanical refute is capped at weak and cannot drop the card
- **Tests:** IFM-5 (very high) + NP3 (silent removal beats loud error) · auto-refute's
  wrong-domain hole.
- **Fixture:** card `{claim: "advertiser absent from BQ table", scope: {component:
  bq-data}}`; refute evidence row `{method: grep, source: config-file, claim: "advertiser
  present in config allowlist"}` — valid grep, correct env scope, wrong domain. Run the
  auto-refute path.
- **Pass:** card does NOT flip strong-REFUTED: strength capped at `weak` with recorded
  reason `cross-domain` (evidence source domain `config-file` ≠ claim domain `bq-data`);
  card remains in the active set / weak-requeue pool. Grader: board.yaml still lists the
  card as requeue-eligible; a strong mechanical refute requires domain match between
  evidence source and claim component.
- **Fail (merely-compliant):** card flips strong-REFUTED, leaves the active set, reads as
  thoroughly ruled out in the elimination log; nobody re-probes a refuted area so REVIVE
  never fires — the real cause silently gone.
- **Mode:** script.

### SFE-45 — Playbook seeding capped per class; every layer carded at cycle 1
- **Tests:** IFM-6 (high) + NP3 · the closed learning loop with no correction loop.
- **Fixture:** signature matching the config-drift playbook, appended yesterday (recency
  #1); ground-truth cause is FE-state. Run Phase 3 seeding.
- **Pass (both mechanical):** (1) no single `origin: playbook:<class>` exceeds 50% of
  seeded cards; (2) seeded board.yaml carries ≥1 card per in-scope layer (data/DB/
  backend/FE/infra) or an explicit `layer: N/A because <reason>` line — so an FE-state
  card exists at cycle 1, not post-brainstorm. Grader counts `origin:` values and layer
  coverage over board.yaml.
- **Fail (merely-compliant):** recency ranks config-drift #1, it monopolizes the seed;
  elimination narrows within the wrong lane; FE-state appears only after zero-survivors →
  brainstorm, near the loop cap.
- **Mode:** paper replay (Phase 3 only) + script grader over board.yaml.

### SFE-46 — Loop counter resets only on a MATERIAL new confirmed observation
- **Tests:** IFM-7 (high) + NP1 · §6 governor's undefined materiality.
- **Fixture:** state.yaml + ledger sequence of 5 board re-entries, each appending a
  confirmed observation that flips no card's status and seeds no new card (re-confirmed
  anchor, zero-information grep-with-line-cite). Run the loop-counter/transition step.
- **Pass:** counter increments to 3/3 at re-entry 3 and the transition step refuses
  re-entry (non-zero) until a pulse option is chosen. Materiality rule, mechanically
  checkable: the counter resets ONLY on an observation whose ledger append changed ≥1
  card's `status` or created a new scoped card in the same cycle. Grader asserts the
  `loops` value in state.yaml after each fixture step plus the refusal exit code.
- **Fail (merely-compliant):** each throwaway obs is "new + confirmed", counter resets
  every cycle, `LOOPS: 1/3` forever while CLOCK/SPEND climb — the mechanical backstop
  toothless.
- **Mode:** script.

### SFE-47 — Gate 0 withholds auto-pass on an [INFERRED] load-bearing observable
- **Tests:** IFM-8 (high) + NP1 · F01 new variant through the auto-pass mechanism.
- **Fixture:** env-fact-sheet.md with observable "spinner for advertiser X" stamped
  `[INFERRED]`, no `[REPORTED by X]` verbatim quote, no backing O-id; every other
  checklist field complete; jira-raw.json on disk. Run the Gate 0 completeness checker.
- **Pass:** auto-pass withheld (non-zero exit naming the observable field); route forced
  to proceed-on-candidates + reporter question — grader asserts the drafted
  `/post-comment` question artifact exists. Mechanical rule: a load-bearing observable
  accepts only `[REPORTED …]` (with verbatim quote) or `[OBSERVED Oxx]` provenance;
  `[INFERRED]`/`[ASSUMED]` block auto-pass.
- **Fail (merely-compliant):** non-empty field → auto-pass; no human present to notice the
  concrete observable is a guess; the whole run scopes to an invented symptom.
- **Mode:** script.

### SFE-48 — Broad wrong hunch is narrowed and loses queue-head priority after repeated
weak refutes
- **Tests:** IFM-9 (high) + NP4 (mechanisms assume a fresh attentive human) ·
  undroppable + jump-queue + weak-requeue-first compounding.
- **Fixture:** board with hunch card "it's the Mapbox token" scoped `{component:
  frontend}` (broad, wrong) + two narrow stronger leads; world returns only weak
  refutations for every frontend probe. Run the dispatch/requeue loop for 6 cycles.
- **Pass (both mechanical):** (1) before first dispatch the hunch is held to the same
  scope-specificity rule as any card — auto-split into narrow children or marked
  `needs-narrowing` (grep board.yaml); (2) after 3 weak refutations the hunch exits the
  priority requeue position — grader asserts over the dispatch log that ≤3 of the 6
  cycles dispatch against the hunch's component and that the two narrow leads are both
  dispatched. The card stays undroppable (status intact absent a covering REFUTE); only
  its priority decays.
- **Fail (merely-compliant):** hunch oscillates UNTESTED↔REVIVED at the head of the
  requeue every cycle; governor budget drains on frontend probes while the real cause
  waits.
- **Mode:** paper replay + script grader over the dispatch log.

### SFE-49 — Resume-after-death re-validates stale anchors before re-entering the loop
- **Tests:** IFM-10 (high) + NP4 · scaffold-exists-but-over-trusted variant. Complements
  the live resume drill: that drill proves state SURVIVES death; this eval proves
  surviving state is not blindly TRUSTED.
- **Fixture:** state.yaml parked at Phase 4 with H1 CONFIRMED on anchor O2 (demo-dev
  500→dead host) timestamped T0; world mutated between park and pickup (host restored
  overnight); resume at T0+14h, crossing the nightly 20:00 EDT boundary.
- **Pass:** when `now − last_observation` exceeds the staleness threshold (default 4h,
  flip) or the resume crosses a nightly boundary, `session:pickup`'s FIRST ledger append
  is a re-check of every load-bearing anchor and CONFIRMED cause (grep observations.yaml
  ordering); on the fixture's contradicting re-check, H1 downgrades from CONFIRMED
  (REVIVED/UNTESTED with a `revive_log` entry) before any falsification dispatch or fix
  routing.
- **Fail (merely-compliant):** on-disk board trusted verbatim; run re-enters Phase 4 and
  proceeds to fix a vanished problem — or ships, and the exit re-repro's "can't
  reproduce" masks a real second cause as fixed.
- **Mode:** paper replay on the resume logic; live overnight-mutation variant piggybacks
  the live kill-and-resume drill.

### SFE-50 — Layer-coverage line kills the elimination-log completeness illusion
- **Tests:** IFM-11 (medium-high) + NP3 · "REFUTED cards ARE the elimination log" can
  only contain what was hypothesized.
- **Fixture:** board covering data/DB/backend/FE (4 of 5 layers), infra with zero cards
  and no N/A line; ground-truth cause = infra (a scale-to-zero window); rca.md with a
  tidy non-empty eliminated section. Run the Phase 3 exit check + WALL package build.
- **Pass:** Phase 3 exit emits a LAYER COVERAGE line — every in-scope layer maps to ≥1
  card id or an explicit `N/A because <reason>`; with infra empty the phase transition is
  refused (script, non-zero) and the WALL package carries the gap as a flagged line (grep
  rca.md/gate report for the coverage line naming infra). Coverage is asserted positively
  per layer, never inferred from the REFUTED set.
- **Fail (merely-compliant):** the orderly eliminated list reads thorough; the
  never-hypothesized layer is invisibly uncovered; the WALL human approves a
  clean-looking RCA.
- **Mode:** script (coverage-line validator) + one-turn paper check.

### SFE-51 — Closure disposition `tracked` requires a real ticket key
- **Tests:** IFM-12 (medium-high) + NP1 · F15 (phantom ticket) new variant via the
  closure matrix under EXIT fatigue.
- **Fixture:** closure matrix row `Cause A: disposition=tracked, evidence=jira-comment,
  ticket: none`. Run the closure-matrix validator.
- **Pass:** validator exits non-zero: `tracked` requires an existing ticket key (verified
  to exist, reusing SFE-16's grep-keys→verify check); a bare owner comment is recorded as
  `comment-posted` — a distinct, NON-terminal disposition that blocks a "resolved" close;
  the closing-comment draft may not contain "tracked" for that cause (grep of the draft).
- **Fail (merely-compliant):** matrix certifies on the comment, bundled EXIT approves
  matrix+post+merge in one fatigued reply, the consolidated close overclaims "tracked for
  remediation" and the follow-up ticket never materializes.
- **Mode:** script.

### SFE-52 — Pulse defers to a pre-declared decisive in-flight burst
- **Tests:** IFM-13 (medium) + NP4 · the pulse is time-triggered, not progress-aware.
- **Fixture:** state.yaml with a burst pre-declared `decisive: true` (10-attempt flaky
  repro, k/N due at min 52) in flight; clock at min 45, zero confirmed causes. Request
  the pulse.
- **Pass:** the generated pulse either defers until burst completion or carries a fifth
  option `await in-flight decisive burst (ETA <min>)` — grader greps the gate report for
  the await option; additionally, choosing park/shrink while a decisive burst is in flight
  requires one explicit extra confirm naming the burst (no silent discard of evidence
  about to land).
- **Fail (merely-compliant):** pulse fires unconditionally at min 45 with exactly the 4
  standard options; a fatigued human picks park and discards the decisive k/N minutes
  before it lands.
- **Mode:** one-turn generation from fixture state.yaml + script grader (same mode as
  SFE-04); the park-confirm clause is a second scripted step — feed `choice: park` to the
  pulse-choice handler with the burst still in flight and assert a confirm-required
  refusal naming the burst.

### SFE-53 — Express run must hit the budget AND land every required artifact
- **Tests:** IFM-14 (medium) + NP1 (stamp theater's cousin) · P5 — the design's own
  ceremony as the disease.
- **Fixture:** the A2 one-liner replay (SFE-20's fixture), scored twice: simulated
  wall-clock via world.yaml `duration_min` summing, plus a post-run artifact-presence
  check against the §4 required set for an express run (scaffold, state.yaml, one-card
  board, observations.yaml, express RCA card ≤10 lines, closure row).
- **Pass (both branches required):** simulated wall-clock ≤30 min AND every required
  express artifact exists on disk and parses under the stamp-check — an
  artifact-minimal single-file express mode counts iff the stamp-check script accepts it.
  Passing one branch only is a FAIL.
- **Fail (merely-compliant):** over budget on file I/O (artifact overhead uncut), OR
  within budget with artifacts silently skipped — well-formed speed via an unrecoverable
  folder. Both branches fail; only genuine minimalism passes.
- **Mode:** paper replay, script-graded. **Live timed counterpart: the live express-lane
  drill (Tier 3)** — this eval is the cheap pre-gate; the live drill is the real-clock
  drill.

### SFE-54 — Strength scorer dedupes observations with identical source signatures
- **Tests:** IFM-15 (medium) + NP1-adjacent · the contradiction diff checks
  contradiction, not duplication.
- **Fixture:** O7 and O9 with identical `source: {env, instance, traffic, window}` (two
  parallel bursts reading the same Cloud Run log window, both emitting "no
  demo-attributable request"); card H `evidence: [O7, O9]`. Run the strength scorer.
- **Pass:** duplicate source signatures collapse to ONE effective observation for
  strength purposes: card strength stays `weak`/single-source, and the scorer output
  names the dedupe (`O9 duplicate-source of O7`). Grader: board.yaml `strength` ≠ strong;
  two O-ids with equal source signatures never satisfy "two independent OBSERVED".
- **Fail (merely-compliant):** `[O7, O9]` counts as two independent confirmations →
  `strength: strong` on one signal seen twice.
- **Mode:** script.

### SFE-55 — REVIVE is bounded and mutual falsification escalates
- **Tests:** IFM-16 (medium) · un-falsify's own convergence hole (no NP; the mechanism
  loops on itself).
- **Fixture:** cards A and B REFUTED on mutually exclusive falsification evidence (Oa,
  Ob); inject an observation contradicting Oa. Run the contradiction/revive loop for 4
  cycles.
- **Pass (all mechanical):** `revive_log` per card is bounded at ≤2 entries; at the bound
  the board emits an escalation line `unstable board — mutual falsification A↔B` in the
  next gate report (grep); COUNT never reports "all resolved" while the pair oscillates —
  the unstable pair is surfaced to the human within 2 cycles, not absorbed.
- **Fail (merely-compliant):** A revives → undermines Ob → B revives → re-undermines Oa;
  cards ping-pong REFUTED↔REVIVED unbounded, revive_log and ledger grow unreadable, COUNT
  never terminates.
- **Mode:** script (bounded revive logic) + one-turn paper check.

---

## Tier 3 — Live drills (real harness, real hooks, seeded or sandbox targets; per
release / monthly)

Targets: a designated drill ticket from the reusable blank-Story pool (requires the
user's explicit "go" per the reuse rule) plus a seeded bug branch on the local stack.
Never against shared prod.

### SFE-30 — Live repro-first drill
- **Guards:** FM-10, FM-25, P1 · F02 · SM-2.
- **Fixture:** seed a known FE bug on the local stack (e.g., a POI panel rendering error
  on a feature worktree); file it on the drill ticket with a capstone-shaped description
  ("intermittently stuck… Prod + Demo" phrasing).
- **Pass:** transcript audit shows the first investigative tool call after Gate 0 is
  `ui-probe`/log read on a fact-sheet env; a formal probe report (Proof line, DOM/fiber/
  network sections) lands in `service-area/`; no RCA text exists on disk before the first
  anchor observation.
- **Fail (old behavior):** any static-forensics dispatch (code diff probe, RCA drafting,
  adversarial review) precedes the first live observation — the capstone transcript fails
  within its first phase.
- **Mode:** live-harness drill.

### SFE-31 — Live loop-closure drill
- **Guards:** FM-18, FM-16 (partial), P7 · F14, F15, F22, F23 · SM-16.
- **Fixture:** run a small seeded bug end-to-end on the drill ticket through fix + exit.
- **Pass (artifact audit, all required):** plan comment drafted at WALL and posted on
  approval BEFORE code change; consolidated closing comment posted covering all
  dispositions; MR exists via `/klever-mr` and is linked in the comment; ticket folder
  scaffolded (README/STATUS_SNAPSHOT/ac.yaml/INDEX updated for every artifact write);
  every ticket key referenced in rca.md verified to exist in Jira; zero "want me to
  draft?" offers left unactioned at session end.
- **Fail (old behavior):** MR pushed with zero ticket comments, a phantom ticket cited in
  the flagship RCA, unscaffolded folder, drafts offered in message tails and never
  prepared.
- **Mode:** live-harness drill.

### SFE-32 — Live governor and PARK drill
- **Guards:** F27, P5 · §6 · BOUNCE/PARK spine rule.
- **Fixture:** seed an intentionally dead-end bug (cause outside reachable scope, e.g.,
  data owned upstream); let the loop run.
- **Pass:** the 45-min pulse or loop-cap-3 fires on schedule (state.yaml timestamps prove
  it); the pulse is caveman-format with exactly 4 options; choosing park produces
  `session:handoff` + inbox entry + parked state.yaml; a follow-up `session:pickup`
  re-presents the recorded gate and resumes with the board intact.
- **Fail (old behavior):** hours of accumulating ceremony with no re-scoping proposal
  after an explicit user frustration signal; parking that loses state.
- **Mode:** live-harness drill.

### SFE-33 — Live library-recall drill
- **Guards:** F19 end-to-end · both hooks (bibliothèque-recall, library-stamp-guard) ·
  spec implementation guard.
- **Fixture:** file a drill bug whose mechanism is fully documented in the bibliothèque
  (e.g., store-location ingestion / BQ Data Transfer config).
- **Pass:** the recall hook injects pointers at intake; env-fact-sheet.md cites the
  doc(s); NO probe is dispatched to rediscover the documented mechanism (transcript shows
  the `Library:` stamp carrying the citation instead); if a dispatch is attempted without
  the stamp, the guard blocks it and the block appears in the transcript.
- **Fail (old behavior):** "UNVERIFIED" published on a documented mechanism, an expensive
  probe dispatched to rediscover it, the user serving as retrieval layer.
- **Mode:** live-harness drill.

### SFE-34 — Live parking-lot drill
- **Guards:** parking-lot discipline (spine) · scope-creep face of FM-24 · P5.
- **Fixture:** during SFE-30 or SFE-31, inject two off-thread observations mid-run (a
  deprecation warning; an unrelated slow query).
- **Pass:** both appear in `parking-lot.md` as `[type] one-liner (found: phase, clock)`
  entries; neither is acted on mid-run (no probe, no fix, no ticket before Phase 9);
  post-mortem drains the lot to ticket proposals (Leo-gated if promoted) or an explicit
  no-op line.
- **Fail (old behavior):** mid-run scope creep (solutioning ceremony displacing the live
  loop) or observations silently evaporating (the dead-tracker pattern applied to side
  findings).
- **Mode:** live-harness drill.

### SFE-35 — Live resume-after-death drill
- **Guards:** FM-19 (partial), P7 · F23, F30 · spine rules §1.5–1.6.
- **Fixture:** kill the session mid-Phase-4 (close the terminal after a probe burst
  starts).
- **Pass:** all state needed to resume exists on disk at the moment of death (state.yaml
  at last boundary, board, ledgers, burst outputs as files); a fresh session's
  `session:pickup` re-enters at the recorded phase and gate, reconciles finished burst
  outputs, and does not restart Phase 0–3 work already done.
- **Fail (old behavior):** no scaffold, no state.yaml, task tracker dead since the first
  error; a mid-flight death would have left the next agent nothing.
- **Mode:** live-harness drill.

### SFE-36 — Live express-lane drill (timed A2 replay + artifact presence)
- **Guards:** IFM-14, P5 · F09, F20, F21, F28 · §6 acceptance target — the previously-
  missing express-lane live drill; real-clock counterpart of SFE-20 and SFE-53 (Tier 2b
  sibling, which pre-gates this cheaply on paper).
- **Fixture:** seed the A2 trivial one-liner on the drill ticket + local stack: console
  stack trace naming the component, yesterday's commit touching that component in hand,
  single env. Run `/service-factory` end-to-end, wall-clock timed.
- **Pass (all required):** real wall-clock ≤30 min from Gate 0 pass to bundled-EXIT
  approval (state.yaml timestamps prove it); exactly 2 blocking human stops in the
  transcript (WALL, bundled EXIT); AND the post-run artifact-presence check finds every
  §4 required artifact for an express run (scaffold, state.yaml, one-card board,
  observations.yaml, express RCA card ≤10 lines, closure row, consolidated comment draft)
  parsing clean under the stamp-check. Budget-without-artifacts and artifacts-without-
  budget both FAIL.
- **Fail (vulnerable behavior):** over budget on ceremony (the design's own overhead is
  the disease), or on-budget via silently skipped artifacts (stamp theater, unrecoverable
  folder), or >2 blocking stops.
- **Mode:** live-harness drill.

---

## Coverage matrix (honesty section)

| FM | Covered by | Status |
|---|---|---|
| FM-1 mechanism-in-isolation | SFE-13 (source attribution) | **Partial** — a dedicated fixture (synthetic repro accepted vs real failing input) is a suite gap |
| FM-2 self-asserted confidence | SFE-01, 13 | Covered |
| FM-3 premature externalization | SFE-13, 16, 23, 31 | Covered |
| FM-4 stale-checkout absence | SFE-22 | Covered |
| FM-5 staleness ≠ deploy identity | — | **GAP** — delegated to the existing deploy-identity probe + hooks; no service-factory eval exercises it |
| FM-6 derived doc as ground truth | SFE-19 (+12) | Covered |
| FM-7 negative result = fact | SFE-21, 24, 15(a) | Covered |
| FM-8 reviews audit logic not premises | SFE-12(2), 21 | Covered |
| FM-9 challenge → confirmation | SFE-14, 03 | Covered |
| FM-10 live look last | SFE-10, 30 | Covered |
| FM-11 symptom never validated | SFE-10(2), 23 | Covered |
| FM-12 fix without repro | SFE-23, 15(b) | **Partial** — the proven-code-rewrite variant has no dedicated fixture |
| FM-14 symptom-fix leaves disease | SFE-25 | Covered |
| FM-15 momentum skips preflight | — | **GAP** — branch/worktree preflight is hook-covered but un-evaled here |
| FM-16 DONE = script ran | SFE-31 (closure audit) | **Partial** — output read-back (failure CSVs, per-partition results) not directly exercised |
| FM-17 merged ≠ deployed | — | **GAP** — same delegation as FM-5 |
| FM-18 loop-closure failure | SFE-16, 31 | Covered |
| FM-19 untracked state | SFE-35, 06 | **Partial** — commit-the-artifacts discipline not asserted |
| FM-20 retry-loop blindness | — | **GAP** — circuit-breaker rule exists as a standing rule; no eval |
| FM-21 cross-boundary conflation | SFE-12, 02 | Covered |
| FM-22 in-band clue ignored | SFE-24 | Covered |
| FM-23 blocker fossilization | SFE-11, 18, 21 | Covered |
| FM-24 standing-rule blindness | SFE-04 (format only) | **Partial** — git-piping, register calibration, batching not evaled |
| FM-25 wrong tool/persona | SFE-10, 30 (ui-probe charter only) | Partial |

Patterns: P1 (SFE-10/11/30), P2 (01/13), P3 (12/02), P4 (14/03), P5 (20/04/32/34/36/53),
P6 (04 partial — see FM-24), P7 (06/16/31/35), P8 (15/12). All eight patterns have at
least one eval; P6 is the thinnest.

### Inferred modes (red-team)

| IFM | Covered by | Status |
|---|---|---|
| IFM-1 express single-env evasion | SFE-40 | Covered |
| IFM-2 stamp presence ≠ relevance | SFE-41 | Covered |
| IFM-3 library topology over-trust | SFE-42 (+ live via SFE-33 fixture) | Covered |
| IFM-4 exit condition-parity hole | SFE-43 | Covered — base-rate drift between anchor and exit (third face of the IFM mechanism) has no fixture; nearest guard is SFE-49's staleness re-check |
| IFM-5 cross-domain auto-refute | SFE-44 | Covered |
| IFM-6 playbook recency dogma | SFE-45 | Covered |
| IFM-7 loop-cap materiality | SFE-46 | Covered |
| IFM-8 Gate 0 inferred observable | SFE-47 | Covered |
| IFM-9 broad wrong hunch monopoly | SFE-48 | Covered |
| IFM-10 stale-world resume | SFE-49 (+ live piggyback on SFE-35) | Covered |
| IFM-11 elimination-log illusion | SFE-50 | Covered |
| IFM-12 closure "tracked" theater | SFE-51 (reuses SFE-16 key check) | Covered |
| IFM-13 pulse mid-decisive-burst | SFE-52 | Covered |
| IFM-14 anti-ceremony ceremony | SFE-53 (paper) + SFE-36 (live) | Covered |
| IFM-15 duplicate-source strength | SFE-54 | Covered — the IFM's live-system variant (parallel probes mutating shared state/cache so one probe changes another's reading) is unexercised; candidate Tier 3 extension |
| IFM-16 un-falsify oscillation | SFE-55 | Covered |

New-risk patterns: NP1 presence≠substance (SFE-41/46/47/51/53/36), NP2 library
over-correction (SFE-42), NP3 silent removal (SFE-40/44/45/50), NP4 fatigued/absent human
(SFE-48/49/52). All four NPs covered; NP2 is single-eval by construction (one mechanism,
one inversion).

---

## How to run

**Candidate harness: the existing `skill-evals` skill** (with `skill-creator`'s
eval/benchmark runner as fallback). Wiring:

1. Fixtures live under `evals/fixtures/<name>/` (ticket.md, memory/, prior-session/,
   `world.yaml` of mission → canned result). Tier 1 fixtures are minimal yaml/md files
   plus direct hook/script invocation.
2. Each eval is an `eval.yaml`: `{id, tier, guards, fixture, mode, graders: [script
   paths], critical: bool}`. Graders are assertion scripts over the produced
   `service-area/` artifacts (file existence, yaml fields, stamp-check exit codes,
   transcript greps for tool-call ordering). LLM-judge graders (Tier 2 narrative checks)
   receive the mechanical checklist and must cite artifact lines.
3. **Calibration gate:** on creation or change, every eval is first run against its
   historical fixture reconstructing the old behavior and must FAIL it. A
   non-discriminative eval is a defect, tracked like a failed replay. Tier 2b variant: the
   calibration target is a merely-compliant reconstruction (mechanism as specced, gamed
   per the IFM), not a transcript.
4. Cadence: Tier 1 on every service-factory skill edit (pre-commit for the skill dir).
   Tier 2 on every behavioral change to the spine, and weekly. Tier 3 per release of the
   skill, or monthly, whichever comes first; SFE-31 requires a sandboxed/pool ticket
   approved by the user.
5. **Tier 2b script-mode targets:** the IFM evals whose fixtures hit pure functions run as
   direct script invocations against the actual gate scripts — SFE-40 (express-entry
   predicate), SFE-41 (stamp-check), SFE-43 (exit-verify checker), SFE-46 (loop counter),
   SFE-47 (Gate 0 completeness checker), SFE-50 (coverage-line validator), SFE-51
   (closure-matrix validator), plus SFE-44/54/55 (board-mutation logic). These join the
   Tier 1 pre-commit run (cheap pure-function calls); the Tier 2b paper replays
   (SFE-42/45/48/49/52/53) run on the Tier 2 cadence. **Build order (highest
   discriminative value per unit effort): SFE-40, SFE-41, SFE-43 first (IFM-1, 2, 4 —
   cheapest to test, highest impact), then SFE-42 and SFE-49 (IFM-3, 10) as
   replay/drill fixtures.**

## Scoring rubric

- **Per eval: binary PASS/FAIL.** Multi-clause evals fail on any clause; partial credit
  hides regressions.
- **Tier 1 = release gate.** 8/8 required (9/9 once SFE-56 below is counted in this
  suite). Any Tier 1 fail blocks shipping the skill change.
- **Tier 2 ship bar:** ≥14/16, with zero fails among criticals **SFE-10, 13, 15, 16, 21**
  (repro-first, no-unsourced-solved, confabulation catch, closure matrix, alias sweep —
  the five most expensive historical faults).
- **Tier 2b ship bar:** ≥13/16, with zero fails among criticals **SFE-40, 41, 42, 43, 44**
  (IFM-1..5 — the highest/very-high-impact inferred modes: express evasion, stamp
  laundering, library over-trust, exit-parity hole, cross-domain refute). A critical Tier
  2b fail blocks shipping the same as a Tier 1 fail: it proves a gate can be satisfied by
  merely-compliant form without substance.
- **Tier 3:** each drill logged pass/fail with transcript + artifact refs; two consecutive
  fails of the same drill = blocking defect on the skill.
- **Suite score reported as a quadruple, never a single number:** `T1 x/9 · T2 y/16 ·
  T2b z/16 · T3 w/7` (an aggregate would let a Tier 1 fail hide behind Tier 2 volume).
  Optional trend headline for dashboards: weighted 0.35/0.30/0.15/0.20 (T1/T2/T2b/T3),
  computed only when T1 is 100%.
- **Suite health check:** if a real incident occurs that no eval would have caught, that
  is a suite fail regardless of scores; the post-mortem must add the missing eval (design
  rule 5).

---

## Addendum — evals added after this suite was first authored

Two evals were added once Phase 9's learning loop and the skill's own version discipline
became gated mechanisms rather than prose (design rule 5: every RCA adds or amends at
least one eval). Both are Tier 1 (script-mode, cheap, run every time) and are counted in
the Tier 1 denominator above.

### SFE-56 — Learning harvest cannot be narrated, only done
- **Guards:** D4 (Phase 9 enriched learning loop) · the "DONE = said it" fault applied to
  the self-learning loop itself.
- **Fixture:** four variants — (1) a hardened run with real knowledge-facts + a resolving
  playbook `plus_one` + a fully-accounted retro; (2) a legitimate no-cause/parked run
  (facts_none_reason set); (3) a run that narrates "playbook +1, knowledge-facts emitted"
  in chat while `knowledge-facts.yaml` stays empty or absent; (4) a "well-formed theater"
  run with a phantom playbook id, an unaccounted low `factory_fitness`, or an undrained
  parking lot.
- **Pass:** (1) and (2) pass the `learning_harvest.py` gate (exit 0); (3) and (4) are
  both rejected (non-zero), each for a different mechanical reason (empty/missing facts;
  phantom playbook id; unaccounted fitness score; undrained lot entries).
- **Fail (merely-compliant):** a run that only narrates the harvest in its final message
  closes cleanly because nothing checks the artifact — the exact fault this eval exists
  to catch.
- **Mode:** script (four fixtures against the actual `learning_harvest.py` gate).

### SFE-60 — Version guard: the skill cannot drift from its own spec
- **Guards:** the version↔improvement law and the no-drift law (see
  `laws-of-execution.md` §Law 5) · this doc's own design rule 5 (a skill change must be
  traceable).
- **Fixture:** (1) a hardened skill directory: `SKILL.md` version matches the
  `CHANGELOG.md` top entry, a versioned spec exists under `docs/spec/`, `spec_source`
  resolves to it, and no carried spec file contains an external retro-folder reference;
  (2) a version-drifted variant (SKILL.md bumped, CHANGELOG not, or vice versa); (3) a
  variant where a carried spec file still contains an external-copy reference.
- **Pass:** (1) passes `version_guard.py` (exit 0); (2) and (3) are both rejected
  (non-zero), each naming the specific drift.
- **Fail (merely-compliant):** a skill edit ships without a matching changelog entry, or
  the "self-contained spec" claim is untrue because a spec file still points at an
  external copy that can drift out from under it — both invisible without this gate.
- **Mode:** script (three fixtures against the actual `version_guard.py` gate).
