# Wayfinder failure-mode dossier — proven modes only

**Date:** 2026-09-30 · **Scope:** the wayfinder harness (SKILL.md 0.3.0, `wayfinder_runs.py`, `wayfinder-report-back`, `wayfinder-viewer`)
**Evidence base:** 33 traced runs across 4 maps (`runs/INDEX.md`), the raw telemetry in `runs/map-22.yaml` and `runs/map-38.yaml`, the interim reflection on #204, the cross-system class evidence on #135, and **live measurement of map #22 taken on 2026-09-30**.

**Admission rule for this dossier:** a failure mode is listed only if it has at least one instance that was *observed*, not predicted. Hypotheticals are excluded by construction. Each mode carries its evidence and the provenance of that evidence (`MEASURED` = verified first-hand today; `TELEMETRY` = recorded friction in a run trailer; `SECONDARY` = asserted in the 2026-09-29 run report, not independently re-verified here).

---

## Core assumption: what wayfinder actually is, mechanically

Everything below follows from one property of the design.

> **The map is a write-once cache of the world's state, and nothing in the harness ever invalidates it.**

Wayfinder records assertions — a ticket body, a `Decisions so far` line, a blocking edge, an assignee, a `Not yet specified` patch. Every one is true at the instant it is written. The world then moves: MRs merge, other vehicles execute tickets, sibling maps ratify contradicting decisions, priorities change. **No verb in the harness re-reads.** There is no freshness stamp, no TTL, no re-verification step in `chart`, `resolve`, `report`, or the frontier query.

Four corollaries, each of which shows up as a distinct failure mode below:

1. **Decay is invisible.** A stale assertion and a fresh one are byte-identical on screen. The reader cannot tell them apart, so the reader trusts both.
2. **The only inbound repair path is unenforceable.** `wayfinder-report-back` requires an *unrelated* session — one merging an MR, in a different repo, under a different skill — to remember that a GitHub issue on a planning map exists. Sender-side discipline across a system boundary has no mechanism behind it, so it fails at a rate proportional to how many other vehicles touch the same work.
3. **Mechanically-enforced queries run over unenforced inputs.** The frontier query is precise about labels, `parent`, `assignees` and `blockedBy`. All four are set by a free-form `gh issue create` / `gh issue edit` with no gate. A rigorous query over ungoverned data produces confident, wrong answers.
4. **The map summarises itself across sessions.** `Decisions so far` gists a ticket; the next session reads the gist, not the ticket. Error compounds forward and there is no back-pressure from the source.

The failure modes are not independent bugs. They are four faces of no-invalidation, plus one second-order mode where the repair loop itself is corrupted.

---

## FM-1 — Claims never expire, so the frontier silently empties

**Severity: critical. Live right now on map #22.**

The spec makes assignment the claim (SKILL.md:97: *"That assignee _is_ the claim: an open, unassigned ticket is unclaimed"*), and the frontier query drops any assigned ticket (SKILL.md:35). The claim is released by exactly one path: `resolve`, which closes the issue. **There is no un-claim verb anywhere in SKILL.md's 261 lines.**

Therefore any session that claims a ticket and does not resolve it removes that ticket from the frontier **permanently**.

That is not an edge case. It is the harness's own recommended autonomous pattern. The 2026-09-29 run dispatched eight read-only scouts, and the run report states the instruction plainly: *"Agents were instructed to post findings and stop."* Eight claims, zero resolutions.

### Evidence — `MEASURED` 2026-09-30

Map #22 has 13 open children. **Ten are assigned to `gabriel-amyot` with zero open blockers**, i.e. removed from the frontier by claim alone:

```
207 206 205 202 169 161 160 149 130 127   ← claimed, unresolved, not on the frontier
```

The spec's own frontier query, run verbatim today, returns **two** tickets:

```
171  Cutover acceptance: the closing issue where parity is proven reached
147  How the competitor layer is implemented
```

One of those two is poisoned (see FM-2). So a route session opening map #22 today sees **one** genuinely takeable ticket where the real takeable set is roughly eleven.

**This is a recurrence of a failure the spec has already fixed once, via a different cause.** SKILL.md:37 documents: *"Measured on a live map: the query reported a 2-ticket frontier where the real frontier was 6, hiding three takeable tickets including one due that day."* That cause was `totalCount` counting closed blockers, and it was fixed in 0.2.3. Same map, same symptom, same order of magnitude — **new cause**. The frontier query is a repeat offender because it depends on four ungoverned inputs (corollary 3) and each one can empty it independently.

### Why the existing design does not catch it

`harvest` detects untraced *closures* (GAPs). It has no notion of an untraced *claim*. A ticket claimed and abandoned is indistinguishable from a ticket being actively worked, forever.

