"""Fetch live tracker state for a mission's members into computed.json. Never edits mission.yaml.

Usage: mission_fetch.py <slug|path> [--offline]

For each Jira member: status and summary (jira_skill.py search).
For each GitHub member: state, title, labels, updatedAt (gh issue view).
Flags a mismatch when the mission's role disagrees with the tracker
(role current but tracker closed or Done, or role done but tracker open).
"""
from __future__ import annotations

import json
import re
import sys

from mission_lib import GH_REPO, JIRA_ORG, JIRA_SKILL, load, mission_dir, now_utc, run

JIRA = str(JIRA_SKILL)
DONE_WORDS = re.compile(r"done|termin|closed|won't|wont|resolved|ferm", re.I)


def jira_status(keys: list[str]) -> dict:
    if not keys:
        return {}
    if not JIRA_ORG:
        return {k: {"error": "no jira_org in the mission config"} for k in keys}
    r = run(["python3", JIRA, "--org", JIRA_ORG, "search", f"key in ({', '.join(keys)})"], check=False)
    out = r.stdout
    start = out.find("[")
    if r.returncode != 0 or start < 0:
        return {k: {"error": (r.stderr or out).strip()[:200]} for k in keys}
    return {row["key"]: {"status": row.get("status"), "title": row.get("summary")} for row in json.loads(out[start:])}


def gh_state(ref: str) -> dict:
    n = ref.lstrip("#")
    if not GH_REPO:
        return {"error": "no gh_repo in the mission config"}
    r = run(["gh", "issue", "view", n, "-R", GH_REPO, "--json", "state,title,labels,updatedAt,url"], check=False)
    if r.returncode != 0:
        return {"error": r.stderr.strip()[:200]}
    j = json.loads(r.stdout)
    return {"status": j["state"].lower(), "title": j["title"], "labels": [x["name"] for x in j["labels"]],
            "updated": j["updatedAt"], "url": j["url"]}


def mismatch(role: str, status: str | None) -> str | None:
    if not status:
        return None
    closed = bool(DONE_WORDS.search(status)) or status == "closed"
    if role == "current" and closed:
        return f"mission says current, tracker says {status}"
    if role == "done" and not closed:
        return f"mission says done, tracker says {status}"
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    d = mission_dir(sys.argv[1])
    m = load(d)
    offline = "--offline" in sys.argv
    members = m.get("members") or []
    jira = {} if offline else jira_status([x["ref"] for x in members if x.get("kind") == "jira"])
    trackers = []
    for x in members:
        if x.get("kind") not in ("jira", "gh"):
            continue
        live = {"error": "offline"} if offline else (jira.get(x["ref"], {"error": "not returned"}) if x["kind"] == "jira" else gh_state(x["ref"]))
        trackers.append({"ref": x["ref"], "kind": x["kind"], "url": x.get("url"), "role": x.get("role"),
                         "title": live.get("title") or x.get("title"), "status": live.get("status"),
                         "error": live.get("error"), "mismatch": mismatch(x.get("role", ""), live.get("status"))})
    root = None
    ri = m.get("root_issue") or {}
    if ri.get("number") and not offline:
        root = gh_state(str(ri["number"]))
    out = {"fetched_at": now_utc(), "offline": offline, "root": root, "trackers": trackers,
           "mismatches": sum(1 for t in trackers if t["mismatch"])}
    (d / "computed.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"fetched {len(trackers)} tracker(s), {out['mismatches']} mismatch(es) -> {d / 'computed.json'}")
    for t in trackers:
        if t["mismatch"] or t["error"]:
            print(f"  {t['ref']}: {t['mismatch'] or t['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
