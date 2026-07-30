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
  train-diff-to-testplan.py --repo . --range 1.1.79..1.1.86           # by deployed prod tags (CORRECT)

IMPORTANT — the range must be the ACTUAL PROMOTED delta: previously-deployed prod tag ..
newly-deployed prod tag. Do NOT use `origin/main..origin/dev` for a real train: dev holds
deliberately-EXCLUDED work, and trains are cherry-picked, so that range over-reports. The
authoritative answer to "what shipped" is the train manifest, not any single-repo diff.

LIMITS (read before trusting output):
- This sees ONLY app-front-portal. A backend/UM/DAC/dataform change ships no frontend diff
  yet can break a portal feature (KTP-739). Portal-diff is a SECONDARY signal.
- If a shared/config/CI file changed, the plan sets fail_closed=true → run the FULL set.

Exit codes: 0 = plan produced. 2 = git diff failed (bad range/repo).
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
    """Return [(status, path)] for the range. Uses --name-status -z with rename/copy
    detection so renames map BOTH sides (a file moving out of a feature area must not
    silently vanish from that area's plan). Statuses: A/M/D/Rxxx/Cxxx."""
    try:
        out = subprocess.check_output(
            ["git", "-C", repo, "diff", "--name-status", "-z",
             "--find-renames", "--find-copies", rng],
            stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        print(f"git diff failed for range {rng!r} in {repo!r}: {e.stderr or e}", file=sys.stderr)
        sys.exit(2)
    toks = [t for t in out.split("\0") if t != ""]
    entries = []
    i = 0
    while i < len(toks):
        status = toks[i]
        code = status[0]
        if code in ("R", "C"):  # rename/copy: status \0 oldpath \0 newpath
            old, new = toks[i + 1], toks[i + 2]
            entries.append((status, old))   # keep old side so the source area still fires
            entries.append((status, new))
            i += 3
        else:                              # A/M/D/T: status \0 path
            entries.append((status, toks[i + 1]))
            i += 2
    return entries


def infer_areas(entries):
    hit = {}
    for status, f in entries:
        for prefix, area in FEATURE_MAP:
            if f.startswith(prefix) or ("/" + prefix) in f or f == prefix:
                hit.setdefault(area, []).append(f"{status}:{f}")
    return hit


# Paths that FAIL CLOSED: a change here can affect any feature, so the plan must
# fall back to a FULL pass, not a diff-narrowed one. (Codex review: a shared-context,
# CI, dependency, or config change can silently invalidate the diff-targeting.)
FAIL_CLOSED_PREFIXES = [
    "app/(frontend)/context/",   # AppProvider et al — cross-app mode/permission/preview state
    "lib/",                       # shared libs/utils
    "middleware.ts", "next.config", "package.json", "package-lock.json",
    ".gitlab-ci.yml", "Dockerfile", "tsconfig",
]


def build_plan(repo, rng):
    entries = changed_files(repo, rng)                 # [(status, path)]
    paths = [p for _, p in entries]
    hit = infer_areas(entries)
    code_exts = (".ts", ".tsx", ".js", ".jsx")
    unmapped = sorted({p for _, p in entries
                       if not any(p.startswith(pre) or ("/" + pre) in p or p == pre
                                  for pre, _ in FEATURE_MAP)
                       and p.endswith(code_exts)})
    fail_closed_hits = sorted({p for p in paths
                               if any(p.startswith(fp) or ("/" + fp) in p for fp in FAIL_CLOSED_PREFIXES)})
    targeted = []
    for area, area_files in hit.items():
        meta = dict(AREAS.get(area, {"title": area, "checks": []}))
        meta["area"] = area
        meta["changed_files"] = sorted(set(area_files))   # expose ALL, no truncation
        targeted.append(meta)
    return {
        "range": rng,
        "repo": repo,
        "changed_file_count": len(paths),
        "fail_closed": bool(fail_closed_hits),
        "fail_closed_files": fail_closed_hits,
        "core_smoke": CORE_SMOKE,
        "targeted_areas": targeted,
        "targeted_area_keys": sorted(hit.keys()),
        "unmapped_code_files": unmapped,
        "all_changed": [f"{s}:{p}" for s, p in entries],
        "scope_warning": (
            "FAIL CLOSED: a shared/config/dependency/CI file changed. Diff-targeting is NOT trustworthy for "
            "this train — run the FULL feature set, not just targeted_areas."
        ) if fail_closed_hits else None,
        "cross_repo_warning": (
            "This tool sees ONLY app-front-portal files. A backend / user-management / DAC / dataform change "
            "ships NO frontend diff yet can break a portal feature (KTP-739 AI Insights = exactly this). "
            "Portal-diff inference is a SECONDARY signal — the train manifest (all releasing repos + data "
            "contracts) is the primary source of what to validate. Do NOT treat an empty portal diff as 'nothing to test'."
        ),
        "notes": [
            "Run core_smoke ALWAYS. If fail_closed, run the FULL feature set. Else run targeted_areas.",
            "unmapped_code_files did not match FEATURE_MAP — eyeball them; extend FEATURE_MAP if a new area appears.",
            "Data-backed areas: verify the data source from the TRAIN MANIFEST declaration (producer/table/advertiser/freshness), NOT from frontend paths. A backend-only release triggers no area here but can still ship a broken data-backed panel (KTP-739).",
            "playwright specs per area are logic/e2e tests of MIXED fidelity — several test pure functions, not the deployed surface. Do not treat them as deployment signal without curating a release-smoke subset.",
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
    print("!! " + plan['cross_repo_warning'] + "\n")
    if plan.get('scope_warning'):
        print("!! " + plan['scope_warning'])
        print("   triggered by: " + ", ".join(plan['fail_closed_files']) + "\n")
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
