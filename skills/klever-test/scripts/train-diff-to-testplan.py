#!/usr/bin/env python3
"""
train-diff-to-testplan.py — infer a post-prod-train portal regression plan from a git diff.

Given a git range on app-front-portal (the promotion delta — e.g. the previously
deployed prod tag .. the newly deployed prod tag, or origin/main..origin/dev while
assembling a train), this:
  1. lists changed files,
  2. maps each path to a portal FEATURE AREA via FEATURE_MAP,
  3. emits a test plan = ALWAYS-ON CORE SMOKE (unconditional) + TARGETED area checks
     (only the areas the diff touched) + DATA-LAYER checks for data-backed areas.

The output is a JSON plan consumed by klever-test mode 7 (post-train-regression.md),
which executes it live on prod via ui-probe. This is the "smart" layer: instead of
running the whole suite every time, it runs the always-on core PLUS exactly the
features the train changed. The always-on core is what guards against "a major thing
broke even though the diff didn't touch it" — it is deliberately fixed.

Usage:
  train-diff-to-testplan.py --repo <path-to-app-front-portal> --range <base>..<head> [--json]
  train-diff-to-testplan.py --repo . --range 1.1.79..1.1.86           # by deployed tags
  train-diff-to-testplan.py --repo . --range origin/main..origin/dev   # while assembling

Exit 0 always (a plan is always produced; core smoke runs even on an empty diff).
"""
import argparse
import json
import subprocess
import sys

# --- Feature map: path prefix (matched as substring on the repo-relative path) -> feature area key.
# Order matters only for readability; a file can map to several areas (all that match are added).
FEATURE_MAP = [
    ("components/map/",                 "measurement_map"),
    ("app/(frontend)/measurement",      "measurement_map"),
    ("app/api/map/",                    "measurement_map"),
    ("components/planning-map/",        "planning_map"),
    ("app/(frontend)/planning",         "planning_map"),
    ("lib/permissions/",               "permissions_nav"),
    ("components/layout/app-sidebar",   "permissions_nav"),
    ("components/layout/app-top-nav",   "permissions_nav"),
    ("app/api/permissions/",           "permissions_nav"),
    ("components/layout/client-preview", "mode_switcher"),
    ("app/(frontend)/home",             "home_ai_insights"),
    ("components/home/",                "home_ai_insights"),
    ("lib/mode/",                       "mode_switcher"),
    ("components/layout/mode",           "mode_switcher"),
    ("components/layout/demo-only",      "mode_switcher"),
    ("components/reports/",             "reports"),
    ("app/(frontend)/reports",          "reports"),
    ("app/api/report",                  "reports"),
    ("components/bi-agent/",           "bi_agent"),
    ("components/media-plan/",         "media_plan"),
    ("middleware.ts",                  "auth_guard"),
    ("app/(frontend)/layout",           "auth_guard"),
]

# --- Feature-area catalogue: what each area's targeted validation is.
# `data_layer` (optional): a BQ check the mode runs read-only (like TC6). `playwright`:
# the existing e2e spec that covers it (the long-term CICD anchor).
AREAS = {
    "measurement_map": {
        "title": "Measurement Map + vendor layers",
        "route": "/measurement",
        "checks": ["Mapbox tiles render", "Placer/Goldfish layers load",
                   "all /api/map/* return 200", "no ChunkLoadError", "cluster pins render"],
        "playwright": ["visitor-flow-lines.spec.ts", "store-detail-panel.spec.ts"],
    },
    "planning_map": {
        "title": "Planning Map",
        "route": "/planning",
        "checks": ["Planning map renders", "service-area / ZIP interactions", "no console errors"],
        "playwright": [],
    },
    "permissions_nav": {
        "title": "Permission gates + nav visibility",
        "route": "/home",
        "checks": ["nav items match granted components", "gated routes hidden when ungranted",
                   "account-components endpoint 200"],
        "playwright": ["admin-permissions.spec.ts", "bulk-grant-modal.spec.ts", "scope-editor.spec.ts"],
    },
    "home_ai_insights": {
        "title": "Home / Monthly Summary / AI Insights",
        "route": "/home",
        "checks": ["Monthly Summary metric cards render", "What's New renders",
                   "AI Insights panel renders for a granted user + advertiser WITH an insight row"],
        "data_layer": {
            "note": "AI Insights is data-backed. Confirm the insights table exists AND has OK/SUCCESS rows for the advertiser under test before asserting the panel should render.",
            "table_hint": "proximityreport.bigquery.{projectId}.{insightsDatasetId}.ai_insights (verify runtime-resolved values from the proximity-report startup log)",
        },
        "playwright": ["campaign-insights-logic.spec.ts"],
    },
    "mode_switcher": {
        "title": "Demo/Internal/Client-Preview mode + demo spotlight",
        "route": "/measurement",
        "checks": ["switcher visible to internal user (3 modes)", "Client Preview locks to client scope",
                   "switcher absent for non-internal login (negative)",
                   "demo spotlight ON in Demo, OFF in Internal/Client (negative)"],
        "playwright": [],
    },
    "reports": {
        "title": "Reports",
        "route": "/reports",
        "checks": ["report list renders", "campaign selector works", "export path intact"],
        "playwright": ["market-copy.spec.ts"],
    },
    "bi_agent": {
        "title": "BI Agent surface",
        "route": "/reports",
        "checks": ["BI Agent sidebar renders only for granted users"],
        "playwright": [],
    },
    "media_plan": {
        "title": "Media Plan Agent panel",
        "route": "/planning",
        "checks": ["Media Plan panel renders only for granted users"],
        "playwright": ["media-plan-logic.spec.ts"],
    },
    "auth_guard": {
        "title": "Auth / route guard",
        "route": "/home",
        "checks": ["authenticated load succeeds (no login wall)", "middleware redirects unauth"],
        "playwright": [],
    },
}

