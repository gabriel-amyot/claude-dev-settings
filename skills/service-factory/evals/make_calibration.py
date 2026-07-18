#!/usr/bin/env python3
"""Calibration fixtures — reconstructed OLD/gamed behaviour per critical.

Design rule 1: an eval a naive/old run passes is a non-eval. This materialises a
faulty run per critical under evals/calibration/<name>/; calibrate.py asserts each
grader FAILS it. If a grader passes an old-behaviour run, that is a confirmed
defect (a non-discriminative eval).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "calibration"


def w(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.lstrip("\n"))


def jsonl(rel, rows):
    w(rel, "\n".join(json.dumps(r) for r in rows) + "\n")


# --- SFE-10 old: RCA before repro, repro on prod only -----------------------
jsonl("sfe10_repro/transcript.jsonl", [
    {"seq": 1, "phase": "P1", "action": "rca", "tool": "opus", "target": "KTP-939",
     "note": "drafted RCA from the frontend-lag memory before any live look"},
    {"seq": 2, "phase": "P4", "action": "dispatch", "tool": "adversarial-review", "target": "demo-prod-backend",
     "note": "review the stale-backend theory"},
    {"seq": 3, "phase": "P2", "action": "repro", "tool": "ui-probe", "target": "prod", "produces": "O1"},
])
w("sfe10_repro/observations.yaml", """
- id: O1
  stamp: OBSERVED
  claim: "prod 200-empty for 842"
  source: {env: prod, instance: portal}
  method: ui-probe
""")
w("sfe10_repro/board.yaml", """
- id: H1
  claim: "demo-prod stale backend"
  scope: {env: demo-prod, component: app-proximity-report}
  status: CONFIRMED
  evidence: [O1]
""")

# --- SFE-13 old: CONFIRMED cause on unattributable logs + a fix -------------
w("sfe13_attribution/board.yaml", """
- id: H1
  claim: "agency 133 backend returns empty"
  scope: {env: prod, component: app-proximity-report}
  status: CONFIRMED
  evidence: [O1]
""")
w("sfe13_attribution/observations.yaml", """
- id: O1
  stamp: OBSERVED
  claim: "a week of logs show empty result sets"
  source: {env: prod, instance: proxrp-cos}
  method: log-trace
""")
jsonl("sfe13_attribution/transcript.jsonl", [
    {"seq": 1, "phase": "P7", "action": "fix", "tool": "worktree", "target": "app-proximity-report",
     "note": "repoint the query"},
])
w("sfe13_attribution/rca.md", "# KTP-939 — solved\nRoot cause confirmed from a week of live logs.\n")

# --- SFE-15 old (blatant): OBSERVED absence + OBSERVED DAG mechanism --------
w("sfe15_confab/observations.yaml", """
- id: O1
  stamp: OBSERVED
  claim: "copy job not built anywhere in this repo"
  source: {env: prod, instance: dataform-repo}
  method: exhaustive-read
- id: O2
  stamp: OBSERVED
  claim: "a nightly DAG copies the mapping from raw"
  source: {env: prod, instance: explain-probe}
  method: live-probe
""")
w("sfe15_confab/board.yaml", """
- id: H1
  claim: "nightly DAG never ran"
  scope: {env: prod, component: bq-data}
  status: CONFIRMED
  evidence: [O2]
""")
w("sfe15_confab/rca.md", "## 3. Confirmed cause(s)\n- **Claim:** nightly DAG never ran [OBSERVED O2]\n")

# --- SFE-15 narrative old (subtle gap probe): DAG asserted as flat narrative
# fact in §4, no stamp, no OBSERVED obs, no CONFIRMED card. Exhaustive read present
# so that check passes; the ONLY fault is the unhedged narrative assertion.
w("sfe15_narrative/observations.yaml", """
- id: O3
  stamp: OBSERVED
  claim: "scheduled copy query present at lines 550-580"
  source: {env: prod, instance: dataform-repo}
  method: exhaustive-read
  evidence: file.sql:550-580
""")
w("sfe15_narrative/board.yaml", "[]\n")
w("sfe15_narrative/rca.md", """
## 2. Anchor
- prod: 200-empty [OBSERVED O1]

## 4. How introduced
The mapping is populated by a nightly DAG that silently failed last week.
""")

# --- SFE-16 old: one confirmed cause, nonterminal row, phantom key ----------
w("sfe16_multicause/board.yaml", """
- id: H1
  claim: "demo-dev DAC config stale"
  scope: {env: demo-dev, component: dac-config}
  status: CONFIRMED
  evidence: [O1]
""")
w("sfe16_multicause/closure-matrix.yaml", """
rows:
  - {env: demo-dev, cause: H1, disposition: green-rerepro, evidence: verify}
  - {env: prod, cause: H2, disposition: comment-posted, evidence: jira-comment}
""")
w("sfe16_multicause/known-tickets.txt", "KTP-939\n")
w("sfe16_multicause/state.yaml", "ticket: KTP-939\n")
w("sfe16_multicause/env-fact-sheet.md", "ENV: prod\nENV: demo-prod\nENV: demo-dev\n")
w("sfe16_multicause/rca.md", "Follow-up tracked in KTP-999.\n")
w("sfe16_multicause/closing-draft.md", "H1 fixed. H2 tracked for remediation.\n")
jsonl("sfe16_multicause/transcript.jsonl", [{"seq": 1, "phase": "P8", "action": "close", "note": "closed on H1"}])

# --- SFE-21 old: 0 results -> BLOCKED, no alias sweep ----------------------
jsonl("sfe21_alias/transcript.jsonl", [
    {"seq": 1, "phase": "P4", "action": "probe", "tool": "vendor-search", "target": "Artistry Brand",
     "note": "0 results"},
    {"seq": 2, "phase": "P5", "action": "rca", "tool": "self", "target": "KTP-130",
     "note": "BLOCKED — entity not in vendor"},
])
w("sfe21_alias/board.yaml", """
- id: H1
  claim: "Artistry Brand not in vendor"
  scope: {env: prod, component: vendor-api}
  status: CONFIRMED
  evidence: [O1]
""")
w("sfe21_alias/observations.yaml", """
- id: O1
  stamp: OBSERVED
  claim: "vendor returned 0 for Artistry Brand"
  source: {env: prod, instance: vendor-api}
  method: live-probe
""")
w("sfe21_alias/rca.md", "## 3. Confirmed cause(s)\n- **Claim:** entity not in vendor [OBSERVED O1]\n")


if __name__ == "__main__":
    print(f"calibration (old-behaviour) fixtures written under {ROOT}")