---

## FM-2 — Declared blocking edges do not exist, and the closing gate is takeable

**Severity: critical. Live right now on map #22.**

Blocking is the harness's only structural safety property: it is what stops a session doing work out of order, and SKILL.md:99 makes it load-bearing (*"essential because it renders the frontier visually"*). Edges are written once at charting, in a second pass, through a raw `gh api` call with a documented footgun (the `issue_id` must be the database id, not the `#number`, and *"passing the `#number` silently targets the wrong issue"*, SKILL.md:34). **Nothing ever re-reads an edge to confirm it took.**

### Evidence — `MEASURED` 2026-09-30

The 2026-09-29 run report draws the map's dependency graph and states its legend explicitly: *"Solid edges are enforced blocking edges in GitHub, not prose."* It draws four solid edges into the cutover gate: `#130 → #171`, `#147 → #171`, `#127 → #171`, `#160 → #171`.

Queried against the authoritative endpoint the spec itself names (`/dependencies/blocked_by`):

| Issue | Declared blockers (prose + diagram) | Actual `blocked_by` |
|---|---|---|
| **#171** cutover acceptance | #130, #147, #127, #160 | **empty** |
| #130 | — | empty |
| #127 | — | empty |
| #160 | — | empty |
| #147 | #169 (per the map body) | #195 (closed) |

Four declared edges, **zero** of them real.

**The consequence is the worst available one.** #171 is the map's closing gate. The run report's own appendix records the standing instruction: *"Did not walk #171. It is the closing issue and the map says do not walk it to make progress."* Because its four blockers are absent and it carries no assignee, #171 is **unblocked, unclaimed, and first in map order** — so the spec's rule *"First in map order wins"* (SKILL.md:35) hands the closing gate to the next route session as its first pick. The only thing standing between an autonomous session and prematurely walking the cutover gate is a sentence of prose that the model has to remember.

### Second instance — `TELEMETRY` + `SECONDARY`

The map body recorded *"#147 is blocked by #169"*. Measured on 2026-09-29, two of #169's three branches leave #147 unchanged, and the real blocker was #195. The prose dependency was both mechanically absent and semantically wrong.

### Third instance — `TELEMETRY`, run `5af587d0` (#35)

> *"#35 was dispatched despite its own entry condition (wait for #31's approved v1 cut) being unmet; #31 is still open with prep only."*

The entry condition was stated in prose and wired as no edge, so nothing checked it.

---

## FM-3 — Tickets are created outside the index and become invisible

**Severity: high. Recurring; one live instance.**

The frontier query keys on three properties set at creation: `parent`, a `wayfinder:<type>` label, and (for tracing) a run trailer. `gh issue create` enforces none of them. A ticket missing any one drops out of the mechanism while still looking correct to a human reader.

### Evidence — labels missing, `TELEMETRY` ×2

