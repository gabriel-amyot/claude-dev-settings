```
derived_from: KTP-939 fault report (03), bug catalog (09), red-team (11)
```

# Threat model — fault/mode → gate/eval defense map

A maintainer's reference, not a narrative. Every row: a fault class or failure mode the
design defends against, which gate script and/or eval defends it, and how. Sourced from
the KTP-939 fault audit: a fully-audited historical session (34 verified faults, patterns
P1–P8), a companion 17-incident catalog (25 failure modes FM-1..25 / 17 success modes),
and a red-team pass anticipating failure modes of this design itself (IFM-1..16, cross-
cutting patterns NP1–NP4). Full narrative detail lives in `service-factory-spec-0.1.0.md`
(the design) and `evals-spec-0.1.0.md` (the acceptance harness); this document only maps
threat → defense.

**Gates** (`gates/*.py`, exit 0 = pass): `gate0_completeness`, `express_predicate`,
`stamp_check`, `coverage_line`, `loop_counter`, `exit_verify`, `closure_matrix`,
`learning_harvest`, `board_ops` (imported mutation library), `version_guard`.
**Evals:** Tier 1 SFE-01/02/03/04/05/06/07/08, Tier 2 SFE-10..25, Tier 2b SFE-40..55,
Tier 1 additions SFE-56/60, Tier 3 SFE-30..36.

---

## Part A — Historical patterns (P1–P8, KTP-939 fault report + bug-session catalog)

Each pattern rolls up several ranked faults (F-codes, fault report) and failure modes
(FM-codes, bug-session catalog). One row per pattern; representative codes only.

