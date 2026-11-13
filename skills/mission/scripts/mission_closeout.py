"""Post-mission close-out: gather facts, render the close-out report, gate the mission close.

Usage:
  mission_closeout.py gather [<slug>] [--scope NAME] [--seed-jira K1,K2] [--seed-gh N1,N2]
                             [--aliases "a,b"] [--repo PATH ...] [--depth 4] [--offline]
  mission_closeout.py render [<slug>] [--scope NAME] [--open]
  mission_closeout.py gate   [<slug>] [--scope NAME]

gather collects FACTS only. It never classifies, closes or posts anything. It writes
closeout-facts.json to the mission folder (or missions/_closeout/<scope>/ when there is no
mission record). Every fact it could not read is UNKNOWN with a reason. Nothing is ever PASS.

The agent then writes closeout.yaml (the bucket list, see references/closeout-procedure.md).
render turns closeout.yaml + closeout-facts.json into closeout.html (overwritten, never dated).
gate exits 1 unless closeout.yaml exists, every checklist step has a status, and every ORPHAN
item is parked with a named successor. /mission close and mission_sync (status: done) call it.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import html
import json
import pathlib
import re
import subprocess
import sys

from mission_lib import (GH_REPO, JIRA_BROWSE, JIRA_ORG, JIRA_SKILL, MISSIONS_DIR, MR_UNKNOWN_REASON, PM_ROOT,
                         config_problem, load, now_utc, run)

JIRA = str(JIRA_SKILL)
UNKNOWN = "UNKNOWN"
BUCKETS = ["CLOSE-WITH-EVIDENCE", "SUPERSEDE", "KEEP", "ORPHAN", "FALSE-PREMISE", "HUMAN-ONLY"]
NEEDS_SUCCESSOR = {"KEEP"}
CHECKLIST = [
    ("tracker-status", "Every member and child ticket: live status matches the evidence"),
    ("parent-closing-comments", "Every closed parent has an evidence-backed closing comment"),
    ("description-vs-reality", "Closed parents: description and summary match what shipped"),
    ("done-without-evidence", "No ticket is Done without AC evidence, security tickets first"),
    ("obsolete-items", "Items made obsolete by later changes are superseded or rescoped"),
    ("github-tree", "Open GitHub sub-issues under the root, parent and seeds are reviewed"),
    ("false-premises", "Record text that is no longer true is listed for correction"),
    ("orphans", "Every remaining item has a successor home"),
    ("wayfinder-closes", "Wayfinder map children are closed through the wayfinder tool, not raw gh close"),
    ("dependencies", "Every stated ordering between maps or issues exists as a blockedBy edge"),
    ("reflections", "Reflections are written, and stay under their map until written"),
    ("risk-acceptance", "Every live known gap has a risk acceptance by a named decider"),
    ("handoffs", "Pending session handoffs for this scope are completed or closed"),
    ("drafts", "Unsent drafts are posted, superseded or deleted"),
    ("infra-tails", "Cleanup MRs, branches and unapplied infra changes are finished or owned"),
]
STEP_STATES = {"done", "na", "open", "unknown"}
PENDING_HANDOFF = {"awaiting_initiation", "initiated"}
DONE_WORDS = re.compile(r"done|termin|closed|won't|wont|resolved|ferm|abandon", re.I)


# ---------------------------------------------------------------- location

def closeout_dir(slug: str | None, scope: str | None) -> tuple[pathlib.Path, dict]:
    if config_problem():
        sys.exit(config_problem())
    if slug:
        d = MISSIONS_DIR / slug
        if not (d / "mission.yaml").exists():
            sys.exit(f"mission not found: {slug} (looked in {d}). Use --scope NAME with seeds for a scope without a record.")
        return d, load(d)
    if not scope:
        sys.exit("give a mission slug, or --scope NAME with --seed-jira/--seed-gh")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", scope):
        sys.exit("--scope must be lowercase letters, digits and dashes")
    d = MISSIONS_DIR / "_closeout" / scope
    d.mkdir(parents=True, exist_ok=True)
    return d, {}


def split(v: str | None) -> list[str]:
    return [x.strip() for x in (v or "").split(",") if x.strip()]


# ---------------------------------------------------------------- jira

def parse_json(out: str):
    for i, line in enumerate(out.splitlines()):
        if line.startswith("{") or line.startswith("["):
            return json.loads("\n".join(out.splitlines()[i:]))
    raise ValueError("no JSON in output")


def jira_call(*args: str):
    """A non-zero exit is an error even when stdout holds JSON: an auth failure can print an empty list."""
    if not JIRA_ORG:
        return {"error": "no jira_org in the mission config"}
    r = run(["python3", JIRA, "--org", JIRA_ORG, *args], check=False)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout).strip()[-200:] or f"exit {r.returncode}"}
    try:
        data = parse_json(r.stdout)
    except (ValueError, json.JSONDecodeError):
        return {"error": (r.stderr or r.stdout).strip()[-200:] or "no JSON in output"}
    return data


def jira_children(keys: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (child keys, required-query errors, legacy-query errors).

    'parent in' works for every project type, so its failure means the children are unknown.
    'Epic Link' is a legacy field that some projects do not have, so its failure alone is tolerated."""
    found, errors, legacy = [], [], []
    if not keys:
        return found, errors, legacy
    keyset = ", ".join(keys)
    for jql, sink in ((f"parent in ({keyset})", errors), (f'"Epic Link" in ({keyset})', legacy)):
        data = jira_call("search", jql, "--max", "200")
        if isinstance(data, dict):
            sink.append(f"{jql}: {data.get('error')}")
            continue
        found += [row["key"] for row in data if row.get("key")]
    return found, errors, legacy