- Run `e2953c70` (#127): *"#127 was created with no `wayfinder:` type label, so it was invisible to the label-based tooling and the report verb refused it. Nothing at creation time enforces the label."*
- Run `5af587d0` (#35): *"#35 was created with no wayfinder label, so the resolve tool refused it until the label was added."*

### Evidence — parent missing, `MEASURED` 2026-09-30

**#208** — *"Seven open defects in the shipped /planning map"* — carries `wayfinder:grilling` (a ticket type, not a map type) and **has no parent**. It is therefore a child of no map and appears in no frontier query anywhere. Its subject is map #22's own shipped artifact.

This matters for the solution space: the interim reflection's P2 proposes enforcing **the label**. P2 as drafted would not have caught #208, because #208's label is correct and its **parent** is missing. The enforcement surface is wider than the drafted fix.

### Evidence — trailers missing, `MEASURED` from telemetry files

`runs/INDEX.md` reports **9 untraced runs (GAPs) against 33 traced**, i.e. 27% of closures leave no evidence. Map #38 alone carries **8 GAPs** (#132, #131, #53, #51, #49, #45, #42, #40). Map #22 carries one (#129, *"closed with no run trailer — this run was never traced"*).

The harness is honest about this (SKILL.md:177: *"best-effort by placement, not a gate"*), and detection-not-prevention is a deliberate choice. It is listed here because 27% is the measured leakage rate that every downstream reflection reasons over, and FM-6 depends on that number.

---

## FM-4 — Stale premises: the map advertises finished work as frontier

**Severity: high. Three instances on map #22; four more outside wayfinder entirely.**

The direct expression of corollary 2. A ticket's body is a snapshot of the world at authoring time; work then happens elsewhere; nothing tells the map.

### Evidence — `TELEMETRY` ×3

| Run | Ticket | The stale claim | Cost |
|---|---|---|---|
| `6fde0804` | #29 | *"the ticket was already merged a week before this session was dispatched; map #22 still read 'built, awaiting merge', so the route was sent to do work that was done"* | A full session spent on finished work |
| `cc4a5108` | #28 | *"executed by another vehicle on 2026-09-18 and left open for a week reading 'blocked on Gabriel's go'. Nothing links a Jira board mutation back to the wayfinder ticket that authorised it, so the map kept advertising finished work as frontier"* | Seven days of false frontier |
| `2256982f` | #160 | *"the session was dispatched to fix Canada while the priority was the US backend; the handoff carried no priority context"* | Wrong work, correctly executed |

### Evidence — `SECONDARY`, #202

The map recorded #202 as closeable. Verified file-by-file on 2026-09-29, false: !396 is only partially recovered and four artefacts survive on a single closed branch. The run report records the mechanism: *"That claim was carried from a summary and never re-tested."* That is corollary 4 — compounding through the gist — producing a false status.

Note the interaction with FM-1: #202 is claimed-and-unresolved, so it is currently hidden from the frontier. When its claim is eventually released, a known-not-closeable ticket returns to the frontier carrying its original premise.

### Evidence that this is a class, not wayfinder hygiene — `SECONDARY`, #135

Four further recorded instances inside media-api and its DAC, a system with no shared code, tracker, or language with wayfinder. The #135 analysis states the generalisation: *"The class is not about repos that cannot verify their own claims. It is about any artifact that records a state and is read later as a fact."*

### Why `wayfinder-report-back` did not prevent any of them

It exists for exactly this and caught none of the three. It is a **sender-side** mechanism, and the sender is a session in another repo under another skill with no reason to know the map exists. This is the strongest argument in the evidence for a receiving-side check.

---

## FM-5 — Cross-map blindness lets sibling maps ratify contradicting architecture

**Severity: high. Two instances, one of them architectural and still unowned.**

The frontier query is scoped to one map by `parent.number`. Maps that share infrastructure have no mechanical link. SKILL.md has no notion of a cross-map dependency; sibling maps are named in prose in the `Notes` block, and prose is read by humans, not queries.

### Evidence — `TELEMETRY`, run `e2953c70` (#127)

> *"The ticket that had to be reconciled against (#17) lives on a SIBLING map (#13), so it never appears in this map's frontier and DECISIONS.md carried one line out of it. The spec has no notion of a cross-map dependency, so a session walking one map is structurally blind to a decision another map made about shared infrastructure."*

### Evidence — `SECONDARY`, the census store collision

Map #22's #148 was resolved and closed with a design naming **PostgreSQL + PostGIS as the census source of truth**. Sibling map #13 (*"Serve ZIP-level census to the Planning Map"*) had **already ratified BigQuery + Dataform `vw_census_*`**, with [KTP-1003](https://beklever.atlassian.net/browse/KTP-1003) owning the load. The 2026-09-29 scout measured the backend: **129 BigQuery file references against zero** references to Postgres, PostGIS, DuckDB or Cloud SQL.

The aggravating detail: **the design's own §2.1 flagged the collision, and nobody took it.** A closed ticket on map #22 now carries a ratified architectural decision that contradicts a ratified decision on map #13, and the contradiction was visible in writing before the ticket closed. Nothing in the harness routes a flagged cross-map conflict to an owner.

---

## FM-6 — The outcome vocabulary forces mislabelling, corrupting the repair loop

**Severity: medium, but it is the mode that degrades every other repair.**

Telemetry is the sole input to reflection, which is the sole mechanism by which the spec improves. `--outcome` admits five values (`resolved`, `out_of_scope`, `horizon`, `partial`, `abandoned`) and `mode` three (`chart`, `resolve`, `report`). Situations that fit none get recorded as the least-wrong neighbour, so the corpus the retro reasons over is contaminated at source.

### Evidence — `TELEMETRY` ×3

| Run | Situation | Recorded as | Why that is wrong |
|---|---|---|---|
| `e2953c70` (#127) | Route session corrects a claimed ticket and deliberately leaves it open | `mode: report` | `report` is explicitly defined as *"a session that was NOT walking the map"* (SKILL.md:166). Route work is filed as incidental work. |
| `fa622ea1` (#63) | Ticket whose **parent decision was retired**; measurements stay valid, purpose evaporates | `partial` | *"'partial' is the least-wrong outcome and does not say this"* |
| `e65105a3` (#22) | Disposal session: disposes deposited reports, creates 5 tickets, resolves none | `chart` | It charted nothing; it pollutes the charting signal |

### The second-order cost, `MEASURED`

`partial` appears 4 times against 12 `resolved` on map #22. The interim reflection flags that it cannot tell whether that is a real signal: *"Nobody has asked whether `partial` is doing too much work."* That is the corruption made visible — a third of the non-resolved outcomes are an overloaded bucket, so no conclusion can be drawn from the distribution.

Combined with FM-3's 27% untraced closures, the reflection corpus is both lossy and mislabelled. Every proposed fix in this dossier will be judged against that corpus.

---

## FM-7 — The spec is unreadable by the sessions required to follow it

**Severity: medium. Mechanically verified; it is an upstream cause of FM-3.**

`SKILL.md:5` is `disable-model-invocation: true`. A dispatched subagent therefore **cannot load the skill** and must work from a procedure relayed through its prompt by the parent session.

### Evidence — `TELEMETRY`, run `c76b0e54` (#31)

> *"the wayfinder skill is disable-model-invocation, so a dispatched route session cannot load it and must follow a relayed procedure instead"*

### Why it is a cause and not just an annoyance

Every rule in FM-3 (label at creation, parent at creation, trailer at closure) lives only in SKILL.md. A subagent that cannot read SKILL.md cannot follow them, and correctness then depends on how completely the parent paraphrased 261 lines into a prompt. The 2026-09-29 run dispatched **eight** such subagents. FM-1's ten stale claims and FM-3's orphan #208 are both consistent with relayed-procedure drift, though the dossier does not claim that link is proven.

---

## FM-8 — The mandated external adversarial review fails open

**Severity: medium. Two instances. Classification disputed — see below.**

Certain ticket types mandate an external adversarial pass. When the external tool fails, the ticket resolves anyway. The gate is advisory and its failure mode is silent acceptance.

### Evidence — `TELEMETRY` ×2

| Run | What happened | Outcome recorded |
|---|---|---|
| `5af587d0` (#35) | *"codex exec timed out four times with zero output (10/10/10/7 min), saturated by concurrent sessions; the required external adversarial review could not run"* | `partial` — ticket closed |
| `c76b0e54` (#31) | *"codex exec on a long document runs 20+ min and its piped output only flushes at exit; the mandated second adversarial pass did not return within the session"* | `resolved` — ticket closed |

Both tickets closed. Neither records in its outcome that a mandated gate did not execute. A later reader sees `resolved` and infers the review happened.

### The classification dispute, stated openly

The interim reflection routes this to `/gab-operationalize` as a `tooling` problem, on the grounds that `codex exec` behaviour is not a wayfinder spec concern. **This dossier disagrees and keeps it.** The tool's flakiness is indeed out of scope; what is in scope is that the harness has **no representation for "a mandated gate did not run"**, so it records a clean outcome over an incomplete process. That is a spec gap in the same family as FM-6, and it is directly relevant to hardening the local harness. Flagged for the adversarial reviewer to rule on.

---

## Mode summary

| # | Failure mode | Severity | Instances | Strongest provenance |
|---|---|---|---|---|
| FM-1 | Claims never expire; frontier silently empties | critical | 10 live | `MEASURED` today |
| FM-2 | Declared blocking edges do not exist; closing gate takeable | critical | 4 absent edges + 2 | `MEASURED` today |
| FM-3 | Tickets created outside the index (label / parent / trailer) | high | 2 + 1 live + 9 GAPs | `MEASURED` + `TELEMETRY` |
| FM-4 | Stale premises: finished work advertised as frontier | high | 3 (+4 cross-system) | `TELEMETRY` ×3 |
| FM-5 | Cross-map blindness; contradicting ratified architecture | high | 2 | `TELEMETRY` + `SECONDARY` |
| FM-6 | Outcome vocabulary forces mislabelling; corrupts repair loop | medium | 3 | `TELEMETRY` ×3 |
| FM-7 | Spec unreadable by dispatched subagents | medium | 1 (+ downstream) | `TELEMETRY`, verified in frontmatter |
| FM-8 | Mandated external adversarial review fails open | medium | 2 | `TELEMETRY` ×2 |

### Deliberately excluded

- **Per-type ticket quality bar.** Sits on the skill's own Horizon with stated reasoning. No run evidence in 33 runs contradicts that deferral.
- **One-ticket-per-session sizing.** Appears in zero friction entries.
- **`codex exec` reliability itself.** Real, but not a wayfinder spec concern. Only its *unrepresentability* is kept, as FM-8.
- **Agent-fleet saturating the human** (8 scouts → 7 rulings needed). One occurrence, and it is arguably the harness working correctly. Not admitted on a single instance.
