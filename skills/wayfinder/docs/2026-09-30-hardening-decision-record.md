# Wayfinder hardening — decision record

**Date:** 2026-09-30
**Chain:** telemetry + live measurement → failure-mode dossier (8) → Codex adversarial review → adjudicated survivors (9) → solution candidates (18) → Codex adversarial review → this record.

| Artifact | Path |
|---|---|
| Dossier (superseded) | `docs/2026-09-30-failure-mode-dossier.md` |
| **Adjudicated failure modes S1–S9** | `docs/2026-09-30-failure-modes-survivors.md` |
| Solution candidates (18) | `docs/2026-09-30-solution-candidates.md` |
| Codex review 1 — modes | `/tmp/wf-codex-review-out.md` |
| Codex review 2 — solutions | `/tmp/wf-codex-solutions-out.md` |

---

## Codex review 2: outcome

18 solutions reviewed. **7 SHIP WITH FIX, 11 REJECT, 0 SHIP as printed.**

Real defects it caught in the proposed code, all accepted:

- **S9-A and S9-B both raise `NameError`.** `build_run` has no `closed` parameter or local; `run["closed"] = closed` cannot execute (`wayfinder_runs.py:285-310`).
- **S6-A is not a runnable insertion** as printed — a module constant followed by an indented `if` inside a function.
- **S3-A must classify the *latest relevant* trailer, not "any prior resolution."** An old resolution on a reopened ticket would otherwise close it again and discard the new answer. It must also read and validate `--body-file` *before* deciding to resume.
- **S1-A claims "first in map order"** but `_list_issues` establishes no ordering (`wayfinder_runs.py:350-375`), and it references an `audit --map` argument that S7-B never defines.
- **S1-B cannot fail on the observed bug.** Its fixture has five rows and bypasses `_list_issues`, so it cannot detect a 30-row truncation. Rejected as an S1 solution; survives only as a companion predicate test.
- **S4-B has an ordering bug that defeats its own purpose:** `cmd_frontier` returns early on an empty clean frontier, *before* the stale-claim block runs. The exact starvation case still prints only "EMPTY frontier."
- **S7-A would not have caught #208.** The orphan came from a session that did not know wayfinder existed; no creation-time write gate reaches it.

Its strongest structural point, accepted in full:

> Several proposed checks return success for absence of input — no edge block, no premises block, no sibling block. **That is the same false-green shape as the current empty frontier.**

And the self-check paradox: a model that wrote the wrong edge, premise, or sibling list will also approve it. A read-back proves GitHub *stored* a declaration; it cannot prove the declaration was *right*.

---

## Where Codex was wrong, and it changes its top recommendation

Codex opened with an "execution and trust fault": that `gh api repos/.../issues/N` and the dependency endpoints **return HTTP 404**, and on that basis it marked S2-A *"blocked on a working write API"* and downgraded S4-B.

**Measured in the real environment on 2026-09-30, after the review:**

```
gh api repos/gabriel-amyot/klever-project-management/issues/171 --jq .id
→ 5529979481

gh api repos/gabriel-amyot/klever-project-management/issues/147/dependencies/blocked_by --jq '[.[]|.number]'
→ [195]        rc=0
```

Both endpoints work. The 404 was an artifact of **Codex's own sandbox**, not of the toolchain. The author's earlier measurements of #171's absent edges used this same endpoint successfully.

This is worth recording plainly, because it is the session's sharpest lesson: **Codex wrote *"A 404 is a failed measurement, not evidence that an edge or assignment event is absent"* and then built its headline finding on its own 404.** A failed probe read as a fact about the world — the identical failure class as S1's empty frontier, S3's false success message, and S5's stale premises. No reviewer is outside the class they are reviewing.

**Consequences:** S2-A's precondition is satisfied; the preflight Codex demanded can actually be run. S4-B's timeline lookup also works (used to date the ten stale claims). Codex's *other* objections to S4-B stand: the `--paginate` multi-document JSON risk against `json.loads`, the early-return ordering bug, and that age is not proof of death.

Everything else in Codex's review survives.

---

## Adjudicated position

### Ship, in this order

