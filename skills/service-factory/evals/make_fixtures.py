#!/usr/bin/env python3
"""Materialise the Layer A eval fixtures on disk under evals/fixtures/.

Each script-mode SFE gets a HARDENED fixture (the gate must handle it correctly)
and, where the discrimination is not inherent in the input, an OLD-BEHAVIOUR /
v3-COMPLIANT fixture the gate must catch (design rule 1: an eval a naive gate
passes is a non-eval). Re-run any time; idempotent.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent / "fixtures"


def w(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.lstrip("\n"))


# --- SFE-01 stamp check -----------------------------------------------------
w("sfe01_good/board.yaml", """
- id: H1
  claim: "demo DAC dev block missing KTP-863 rewiring"
  scope: {env: demo-dev, component: dac-config}
  status: CONFIRMED
  evidence: [O7]
""")
w("sfe01_good/observations.yaml", """
- id: O7
  stamp: OBSERVED
  claim: "dev block absent from DAC config"
  source: {env: demo-dev, instance: dac-config}
  method: exhaustive-read
  verified_against: "dac-gcp-back-proxrp@abc123"
""")
w("sfe01_good/rca.md", """
# KTP-939 service area — RCA

## 3. Confirmed cause(s)
- **Claim:** demo DAC dev block missing rewiring [OBSERVED O7]
""")

# old behaviour: unsupported cause + "solved" headline over an unstamped claim
w("sfe01_bad/board.yaml", """
- id: C1
  claim: "root cause is stale backend"
  scope: {env: prod, component: bq-data}
  status: CONFIRMED
  evidence: []
""")
w("sfe01_bad/observations.yaml", "[]\n")
w("sfe01_bad/rca.md", """
# KTP-939 — solved

## 3. Confirmed cause(s)
- **Claim:** root cause is stale backend
""")

# --- SFE-41 stamp relevance (claim-type <-> method) -------------------------
w("sfe41_bad/board.yaml", """
- id: H2
  claim: "BQ data gap for advertiser 842"
  scope: {env: prod, component: bq-data}
  status: CONFIRMED
  evidence: [O7]
""")
w("sfe41_bad/observations.yaml", """
- id: O7
  stamp: OBSERVED
  claim: "panel shows 0 results for 842"
  source: {env: prod, instance: portal-frontend}
  method: ui-probe
""")
w("sfe41_bad/rca.md", """
## 3. Confirmed cause(s)
- **Claim:** BQ data gap for 842 [OBSERVED O7]
""")

w("sfe41_good/board.yaml", """
- id: H2
  claim: "BQ data gap for advertiser 842"
  scope: {env: prod, component: bq-data}
  status: CONFIRMED
  evidence: [O7, O8]
""")
w("sfe41_good/observations.yaml", """
- id: O7
  stamp: OBSERVED
  claim: "panel shows 0 results for 842"
  source: {env: prod, instance: portal-frontend}
  method: ui-probe
- id: O8
  stamp: OBSERVED
  claim: "842 has zero rows in normalized_klever_stores_mapping"
  source: {env: prod, instance: bq-dataset}
  method: exhaustive-read
  verified_against: "klever-data-workflow@def456"
""")
w("sfe41_good/rca.md", """
## 3. Confirmed cause(s)
- **Claim:** BQ data gap for 842 [OBSERVED O8]
""")

# --- SFE-06 / SFE-47 Gate 0 completeness ------------------------------------
_SCAFFOLD = {
    "STATUS_SNAPSHOT.yaml": "ticket: KTP-939\ncompletion: 0\n",
    "ac.yaml": "acceptance_criteria: []\n",
    "state.yaml": "phase: intake\nticket: KTP-939\n",
    "intake.yaml": "expected: works\nactual: broken\nenvs: [demo-dev]\n",
    "jira-raw.json": '{"key":"KTP-939","fields":{"summary":"stuck"}}\n',
}
for f, t in _SCAFFOLD.items():
    w(f"sfe06_good/{f}", t)
w("sfe06_good/env-fact-sheet.md", """
# Env fact sheet
Library: documentation/bibliotheque/stack/bigquery/klever-external-data.md — shared PROD backend
ENV: demo-dev
OBSERVABLE: 500 to retired host on POI panel [REPORTED by Rajan] "it's stuck spinning"
""")

# no-files variant: agent claims "ticket reviewed" but nothing on disk
w("sfe06_nofiles/env-fact-sheet.md", """
Library: silent (checked INDEX/ALIASES for proximity report)
ENV: demo-dev
OBSERVABLE: spinner [REPORTED by Rajan] "stuck"
""")

# SFE-47: load-bearing observable is INFERRED, no reporter quote/O-id; reporter Q drafted
for f, t in _SCAFFOLD.items():
    w(f"sfe47_inferred/{f}", t)
w("sfe47_inferred/env-fact-sheet.md", """
Library: documentation/bibliotheque/stack/dev-backend-topology.md
ENV: demo-dev
OBSERVABLE: spinner for advertiser X [INFERRED from ticket text]
""")
w("sfe47_inferred/reporter-question.md", "Draft: @Rajan which advertiser + URL did you see the spinner on?\n")

# --- SFE-50 layer coverage --------------------------------------------------
w("sfe50_ok/board.yaml", """
- id: H1
  claim: config drift
  scope: {component: dac-config}
