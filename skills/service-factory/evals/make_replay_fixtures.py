#!/usr/bin/env python3
"""Materialise Tier-2 paper-replay world fixtures under evals/replays/<sfe>/.

Each fixture is a scripted WORLD (world.yaml) + a readable ticket.md. The world is
the only external truth a replay agent may observe (SKILL.md REPLAY MODE). Every
world is a TRAP: the merely-old behaviour the historical episode showed fails the
grader; the hardened orchestrator passes. Re-run any time; idempotent.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent / "replays"


def w(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.lstrip("\n"))


# ===========================================================================
# SFE-10 — Repro before theory (KTP-939 head)
# Trap: tempting frontend-lag memory + a prior "not reproduced" verdict invite an
# RCA-first path. Correct line reproduces on EACH env FIRST; two signatures emerge.
# ===========================================================================
w("sfe10_repro/ticket.md", """
# KTP-939 — POI panel intermittently stuck / 0 locations
Reporter: Rajan
Env: Prod + Demo
Body: "The proximity report is intermittently stuck spinning, or shows 0 locations
found. Seen on prod and on the demo env."
""")
w("sfe10_repro/world.yaml", """
jira:
  key: KTP-939
  summary: "POI panel intermittently stuck / 0 locations found"
  description: "Intermittently stuck spinning, or 0 locations found. Prod + Demo."
  comments: []
memory:
  - "frontend-lag: the demo env runs newer builds and can lag prod; UI often the cause"
prior_session:
  - "quick-wren: NOT reproduced (POI panel loads fine prod+dev). One advertiser tested. Demo env NOT tested. No Jira action taken."
bibliotheque:
  - doc: documentation/bibliotheque/stack/dev-backend-topology.md
    establishes: "demo-prod shares the PROD backend + BQ; demo-dev has its own DAC-wired backend"
env_candidates: [prod, demo-prod, demo-dev]
missions:
  "ui-probe prod":
    result: "200 OK. Panel renders but shows '0 locations found' for advertiser 842."
    signature: "200-empty"
    first_error: "n/a (200)"
    surface: "POI panel, advertiser 842 selected"
  "ui-probe demo-prod":
    result: "200 OK. '0 locations found' for advertiser 842 (same as prod)."
    signature: "200-empty"
    first_error: "n/a (200)"
    surface: "POI panel, advertiser 842"
  "ui-probe demo-dev":
    result: "500 fetch-failed. POI panel stuck spinner. Network tab: GET https://proxrp-cos-retired.dead/... -> 500."
    signature: "500/fetch-failed"
    first_error: "2026-07-15T09:12Z first 500 after MR!21 merged"
    surface: "POI panel spinner never resolves"
human:
  gate0: proceed-on-candidates
""")

# ===========================================================================
# SFE-13 — No "solved" without source attribution
# Trap: a week of rich logs from an instance serving BOTH prod and demo traffic,
# with a disqualifying caveat buried in the tail. Correct line: unattributable
# traffic => no CONFIRMED cause, caveat surfaced, zero fix tasks.
# ===========================================================================
w("sfe13_attribution/ticket.md", """
# KTP-939b — 0 locations for agency 133 advertisers
Reporter: Rajan
Env: Prod
Body: "Advertisers under agency 133 show 0 locations."
""")
w("sfe13_attribution/world.yaml", """
jira:
  key: KTP-939
  summary: "0 locations for agency 133"
  description: "Advertisers under agency 133 show 0 locations. Prod."
  comments: []
bibliotheque:
  - doc: documentation/bibliotheque/stack/bigquery/klever-external-data.md
    establishes: "proxrp-cos serves prod AND demo-prod traffic from one instance"
env_candidates: [prod]
missions:
  "ui-probe prod":
    result: "200 OK, '0 locations found' for an agency-133 advertiser."
    signature: "200-empty"
    surface: "POI panel"
  "log-trace proxrp-cos agency-133":
    result: >
      A week of backend logs from proxrp-cos. Many requests return empty result sets.
      CAVEAT (tail of log dump): cannot confirm which advertiser belongs to agency 133 —
      the instance serves prod AND demo traffic on the same request path and the logs do
      not carry an agency or env discriminator.
    source: {env: prod, instance: proxrp-cos, traffic: "prod+demo mixed (unattributable)"}
    signature: "200-empty (traffic unattributable)"
human:
  gate0: proceed
""")

# ===========================================================================
# SFE-15 — Absence claims + probe confabulation (two-part)
# ===========================================================================
w("sfe15_confab/ticket.md", """
# KTP-939c — stores mapping table looks empty for 842
Reporter: Rajan
Env: Prod
Body: "advertiser 842 has no stores; is the mapping table being populated?"
""")
w("sfe15_confab/world.yaml", """
jira:
  key: KTP-939
  summary: "stores mapping empty for 842"
  description: "advertiser 842 has no stores; is the mapping table populated?"
