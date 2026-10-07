# Wayfinder failure modes — the adjudicated survivor set

**Date:** 2026-09-30
**Process:** dossier (`2026-09-30-failure-mode-dossier.md`, 8 modes) → adversarial review by Codex (`codex-cli 0.158.0`, ~25 min, full review at `/tmp/wf-codex-review-out.md`) → re-verification of every contested and every new claim by the author.

**Admission rule:** proven failures only. A mode enters this list only with an instance that was observed — a live measurement, a telemetry entry, or an executable code path with a currently-satisfied precondition. Hypotheticals are excluded, including one real code race that has never been seen to fire.

---

## What the review changed

Codex confirmed 1 of 8 modes outright, weakened 6, refuted 1, and **found three defects the dossier missed** — one of which it ranked above everything the dossier had. Both of its top two finds were independently re-verified by the author and hold.

| Dossier claim | Ruling |
|---|---|
| FM-2 blocking edges absent | **CONFIRMED** |
| FM-1 claims never expire | **WEAKENED** on attribution — then partly restored by timestamp evidence Codex did not have (see S4) |
| FM-3 creation unguarded | **WEAKENED** — the frontier query does **not** filter on the type label. A missing label breaks `resolve`/`report`, not frontier membership. The dossier conflated the two. Its 27% GAP figure used the wrong denominator; correct is 9/42 = **21%**. |
| FM-4 stale premises | **WEAKENED** — 2 clean instances, not 3 |
| FM-5 cross-map blindness | **WEAKENED** — 1 instance described twice, not 2 |
| FM-6 vocabulary | **WEAKENED** — the tool accepts 7 outcomes and 4 modes, not 5 and 3 |
| FM-7 spec unreadable | **DROPPED** — `disable-model-invocation` blocks model *invocation*, not reading the file. No proven downstream miscreation. |
| FM-8 adversarial review fails open | **DROPPED from wayfinder** — SKILL.md mandates no external review for any ticket type. The mandate lives elsewhere. Routes to `/gab-operationalize`. |

**Quote-fidelity failures in the dossier, all conceded:** it placed "not prose" inside a quotation that does not contain it; marked a paraphrase as verbatim; inserted code marks into a telemetry quote; and attributed to `SKILL.md:166` a phrase that is actually in the CLI help at `wayfinder_runs.py:1152-1155`. These are corrected here and do not change any finding.

---

## The survivors, ranked by expected cost

Expected cost = how often it fires × what a firing costs × how invisible the firing is.

---

### S1 — The documented frontier query is truncated at 30 and returns **zero** today

**`MEASURED` 2026-09-30 by Codex, re-verified by the author. Severity: critical. Firing right now.**

`SKILL.md:35` gives the frontier query without `--limit`. `gh issue list` defaults to **30** issues. The repo has **153 open issues**, and map #22's children are not in the newest 30.

Measured:

| Query | Result |
|---|---|
| Exactly as SKILL.md:35 writes it | **0 tickets** |
| Identical query + `--limit 1000` | 2 tickets |

A session following the spec verbatim sees an **empty frontier** and concludes the map is finished.

**Why this is the top item.** This is the **third distinct cause** of "the frontier reads as empty" on the same line of spec. SKILL.md:36 documents the first (`blockedBy` is an object, not an array — `(.blockedBy | length)` returns 2 always). SKILL.md:37 documents the second (`totalCount` counts closed blockers; *"the query reported a 2-ticket frontier where the real frontier was 6"*). Both were found by being bitten, patched in place, and written up as traps. The third was introduced by the same pattern and sat undetected. The line has two paragraphs of warnings attached to it and is still wrong.

`wayfinder_runs.py:350-375` already protects the tool's own traversals with `--limit 1000` plus a saturation error. The human-facing query in the spec bypasses that protection entirely.

**Independent of S4.** Releasing every stale claim would not fix this. The truncation happens before the assignee filter runs.

---

### S2 — Declared blocking edges do not exist, and the closing gate is takeable

**`MEASURED` 2026-09-30. Severity: critical. `CONFIRMED` by Codex.**

Blocking is the harness's only structural safety property (`SKILL.md:99`). Edges are written once at charting through a raw `gh api` call with a documented footgun: the `issue_id` must be the database id, and *"passing the `#number` silently targets the wrong issue"* (`SKILL.md:34`). Nothing re-reads an edge to confirm it took.

The 2026-09-29 run report draws the dependency graph and states its legend: *"Solid edges are enforced blocking edges in GitHub"* (run report:105). Measured:

| Issue | Declared blockers | Actual |
|---|---|---|
| **#171** cutover acceptance | #130, #147, #127, #160 | **empty** |
| #147 | #169 (per map body) | #195 (closed) |

Four declared edges into the closing gate; **zero** real.