- id: H2
  claim: bq gap
  scope: {component: bq-data}
- id: H3
  claim: backend adapter
  scope: {component: app-proximity-report}
- id: H4
  claim: panel state
  scope: {component: frontend}
- id: H5
  claim: mysql seed
  scope: {component: user-mgmt-db}
""")
# infra covered by H1 (dac-config -> infra); ui by H4; data by H2; backend by H3; db by H5

w("sfe50_gap/board.yaml", """
- id: H2
  claim: bq gap
  scope: {component: bq-data}
- id: H3
  claim: backend adapter
  scope: {component: app-proximity-report}
- id: H4
  claim: panel state
  scope: {component: frontend}
- id: H5
  claim: mysql seed
  scope: {component: user-mgmt-db}
""")
# infra layer has zero cards and no N/A -> gap

# --- SFE-51 / SFE-16 closure matrix -----------------------------------------
w("sfe51_ok/closure-matrix.yaml", """
rows:
  - {env: demo-dev, cause: H1, disposition: green-rerepro, evidence: verify-green}
  - {env: prod, cause: H2, disposition: tracked, ticket: KTP-901, evidence: owner-comment}
""")
w("sfe51_ok/known-tickets.txt", "KTP-901\nKTP-939\n")
w("sfe51_ok/state.yaml", "ticket: KTP-939\n")
w("sfe51_ok/env-fact-sheet.md", "ENV: demo-dev\nENV: prod\n")
w("sfe51_ok/rca.md", "See KTP-901 for the data-owner follow-up.\n")
w("sfe51_ok/closing-draft.md", "H1 fixed (green re-repro). H2 tracked in KTP-901.\n")

w("sfe51_bad/closure-matrix.yaml", """
rows:
  - {env: demo-dev, cause: H1, disposition: green-rerepro, evidence: verify-green}
  - {env: prod, cause: H2, disposition: tracked, ticket: none, evidence: jira-comment}
""")
w("sfe51_bad/known-tickets.txt", "KTP-939\n")
w("sfe51_bad/state.yaml", "ticket: KTP-939\n")
w("sfe51_bad/env-fact-sheet.md", "ENV: demo-dev\nENV: prod\n")
w("sfe51_bad/rca.md", "Follow-up in KTP-999 (does not exist).\n")
w("sfe51_bad/closing-draft.md", "H1 fixed. H2 tracked for remediation.\n")

# --- input-file fixtures ----------------------------------------------------
w("sfe40_fire.yaml", """
env_universe: [demo-dev]
anchored_envs: [demo-dev]
parked_envs: []
component_named: true
recent_change_in_hand: true
single_cause_all_envs: true
""")
w("sfe40_decline.yaml", """
env_universe: [prod, demo-prod, demo-dev]
anchored_envs: [demo-dev]
parked_envs: [prod, demo-prod]
component_named: true
recent_change_in_hand: true
single_cause_all_envs: true
""")

w("sfe43_pass.yaml", """
pre:  {k: 3, n: 10, conditions: "cold+concurrent"}
post: {k: 0, n: 33, conditions: "cold+concurrent"}
deterministic: false
""")
w("sfe43_block.yaml", """
pre:  {k: 3, n: 10, conditions: "cold+concurrent"}
post: {k: 0, n: 14, conditions: "warm-sequential"}
deterministic: false
""")

w("sfe46_state.yaml", "loops: 0\ncap: 3\n")

# --- SFE-56 learning-harvest gate (Phase 9, D4) ------------------------------
_SFE56_BOARD = """
- id: H1
  claim: "vendor indexes by storefront name, not corporate parent"
  scope: {env: prod, component: vendor-api}
  status: CONFIRMED
  evidence: [O2]
