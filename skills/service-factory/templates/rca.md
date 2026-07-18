# RCA — Service Factory

The one file every run fills. Slow path = full; express path = the ≤10-line card
at the bottom, SAME 7 headings. Evidence bar is identical on both paths; only the
document size collapses. All prose is `/caveman` register.

Every claim carries a stamp: `[OBSERVED <O-id>]` · `[INFERRED <from what>]` ·
`[REPORTED <by whom>]` · `[ASSUMED]`. The WALL (stamp-check gate) rejects any
load-bearing cause claim not backed by an `[OBSERVED]` row whose method fits the
claim — a symptom-method (ui-probe) cannot back a mechanism claim (IFM-2).

---

## 1. Symptom
- Reported (verbatim + reporter): `[REPORTED …]`
- Envs reported: `{…}`
- **Intermittency** (required whenever the report says "sometimes/intermittent"):
  rate `k/N`, correlating conditions (network/load/data), since when. Omit only if
  strictly deterministic → write `intermittency: n/a — deterministic`.

## 2. Anchor (per env)
One row per reported env. Symptom-surface proof (`[OBSERVED O-id]`, method),
reproduced signature (e.g. `500/fetch-failed`, `200-empty`, `UI-stuck`),
first-error time. An env with no anchor = `parked-with-comment` (and the express
lane is BLOCKED for the whole ticket — IFM-1).

## 3. Confirmed cause(s)
One block per cause (multi-cause is expected):
- **Claim:** …
- **Evidence:** `[O-ids]` (method must fit the claim type)
- **Stamp:** `[OBSERVED]`
- **Scope:** `{env: …, component: <git-ref repo-alias + path>}`  ← component is a
  git reference from the bibliothèque index, never a made-up label (D5).

## 4. How introduced
The grounded theory of how this entered the system (recent change / migration /
data event). Far-fetched theories are filtered. `[INFERRED …]` allowed here but
flag it.

## 5. Eliminated hypotheses
Each with its falsification evidence + strength (enum). **Distinguish REFUTED
(genuinely disproven) from SHELVED (not-refuted, skipped for budget — stays
revivable, excluded from the elimination log)** (D1). Cross-domain disproof caps
at `strength: weak` (IFM-5).
- **Layer coverage line (mandatory):** each in-scope stack layer (ui / backend /
  data / db / infra) → `≥1 card` or `N/A because …`. A zero-card layer is a
  WALL-flagged gap, not silent absence (IFM-11).

## 6. Open Questions / Unverified
The no-cause package lives here (best surviving hypothesis + everything eliminated
+ risk) — never a `Verdict:` line without a stamp (KTP-688 convention).
Unmapped-surface findings (unknown data source, un-checked-out repo) → flag to
librarian (D10), not a dead end.

## 7. Fix + follow-ups + hack-debt
- Per-cause disposition: `fix / Leo-ticket / owner-handoff` + closure criterion
  (green re-repro per env, OR a tracked follow-up **with a real ticket key** —
  bare comment ≠ tracked, IFM-12).
- Exit verification: same repro red→green per env per cause (flaky: `0/N` post vs
  `k/N` pre under the **same conditions**, N from the conservative CI bound — IFM-4).
- Hack-debt assessment: did the quick fix create future work / break architecture?
  → follow-up ticket.

---

## Knowledge harvest (Phase 9 — feeds the bibliothèque, D4)
- **Knowledge-facts learned this run:** each = {fact, provenance `inferred|verbatim`,
  raw-source link, back-link to this RCA}.
- **Playbook:** used an existing playbook? `+1 <playbook-id>`. Invented a new
  signature→checks path? → **playbook proposal** (reviewed, then made official).

---

## EXPRESS RCA CARD (fast path — ≤10 lines, same 7 headings)
```
SYMPTOM: <one line + intermittency n/a|k/N>            [REPORTED <who>]
ANCHOR:  <env: signature + O-id>                        [OBSERVED]
CAUSE:   <claim> @ <git-ref>                            [OBSERVED <O-id>]
INTRODUCED: <one line>                                  [INFERRED|OBSERVED]
ELIMINATED: <layer coverage: all layers carded/N-A>
OPEN: <none | …>
FIX: <disposition> · EXIT: <same-repro green>
HARVEST: playbook +1 <id> | proposal: <none|id>
```