def jira_facts_from(key: str, meta, comments, desc) -> dict:
    """Pure: build one ticket's facts. Any unreadable field is UNKNOWN."""
    ok_meta = isinstance(meta, dict) and not meta.get("error") and meta.get("key")
    ok_comments = isinstance(comments, list)
    f = {"key": key, "url": JIRA_BROWSE + key}
    if ok_meta:
        f.update({k: meta.get(k) for k in ("summary", "status", "status_category", "type", "resolution",
                                           "resolution_date", "parent_key", "epic_key", "updated", "assignee")})
    else:
        f.update({"status": UNKNOWN, "resolution": UNKNOWN,
                  "error": (meta or {}).get("error", "no metadata") if isinstance(meta, dict) else "no metadata"})
    if ok_comments:
        dates = sorted(str(c.get("created", "")) for c in comments)
        f["comment_count"] = len(comments)
        f["last_comment_at"] = dates[-1] if dates else None
        f["last_comment_author"] = max(comments, key=lambda c: str(c.get("created", ""))).get("author") if comments else None
    else:
        f.update({"comment_count": UNKNOWN, "last_comment_at": UNKNOWN, "last_comment_author": UNKNOWN})
    if isinstance(desc, dict) and "description" in desc:
        f["description_excerpt"] = (desc.get("description") or "")[:1500]
    else:
        f["description_excerpt"] = UNKNOWN
    closed = ok_meta and (bool(meta.get("resolution")) or bool(DONE_WORDS.search(
        f"{meta.get('status_category') or ''} {meta.get('status') or ''}")))
    f["closed"] = closed if ok_meta else UNKNOWN
    rd = str(meta.get("resolution_date") or "") if ok_meta else ""
    if not ok_meta or not ok_comments:
        f["comment_after_close"] = UNKNOWN
    elif not closed:
        f["comment_after_close"] = None
    elif not rd:
        f["comment_after_close"] = UNKNOWN
        f["comment_after_close_reason"] = "no resolution date on the ticket; compare last_comment_at with the status history"
    else:
        f["comment_after_close"] = any(str(c.get("created", ""))[:16] >= rd[:16] for c in comments)
    f["closed_without_comments"] = UNKNOWN if not (ok_meta and ok_comments) else (closed and not comments)
    return f


def jira_ticket(key: str) -> dict:
    return jira_facts_from(key, jira_call("metadata", key), jira_call("comments", key), jira_call("description", key))


