# dark-factory-v2 — 0.5.0 Hardening Spec

**Status:** Spec (ready to implement in a fresh session). Source: KTP-728 + KTP-699 trial retros.
**Decision basis:** ADR-003 (live-verify data claims). **Telemetry:**
`runs/run-2026-06-02-KTP-728.yaml`, `runs/run-2026-06-02-KTP-699.yaml`.

## What the trial proved

- Gates work (prediction #1): `HALT_PRESHIP` (728, AC PARTIAL by design), `BLOCKED_SPEC_QUALITY` (699).
- Scripting belt works: generator + 12 tests + staged load, zero review criticals, correct classification.
- The damage was upstream reasoning/staleness (prediction #2): a false data-layer blocker from a stale
  local checkout cost two abandoned runs. Fix the front gate's relationship to truth.

## Ranked changes (apply in order; top 3 are the high-value, twice-flagged ones)

### 1. Concierge live-verifies every data-layer blocker  [Contract 1] — HEADLINE (ADR-003)
Any open_question/blocker asserting a table/view exists-or-missing, a column present/absent/count, or a
serving path MUST be verified against the live source first: `bq show --schema` / `bq ls` / `bq query`
for data, `git show origin/dev:<path>` for code. Stale local trees are not evidence. Add a one-line
assumption audit to every blocker ("what established this; could the premise be false?"). If live
access is unavailable, mark the blocker `unverified` and flag it — do not assert it as fact.

### 2. Live-schema preflight feeding analyst/design  [Contract 1 → analyst/assumptions.json; Contract 2 reads it]
Before design writes column lists, run `bq show --schema` on every table in `affected-repos.json`; pin
exact column count + names into `assumptions.json` marked `VERIFIED`. Kills the F4 "no COUNTRY column"
and "22-vs-20 columns" errors. (Twice-flagged: 699 + 728 → promote.)

### 3. New demo brand ⇒ new advertiser id  [Contract 1]
A fabricated/new brand must NOT reuse an existing demo-advertiser entity (728 bound "Lumberjack
Pastries" to 827 = FitConnect). Add an advertiser-identity check: the id must be unused in BOTH the perf
tables AND the demo-agency registry. Cite KTP-699 / KTP-755 (same identity-collision class).

### 4. Flag / split backend-gated sub-ACs  [Contract 1]
When an AC sub-criterion depends on un-landed backend work (728: CD-layer needs
`CountyPerformanceBigQueryAdapter` to read CDUID; it filters COUNTY_FIPS only), the concierge names it
as a deferred sub-AC or recommends splitting the seedable part (province+FSA) from the backend-gated
part (CD). A single-AC ticket whose AC can't fully pass should be split or flagged at the gate, not
discovered at HALT_PRESHIP.

### 5. Structured review findings + QA test_ref on disk  [Contracts 5 + 6]
Review writes `review/findings.json` (even at criticals:0); QA writes `qa/result.yaml` with `test_ref`
(command + output path), not just a raw diff. 728's PARTIAL had to be reconstructed from the grill
report because review left only a 293KB diff and QA left no test_ref. (Twice-flagged: 699 + 728 → promote.)

### 6. Fix / document the resume path  [workflow.js + SKILL.md]
`resumeFromRunId` + `humanDecisions` returns `BLOCKED_NEEDS_HUMAN_AGAIN` off the cached concierge
verdict; the only reliable unblock was resolve-in-Jira + run-fresh. Either RE-RUN the concierge on
resume (so a ticket-side resolution is re-read) or have the orchestrator explicitly instruct
"resolve in the ticket + run fresh" instead of looping on a cached needs_human verdict.

## Cross-run pattern (promote, don't re-propose)
Improvements #2 (live prereq/schema probe before the gate) and #5 (structured findings + test_ref
before PASS) appear in BOTH the 699 and 728 retros. Two hits → bake into the contracts now.

## Done-when
- Contracts 1/2/5/6 + workflow.js/SKILL.md updated per the above; `node --check` clean.
- ADR-003 referenced; `CHANGELOG.md` 0.5.0 entry; SKILL.md version → 0.5.0.
- No ticket re-run in the hardening session (that's separate). Build blind — these are generic rules,
  no KTP-728/699 specifics in the spine or shared contracts (ADR-002 / 0.4.1 boundary still holds).