| # | Solution | Required correction |
|---|---|---|
| 1 | **S3-A** resume-on-resolution-only | Classify the *latest relevant* trailer; read and validate `--body-file` before the resume decision; `--force` must state it will post a second comment. |
| 2 | **S6-B** effective outcome in `reflect` | Bucket name `OPEN_NOW`, not `STILL-OPEN`; missing/unknown `issue_state` → `UNKNOWN_STATE`, never counted as resolved; keep the raw outcome alongside. |
| 3 | **S6-A** refuse contradictory `report` | Make `CLOSING_OUTCOMES` a module constant; place the guard inside `cmd_report` after `outcome = args.outcome`. A successful `--close` flag is not proof the close succeeded — S6-B still required. |
| 4 | **S2-A** verified `block` + repair #171's four edges | Preflight both API surfaces first (now known to work); fail before the write if either is unavailable; on read-back failure report `unknown` and forbid a blind retry. |
| 5 | **S1-A** `frontier` subcommand | Only *after* the edge repair. Drop the `audit --map` reference; either implement map order or stop claiming it; treat a failed `blockedBy` read as an error, never `or {}`. |
| 6 | **S7-B** repo-wide orphan sweep | Wire it into an existing command or orientation — a defined-but-uninvoked subcommand detects nothing. Do not advertise "no orphans": unlabelled tickets are outside the scan. |
| 7 | **S2-B** edge manifest | Read-only audit. Reject malformed/duplicate lines; require the block on opted-in maps rather than passing green on absence. Drop `--apply`. |

**S1-A and the S2 edge repair are one release unit.** Shipping S1-A alone makes the real frontier visible with #171 — the closing gate, unblocked only because four declared edges do not exist — sitting first. This is the one hard sequencing constraint.

### Do not ship

S1-B as a standalone solution, S3-B, S4-A as prevention, S4-B, S5-A, S5-B, S7-A as the S7 fix, S8-A, S8-B, S9-A, S9-B.

### Data repair, required regardless of any solution

- **Release the ten stale claims on map #22** (#127, #130, #149, #160, #161, #169, #202, #205, #206, #207). Until this runs, the real frontier is 2 against a true ~12, and every other fix operates on a starved board. Record it as a `process` friction entry, not a silent tidy-up.
- **Wire the four missing edges into #171**, once `block` exists and its preflight passes.
- **Re-parent or close #208.**

---

## The four modes left with no acceptable solution

This is the most important output of the review and it is not softened.

| Mode | Why every proposal failed | What a real solution needs |
|---|---|---|
| **S4** claims never released | Both proposals depend on the actor. No ended session can invoke a release verb, and all agent sessions share one GitHub identity, so `me in holders` cannot prove ownership. A TTL invites claim theft on HITL tickets that legitimately sit for days. | A safe claim-owner identity (per-session, not per-account) or a reviewed-release protocol with read-back. Not age inference. |
| **S5** stale premises | Both declare success on missing input, and both ask the acting model to audit its own premise. Neither would have stopped #29 or #28, whose real state lived outside GitHub. | External-state evidence with a source link and timestamp, checked on the **selected** ticket only, that cannot report green on an unverifiable reference. |
| **S8** cross-map contradiction | The census collision *was already flagged in writing* inside the design and nobody took it. Another place to write a flag does not fix a failure to route one. | Actual ownership: one conflict ticket linked from both maps, whose closure or explicit disposition gates ratifying the disputed design. |
| **S9** outcome vocabulary | Both raise `NameError`; worse, a `--no-close` resolution leaves a trailer that trips S3-A's resume path on the next `resolve`, and retains the claim, worsening S4. | Route/open semantics that cannot trigger the close-on-trailer branch. Blocked behind S3-A landing. Add `parent_retired` alone as an interim. |

S4 and S5 are the two highest-frequency modes in the evidence. **The session ends with the two most common failures unsolved, and that is the honest result** — a proposal that appears to fix them while declaring green on absence would be worse than the gap.

---

## Out of scope, routed elsewhere

`codex exec` reliability → `/gab-operationalize`. A fresh instance occurred in this very session: a `codex exec` wrapped in `timeout` (absent on macOS) **exited 0 having run nothing**, and was caught only because the output file was checked. That is the FM-8 shape — a mandated gate failing open with a success code — and it is not a wayfinder spec concern.

Also noted and excluded as unproven: `harvest`/`reflect` both fetch before acquiring the lock (`wayfinder_runs.py:203-216, 968-980`), so two runs can publish in reverse order. Real interleaving, never observed to fire.
