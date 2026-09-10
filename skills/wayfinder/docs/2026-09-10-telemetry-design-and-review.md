# Wayfinder telemetry — design record and adversarial review

Built 2026-09-10 for wayfinder `0.2.0`. Three adversarial rounds against `codex exec -s read-only`
(codex-cli 0.149.1): rounds 1 and 2 against the design, round 3 against the implementation.

## The problem the design had to solve

`dark-factory` can enforce its Retro because a JS orchestrator (`dark-factory.workflow.js`) executes
the phase. Wayfinder is prose with no orchestrator, so the same shape copied over would have been a
skippable instruction. Three shapes were considered:

1. **Copy dark-factory.** A `contracts/9-retro.md` equivalent plus a per-run YAML the session writes.
   Rejected: the write is a separate step after the work, and a separate step in prose is skipped.
2. **GitHub-only.** Trailers in comments, no local store, everything derived on demand. Rejected in
   part: it gives no cross-map view without refetching every issue, and cross-map recurrence is the
   strongest signal for a spec change.
3. **Chosen: telemetry rides the mandatory artifact.** The trailer lives inside the comment the
   session already had to post, and one command does the post-and-close the spec already prescribed.
   The local store is a derived cache with a single writer.

## What it is honestly worth

Best-effort by **placement**, not mandatory. Nothing stops a session closing an issue in the GitHub
UI. What the design buys: the traced path is the easy path, and an untraced run is *detected* by
`harvest` as a GAP rather than vanishing. Every artifact says this in the same words.

## Round 1 — against the design

| Finding | Disposition |
|---|---|
| HIGH close guard not registered | Accepted; wired in tracked settings.json + `wired:` fixture assertion |
| HIGH chart has no mandatory artifact | Accepted; reworked, then found insufficient in round 2 |
| HIGH guard bypassable, fails open | Accepted; guard became warn-only and network-free |
| HIGH recurrence never fires by itself | Accepted; RECURRING now prints on every `resolve` from the local cache |
| MED retries duplicate telemetry | Accepted; `run_id` + dedupe |
| HIGH conflicts with external-post controls | Refuted on facts: `external-post-gate.sh` is unwired and its regex anchors on REST endpoint paths, not `gh issue comment`. Posting posture is inherited from the existing spec and recorded as such. |
| MED hook latency | Resolved by removing the network call |
| MED duplicates claude-reflect / gab-operationalize | Accepted as documentation; explicit ownership boundary |
| LOW derived data drifts | Accepted; single canonical store, index regenerated |
| LOW fixtures prove parsing only | Accepted; claim narrowed in the fixture header |
| HIGH reflection-by-label not terminal | Accepted; precondition moved into `reflect`, reflection made repeatable |
| MED existing maps have no reflection child | Accepted; `reflect` works on any map |
| MED `spec_fitness` is weak evidence | Accepted; **score cut entirely** |
| MED friction signatures brittle | Accepted; closed tag vocabulary, RECURRING keys on the tag |
| LOW version check unenforced | Accepted; pre-commit gate proposed |

## Round 2 — against the revised design

Codex opened by naming two dispositions as dishonest, correctly.

| Finding | Disposition |
|---|---|
| HIGH telemetry still silently fails | **Accepted.** Every "mandatory" claim removed from the tool docstring, CHANGELOG and SKILL.md. |
| HIGH the reflection ticket is a fig leaf for chart telemetry | **Accepted in part.** The false claim was removed. The ticket was kept, reframed as the human-facing retro prompt Gabriel asked for, explicitly not a gate. |
| HIGH `resolve` not recoverable after partial failure | **Accepted.** Resume, not force. |
| MED local persistence is gold plating | **Rejected in part.** `runs/` kept for the cross-map view. The **pre-commit version gate was cut** as disproportionate: a global `core.hooksPath` hook firing on every commit in every repo to serve one skill. The tag vocabulary was kept, because Codex's own round-1 finding said prose signatures do not recur. |
| HIGH a file lock is insufficient | **Accepted, and improved on.** `harvest`/`reflect` are the only writers and hold one `flock` across both the map file and the index. |

Added after round 2, not from a finding: `TELEMETRY_EPOCH` so pre-telemetry closures are not
permanent GAP noise; `resolve` refuses an issue with no `wayfinder:` label; `resolve` refuses an
issue claimed by another login.

## Round 3 — against the implementation

Every finding was a real code defect. All fixed.

| Finding | Fix |
|---|---|
| HIGH `reflect` writes the cache while the docs claim `harvest` is the only writer | Docs corrected to name both writers; both take the lock |
| HIGH shared `.tmp` filename lets two writers clobber each other | Temp name carries the pid |
| HIGH index can mix two harvest generations | One `flock` held across the map write and the index regeneration |
| HIGH `chart` non-idempotent: a failed reflection-issue create makes a retry post a second trailer | Order inverted — reflection ticket first, trailer second — plus an existing-trailer skip |
| HIGH no detector for a map missing its reflection ticket | `missing_reflection` in the harvest report, the printout and the index header |
| MED a malformed trailer crashes `regenerate_index` | `validate_run()` + `extract_trailers` returns (good, bad); malformed runs are reported, never iterated; the index is defensive too |
| MED `check` claimed a schema self-test it did not do | `check` now round-trips a trailer and asserts a scalar `friction` is rejected |
| MED map state hard-coded `OPEN` | `state` requested and used |
| MED `--limit 300` silently truncates both traversals | Limit raised and **saturation is a hard error**, because a short list means a missing GAP |
| LOW `--body` can exceed the argv limit on a long resolution | All comments post via `--body-file` through a temp file |

## Round 4 — verifying the round-3 fixes

Codex confirmed 6 of 9 fixed in code and refused to sign off on three, all correctly:

| Finding | Fix |
|---|---|
| NOT FIXED: `harvest --all` still had its own hard-coded `--limit 300` with no saturation check | Routed through `_list_issues`, so a truncated map list is the same hard error as a truncated child list. This was the shipping blocker. |
| NEW: `SKILL.md` still carried the stale "harvest is the only writer" claim after the tool docstring was corrected | Corrected to name both writers and the shared lock |
| PARTIALLY FIXED: `check`'s scalar-`friction` fixture was missing other required fields, so its rejection did not prove the friction check fired | The fixture is now an otherwise-valid run with only `friction` broken, and the assertion checks the rejection *reason* mentions friction |

## Round 5 — sign-off

All three verified in code. Codex: "I am satisfied this is sound enough to ship." Five rounds total,
against a stated maximum of five.

## Verification

- `python3 tools/wayfinder_runs.py check` — version coupling, trailer round-trip, schema rejection.
- `harvest --all` against the three live maps: 0 errors, correct `pre_telemetry_closures` split,
  `missing_reflection` fires on all three (none was charted under 0.2.0).
- `hooks/evals/run_hook_evals.py --hook wayfinder-close-guard` — 12/12 cases.
- Every mutating path exercised with `--dry-run` only. No live issue was modified.

## Known open item

The close guard is registered in `~/.claude-shared-config/settings.json` but **not** in the live
`~/.claude/settings.json`, which is outside this work's scope. Its fixture wiring assertion is
therefore designed-red until Gabriel applies it, the same convention `file-guard.sh` and
`config-protect.sh` already use here.