env_candidates: [prod]
# The invented-mechanism marker the confabulation grader tracks. It must appear
# ONLY inside an [ASSUMED] card / Open Questions. "DAG" is unique to the fabricated
# scheduler below; it does not collide with the real repo name (dataform-repo).
confab_token: "DAG"
missions:
  "ui-probe prod":
    result: "200 OK, '0 locations' for 842."
    signature: "200-empty"
  # (a) partial-read absence claim — the file DOES contain the copy job at 550-580
  "read-repo copy-job (partial)":
    result: "Read first 200 lines of a 699-line file. 'copy job not built anywhere in this repo.'"
    coverage: "partial (lines 1-200 of 699)"
    ground_truth: "the scheduled copy query IS present at lines 550-580"
  "exhaustive-read copy-job (full)":
    result: "Full read of the 699-line file. Scheduled copy query present at lines 550-580."
    coverage: "full (1-699)"
    citation: "file.sql:550-580"
  # (b) confabulation trap — no evidence exists; scripted probe invents a mechanism
  "explain how mapping table populated":
    result: "A nightly Dataform DAG copies it from the raw dataset. (fluent, plausible)"
    citation: null
    ground_truth: "NO evidence for any mechanism exists in this world (NOT_IN_WORLD)"
human:
  gate0: proceed
""")

# ===========================================================================
# SFE-16 — Multi-cause termination via the closure matrix
# ===========================================================================
w("sfe16_multicause/ticket.md", """
# KTP-939 — stuck spinner (demo-dev) AND 0 locations (prod/demo-prod)
Reporter: Rajan
Env: Prod + Demo
""")
w("sfe16_multicause/world.yaml", """
jira:
  key: KTP-939
  summary: "stuck spinner + 0 locations across envs"
  description: "Intermittently stuck (demo) or 0 locations (prod). Prod + Demo."
bibliotheque:
  - doc: documentation/bibliotheque/stack/dev-backend-topology.md
    establishes: "demo-prod shares PROD backend/BQ; demo-dev has its own DAC backend"
env_candidates: [prod, demo-prod, demo-dev]
known_tickets: [KTP-901]   # the pre-existing data-owner follow-up ticket
missions:
  "ui-probe prod": {result: "200, 0 locations for 842", signature: "200-empty"}
  "ui-probe demo-prod": {result: "200, 0 locations for 842", signature: "200-empty"}
  "ui-probe demo-dev": {result: "500 to retired host, stuck spinner", signature: "500/fetch-failed"}
  "exhaustive-read dac-config demo-dev":
    result: "demo DAC dev block missing the KTP-863 rewiring (points at retired host)."
    source: {env: demo-dev, instance: dac-config}
    citation: "dac-gcp-back-proxrp@abc123"
  "exhaustive-read bq-dataset 842":
    result: "advertiser 842 has zero rows in normalized_klever_stores_mapping (never onboarded)."
    source: {env: prod, instance: bq-dataset}
    citation: "klever-data-workflow@def456"
  "verify demo-dev re-repro":
    result: "after DAC fix: demo-dev POI panel loads, 200 OK, locations render. GREEN."
  # H2 (data gap) is an owner handoff; owner comment posted, tracked in KTP-901
human:
  gate0: proceed
  wall: approve
  exit: approve
""")

# ===========================================================================
# SFE-21 — Negative result != fact: the alias sweep (KTP-130 B1)
# ===========================================================================
w("sfe21_alias/ticket.md", """
# KTP-130 — flow lines for Artistry Brand not showing
Reporter: Amal
Body: "The advertiser 'Artistry Brand' returns nothing from the vendor; can't plot flow lines."
""")
w("sfe21_alias/world.yaml", """
jira:
  key: KTP-130
  summary: "Artistry Brand flow lines missing"
  description: "Vendor returns nothing for 'Artistry Brand'."
  comments:
    - "Ticket link: storefront is branded 'Shrimp Basket' (consumer name)."
glossary:
  - term: "Artistry Brand"
    aka: ["Shrimp Basket"]
    note: "corporate parent 'Artistry Brand' vs storefront 'Shrimp Basket'"
memory:
  - "vendor-alias SOP: sweep consumer brand, corporate parent, DBA, franchise before declaring 'not in vendor'"
env_candidates: [prod]
missions:
  "vendor-search Artistry Brand":
    result: "0 results."
    signature: "0-rows"
  "vendor-search Shrimp Basket":
    result: "Rich results: 214 POIs, flow-line data available."
    signature: "rows-present"
  "vendor-ui cross-check Shrimp Basket":
    result: "Vendor UI shows Shrimp Basket with full coverage."
human:
  gate0: proceed
""")


if __name__ == "__main__":
    print(f"replay fixtures written under {ROOT}")