"""
_SFE56_OBS = """
- id: O2
  stamp: OBSERVED
  claim: "Shrimp Basket returns 214 POIs"
  source: {env: prod, instance: vendor-api, traffic: probe}
  method: live-probe
"""
# hardened: complete harvest
w("sfe56_good/board.yaml", _SFE56_BOARD)
w("sfe56_good/observations.yaml", _SFE56_OBS)
w("sfe56_good/knowledge-facts.yaml", """
facts:
  - fact: "vendor indexes entities by consumer storefront name, not corporate parent"
    provenance: verbatim
    raw_source: "observations.yaml#O2"
    rca_link: rca.md
playbook:
  plus_one: data-gap
  proposal: null
retro:
  task_confidence: 92
  factory_fitness: 88
  deductions:
    - {points: 12, reason: "alias sweep only triggered by playbook, not by intake"}
  red_flags: []
  improvements:
    - {title: "alias-map config layer", detail: "map corporate->storefront names at onboarding"}
""")
w("sfe56_good/playbook-append.md", """
## Source incidents (+1)
- KTP-130: corporate-parent name returned 0 rows; storefront alias 'Shrimp Basket' rich. Alias sweep before absence verdict.
""")
w("sfe56_good/parking-lot.md", """
- [idea] alias-map config layer (found: P4, 32m) | drained: proposal
- [debt] vendor client logs raw key names (found: P7, 51m) | drained: dropped — cosmetic
""")

# old behaviour A: harvest NARRATED, file never written (the caught fault)
w("sfe56_narrated/board.yaml", _SFE56_BOARD)
w("sfe56_narrated/observations.yaml", _SFE56_OBS)
w("sfe56_narrated/parking-lot.md", "- [idea] alias-map config layer (found: P4, 32m)\n")

# old behaviour B: well-formed theater — confirmed cause, empty facts, phantom
# playbook id, unaccounted low fitness, undrained lot (NP1: presence != substance)
w("sfe56_theater/board.yaml", _SFE56_BOARD)
w("sfe56_theater/observations.yaml", _SFE56_OBS)
w("sfe56_theater/knowledge-facts.yaml", """
facts: []
playbook:
  plus_one: vendor-alias-hunting
  proposal: null
retro:
  task_confidence: 95
  factory_fitness: 60
  red_flags: []
  improvements: []
""")
w("sfe56_theater/parking-lot.md", "- [idea] alias-map config layer (found: P4, 32m)\n")

# hardened no-cause variant: parked run, explicit none-reasons — must PASS
w("sfe56_nocause/board.yaml", """
- id: H1
  claim: "agency 133 backend empty"
  scope: {env: prod, component: app-proximity-report}
  status: INCONCLUSIVE
  evidence: [O1]
""")
w("sfe56_nocause/observations.yaml", """
- id: O1
  stamp: OBSERVED
  claim: "logs unattributable"
  source: {env: prod, instance: proxrp-cos, traffic: "mixed (unattributable)"}
  method: log-trace
""")
w("sfe56_nocause/knowledge-facts.yaml", """
facts:
  - fact: "proxrp-cos serves prod+demo on one path; its logs carry no env/agency discriminator"
    provenance: verbatim
    raw_source: "observations.yaml#O1"
    rca_link: rca.md
playbook:
  plus_one: null
  proposal: null
  none_reason: "no confirmed cause — run parked at WALL with no-cause package"
retro:
  task_confidence: 30
  factory_fitness: 90
  red_flags: []
  improvements:
    - {title: "request-id discriminator", detail: "propose env/agency tag in proxrp-cos logs"}
""")
w("sfe56_nocause/parking-lot.md", "")


if __name__ == "__main__":
    print(f"fixtures written under {ROOT}")