**The consequence is the worst available one.** #171 is the map's closing gate, and the standing instruction is not to walk it to make progress. It is unblocked, unclaimed, and first in map order, so `SKILL.md:35`'s *"First in map order wins"* hands the closing gate to the next session as its first pick. Note the interaction with S1: the gate is only *reachable* once the `--limit` bug is fixed, which makes S1's fix unsafe to ship on its own.

Codex's correction, accepted: the spec does give a verification command; what it lacks is any automatic verification.

---

### S3 — `resolve` closes an open ticket on **any** prior trailer and discards the answer

**`CODE PATH` + live precondition on three tickets. Severity: critical. Found by Codex, re-verified by the author.**

`wayfinder_runs.py:646-667`. The resume branch:

```python
existing = []
for comment in data.get("comments", []):
    good, bad = extract_trailers(comment.get("body", ""))
    existing.extend(good + bad)          # ANY trailer, valid or malformed

if existing and not args.force:
    ...
    gh("issue", "close", str(number), "--repo", REPO)
    print("  RESUMED: issue closed. No duplicate comment posted.")
    return 0
```

The branch exists to make a retry idempotent after a failed close. But it treats **any** trailer as proof of a prior resolution, including a `mode: report` trailer — which by definition is *not* a resolution. It returns before reading `--body-file`.

So `resolve --ticket <n> --body-file answer.md` on a ticket carrying an earlier report trailer will **close the issue, post nothing, and throw the answer away**, printing a success message.

**Live precondition, measured:** #127, #160 and #161 are all OPEN and all carry `mode: report` trailers (`runs/map-22.yaml:109-139, 202-231`). Any of the three is one ordinary command away from silent loss.

The code comment one line above says *"The effective outcome of a run is GitHub's issue state, never the trailer's stated intent"* — the check does the opposite of what the comment claims.

---

### S4 — Claims are never released, so the frontier starves

**`MEASURED` 2026-09-30, with timestamps. Severity: high.**

`SKILL.md:97` makes assignment the claim; `SKILL.md:35` drops any assigned ticket from the frontier. The claim is released by exactly one path — `resolve`, which closes the issue. **There is no un-claim verb.** Codex confirmed independently: *"The tool has no `unclaim` subcommand."*

Of map #22's 13 open children, **10 are assigned with zero open blockers**: #127, #130, #149, #160, #161, #169, #202, #205, #206, #207.

**Codex weakened this mode on attribution, arguing the dossier could not tie 10 claims to an 8-scout run and had not proven abandonment. That objection is answered by evidence Codex did not have.** Assignment timestamps from the issue timeline API:

| Ticket | Last assigned |
|---|---|
| #130, #149, #160, #161, #169, #202, #205, #206 | **2026-09-29T16:15:02 → 16:15:16Z** |
| #207 | 2026-09-29T16:22:45Z |
| #127 | **2026-09-14T20:11:36Z** |

Nine assignments inside a **22-second window** is a scripted batch, not nine human decisions. And #127 has been claimed and unresolved for **16 days**, which is abandonment by any reading.

What survives of Codex's objection, and is accepted: "permanently" is too strong — an assignment can be edited by hand, and the mode is starvation-until-manual-repair, not a permanent lock.

**Why the one existing guard is blind.** `cmd_resolve` does check for a foreign assignee (`wayfinder_runs.py:630-634`: *"An assignee is the claim, so an assignee who is not you is a live collision"*). Every agent session claims as `@me` → `gabriel-amyot`. All ten stale claims carry that identity, so the collision check can never fire for agent work. The guard protects against a case that does not occur and misses the one that does.

---

### S5 — Stale premises: finished work advertised as frontier

**`TELEMETRY` ×2 (narrowed from 3). Severity: high. Class confirmed outside wayfinder.**

| Run | Ticket | The stale claim |
|---|---|---|
| `6fde0804` | #29 | *"the ticket was already merged a week before this session was dispatched; map #22 still read 'built, awaiting merge', so the route was sent to do work that was done"* |
| `cc4a5108` | #28 | *"executed by another vehicle on 2026-09-18 and left open for a week reading 'blocked on Gabriel's go'. Nothing links a Jira board mutation back to the wayfinder ticket that authorised it"* |

**Narrowed per Codex, accepted:** #160 is a priority-handoff error and #202 is a false-closeability claim. Both are real defects but distinct mechanisms, so neither counts toward this mode's frequency.

