"""Create a mission: folder, mission.yaml, GitHub root issue (kind:mission), optional parent link.

Usage:
  mission_new.py --slug ttd-ot-feedback --title "TTD MCP: address OT feedback" \
      --destination "..." --why "..." [--parent 594] [--session clear-wren] [--no-issue]

It does not commit. Run mission_sync.py next.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile

from mission_lib import GH_REPO, MISSIONS_DIR, SKILL_DIR, gh_url, load, now_utc, run, save

LABEL = "kind:mission"


def issue_body(slug: str, destination: str, why: str) -> str:
    d = MISSIONS_DIR / slug
    return f"""<!-- mission-root v1 -->
## Destination
{destination}

## Why
{why}

## Mission record
- **Main record:** [missions/{slug}/mission.yaml]({gh_url(d / 'mission.yaml')})
- **Summary with journey diagram:** [missions/{slug}/README.md]({gh_url(d / 'README.md')})
- **Report (local):** `missions/{slug}/report.html`. Run `/mission report {slug}`.

Agents: read `mission.yaml` before you reason about this work. Its `decisions`, `disproven` and `scope_constraints` win over any other file. Linked issues are members. They are linked, not nested.
"""


def ensure_label() -> None:
    names = run(["gh", "label", "list", "-R", GH_REPO, "-L", "300", "--json", "name", "--jq", ".[].name"]).stdout.split()
    if LABEL not in names:
        run(["gh", "label", "create", LABEL, "-R", GH_REPO, "--color", "5319e7",
             "--description", "Mission root: one cross-session outcome with a mission.yaml record"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--destination", required=True)
    ap.add_argument("--why", default="")
    ap.add_argument("--parent", type=int)
    ap.add_argument("--session", default="none")
    ap.add_argument("--no-issue", action="store_true")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,60}", a.slug):
        sys.exit("slug must be lowercase letters, digits and hyphens")
    d = MISSIONS_DIR / a.slug
    if (d / "mission.yaml").exists():
        sys.exit(f"mission already exists: {d}")
    (d / "evidence").mkdir(parents=True, exist_ok=True)
    ts = now_utc()
    text = (SKILL_DIR / "assets" / "mission.template.yaml").read_text()
    for k, v in {"__SLUG__": a.slug, "__TITLE__": a.title.replace('"', "'"), "__NOW__": ts,
                 "__DESTINATION__": a.destination, "__WHY__": a.why or "TBD", "__SESSION__": a.session}.items():
        text = text.replace(k, v)
    (d / "mission.yaml").write_text(text)
    (d / "evidence" / ".gitkeep").touch()

    m = load(d)
    if not a.no_issue:
        ensure_label()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(issue_body(a.slug, a.destination, a.why or "TBD"))
        url = run(["gh", "issue", "create", "-R", GH_REPO, "--title", f"Mission: {a.title}",
                   "--body-file", f.name, "--label", LABEL, "--label", "status:in-progress"]).stdout.strip().splitlines()[-1]
        number = int(url.rstrip("/").split("/")[-1])
        m["root_issue"] = {"number": number, "url": url}
        if a.parent:
            iid = run(["gh", "api", f"repos/{GH_REPO}/issues/{number}", "--jq", ".id"]).stdout.strip()
            run(["gh", "api", "-X", "POST", f"repos/{GH_REPO}/issues/{a.parent}/sub_issues", "-F", f"sub_issue_id={iid}"])
            p = json.loads(run(["gh", "issue", "view", str(a.parent), "-R", GH_REPO, "--json", "title,url"]).stdout)
            m["parent_issue"] = {"number": a.parent, "url": p["url"], "title": p["title"]}
    save(d, m)
    print(json.dumps({"mission_dir": str(d), "root_issue": m.get("root_issue"), "parent": m.get("parent_issue")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