# --- Always-on core smoke: runs EVERY time regardless of the diff. This is the fixed
# "did a major thing break" guard the user asked for — the same big group each run.
CORE_SMOKE = {
    "title": "Core smoke (ALWAYS run — guards against undiffed breakage)",
    "checks": [
        "Portal loads authenticated (no Auth0 wall, no 502)",
        "Record served build version (front-portal) + backend version",
        "Each top-nav route (/home, /measurement, /planning, /reports) renders, no 500, no error page",
        "Measurement Map renders with vendor tiles + /api/map/* 200 (the highest-value single smoke)",
        "Fresh-session + stale-tab reload: no ChunkLoadError / _next chunk 404 (post-MIG-swap check)",
        "No NEW console errors vs the prior baseline",
    ],
}


def changed_files(repo, rng):
    try:
        out = subprocess.check_output(
            ["git", "-C", repo, "diff", "--name-only", rng],
            stderr=subprocess.DEVNULL, text=True)
    except subprocess.CalledProcessError as e:
        print(f"git diff failed for range {rng!r} in {repo!r}: {e}", file=sys.stderr)
        sys.exit(2)
    return [l.strip() for l in out.splitlines() if l.strip()]


def infer_areas(files):
    hit = {}
    for f in files:
        for prefix, area in FEATURE_MAP:
            if prefix in f:
                hit.setdefault(area, []).append(f)
    return hit


def build_plan(repo, rng):
    files = changed_files(repo, rng)
    hit = infer_areas(files)
    unmapped = [f for f in files
                if not any(p in f for p, _ in FEATURE_MAP)
                and (f.endswith(".ts") or f.endswith(".tsx") or f.endswith(".js") or f.endswith(".jsx"))]
    targeted = []
    for area, area_files in hit.items():
        meta = dict(AREAS.get(area, {"title": area, "checks": []}))
        meta["area"] = area
        meta["changed_files"] = sorted(set(area_files))[:12]
        targeted.append(meta)
    return {
        "range": rng,
        "repo": repo,
        "changed_file_count": len(files),
        "core_smoke": CORE_SMOKE,
        "targeted_areas": targeted,
        "targeted_area_keys": sorted(hit.keys()),
        "unmapped_code_files": unmapped[:30],
        "notes": [
            "Run core_smoke ALWAYS. Run targeted_areas for what the diff touched.",
            "unmapped_code_files did not match FEATURE_MAP — eyeball them; if a new feature area appears, extend FEATURE_MAP.",
            "For any area with a data_layer block, verify the data source BEFORE asserting the UI should render (KTP-739 lesson: a panel hidden because its BQ table is empty/absent is a data problem, not a UI pass/fail).",
            "playwright specs listed per area are the long-term CICD anchor; run them locally against dev to complement the live-prod ui-probe pass.",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="path to app-front-portal checkout")
    ap.add_argument("--range", required=True, help="git range, e.g. 1.1.79..1.1.86 or origin/main..origin/dev")
    ap.add_argument("--json", action="store_true", help="emit JSON (default: human summary)")
    args = ap.parse_args()
    plan = build_plan(args.repo, args.range)
    if args.json:
        print(json.dumps(plan, indent=2))
        return
    print(f"# Post-train regression plan  ({plan['range']})")
    print(f"{plan['changed_file_count']} changed files -> areas: {', '.join(plan['targeted_area_keys']) or '(none — core smoke only)'}\n")
    print(f"## {plan['core_smoke']['title']}")
    for c in plan['core_smoke']['checks']:
        print(f"  - [ ] {c}")
    print()
    for a in plan['targeted_areas']:
        print(f"## {a['title']}  (route {a.get('route','?')})")
        for c in a.get('checks', []):
            print(f"  - [ ] {c}")
        if a.get('data_layer'):
            print(f"  - [DATA] {a['data_layer']['note']}")
        print()
    if plan['unmapped_code_files']:
        print("## Unmapped code files (eyeball — extend FEATURE_MAP if a new area):")
        for f in plan['unmapped_code_files']:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