| Pattern | One-line description | Representative faults/modes | Defending gate/eval | How it defends |
|---|---|---|---|---|
| **P1** — Static-first epistemics | Ground truth (primary source, running app) consulted last; derived docs/diffs/logs exhausted first. | F01, F02, F11, F18, F25, F26 · FM-4, FM-6, FM-7, FM-10, FM-11, FM-22 | `gate0_completeness.py` (SFE-06) · Phase-ordering law (repro is Phase 2, before any RCA text) · SFE-10/30 (transcript: first act after Gate 0 is repro) | Gate 0 mechanically requires `jira-raw.json` + a confirmed (not inferred) observable on disk before intake can pass — the primary source cannot be skipped. Phase order is fixed (Law 3): no Cause-typed card may exist before an anchor. SFE-10/30 grade the transcript for "repro before theory" directly. |
| **P2** — Confidence laundering | Confidence entered as self-asserted input ("confirmed"/"(VERIFIED)") rather than a probe output; caveats demoted below headlines. | F03, F05, F06, F13, F24 · FM-1, FM-2, FM-3, FM-16 | `stamp_check.py` (SFE-01, SFE-41) | Every Cause claim must cite an `[OBSERVED]` ledger row of a method that fits the claim type; a document-level "(VERIFIED)" headline over an unstamped/mismatched claim is a mechanical, non-zero-exit reject — confidence cannot be applied at the document level, only earned per-claim. |
| **P3** — Cross-boundary identity conflation | A fact true of one env/component/system transplanted to another with no bridging check. | F03, F04, F06, F07, F11 · FM-4, FM-5, FM-17, FM-21 | `board_ops` scope rule (SFE-02) · `stamp_check.py` method-fitness (SFE-41) · SFE-12, SFE-42 (paper replays) | REFUTE only applies when the verdict's scope covers the claim's scope — a narrower verdict auto-splits per env instead of killing the whole card. A library-sourced topology fact cannot scope a Cause card unless it is itself a falsify-tested card or a live-probed observation (SFE-42 traps the un-carded version). |
| **P4** — Belief revision outsourced to the user | Contradictions held in hand and only resolved when the user forced them. | F04, F07, F10, F16, F19 · FM-9 | `board_ops` hunch-guard (SFE-03) · SFE-14 (challenge = falsification trigger) | A hunch card is undroppable except by a scope-covering REFUTE — prose dismissal cannot kill it. A user challenge is graded as requiring the NEXT dispatch to target the challenged card with a falsify-test, not to gather more confirming evidence elsewhere. |
| **P5** — Ceremony momentum | Process mass (RCA, review, ticket drafts, structured essays) displaces the cheap decisive act, even under an explicit user demand to shrink scope. | F02, F09, F20, F21, F27, F28 · FM-10, FM-15, FM-24, FM-25 | `express_predicate.py` + gate-budget table (SFE-20, SFE-36, SFE-53) · `loop_counter.py` + governor pulse (SFE-04, SFE-32) | The express lane is a mechanical predicate with a 2-blocking-stop / ≤15–30-min acceptance target, tested for BOTH budget and artifact completeness (SFE-53/36 fail either alone). The governor pulse fires on a hard clock/loop threshold regardless of narrative momentum. |
| **P6** — Preference and standing-rule blindness | Documented, always-on preferences (brevity, register, git-piping, batching) overridden by default habits. | F20, F21, F28, F29, F32, F33, F34 | `/caveman`-for-all-outputs (D3, Law 1 rule 7) · SFE-04 (format check only) | Weakest coverage in the suite (the acceptance harness's own honesty note flags P6 as thinnest): the register rule is spec law but has no dedicated mechanical gate beyond the S14 gate-report format check. Residual risk — not fully closed. |
| **P7** — Loop-closure failure | Approved/mandated closing actions silently dropped while the narrative asserts closure. | F14, F15, F22, F23, F30, F31 · FM-18, FM-19 | `closure_matrix.py` (SFE-16, SFE-51) · `learning_harvest.py` (SFE-56) · `gate0_completeness.py` (scaffold-before-intake, SFE-06) · resume staleness recheck (SFE-35, SFE-49) | The closure matrix requires a real, existing ticket key for any `tracked` disposition — a bare comment is a distinct non-terminal state that blocks "resolved." The learning-harvest gate refuses close until knowledge-facts/playbook/retro/parking-lot are materially on disk, not narrated. Scaffold-before-intake and resume-revalidation close the "session died, nothing to resume" and "stale board trusted verbatim" failure shapes. |
| **P8** — Serial unverified subagent relay | One accumulating-context prober handles many missions; errors self-audited instead of caught by a fresh falsifier; an orchestrator-scoped review treated as independent confirmation. | F08, F10, F12, F13 · FM-7, FM-8 | Library-first `Library:` line (Phase 4 design) + fresh-context probe dispatch (Law 3 P4) · `stamp_check.py` method-fitness (SFE-41) · SFE-05/33 (library hooks) | Every probe mission is fresh-context per design and carries a `Library:` stamp so the same accumulating-context agent cannot silently launder its own earlier error forward. A review's attack surface must include the orchestrator's own premises (the assumption-audit rule), so a self-scoped review cannot read as independent confirmation. |

---

## Part B — Inferred failure modes of the design itself (IFM-1..16, red-team)

These guard against the design's OWN mechanisms being gamed by a merely-compliant run
(form without substance), not historical episodes.

| IFM | One-line description | Defending gate/eval | How it defends |
|---|---|---|---|
| IFM-1 | Express fires on a single anchored env while other reported envs sit `parked-with-comment`, re-admitting a multi-cause bug through the design's own guard. | `express_predicate.py` (SFE-40) | Predicate reads the env universe from `env-fact-sheet.md`, never from the anchor set — any unanchored reported env is a mechanical decline, not a pass. |
| IFM-2 | Stamp-check validates citation *presence*, not *relevance* — a symptom-method row (`ui-probe`) laundered as support for a mechanism claim. | `stamp_check.py` (SFE-41) | Claim-type ↔ evidence-method compatibility check: a mechanism-class Cause requires a mechanism-method row (log-trace/exhaustive-read/red-test) or a domain-matched live-probe — a symptom-only row cannot satisfy it even though it genuinely resolves. |
| IFM-3 | A load-bearing library topology fact is trusted as confirmed context and never re-derived, even if stale. | Attest procedure (library-as-lead vs library-as-verified-fact) (SFE-42, live piggyback SFE-33) | A Cause scoped to a library-sourced topology fact requires either a falsify-tested board card for that fact or a live-probe observation backing it — un-carded library context cannot scope a Cause alone. |
| IFM-4 | Statistical exit standard certified under easier post-fix conditions than the pre-fix anchor (condition-parity + point-estimate-N holes). | `exit_verify.py` (SFE-43) | Blocks on condition-string mismatch between pre/post trials AND recomputes N from the conservative (lower-bound) confidence estimate of p̂, not the point estimate. |
| IFM-5 | Auto-refute kills a true hypothesis on valid-but-wrong-domain evidence (e.g. a config grep against a BQ-data claim); REVIVE never fires because nobody re-probes a "settled" area. | `board_ops` cross-domain cap (SFE-44) | A refute whose evidence source domain ≠ the claim's domain is capped at `strength: weak` and cannot drop the card from the active/requeue set — only a domain-matched disproof earns a strong REFUTE. |
| IFM-6 | Playbook recency-weighting lets yesterday's incident class monopolize seeding; the true (different-lane) cause appears only after brainstorm, near the loop cap. | Phase 3 seeding cap + `coverage_line.py` (SFE-45) | No single playbook origin may exceed 50% of seeded cards, and every in-scope layer must carry ≥1 card (or explicit N/A) at Phase 3 exit — the true lane is on the board at cycle 1, not post-brainstorm. |
| IFM-7 | Loop-cap materiality undefined — a stream of throwaway "new + confirmed" observations resets the counter every cycle, disarming the mechanical backstop. | `loop_counter.py` (SFE-46) | Counter resets ONLY on an observation that flips a card's status or seeds a new scoped card in the same cycle; a re-confirmed anchor or zero-information grep does not reset it. |
| IFM-8 | Gate 0 auto-passes on a non-empty but *inferred* (guessed) observable, with no human present to notice it isn't confirmed. | `gate0_completeness.py` (SFE-47) | A load-bearing observable accepts only `[REPORTED …]` (verbatim quote) or `[OBSERVED O-id]` provenance; `[INFERRED]`/`[ASSUMED]` withholds auto-pass and forces proceed-on-candidates + a reporter question. |
| IFM-9 | A broad, wrong human hunch is undroppable + jumps the queue + requeues first on every weak refute, monopolizing the governor budget. | `board_ops` hunch scope-specificity + weak-requeue priority decay (SFE-48) | A hunch is held to the same scope-specificity rule as any card (auto-split or `needs-narrowing` before dispatch); after repeated weak refutes it loses priority position while remaining undroppable in status. |
| IFM-10 | Resume-after-death trusts a stale on-disk board verbatim; an overnight environment change (host restored, data backfilled) silently invalidates a CONFIRMED anchor. | Resume staleness recheck (Phase 0 / `session:pickup` design) (SFE-49, live piggyback SFE-35) | Crossing the staleness threshold or a nightly boundary forces a re-validation of every load-bearing anchor and CONFIRMED cause as the FIRST act on resume, before any further falsification or fix routing. |
| IFM-11 | "REFUTED cards ARE the elimination log" can only contain what was hypothesized — a never-seeded layer reads as invisibly covered by a tidy-looking eliminated list. | `coverage_line.py` (SFE-50) | Phase 3 exit emits a positive per-layer coverage line (≥1 card or explicit N/A); a zero-card in-scope layer is a mechanical WALL-flagged gap, never inferred as "covered" from the REFUTED set. |
| IFM-12 | Closure `tracked` theater — an owner handoff closed on a bare posted comment with no real follow-up ticket. | `closure_matrix.py` (SFE-51, reuses SFE-16's key-existence check) | `tracked` is legal only with an existing, verified ticket key; a bare comment is the distinct non-terminal disposition `comment-posted`, which blocks a "resolved" close. |
| IFM-13 | The 45-min pulse is time-triggered, not progress-aware — it can fire seconds before a pre-declared decisive burst lands, and a fatigued human discards it. | Governor pulse decisive-burst deferral (SFE-52) | A burst marked `decisive: true` due to land within the pulse window either defers the pulse or adds a 5th "await" option; discarding it anyway requires one explicit extra confirmation naming the burst. |
| IFM-14 | The anti-ceremony design becomes its own ceremony — the express lane cuts human stops but not artifact overhead, or an implementation silently skips artifacts to hit the time budget. | Express artifact-presence check + budget (SFE-53 paper, SFE-36 live) | Both branches (wall-clock AND artifact completeness) are graded together; passing only one is a FAIL — genuine minimalism is the only way to pass both. |
| IFM-15 | Two parallel probes reading the same signal are counted as independent confirmation, upgrading a card to `strength: strong` on one fact seen twice. | `board_ops` strength-scorer dedupe (SFE-54) | Observations sharing an identical `source` signature collapse to one effective observation for strength purposes — duplicate-source evidence never upgrades strength on its own. |
| IFM-16 | Two mutually-falsifying cards oscillate REFUTED↔REVIVED forever; COUNT never converges. | `board_ops` bounded REVIVE + oscillation escalation (SFE-55) | `revive_log` is bounded at ≤2 entries per card; at the bound, an oscillating pair escalates as "unstable board" to the human instead of looping unbounded. |

---

## Part C — Cross-cutting new-risk patterns (NP1–NP4)

| NP | One-line description | Defending gates/evals | How it defends |
|---|---|---|---|
| **NP1** — Presence ≠ substance | Every mechanical gate (stamp-check, Gate 0, closure matrix, loop counter) can be satisfied by well-formed structure with no real substance behind it. | `stamp_check`, `gate0_completeness`, `closure_matrix`, `loop_counter`, `learning_harvest` (SFE-41, 46, 47, 51, 53, 36, 56) | Each of these gates carries a materiality/relevance predicate layered on top of its presence check (method-fitness, provenance-type, real-ticket-key, status-changing observation, non-empty artifact content) — form alone cannot satisfy any of them. |
| **NP2** — Library-first over-correction | The fix for "rediscovering a documented fact" (never re-derive what the library says) creates a new risk: a stale library fact propagates unchallenged for the whole run. | Attest procedure's library-as-lead distinction (SFE-42) | A library-sourced fact may seed a lead, but scoping a Cause to it requires either a falsify-test on that fact as its own card, or a live-probe observation — the rule against re-deriving documented mechanisms does not extend to skipping verification of load-bearing scope claims. |
| **NP3** — Silent removal beats loud error | An area that never enters the board, or silently leaves it, looks the same as "thoroughly investigated and cleared" — absence is invisible. | `coverage_line.py`, `board_ops` cross-domain cap, Phase 3 seeding cap (SFE-40, 44, 45, 50) | Coverage is asserted positively (every in-scope layer needs ≥1 card or explicit N/A) rather than inferred from what happens to be in the REFUTED set; a cross-domain refute is capped weak instead of silently dropping a card; no single playbook can monopolize the seed and starve an under-represented layer. |
| **NP4** — Time/priority mechanisms assume a fresh, attentive, present human | The governor, pulse, and hunch-priority mechanisms move human load around but still terminate on human judgment at the WALL/EXIT/pulse — and degrade under fatigue or elapsed time. | Hunch weak-requeue decay, resume staleness recheck, decisive-burst pulse deferral (SFE-48, 49, 52) | A wrong broad hunch loses queue priority over time even though it stays undroppable; a resumed session re-validates stale state before trusting it; a pulse due to coincide with decisive evidence defers or demands an explicit extra confirmation rather than assuming the human will catch the timing themselves. |

---

## Meta-gates (defend the design's own integrity, not a KTP-939-era fault)

| Gate | Defends against | Eval |
|---|---|---|
| `learning_harvest.py` | The self-learning loop (D4) itself being satisfied by narration instead of a materialized artifact — "DONE = said it" applied to Phase 9. Rolls up under **P7** (loop-closure failure) as the newest instance of that historical pattern. | SFE-56 |
| `version_guard.py` | Spec drift: the skill's version silently diverging from its changelog, or the carried spec silently referencing an external copy that can change out from under it. Not a KTP-939-era fault — it defends the self-containment property this consolidation (D9, and this very document set) establishes. | SFE-60 |

---

## Reading this table

- A row with one gate and no eval id still has mechanical enforcement — its eval is
  implicit in the gate's own script tests; cross-check `evals-spec-0.1.0.md` if the
  precise SFE id matters.
- **P6** and the FM-5/FM-15/FM-17/FM-20 gaps noted in `evals-spec-0.1.0.md`'s coverage
  matrix are real, acknowledged gaps, not oversights in this table — they are delegated to
  other harness mechanisms (deploy-identity probe, branch/worktree guard hooks, circuit-
  breaker rule) or left as documented residual risk.
- This table is descriptive of the design as specified in `service-factory-spec-0.1.0.md`.
  When a gate script changes, re-derive the "how it defends" cell from the script, not
  from memory of this table.