def gather_jira(seeds: list[str], offline: bool) -> dict:
    if not seeds:
        return {"status": UNKNOWN, "reason": "no Jira seeds or members", "tickets": []}
    if offline:
        return {"status": UNKNOWN, "reason": "offline", "seeds": seeds, "tickets": []}
    keys, errors, legacy, frontier = list(dict.fromkeys(seeds)), [], [], list(seeds)
    for _ in range(2):
        kids, errs, legs = jira_children(frontier)
        errors += errs
        legacy += legs
        frontier = [k for k in dict.fromkeys(kids) if k not in keys]
        keys += frontier
        if not frontier:
            break
    with cf.ThreadPoolExecutor(6) as ex:
        tickets = list(ex.map(jira_ticket, keys))
    bad = [t["key"] for t in tickets if t["status"] == UNKNOWN]
    status = "OK" if not bad and not errors else ("PARTIAL" if len(bad) < len(tickets) else UNKNOWN)
    reason = "; ".join(([f"children unknown, {e}" for e in errors] + [f"unreadable {bad}"] * bool(bad))[:3]) or None
    return {"status": status, "reason": reason, "seeds": seeds, "unreadable": bad,
            "legacy_query_errors": legacy, "tickets": tickets}


def field_unknowns(jira: dict) -> list[str]:
    """Ticket fields the gatherer could not settle. An UNKNOWN field is never a pass."""
    keys = [t["key"] for t in jira.get("tickets", []) if t.get("closed") is True and t.get("comment_after_close") == UNKNOWN]
    if not keys:
        return []
    return [f"jira-fields: comment_after_close UNKNOWN on {len(keys)} closed ticket(s) {keys}: "
            "no resolution date; read the status history before calling a closing comment present or missing"]


# ---------------------------------------------------------------- github

GH_Q = """query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issue(number:$n){
number title state stateReason url closedAt updatedAt body labels(first:20){nodes{name}}
parent{number repository{nameWithOwner}}
blockedBy(first:50){nodes{number repository{nameWithOwner}}}
blocking(first:50){nodes{number repository{nameWithOwner}}}
subIssues(first:100){totalCount nodes{number repository{nameWithOwner}}}}}}"""


def gh_ref(ref: str) -> tuple[str, int]:
    m = re.fullmatch(r"(?:([\w.-]+/[\w.-]+))?#?(\d+)", str(ref).strip())
    if not m:
        raise ValueError(f"bad GitHub ref {ref}")
    return m.group(1) or GH_REPO or "", int(m.group(2))


BLOCK_SENTENCE = re.compile(r"[^.\n]*\b(?:block(?:s|ed|ing)?|depend(?:s|ed|ing)?\s+on|wait(?:s|ing)?\s+(?:for|on))\b[^.\n]*", re.I)


def blocking_mentions(body: str) -> list[str]:
    """Issue refs named in a sentence that states an ordering (blocks, depends on, waits for).
    A hint for the agent, not a verdict."""
    refs = []
    for s in BLOCK_SENTENCE.findall(body or ""):
        refs += re.findall(r"#(\d+)", s)
    return sorted(set(refs), key=int)


