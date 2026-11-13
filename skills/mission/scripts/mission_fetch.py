"""Fetch live tracker state for a mission's members into computed.json, and compute drift per thread.

Usage: mission_fetch.py <slug|path> [--offline]

For each Jira member: status and summary (jira_skill.py search).
For each GitHub member: state, title, labels, updatedAt (gh issue view).
Flags a mismatch when the mission's role disagrees with the tracker
(role current but tracker closed or Done, or role done but tracker open).

Threads: each thread's watched refs (its refs, lives_in and home, GitHub issues and Jira tickets) are read live
and compared with the thread's snapshot. A thread with no snapshot gets one (the baseline). A difference sets
drift {at, text}. The snapshot is kept until the thread is re-judged (mission thread set T-n --clear-drift), so a
drifted thread can never be closed on its old evidence. This is the only write to mission.yaml, and it replaces
only the threads block. --offline reads nothing and changes no thread.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import re
import sys

from mission_lib import GH_REPO, JIRA_ORG, JIRA_SKILL, load, locked, mission_dir, now_utc, run, set_section
from mission_links import classify

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


def gh_watch(ref: str) -> dict:
    """State, comment count and a body digest of a GitHub issue ('#N' in gh_repo, or 'owner/repo#N')."""
    repo, _, n = ref.rpartition("#")
    repo = repo or GH_REPO
    if not repo:
        return {"error": "no gh_repo in the mission config"}
    r = run(["gh", "issue", "view", n, "-R", repo, "--json", "state,comments,body"], check=False)
    if r.returncode != 0:
        return {"error": r.stderr.strip()[:200]}
    j = json.loads(r.stdout)
    return {"state": j["state"].lower(), "comments": len(j.get("comments") or []),
            "digest": hashlib.sha256((j.get("body") or "").encode()).hexdigest()[:12]}


def watched_refs(t: dict) -> list[dict]:
    """The GitHub issues and Jira tickets a thread is about or lives in, once each."""
    out, seen = [], set()
    for ln in (t.get("refs") or []) + [t.get("lives_in"), (t.get("home") or {}).get("link")]:
        c = classify(ln) if isinstance(ln, dict) else None
        if not c or c.get("kind") not in ("gh", "jira") or not c.get("ref") or c["ref"] in seen:
            continue
        seen.add(c["ref"])
        out.append({"ref": c["ref"], "kind": c["kind"]})
    return out


def read_live(refs: list[dict]) -> dict:
    """ref -> {state, comments, digest} or {error}. GitHub in parallel, Jira in one search."""
    jira = jira_status(sorted({r["ref"] for r in refs if r["kind"] == "jira"}))
    out = {k: ({"state": v.get("status")} if not v.get("error") else {"error": v["error"]}) for k, v in jira.items()}
    gh = sorted({r["ref"] for r in refs if r["kind"] == "gh"})
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for ref, val in zip(gh, ex.map(gh_watch, gh)):
            out[ref] = val
    return out


def _diff(old: dict, new: dict) -> list[str]:
    parts = []
    if new.get("error"):
        return []
    if old.get("state") != new.get("state") and new.get("state") is not None:
        parts.append(f"state {old.get('state')} -> {new.get('state')}")
    if old.get("comments") is not None and new.get("comments") is not None and new["comments"] != old["comments"]:
        parts.append(f"comments {old['comments']} -> {new['comments']}")
    if old.get("digest") and new.get("digest") and old["digest"] != new["digest"]:
        parts.append("body edited")
    return parts


def compute_drift(threads: list[dict], live: dict, at: str) -> tuple[list[dict], int, int]:
    """Baseline threads with no snapshot; set drift where a watched ref changed since the snapshot.
    Returns (threads, baselined, drifted). Dropped threads are not watched."""
    base = drifted = 0
    for t in threads:
        if t.get("state") == "dropped":
            continue
        refs = watched_refs(t)
        if not refs:
            continue
        snap = t.get("snapshot") or {}
        if not snap.get("watched"):
            got = [{**r, **{k: v for k, v in live.get(r["ref"], {}).items() if k in ("state", "comments", "digest")}}
                   for r in refs if not live.get(r["ref"], {}).get("error") and r["ref"] in live]
            if got:
                t["snapshot"] = {"at": at, "watched": got}
                base += 1
            continue
        old = {w.get("ref"): w for w in snap["watched"]}
        changes = [f"{ref} {', '.join(d)}" for ref, w in old.items() if (d := _diff(w, live.get(ref, {"error": "unread"})))]
        if changes:
            prev = t.get("drift") or {}
            t["drift"] = {"at": prev.get("at") or at, "text": "; ".join(changes) + f" (since {snap.get('at')})", "checked": at}
            drifted += 1
    return threads, base, drifted


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
    if m.get("threads") and not offline:
        with locked(d):
            fresh = load(d)
            threads = fresh.get("threads") or []
            live = read_live([r for t in threads for r in watched_refs(t)])
            threads, base, drifted = compute_drift(threads, live, out["fetched_at"])
            unread = sorted(k for k, v in live.items() if v.get("error"))
            if base or drifted:
                set_section(d, "threads", threads)
            out["threads"] = {"baselined": base, "drifted": drifted, "unread": unread}
            print(f"threads: {base} baselined, {drifted} drifted" + (f", {len(unread)} ref(s) unread (UNKNOWN)" if unread else ""))
            for t in threads:
                if t.get("drift"):
                    print(f"  {t['id']}: {t['drift']['text'][:160]}")
    (d / "computed.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"fetched {len(trackers)} tracker(s), {out['mismatches']} mismatch(es) -> {d / 'computed.json'}")
    for t in trackers:
        if t["mismatch"] or t["error"]:
            print(f"  {t['ref']}: {t['mismatch'] or t['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
