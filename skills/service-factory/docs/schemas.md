# Artifact contract (spec §4, as amended by D1/D5/D6/D7)

All files under `tickets/{PREFIX}/{EPIC|no-epic}/{ID}/service-area/`. Enums are fixed
(D6): an out-of-enum value is a gate reject, never an LLM sentiment call. `cost`,
`likelihood`, `strength` each carry a mechanical rubric — decidable, not vibes.

## board.yaml — hypothesis card
```yaml
- id: H3
  claim: "demo DAC dev block missing KTP-863 rewiring"
  scope: {env: demo-dev, component: dac-config}   # component = git-ref from the
                                                   # bibliothèque index, never freeform (D5)
  falsify_test: "read dev block, diff vs MR!21"
  cost: S            # S | M | L   (S=one read/probe, M=a trace, L=multi-step/build)
  likelihood: high   # low | med | high  (recency-weighted; high=touched recently)
  status: UNTESTED   # UNTESTED | CONFIRMED | REFUTED | INCONCLUSIVE | REVIVED | SHELVED
  strength: strong   # strong = direct observed proof/disproof in the claim's OWN scope
                     # weak    = inferred / cross-env / cross-domain / single-source
  evidence: [O7, O9] # observation ids
  verdict_scope: {env: demo-dev}   # REFUTE legal only if verdict_scope covers scope
  origin: playbook:config-drift    # playbook | hunch | differential | scout | express | library
  layer: infra       # ui | backend | data | db | infra  (or derived from component domain)
  intermittent: false
  revive_log: []     # bounded <=2 (IFM-16); at bound -> escalate "unstable board"
  justification:     # REQUIRED for status REFUTED | CONFIRMED | REVIVED | INCONCLUSIVE
    why: "verdict_scope demo-prod diff matched MR!21 exactly"  # why the verdict
    how: "read dev block, diffed vs MR!21 (O7)"               # how it was shown
    evidence_ref: gate-reports/probe-O7.md   # OPTIONAL pointer (obs id or gate-report path)
  # A bare status with no `justification.why`+`.how` on a non-trivial transition is a gate
  # reject ("killed" alone is not enough). UNTESTED is exempt (nothing was shown yet).
  how_killed: "REFUTED@demo-prod (O7); SHELVED r2 budget; REVIVED r3 on O12 new evidence"
  # ^ lineage: the human-readable refute->shelve->revive trail, so a mermaid RENDER of the
  #   board shows how each card died and what revived it. Rendered from board.yaml, never
  #   authored by hand.
  # D1: a card the budget skips is status SHELVED (tag `shelved: not-refuted, skipped-for-budget`),
  #     fully revivable, EXCLUDED from the elimination log. Only genuine disproof = REFUTED.
```

## observations.yaml — attested observation
```yaml
- id: O7
  stamp: OBSERVED    # OBSERVED | INFERRED | REPORTED | ASSUMED
  claim: "curl to retired host returns 000"
  source: {env: demo-dev, instance: proxrp-cos, traffic: probe}   # mandatory
  method: live-probe # live-probe | log-trace | exhaustive-read | red-test | ui-probe
  evidence: gate-reports/probe-O7.md
  verified_against: "dac-gcp-back-proxrp@abc123"
  n_trials: {k: 3, n: 3, conditions: "cold load"}   # required when intermittent-flagged
```

**Method fitness (IFM-2, enforced by `stamp_check.py`):** a mechanism-class cause (scope
component in a data/db/backend/infra/config domain) needs ≥1 evidence row with method in
{log-trace, exhaustive-read, red-test}, OR a live-probe whose source domain matches the
claim's. `ui-probe` alone is a symptom read and cannot back a mechanism cause.

## Claim stamps
On every ledger row AND every gate-report claim line: `[OBSERVED Oxx]` / `[INFERRED from Oxx]`
/ `[REPORTED by whom]` / `[ASSUMED]`. Load-bearing is structural: Cause blocks, the Narrative,
and OBSERVED/RULED-OUT lines must cite a row id.

## Other files
- **gate report** — `templates/gate-report.md` (S14, ≤12 lines, the only relay format).
- **rca.md** — `templates/rca.md` (7 headings; express = the ≤10-line card, same bar).
- **playbook** — `playbooks/<class>.md` (seeders, never gates; signature → ranked checks → sources).
- **parking-lot** — `- [type] one-liner (found: phase, clock)`; drained only at Phase 9.
- **closure-matrix.yaml** — `rows: [{env, cause, disposition, ticket?, evidence}]`;
  disposition in {green-rerepro, tracked (real key), comment-posted (non-terminal)}.

## knowledge-facts.yaml — Phase 9 harvest (D4, gated by `learning_harvest.py`)
```yaml
facts:                       # >=1 REQUIRED when any cause is CONFIRMED
  - fact: "vendor indexes by storefront name, not corporate parent"
    provenance: verbatim     # verbatim | inferred (D4 enum)
    raw_source: "observations.yaml#O2"   # or a run-dir file path — must resolve
    rca_link: rca.md
facts_none_reason: null      # legal only for no-cause/parked runs
playbook:
  plus_one: data-gap         # must resolve to playbooks/<id>.md; requires
                             # playbook-append.md (the appended source-incident
                             # lines) in the run dir — live runs also append to
                             # the real playbook file
  proposal: null             # or an id; requires playbook-proposal-<id>.md
  none_reason: null          # legal only without a confirmed cause
retro:                       # dark-factory Retro, minimal
  task_confidence: 92        # int 0-100 — is the BUG resolved?
  factory_fitness: 88        # int 0-100 — did the LINE perform well?
  deductions: [{points: 12, reason: "..."}]
  red_flags: []
  improvements: [{title: "...", detail: "..."}]   # feed the next run
```
Parking-lot drain convention (checked by the same gate): every entry line ends with
`| drained: proposal|ticket|dropped|noted`.

## Status-transition justification contract (NEW in 0.3.0)

Every non-trivial status transition must be justified inline on the card. A card whose
status is **REFUTED / CONFIRMED / REVIVED / INCONCLUSIVE** MUST carry a `justification`
block with a short **`why`** (why this verdict) + **`how`** (how it was shown), plus an
OPTIONAL `evidence_ref` pointer (an observation id or a `gate-reports/` path). **UNTESTED is
exempt** — nothing has been shown yet. A bare status with no `why`+`how` is a gate reject:
"killed" alone is not enough. Enforced by `board_ops.justify_transition` (a REFUTED/
CONFIRMED/REVIVED/INCONCLUSIVE card missing either field is rejected).

## EXIT output contract (NEW in 0.3.0)

At the **factory EXIT** — the whole run's terminal state, NOT every internal turn or
sub-run — the run MUST emit exactly three things:

1. the **RCA** (`rca.md`),
2. the **theory-map** (`board.yaml`, the durable living artifact — a mermaid tree is only
   a render of it), and
3. **exactly ONE** outcome of `{targeted-fix handoff | Jira ticket draft}`.

Zero outcomes, or both outcomes, is an exit violation. This is an exit obligation, not a
per-turn requirement: internal rounds emit board mutations and gate reports, only the
terminal state owes the full triple.