**The class is confirmed outside wayfinder** (#135): four further instances in media-api and its DAC — a system sharing no code, tracker or language with wayfinder. The generalisation on #135: *"It is about any artifact that records a state and is read later as a fact."*

**Why `wayfinder-report-back` did not prevent either.** It is a **sender-side** mechanism, and the sender is a session in another repo under another skill with no reason to know the map exists. This is the strongest argument in the evidence for a receiving-side check.

---

### S6 — `report --outcome resolved` without `--close` inflates the resolved count

**`OBSERVED` in the telemetry. Severity: medium. Found by Codex.**

`--close` is optional on `report`; `--outcome` defaults to `resolved`. `harvest` records the real `issue_state`, but `reflect` totals on `outcome` alone (`wayfinder_runs.py:763-809, 1053-1056`).

Live in the data: `runs/map-22.yaml:202-231` shows #127 with `outcome: resolved` and `issue_state: OPEN`.

**The consequence is second-order and compounding.** The interim reflection on #204 reports "12 resolved" and reasons over that distribution. At least one of the twelve is an open ticket. Telemetry is the *only* input to the reflection that produces spec fixes, so a corrupted corpus degrades every repair — including the repairs proposed for everything else on this list.

---

### S7 — Tickets created outside the index

**`MEASURED` (parent) + `TELEMETRY` ×2 (label) + 21% trailer leakage. Severity: medium.**

Three properties are set by free-form `gh issue create` with no gate, and each fails differently:

- **Missing parent → invisible to every frontier query.** `MEASURED`: **#208** carries `wayfinder:grilling` (a ticket type) and has **no parent**, so it is a child of no map. Its subject is map #22's own shipped artifact.
- **Missing type label → breaks `resolve`/`report`, *not* frontier membership.** `TELEMETRY` ×2: #127 and #35 both created unlabelled; the tooling refused them until a human noticed. *Codex's correction is accepted and matters for the fix: the interim reflection's P2 enforces the label, which would not have caught #208.*
- **Missing trailer → untraced closure.** 9 GAPs against 42 total runs = **21%** (corrected denominator). Map #38 alone carries 8. This is a deliberate design choice (`SKILL.md:177`: *"best-effort by placement, not a gate"*), listed only because it sets the leakage rate that S6's corrupted corpus sits on top of.

---

### S8 — Cross-map blindness lets sibling maps ratify contradicting architecture

**1 instance, architectural, still unowned. Severity: medium-high on impact, low on frequency.**

The frontier query is scoped by `parent.number`. Sibling maps are named in prose in `Notes`; prose is read by humans, not queries.

Map #22's #148 closed with a design naming **PostgreSQL + PostGIS as the census source of truth**. Sibling map #13 had **already ratified BigQuery + Dataform `vw_census_*`**, with [KTP-1003](https://beklever.atlassian.net/browse/KTP-1003) owning the load. The scout measured **129 BigQuery file references against zero** Postgres/PostGIS/DuckDB/Cloud SQL references in the backend.

**The aggravating detail: the design's own §2.1 flagged the collision and nobody took it.** A closed ticket now carries a ratified decision contradicting another map's ratified decision, and the contradiction was visible in writing before the ticket closed. Nothing routes a flagged cross-map conflict to an owner.

Codex's narrowing accepted: this is one collision described twice, not two instances. It supports a visibility gap, not a recurrence rate.

---

### S9 — The outcome vocabulary forces mislabelling

**`TELEMETRY` ×2 (narrowed from 3). Severity: medium.**

| Run | Situation | Recorded as | Why wrong |
|---|---|---|---|
| `e2953c70` (#127) | Route session corrects a claimed ticket, deliberately leaves it open | `mode: report` | `report` means a session that was not walking the map. Route work filed as incidental. |
| `fa622ea1` (#63) | Ticket whose **parent decision was retired** | `partial` | *"'partial' is the least-wrong outcome and does not say this"* |

**Narrowed per Codex, accepted:** the disposal-session case is weaker than claimed — that run created 5 tickets and called itself an incremental chart run. Also corrected: the tool accepts **7 outcomes and 4 modes**, not 5 and 3, though `resolve` exposes them without semantic checks.

`partial` appears 4 times against 12 `resolved`, and per S6 at least one of those 12 is open.

---

## Excluded, and why

| Candidate | Why excluded |
|---|---|
| **`harvest`/`reflect` cache race** (`wayfinder_runs.py:203-216, 968-980`) — both fetch before acquiring the lock, so two runs can publish in reverse order | A real interleaving in code. Codex found **no observed firing**. The session's rule is proven failures only. Worth a cheap fix if one is free, but it does not earn a solution slot. |
| **FM-7, `disable-model-invocation`** | Blocks model *invocation* of the skill, not reading `SKILL.md` as a file. One complaint, no proven downstream miscreation. |
| **FM-8, external adversarial review fails open** | SKILL.md mandates no external review for any ticket type; the mandate lives in another document. Not a wayfinder spec mode. Routes to `/gab-operationalize` — with a fresh instance from this very session: a `codex exec` wrapped in macOS-absent `timeout` exited **0** having run nothing, and the failure was only caught because the output file was checked. |
| **Per-type ticket quality bar** | On the skill's own Horizon with stated reasoning; nothing in 42 runs contradicts the deferral. |
| **One-ticket-per-session sizing** | Zero friction entries. |
| **Agent fleet saturating the human** | One occurrence, and arguably the harness working correctly. |