def gh_issue(repo: str, n: int) -> dict:
    if not repo or "/" not in repo:
        return {"error": "no gh_repo in the mission config and no owner/repo in the ref"}
    owner, name = repo.split("/")
    r = run(["gh", "api", "graphql", "-f", f"query={GH_Q}", "-F", f"o={owner}", "-F", f"r={name}", "-F", f"n={n}"], check=False)
    if r.returncode != 0:
        return {"error": r.stderr.strip()[:200]}
    try:
        i = json.loads(r.stdout)["data"]["repository"]["issue"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return {"error": "unexpected GraphQL response"}
    if not i:
        return {"error": "issue not found"}
    subs = i["subIssues"]
    ref = lambda n: f"{n['repository']['nameWithOwner']}#{n['number']}"
    refs = lambda nodes: [ref(n) for n in nodes if n]
    body = i.get("body") or ""
    return {"repo": repo, "number": i["number"], "title": i["title"], "state": i["state"].lower(),
            "state_reason": i.get("stateReason"), "url": i["url"], "closed_at": i.get("closedAt"),
            "updated_at": i.get("updatedAt"), "labels": [x["name"] for x in i["labels"]["nodes"]],
            "body_excerpt": body[:1500],
            "tracker_parent": ref(i["parent"]) if i.get("parent") else None,
            "blocked_by": refs(i["blockedBy"]["nodes"]),
            "blocking": refs(i["blocking"]["nodes"]),
            "blocking_mentions": blocking_mentions(body),
            "sub_issues_total": subs["totalCount"],
            "sub_issues_truncated": subs["totalCount"] > len([n for n in subs["nodes"] if n]),
            "children": refs(subs["nodes"])}


def wayfinder_runs_dir() -> pathlib.Path:
    import os
    return pathlib.Path(os.environ.get("MISSION_WAYFINDER_RUNS")
                        or pathlib.Path.home() / ".claude-shared-config" / "skills" / "wayfinder" / "runs")


def untraced_closes(map_refs: list[str]) -> dict:
    """Map children closed without the wayfinder tool, read from the harvested run telemetry (gaps)."""
    import yaml
    out = {}
    for m in map_refs:
        f = wayfinder_runs_dir() / f"map-{m.split('#')[-1]}.yaml"
        if not f.exists():
            out[m] = {"status": UNKNOWN, "reason": f"no run telemetry at {f}; run wayfinder harvest"}
            continue
        try:
            data = yaml.safe_load(f.read_text()) or {}
        except yaml.YAMLError as e:
            out[m] = {"status": UNKNOWN, "reason": f"telemetry does not parse: {str(e)[:120]}"}
            continue
        out[m] = {"status": "OK", "harvested": str(data.get("harvested")),
                  "issues": sorted(int(g["issue"]) for g in data.get("gaps") or [] if g.get("issue"))}
    return out


def gather_gh(roots: list[str], depth: int, offline: bool) -> dict:
    if not roots:
        return {"status": UNKNOWN, "reason": "no GitHub seeds, members or root issue", "issues": []}
    if offline:
        return {"status": UNKNOWN, "reason": "offline", "roots": roots, "issues": []}
    seen: dict[str, dict] = {}
    frontier = []
    for r in roots:
        repo, n = gh_ref(r)
        frontier.append((f"{repo}#{n}", None, 0))
    while frontier:
        nxt = []
        todo = [x for x in frontier if x[0] not in seen]
        with cf.ThreadPoolExecutor(6) as ex:
            got = list(ex.map(lambda x: gh_issue(*gh_ref(x[0])), todo))
        for (ref, parent, lvl), info in zip(todo, got):
            if ref in seen:
                continue
            info.update({"ref": ref, "parent": parent, "depth": lvl})
            seen[ref] = info
            if lvl < depth:
                nxt += [(c, ref, lvl + 1) for c in info.get("children", [])]
        frontier = nxt
    issues = list(seen.values())
    by_ref = {i["ref"]: i for i in issues}
    maps = [i["ref"] for i in issues if "wayfinder:map" in (i.get("labels") or [])]
    reflections = []
    for i in issues:
        if "wayfinder:reflection" in (i.get("labels") or []):
            par = by_ref.get(i.get("tracker_parent") or "")
            reflections.append({"ref": i["ref"], "state": i.get("state"), "tracker_parent": i.get("tracker_parent"),
                                "parent_is_map": UNKNOWN if par is None else "wayfinder:map" in (par.get("labels") or [])})
    off_map = [r["ref"] for r in reflections if r["state"] == "open" and r["parent_is_map"] is not True]
    unenforced = []
    for i in issues:
        num = i["ref"].split("#")[-1]
        edges = {x.split("#")[-1] for x in (i.get("blocked_by") or []) + (i.get("blocking") or [])}
        missing = [m for m in i.get("blocking_mentions") or [] if m not in edges and m != num]
        if missing:
            unenforced.append({"ref": i["ref"], "state": i.get("state"), "mentioned_without_edge": missing})
    bad = [i["ref"] for i in issues if i.get("error")]
    trunc = [i["ref"] for i in issues if i.get("sub_issues_truncated")]
    status = "OK" if not bad and not trunc else ("PARTIAL" if len(bad) < len(issues) else UNKNOWN)
    return {"status": status, "reason": None if status == "OK" else f"unreadable {bad}, truncated {trunc}",
            "roots": roots, "open": sum(1 for i in issues if i.get("state") == "open"),
            "closed": sum(1 for i in issues if i.get("state") == "closed"),
            "wayfinder_maps": maps, "reflections": reflections, "reflections_off_map": off_map,
            "wayfinder_untraced_closes": untraced_closes(maps),
            "blocking_mentions_without_edge": unenforced, "issues": issues}


# ---------------------------------------------------------------- ledger handoffs

def gather_handoffs(terms: list[str]) -> dict:
    led = PM_ROOT / "sessions" / "ledger.yaml"
    if not led.exists():
        return {"status": UNKNOWN, "reason": f"no ledger at {led}", "pending": []}
    if not terms:
        return {"status": UNKNOWN, "reason": "no aliases or keys to match", "pending": []}
    import yaml
    try:
        data = yaml.safe_load(led.read_text()) or {}
    except yaml.YAMLError as e:
        return {"status": UNKNOWN, "reason": f"ledger does not parse: {str(e)[:120]}", "pending": []}
    pat = re.compile("|".join(re.escape(t) for t in terms), re.I)
    pending = []
    for h in data.get("handoffs") or []:
        if (h or {}).get("status") not in PENDING_HANDOFF:
            continue
        hay = " ".join(str(h.get(k) or "") for k in ("file", "ticket", "theme"))
        where = "metadata" if pat.search(hay) else None
        path = next(iter((PM_ROOT / "sessions").glob(f"*/*/prompts/{h.get('file')}")), None) if h.get("file") else None
        if not where and path and pat.search(path.read_text(errors="ignore")):
            where = "content"
        if where:
            pending.append({"file": h.get("file"), "status": h.get("status"), "ticket": h.get("ticket"),
                            "theme": h.get("theme"), "source_session": h.get("source_session"),
                            "created": str(h.get("created")), "matched_on": where,
                            "path": str(path) if path else UNKNOWN})
    return {"status": "OK", "reason": None, "terms": terms, "pending": pending}


# ---------------------------------------------------------------- drafts

def ticket_folders(keys: list[str], extra: list[pathlib.Path]) -> list[pathlib.Path]:
    found = list(extra)
    tickets = PM_ROOT / "tickets"
    if keys and tickets.exists():
        names = set(keys)
        for p in tickets.rglob("*"):
            if p.is_dir() and p.name in names and "archive" not in p.parts:
                found.append(p)
    return list(dict.fromkeys(p.resolve() for p in found if p.exists()))


POSTED_AS = re.compile(r"^posted[-_]as:\s*\S", re.I | re.M)


def is_posted(draft: pathlib.Path) -> bool:
    """A sibling .posted file, or a 'posted-as: <where>' line in the draft itself."""
    stem = draft.name[:-3]
    stem = stem[:-len(".rendered")] if stem.endswith(".rendered") else stem
    if any((draft.parent / f"{stem}{suffix}").exists() for suffix in (".posted", ".rendered.posted", ".md.posted")):
        return True
    return bool(POSTED_AS.search(draft.read_text(errors="ignore")[:4000]))


REMOTE_HINT = ("no local posted record; the draft may still be published (as a comment, an issue body or a ticket "
               "description). Check the target before calling it unsent; if published, add a posted-as record")


def gather_drafts(folders: list[pathlib.Path]) -> dict:
    """Local records only. A draft with no posted record is never confirmed unsent: its remote state is UNKNOWN."""
    if not folders:
        return {"status": UNKNOWN, "reason": "no ticket folders found for the members", "no_posted_marker": []}
    unmarked, scanned = [], 0
    for f in folders:
        for d in f.rglob("reports/ship/posts/*.md"):
            scanned += 1
            if d.name.endswith(".rendered.md") and (d.parent / d.name.replace(".rendered.md", ".md")).exists():
                continue
            if not is_posted(d):
                unmarked.append({"path": str(d), "remote_state": UNKNOWN, "hint": REMOTE_HINT})
    return {"status": "OK", "reason": None, "folders": [str(f) for f in folders], "scanned": scanned,
            "no_posted_marker": sorted(unmarked, key=lambda x: x["path"])}


# ---------------------------------------------------------------- branches and MRs

def gather_branches(repos: list[str], keys: list[str]) -> dict:
    out = {"mrs": {"status": UNKNOWN, "reason": MR_UNKNOWN_REASON}}
    if not repos:
        out.update({"status": UNKNOWN, "reason": "no --repo given; branches not checked", "branches": []})
        return out
    if not keys:
        out.update({"status": UNKNOWN, "reason": "no keys to match branch names", "branches": []})
        return out
    hits, errors = [], []
    for repo in repos:
        r = run(["git", "-C", repo, "branch", "-a", "--format=%(refname:short)"], check=False)
        if r.returncode != 0:
            errors.append(f"{repo}: {r.stderr.strip()[:120]}")
            continue
        for b in r.stdout.split():
            if any(k.lower() in b.lower() for k in keys):
                hits.append({"repo": repo, "branch": b})
    out.update({"status": "OK" if not errors else ("PARTIAL" if len(errors) < len(repos) else UNKNOWN),
                "reason": "; ".join(errors) or "local refs only; run git fetch first for remote truth",
                "branches": hits})
    return out


# ---------------------------------------------------------------- gather

def cmd_gather(a) -> int:
    d, m = closeout_dir(a.mission, a.scope)
    members = m.get("members") or []
    jira_seeds = list(dict.fromkeys(split(a.seed_jira) + [x["ref"] for x in members if x.get("kind") == "jira"]))
    gh_seeds = split(a.seed_gh) + [x["ref"] for x in members if x.get("kind") == "gh"]
    for k in ("root_issue", "parent_issue"):
        if (m.get(k) or {}).get("number"):
            gh_seeds.append(str(m[k]["number"]))
    gh_seeds = list(dict.fromkeys(str(x).lstrip("#") if "/" not in str(x) else str(x) for x in gh_seeds))
    aliases = list(dict.fromkeys(split(a.aliases) + list(m.get("aliases") or [])))
    folders = [PM_ROOT / x["ref"] for x in members if x.get("kind") == "folder"]

    jira = gather_jira(jira_seeds, a.offline)
    all_keys = list(dict.fromkeys(jira_seeds + [t["key"] for t in jira.get("tickets", [])]))
    facts = {
        "schema": "mission-closeout-facts/v1",
        "fetched_at": now_utc(),
        "scope": {"mission": a.mission, "name": a.scope or a.mission, "jira_seeds": jira_seeds,
                  "gh_seeds": gh_seeds, "aliases": aliases, "repos": a.repo or []},
        "jira": jira,
        "github": gather_gh(gh_seeds, a.depth, a.offline),
        "handoffs": gather_handoffs(aliases + all_keys),
        "drafts": gather_drafts(ticket_folders(all_keys, folders)),
        "branches": gather_branches(a.repo or [], all_keys),
    }
    facts["unknown"] = [f"{k}: {v.get('reason')}" for k, v in facts.items()
                        if isinstance(v, dict) and v.get("status") in (UNKNOWN, "PARTIAL")]
    if facts["branches"]["mrs"]["status"] == UNKNOWN:
        facts["unknown"].append(f"mrs: {facts['branches']['mrs']['reason']}")
    facts["unknown"] += field_unknowns(jira)
    unmarked = facts["drafts"].get("no_posted_marker") or []
    if unmarked:
        facts["unknown"].append(f"drafts: {len(unmarked)} draft(s) with no posted record; remote state not checked, "
                                "verify the target before calling any of them unsent")
    for m, u in (facts["github"].get("wayfinder_untraced_closes") or {}).items():
        if u.get("status") == UNKNOWN:
            facts["unknown"].append(f"wayfinder-telemetry {m}: {u.get('reason')}")
    out = d / "closeout-facts.json"
    out.write_text(json.dumps(facts, indent=2, ensure_ascii=False, default=str))
    j, g = facts["jira"], facts["github"]
    print(f"facts -> {out}")
    print(f"  jira: {j['status']}, {len(j.get('tickets', []))} ticket(s)")
    print(f"  github: {g['status']}, {g.get('open', 0)} open, {g.get('closed', 0)} closed")
    print(f"  handoffs: {facts['handoffs']['status']}, {len(facts['handoffs'].get('pending', []))} pending match(es)")
    print(f"  drafts: {facts['drafts']['status']}, {len(unmarked)} with no posted record (remote UNKNOWN)")
    print(f"  branches: {facts['branches']['status']}, mrs: UNKNOWN")
    for u in facts["unknown"]:
        print(f"  UNKNOWN {u}")
    return 0


# ---------------------------------------------------------------- gate

def load_closeout(d: pathlib.Path):
    import yaml
    f = d / "closeout.yaml"
    return yaml.safe_load(f.read_text()) if f.exists() else None


def gate(d: pathlib.Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). An empty error list means the mission may close."""
    err, warn = [], []
    co = load_closeout(d)
    if co is None:
        return [f"no closeout.yaml in {d}: run /mission check --close first"], warn
    if not (d / "closeout-facts.json").exists():
        err.append("no closeout-facts.json: run mission closeout gather")
    else:
        facts = json.loads((d / "closeout-facts.json").read_text())
        for u in facts.get("unknown") or []:
            warn.append(f"fact source UNKNOWN, review by hand: {u}")
    steps = {s.get("id"): s for s in co.get("checklist") or [] if isinstance(s, dict)}
    for sid, _ in CHECKLIST:
        s = steps.get(sid)
        if not s or s.get("status") not in STEP_STATES:
            err.append(f"checklist step '{sid}' has no status ({'/'.join(sorted(STEP_STATES))})")
        elif s["status"] in ("open", "unknown"):
            warn.append(f"checklist step '{sid}' is {s['status']}")
    for i, it in enumerate(co.get("items") or []):
        where = f"items[{i}] {it.get('id', '?')}"
        b = it.get("bucket")
        if b not in BUCKETS:
            err.append(f"{where}: bucket '{b}' not in {BUCKETS}")
            continue
        succ = it.get("successor") or {}
        named = isinstance(succ, dict) and succ.get("url") and succ.get("title")
        if b == "ORPHAN" and not (named and it.get("parked_by")):
            err.append(f"{where}: ORPHAN without a named successor and parked_by. Give it a home before close.")
        if b in NEEDS_SUCCESSOR and not named:
            err.append(f"{where}: KEEP needs successor with url and title")
        if b == "HUMAN-ONLY" and it.get("state") != "done" and not (named or str(it.get("owner") or "").strip()):
            err.append(f"{where}: HUMAN-ONLY item still open without a named owner or successor. Give it a home before close.")
        if it.get("state", "proposed") == "proposed":
            warn.append(f"{where}: {b} action still proposed")
    return err, warn


def cmd_gate(a) -> int:
    d, _ = closeout_dir(a.mission, a.scope)
    err, warn = gate(d)
    for w in warn:
        print(f"WARN  {w}")
    for e in err:
        print(f"ERROR {e}")
    print("GATE OPEN: the mission may close" if not err else "GATE CLOSED: the mission may not close")
    return 1 if err else 0


# ---------------------------------------------------------------- render

def esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


def link(l) -> str:
    if not isinstance(l, dict):
        return esc(l)
    return f'<a href="{esc(l.get("url"))}">{esc(l.get("ref") or "")} {esc(l.get("title") or l.get("url"))}</a>'


CSS = """body{font:15px/1.5 -apple-system,Segoe UI,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}
h1{margin-bottom:.2rem}.muted{color:#666}.unknown{background:#fff4d6;border-left:4px solid #e0a800;padding:.6rem 1rem}
.gate-ok{background:#e5f6e8;border-left:4px solid #2e8b57;padding:.6rem 1rem}.gate-no{background:#fde8e8;border-left:4px solid #c0392b;padding:.6rem 1rem}
table{border-collapse:collapse;width:100%;margin:.5rem 0 1.5rem}td,th{border-bottom:1px solid #ddd;padding:.35rem .5rem;text-align:left;vertical-align:top}
th{background:#f5f5f5}.b{font-weight:600}section{margin-top:1.5rem}code{background:#f3f3f3;padding:0 .2rem}"""


def cmd_render(a) -> int:
    d, m = closeout_dir(a.mission, a.scope)
    co = load_closeout(d) or {}
    facts = json.loads((d / "closeout-facts.json").read_text()) if (d / "closeout-facts.json").exists() else {}
    err, warn = gate(d)
    title = m.get("title") or co.get("scope", {}).get("name") or a.scope
    h = [f"<!doctype html><meta charset=utf-8><title>Close-out: {esc(title)}</title><style>{CSS}</style>",
         f"<h1>Close-out: {esc(title)}</h1>",
         f"<p class=muted>Facts fetched {esc(facts.get('fetched_at', 'never'))}. Report rendered {esc(now_utc())}.</p>"]
    h.append(f'<div class="{"gate-ok" if not err else "gate-no"}"><b>Close gate: {"OPEN" if not err else "CLOSED"}.</b> '
             + ("".join(f"<br>{esc(e)}" for e in err) or "The mission may close after the human approves.") + "</div>")
    if facts.get("unknown"):
        h.append('<div class="unknown"><b>Not checked (UNKNOWN, never PASS):</b><ul>'
                 + "".join(f"<li>{esc(u)}</li>" for u in facts["unknown"]) + "</ul></div>")
    appr = co.get("approval") or {}
    h.append(f"<p><b>Bucket list approval:</b> {esc(appr.get('by') or 'not approved yet')} {esc(appr.get('at') or '')} "
             f"{link(appr.get('link')) if appr.get('link') else ''}</p>")
    items = co.get("items") or []
    counts = {b: sum(1 for i in items if i.get("bucket") == b) for b in BUCKETS}
    h.append("<table><tr>" + "".join(f"<th>{b}</th>" for b in BUCKETS) + "</tr><tr>"
             + "".join(f"<td class=b>{counts[b]}</td>" for b in BUCKETS) + "</tr></table>")
    for b in BUCKETS:
        rows = [i for i in items if i.get("bucket") == b]
        if not rows:
            continue
        h.append(f"<section id='{b}'><h2>{b} ({len(rows)})</h2><table><tr><th>ID</th><th>Item</th><th>Finding</th>"
                 "<th>Proposed action</th><th>Successor</th><th>State</th></tr>")
        for i in rows:
            ev = " ".join(link(e) for e in i.get("evidence") or [])
            h.append(f"<tr><td>{esc(i.get('id'))}</td><td>{link(i.get('ref')) if i.get('ref') else esc(i.get('title'))}</td>"
                     f"<td>{esc(i.get('finding'))} {ev}</td><td>{esc(i.get('action'))}</td>"
                     f"<td>{link(i.get('successor')) if i.get('successor') else ''}</td><td>{esc(i.get('state', 'proposed'))}</td></tr>")
        h.append("</table></section>")
    steps = {s.get("id"): s for s in co.get("checklist") or [] if isinstance(s, dict)}
    h.append("<section><h2>Checklist</h2><table><tr><th>Step</th><th>Status</th><th>Note</th></tr>")
    for sid, label in CHECKLIST:
        s = steps.get(sid) or {}
        h.append(f"<tr><td>{esc(label)}</td><td class=b>{esc(s.get('status', 'missing'))}</td><td>{esc(s.get('note'))}</td></tr>")
    h.append("</table></section>")
    guide = co.get("human_guide") or []
    if guide:
        h.append("<section><h2>Human-only guide</h2><ol>" + "".join(
            f"<li>{esc(g.get('step') if isinstance(g, dict) else g)}"
            + (f" <code>{esc(g.get('command'))}</code>" if isinstance(g, dict) and g.get("command") else "") + "</li>"
            for g in guide) + "</ol></section>")
    if warn:
        h.append("<section><h2>Warnings</h2><ul>" + "".join(f"<li>{esc(w)}</li>" for w in warn) + "</ul></section>")
    out = d / "closeout.html"
    out.write_text("\n".join(h))
    print(f"report -> {out.as_uri()}")
    if a.open:
        subprocess.run(["open", str(out)], check=False)
    return 0


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gather", "render", "gate"):
        p = sub.add_parser(name)
        p.add_argument("mission", nargs="?")
        p.add_argument("--scope")
        if name == "gather":
            p.add_argument("--seed-jira")
            p.add_argument("--seed-gh")
            p.add_argument("--aliases")
            p.add_argument("--repo", action="append")
            p.add_argument("--depth", type=int, default=4)
            p.add_argument("--offline", action="store_true")
        if name == "render":
            p.add_argument("--open", action="store_true")
    a = ap.parse_args()
    return {"gather": cmd_gather, "render": cmd_render, "gate": cmd_gate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
