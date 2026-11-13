"""Post-mission close-out: gather facts, render the decision-first report, bind approval, gate the close.

Usage:
  mission_closeout.py gather   [<slug>] [--scope NAME] [--seed-jira K1,K2] [--seed-gh N1,N2] [--aliases "a,b"]
                               [--repo PATH ...] [--since DATE] [--exclude "t1,t2"] [--sweep-cap 50] [--depth 4] [--offline]
  mission_closeout.py coverage [<slug>] [--scope NAME]
  mission_closeout.py render   [<slug>] [--scope NAME] [--open]
  mission_closeout.py approve  [<slug>] [--scope NAME] --items A-1,A-2 --by NAME --link URL [--hash H]
  mission_closeout.py record   [<slug>] [--scope NAME] --action A-1 (--before S --after S | --skip REASON)
  mission_closeout.py gate     [<slug>] [--scope NAME]
  mission_closeout.py log      [<slug>] [--scope NAME]
  mission_closeout.py review-checks

gather collects FACTS only (the tree, a sweep outside it, twins, evidence per AC, security obligations,
record internals). It never classifies, closes or posts anything. Every fact it could not read is
UNKNOWN with a reason. Nothing is ever PASS. The agent writes closeout.yaml (v2: items, manifest,
UNKNOWN dispositions; see references/closeout-procedure.md). approve binds a human's yes to the hash
of an exact batch; record writes the read-back of each action. gate exits 1 until the close is real.
/mission close and mission_sync (status: done) call it.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import subprocess
import sys

from mission_lib import (GH_REPO, JIRA_BROWSE, JIRA_KEY_PATTERN, JIRA_ORG, JIRA_SKILL, MISSIONS_DIR, MR_UNKNOWN_REASON, PM_ROOT,
                         closeout_home, config_problem, load, now_utc, run)

JIRA = str(JIRA_SKILL)
UNKNOWN = "UNKNOWN"
BUCKETS = ["CLOSE-WITH-EVIDENCE", "SUPERSEDE", "KEEP", "ORPHAN", "FALSE-PREMISE", "HUMAN-ONLY"]
NEEDS_SUCCESSOR = {"KEEP"}
# Every check names the real (anonymized) case it catches. A check that names no case is not added.
# Group ids refer to the close-out eval ground truth (evals/expected/closeout/full.json "group").
CHECK_REGISTRY = {
    "tracker-status": {"label": "Every member and child ticket: live status matches the evidence", "catches": "J1, J2"},
    "parent-closing-comments": {"label": "Every closed parent has an evidence-backed closing comment", "catches": "J5"},
    "description-vs-reality": {"label": "Closed parents: description and summary match what shipped", "catches": "J5, G2, G3, G11"},
    "done-without-evidence": {"label": "Every AC of a Done ticket has an evidence link, security tickets first", "catches": "J7"},
    "obsolete-items": {"label": "Items made obsolete by later changes are superseded or rescoped", "catches": "J3, J4"},
    "github-tree": {"label": "Open GitHub sub-issues under the root, parent and seeds are reviewed", "catches": "G1, G9"},
    "false-premises": {"label": "Record text that is no longer true is listed for correction", "catches": "G2, G3, G11"},
    "orphans": {"label": "Every remaining item has a successor home that accepted it", "catches": "G5, M1"},
    "wayfinder-closes": {"label": "Wayfinder map children are closed through the wayfinder tool, not raw gh close", "catches": "G12"},
    "dependencies": {"label": "Every stated ordering between maps or issues exists as a blockedBy edge", "catches": "G10"},
    "reflections": {"label": "Reflections are written, and stay under their map until written", "catches": "G8"},
    "risk-acceptance": {"label": "Every live known gap has a residual-risk decision by a named person", "catches": "H3, J7"},
    "handoffs": {"label": "Pending session handoffs for this scope are completed or closed", "catches": "H1, H2, H4"},
    "drafts": {"label": "Drafts with no posted record are checked against their target", "catches": "D1"},
    "infra-tails": {"label": "Cleanup MRs, branches and unapplied infra changes are finished or owned", "catches": "M1"},
}
CHECKLIST_IDS = list(CHECK_REGISTRY)
CHECKLIST = [(k, v["label"]) for k, v in CHECK_REGISTRY.items()]
CONTROL_KINDS = {"security", "access", "safety", "contract"}
CONSEQUENTIAL_AFFECTS = {"production", "authorization", "scope", "prerequisite"}
PER_ITEM_CLASSES = {"security", "cancellation", "changed-commitment"}
ACTION_CLASSES = {"routine"} | PER_ITEM_CLASSES
CLOSE_KINDS = {"close", "transition", "supersede"}
BATCH_CLOSE_CAP = 15
HASHED_FIELDS = ("id", "item", "target", "expected_state", "kind", "action", "evidence", "successor", "class")
NOT_A_NAME = {"", "agent", "claude", "assistant", "ai", "bot", "tbd", "unknown", "none", "n/a", "?", "someone"}
REVIEW_WINDOW = 5
STEP_STATES = {"done", "na", "open", "unknown"}
PENDING_HANDOFF = {"awaiting_initiation", "initiated"}
DONE_WORDS = re.compile(r"done|termin|closed|won't|wont|resolved|ferm|abandon", re.I)


# ---------------------------------------------------------------- location

def closeout_dir(slug: str | None, scope: str | None) -> tuple[pathlib.Path, dict]:
    """The folder that holds the close-out files, and the mission record (empty for a scope without one).
    A mission's files live in its folder, or in missions/_closeout/<slug>/ when the sweep ran before the record
    existed. A --scope whose name is now a mission slug is that mission."""
    if config_problem():
        sys.exit(config_problem())
    if not slug and scope and (MISSIONS_DIR / scope / "mission.yaml").exists():
        print(f"note: '{scope}' has a mission record now; using the mission", file=sys.stderr)
        slug = scope
    if slug:
        d = MISSIONS_DIR / slug
        if not (d / "mission.yaml").exists():
            sys.exit(f"mission not found: {slug} (looked in {d}). Use --scope NAME with seeds for a scope without a record.")
        return closeout_home(d), load(d)
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
        data = jira_call("search", jql, "--max", str(JIRA_CHILD_CAP + 1))
        if isinstance(data, dict):
            sink.append(f"{jql}: {data.get('error')}")
            continue
        if len(data) > JIRA_CHILD_CAP:
            sink.append(f"{jql}: truncated at {JIRA_CHILD_CAP} results")
        found += [row["key"] for row in data[:JIRA_CHILD_CAP] if row.get("key")]
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
    text = (desc.get("description") or "") if isinstance(desc, dict) and "description" in desc else None
    if text is not None:
        f["description_excerpt"] = text[:1500]
        f["description"] = text[:TEXT_BUDGET]
    else:
        f["description_excerpt"] = f["description"] = UNKNOWN
    if ok_comments:
        budget, kept = TEXT_BUDGET, []
        for c in sorted(comments, key=lambda c: str(c.get("created", ""))):
            body = str(c.get("body") or "")
            kept.append({"author": c.get("author"), "created": str(c.get("created", "")), "body": body[:max(budget, 0)]})
            budget -= len(body)
        f["comments"] = kept
    else:
        f["comments"] = UNKNOWN
    f["text_truncated"] = (text is not None and len(text) > TEXT_BUDGET) or (ok_comments and budget < 0)
    ac = ac_evidence(text, comments) if text is not None else {"items": UNKNOWN, "evidence": {}, "without_evidence": UNKNOWN}
    f["ac_items"], f["ac_evidence"], f["ac_without_evidence"] = ac["items"], ac["evidence"], ac["without_evidence"]
    f["security"] = is_security(meta.get("summary") if ok_meta else "", text)
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
    awe = f["ac_without_evidence"]
    f["done_without_evidence"] = UNKNOWN if f["closed"] == UNKNOWN or (closed and awe == UNKNOWN) else bool(closed and awe)
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
    if frontier:
        errors.append(f"depth exhausted after 2 levels: children of {frontier[:10]} not read")
    with cf.ThreadPoolExecutor(6) as ex:
        tickets = list(ex.map(jira_ticket, keys))
    bad = [t["key"] for t in tickets if t["status"] == UNKNOWN]
    status = "OK" if not bad and not errors else ("PARTIAL" if len(bad) < len(tickets) else UNKNOWN)
    reason = "; ".join(([f"children unknown, {e}" for e in errors] + [f"unreadable {bad}"] * bool(bad))[:3]) or None
    return {"status": status, "reason": reason, "seeds": seeds, "unreadable": bad,
            "legacy_query_errors": legacy, "tickets": tickets}


def field_unknowns(jira: dict) -> list[str]:
    """Ticket fields the gatherer could not settle. An UNKNOWN field is never a pass."""
    ts = jira.get("tickets", [])
    out = []
    keys = [t["key"] for t in ts if t.get("closed") is True and t.get("comment_after_close") == UNKNOWN]
    if keys:
        out.append(f"jira-fields: comment_after_close UNKNOWN on {len(keys)} closed ticket(s) {keys}: "
                   "no resolution date; read the status history before calling a closing comment present or missing")
    keys = [t["key"] for t in ts if t.get("text_truncated") is True]
    if keys:
        out.append(f"jira-text: description or comments over the {TEXT_BUDGET}-character budget on {keys}; read them in full by hand")
    keys = [t["key"] for t in ts if t.get("status") != UNKNOWN and t.get("ac_items") == UNKNOWN]
    if keys:
        out.append(f"jira-ac: no AC list found on {len(keys)} ticket(s) {keys}; evidence per AC cannot be checked")
    return out


# ---------------------------------------------------------------- github

NODE = "number repository{nameWithOwner}"
GH_Q = """query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issue(number:$n){
number title state stateReason url closedAt updatedAt body labels(first:100){nodes{name}}
parent{%(node)s}
blockedBy(first:100){totalCount nodes{%(node)s}}
blocking(first:100){totalCount nodes{%(node)s}}
subIssues(first:100){totalCount pageInfo{hasNextPage endCursor} nodes{%(node)s}}
comments(first:100){totalCount pageInfo{hasNextPage endCursor} nodes{body createdAt author{login}}}}}}""" % {"node": NODE}
GH_PAGE_Q = """query($o:String!,$r:String!,$n:Int!,$after:String){repository(owner:$o,name:$r){issue(number:$n){
%s(first:100, after:$after){totalCount pageInfo{hasNextPage endCursor} nodes{%s}}}}}"""
PAGE_FIELDS = {"subIssues": NODE, "comments": "body createdAt author{login}"}


def gh_graphql(query: str, **vars) -> dict:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in vars.items():
        if v is not None:
            args += ["-F" if isinstance(v, int) else "-f", f"{k}={v}"]
    r = run(args, check=False)
    if r.returncode != 0:
        return {"error": r.stderr.strip()[:200] or f"exit {r.returncode}"}
    try:
        return json.loads(r.stdout)["data"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return {"error": "unexpected GraphQL response"}


def paginate(fetch_page, first=None) -> dict:
    """Follow pageInfo cursors. fetch_page(after) returns one connection. truncated when pages run out first."""
    page = first if first is not None else fetch_page(None)
    if not isinstance(page, dict) or "nodes" not in page:
        return {"nodes": [], "total": UNKNOWN, "truncated": True, "error": (page or {}).get("error") if isinstance(page, dict) else "no page"}
    nodes, n = list(page.get("nodes") or []), 1
    while (page.get("pageInfo") or {}).get("hasNextPage") and n < MAX_PAGES:
        page = fetch_page(page["pageInfo"]["endCursor"])
        if not isinstance(page, dict) or "nodes" not in page:
            return {"nodes": nodes, "total": UNKNOWN, "truncated": True, "error": "a later page failed"}
        nodes += page.get("nodes") or []
        n += 1
    return {"nodes": nodes, "total": page.get("totalCount", len(nodes)),
            "truncated": bool((page.get("pageInfo") or {}).get("hasNextPage"))}


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
    data = gh_graphql(GH_Q, o=owner, r=name, n=n)
    if "error" in data:
        return data
    i = (data.get("repository") or {}).get("issue")
    if not i:
        return {"error": "issue not found"}

    def more(field):
        def fetch(after):
            d = gh_graphql(GH_PAGE_Q % (field, PAGE_FIELDS[field]), o=owner, r=name, n=n, after=after)
            return d if "error" in d else ((d.get("repository") or {}).get("issue") or {}).get(field)
        return fetch

    subs = paginate(more("subIssues"), i["subIssues"])
    coms = paginate(more("comments"), i["comments"])
    ref = lambda x: f"{x['repository']['nameWithOwner']}#{x['number']}"
    refs = lambda conn: [ref(x) for x in conn["nodes"] if x]
    body = i.get("body") or ""
    budget, comments = TEXT_BUDGET - len(body), []
    for c in coms["nodes"]:
        b = str(c.get("body") or "")
        comments.append({"author": (c.get("author") or {}).get("login"), "created": c.get("createdAt"), "body": b[:max(budget, 0)]})
        budget -= len(b)
    edges_trunc = any(i[k]["totalCount"] > len(i[k]["nodes"]) for k in ("blockedBy", "blocking"))
    return {"repo": repo, "number": i["number"], "title": i["title"], "state": i["state"].lower(),
            "state_reason": i.get("stateReason"), "url": i["url"], "closed_at": i.get("closedAt"),
            "updated_at": i.get("updatedAt"), "labels": [x["name"] for x in i["labels"]["nodes"]],
            "body": body[:TEXT_BUDGET], "body_excerpt": body[:1500], "comments": comments, "comment_count": coms["total"],
            "comments_truncated": coms["truncated"], "text_truncated": budget < 0,
            "tracker_parent": ref(i["parent"]) if i.get("parent") else None,
            "blocked_by": refs(i["blockedBy"]), "blocking": refs(i["blocking"]), "edges_truncated": edges_trunc,
            "blocking_mentions": blocking_mentions(body),
            "sub_issues_total": subs["total"], "sub_issues_truncated": subs["truncated"],
            "children": refs(subs)}


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
    unread: list[str] = []
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
            else:
                unread += [c for c in info.get("children", []) if c not in seen]
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
    trunc = [i["ref"] for i in issues if i.get("sub_issues_truncated") or i.get("comments_truncated")
             or i.get("edges_truncated") or i.get("text_truncated")]
    unread = sorted(set(unread) - set(seen))
    status = "OK" if not bad and not trunc and not unread else ("PARTIAL" if len(bad) < len(issues) else UNKNOWN)
    reason = None if status == "OK" else "; ".join(x for x in (f"unreadable {bad}" if bad else "", f"truncated {trunc}" if trunc else "",
                                                                f"depth {depth} exhausted: {len(unread)} child issue(s) not read" if unread else "") if x)
    return {"status": status, "reason": reason, "unread_children": unread,
            "roots": roots, "open": sum(1 for i in issues if i.get("state") == "open"),
            "closed": sum(1 for i in issues if i.get("state") == "closed"),
            "wayfinder_maps": maps, "reflections": reflections, "reflections_off_map": off_map,
            "wayfinder_untraced_closes": untraced_closes(maps),
            "blocking_mentions_without_edge": unenforced, "issues": issues}


# ---------------------------------------------------------------- text, AC evidence, security

TEXT_BUDGET = 40000
SWEEP_CAP = 50
JIRA_CHILD_CAP = 200
MAX_PAGES = 20
SECURITY_RE = re.compile(r"\b(auth\w*|security|access[- ]control|permission\w*|tokens?|secrets?|credential\w*|header|gateway|iam|"
                         r"oauth|encrypt\w*|bypass|probe|vulnerab\w*|privilege\w*|authz|authn)\b", re.I)
AC_LINE = re.compile(r"^\s*(?:[-*#]+\s*)?\**\s*(AC[-\s]?(\d+))\s*\**\s*[:.)\-]\s*(.+)$", re.I | re.M)
AC_HEADING = re.compile(r"^\s*(?:h\d\.\s*|#+\s*|\*+)?\s*acceptance criteria\b.*$", re.I | re.M)
BULLET = re.compile(r"^\s*(?:[-*]+|#+(?!\w)|\d+[.)])\s+(.+)$")
LINK_RE = re.compile(r"https?://[^\s)\]|>\"']+")
ALL_ACS = re.compile(r"\ball (?:the )?(?:acs|acceptance criteria)\b", re.I)


def ac_items(text: str):
    """AC items from a description: 'AC1: ...' lines, or the bullets under an 'Acceptance criteria' heading. UNKNOWN when none."""
    labelled = [{"id": f"AC{m.group(2)}", "text": m.group(3).strip()} for m in AC_LINE.finditer(text or "")]
    if labelled:
        return list({a["id"]: a for a in labelled}.values())
    h = AC_HEADING.search(text or "")
    if not h:
        return UNKNOWN
    items = []
    for line in (text or "")[h.end():].splitlines():
        if not line.strip():
            if items:
                break
            continue
        m = BULLET.match(line)
        if not m:
            break
        items.append({"id": f"AC{len(items) + 1}", "text": m.group(1).strip()})
    return items or UNKNOWN


def ac_evidence(description: str, comments: list) -> dict:
    """Evidence links per AC item, read from the comment bodies. without_evidence = AC items with no link."""
    items = ac_items(description)
    if items == UNKNOWN or not isinstance(comments, list):
        return {"items": items, "evidence": {}, "without_evidence": UNKNOWN}
    ev = {a["id"]: [] for a in items}
    for c in comments:
        body = str((c or {}).get("body") or "")
        links = LINK_RE.findall(body)
        if not links:
            continue
        hit = [a["id"] for a in items if re.search(rf"\bAC[-\s]?{a['id'][2:]}\b", body, re.I)]
        for aid in (list(ev) if ALL_ACS.search(body) else hit):
            ev[aid] += [x for x in links if x not in ev[aid]]
    return {"items": items, "evidence": ev, "without_evidence": [k for k, v in ev.items() if not v]}


def is_security(*texts) -> bool:
    return any(SECURITY_RE.search(str(t or "")) for t in texts)


def security_obligations(tickets: list[dict], issues: list[dict]) -> list[dict]:
    """Security obligations live without proof, in every state (Done included). Each one is investigated, never skipped."""
    out = []
    for t in tickets:
        if not t.get("security"):
            continue
        missing = t.get("ac_without_evidence")
        if missing == UNKNOWN or missing:
            out.append({"ref": t["key"], "status": t.get("status"), "reason": "no AC list found" if missing == UNKNOWN
                        else f"AC without an evidence link: {missing}"})
    for i in issues:
        if not is_security(i.get("title"), i.get("body")):
            continue
        n = i.get("comment_count", len(i.get("comments") or []) if isinstance(i.get("comments"), list) else UNKNOWN)
        if n == 0 or n == UNKNOWN:
            out.append({"ref": i["ref"], "status": i.get("state"),
                        "reason": "no comment: the check or probe may never have run" if n == 0 else "comments unread"})
    return out


# ---------------------------------------------------------------- twins

def jira_keys_in(text: str) -> list[str]:
    return sorted(set(re.findall(rf"\b({JIRA_KEY_PATTERN})\b", str(text or ""))))


def gh_refs_in(text: str, known: set[str]) -> list[str]:
    s = str(text or "")
    refs = {f"{m.group(1)}#{m.group(2)}" for m in re.finditer(r"github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)", s)}
    refs |= {f"{m.group(1)}#{m.group(2)}" for m in re.finditer(r"\b([\w.-]+/[\w.-]+)#(\d+)\b", s)}
    refs |= {r for r in known for m in re.finditer(r"(?<![\w/])#(\d+)\b", s) if r.endswith(f"#{m.group(1)}")}
    return sorted(refs)


def _text_of(x: dict, *fields) -> str:
    parts = [str(x.get(f) or "") for f in fields]
    cs = x.get("comments")
    if isinstance(cs, list):
        parts += [str((c or {}).get("body") or "") for c in cs]
    return "\n".join(parts)


def twin_pairs(tickets: list[dict], issues: list[dict]) -> list[dict]:
    """Jira tickets and GitHub issues that cite each other. Review each pair together; a Done twin is never evidence for the open side."""
    tk = {t["key"]: t for t in tickets}
    iss = {i["ref"]: i for i in issues}
    pairs: dict[tuple, set] = {}
    for ref, i in iss.items():
        for k in jira_keys_in(_text_of(i, "title", "body", "body_excerpt")):
            pairs.setdefault((k, ref), set()).add("gh text")
    for key, t in tk.items():
        for ref in gh_refs_in(_text_of(t, "summary", "description", "description_excerpt"), set(iss)):
            pairs.setdefault((key, ref), set()).add("jira text")
    out = []
    for (k, ref), via in sorted(pairs.items()):
        jt, gi = tk.get(k), iss.get(ref)
        js = jt.get("closed") if jt else UNKNOWN
        gs = (gi.get("state") == "closed") if gi else UNKNOWN
        out.append({"jira": k, "gh": ref, "via": sorted(via), "jira_state": jt.get("status") if jt else UNKNOWN,
                    "gh_state": gi.get("state") if gi else UNKNOWN,
                    "states_differ": UNKNOWN if UNKNOWN in (js, gs) else js != gs})
    return out


# ---------------------------------------------------------------- successor coverage

OUT_OF_SCOPE = re.compile(r"out of scope|not in scope|non-goals?|excluded|exclusions?|will not|won't|not covered|left out|deferred", re.I)
STOP = {"the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "is", "be", "it", "this", "that", "from", "by"}


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", str(s or "").lower()) if w not in STOP and len(w) > 2}


def coverage_of(item: dict, successor_text) -> dict:
    """Does the successor cover the item? Reads its explicit out-of-scope lines. UNKNOWN when the text is unread."""
    ref = str(((item.get("ref") or {}) if isinstance(item.get("ref"), dict) else {}).get("ref") or "")
    base = {"item": item.get("id"), "excluded_by": [], "mentioned": UNKNOWN}
    if successor_text is None or successor_text == UNKNOWN:
        return {**base, "status": UNKNOWN}
    words = _words(item.get("title") or item.get("finding"))

    def names_item(line: str) -> bool:
        lw = _words(line)
        return bool(ref and ref in line) or (bool(words) and len(words & lw) / len(words) >= 0.6)

    lines = [ln.strip() for ln in str(successor_text).splitlines() if ln.strip()]
    excluded = [ln for ln in lines if OUT_OF_SCOPE.search(ln) and names_item(ln)]
    mentioned = any(names_item(ln) for ln in lines)
    return {**base, "excluded_by": excluded, "mentioned": mentioned,
            "status": "excluded" if excluded else ("mentioned" if mentioned else "not-mentioned")}


# ---------------------------------------------------------------- sweep outside the tree

def _gh_search(term: str, since: str, cap: int):
    if not GH_REPO:
        return {"error": "no gh_repo in the mission config"}
    r = run(["gh", "search", "issues", term, "--repo", GH_REPO, "--updated", f">={since}", "--limit", str(cap + 1),
             "--json", "number,title,state,url,updatedAt"], check=False)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout).strip()[:200] or f"exit {r.returncode}"}
    try:
        return json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return {"error": "gh search returned no JSON"}


def _merge_hit(sink: dict, ref: str, term: str, extra: dict) -> None:
    h = sink.setdefault(ref, {"ref": ref, "matched_on": [], **extra})
    if term not in h["matched_on"]:
        h["matched_on"].append(term)


def _status(errors: list, total: int) -> str:
    return "OK" if not errors else ("PARTIAL" if len(errors) < total else UNKNOWN)


def _sweep_git(repos: list[str], terms: list[str], since: str | None) -> tuple[dict, dict]:
    if not repos:
        return ({"status": UNKNOWN, "reason": "no --repo given; git history not searched", "hits": []},
                {"status": UNKNOWN, "reason": "no --repo given; MR exclusions not read", "exclusions": []})
    if not since:
        return ({"status": UNKNOWN, "reason": "no start date (mission.created or --since)", "hits": []},
                {"status": UNKNOWN, "reason": "no start date", "exclusions": []})
    pat = re.compile("|".join(re.escape(t) for t in terms), re.I) if terms else None
    hits, errors, per_repo, mrs = [], [], {}, {}
    for repo in repos:
        r = run(["git", "-C", repo, "log", "--all", f"--since={since}", "--format=%H%x1f%s%x1f%b%x1e"], check=False)
        if r.returncode != 0:
            errors.append(repo)
            per_repo[repo] = {"status": UNKNOWN, "reason": r.stderr.strip()[:160]}
        else:
            per_repo[repo] = {"status": "OK"}
            for rec in r.stdout.split("\x1e"):
                parts = rec.strip("\n").split("\x1f")
                if len(parts) < 2 or not pat:
                    continue
                found = sorted({m.group(0).lower() for m in pat.finditer(parts[1] + "\n" + (parts[2] if len(parts) > 2 else ""))})
                if found:
                    hits.append({"repo": repo, "sha": parts[0][:12], "subject": parts[1], "matched_on": found})
        rem = run(["git", "-C", repo, "remote", "get-url", "origin"], check=False)
        url = rem.stdout.strip() if rem.returncode == 0 else ""
        m = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", url)
        if not m:
            mrs[repo] = {"status": UNKNOWN, "reason": MR_UNKNOWN_REASON}
            continue
        pr = run(["gh", "pr", "list", "-R", m.group(1), "--state", "all", "--search", f"updated:>={since}", "--limit", "100",
                  "--json", "number,title,body,state,url"], check=False)
        if pr.returncode != 0:
            mrs[repo] = {"status": UNKNOWN, "reason": pr.stderr.strip()[:160]}
            continue
        lines = [{"pr": p.get("url"), "line": ln.strip()} for p in json.loads(pr.stdout or "[]")
                 for ln in str(p.get("body") or "").splitlines() if OUT_OF_SCOPE.search(ln)]
        mrs[repo] = {"status": "OK" if len(json.loads(pr.stdout or "[]")) < 100 else "PARTIAL", "exclusions": lines}
    mr_bad = [k for k, v in mrs.items() if v["status"] != "OK"]
    return ({"status": _status(errors, len(repos)), "reason": f"git log failed in {errors}" if errors else None,
             "since": since, "repos": per_repo, "hits": hits},
            {"status": _status(mr_bad, len(repos)), "reason": "; ".join(f"{k}: {mrs[k].get('reason') or 'over 100 PRs'}" for k in mr_bad) or None,
             "repos": mrs, "exclusions": [x for v in mrs.values() for x in v.get("exclusions") or []]})


def gather_sweep(aliases: list[str], keys: list[str], since: str | None, repos: list[str], exclusions: list[str],
                 tree_refs: set, offline: bool, cap: int = SWEEP_CAP) -> dict:
    """Search outside the tree: Jira text per alias and key (all states), GitHub since the start, git and MR history.
    Hits already in the tree are dropped. Results are deduped by ref; a capped search is truncated, which is UNKNOWN."""
    terms = list(dict.fromkeys([t for t in aliases + keys if t]))
    if offline:
        return {"status": UNKNOWN, "reason": "offline", "terms": terms, "excluded": []}
    if not terms:
        return {"status": UNKNOWN, "reason": "no aliases or keys to search", "terms": [], "excluded": []}
    ex = re.compile("|".join(re.escape(x) for x in exclusions), re.I) if exclusions else None
    jhits, jerr = {}, []
    for t in terms:
        data = jira_call("search", f'text ~ "{t}" ORDER BY updated DESC', "--max", str(cap + 1))
        if isinstance(data, dict):
            jerr.append(f"{t}: {data.get('error')}")
            continue
        if len(data) > cap:
            jerr.append(f"{t}: truncated at {cap}")
        for row in data[:cap]:
            if row.get("key") and row["key"] not in tree_refs:
                _merge_hit(jhits, row["key"], t, {"summary": row.get("summary"), "status": row.get("status")})
    ghits, gerr = {}, []
    if not since:
        gerr = ["no start date (mission.created or --since)"]
    else:
        for t in terms:
            data = _gh_search(t, since, cap)
            if isinstance(data, dict):
                gerr.append(f"{t}: {data.get('error')}")
                continue
            if len(data) > cap:
                gerr.append(f"{t}: truncated at {cap}")
            for row in data[:cap]:
                ref = f"{GH_REPO}#{row.get('number')}"
                if ref not in tree_refs:
                    _merge_hit(ghits, ref, t, {"title": row.get("title"), "state": str(row.get("state") or "").lower(), "url": row.get("url")})
    excluded = []
    for sink in (jhits, ghits):
        for ref in list(sink):
            h = sink[ref]
            if ex and ex.search(f"{h.get('summary') or ''} {h.get('title') or ''}"):
                excluded.append({**sink.pop(ref), "excluded_by": ex.pattern})
    git, mrs = _sweep_git(repos, terms, since)
    jira = {"status": _status(jerr, len(terms)), "reason": "; ".join(jerr)[:600] or None, "hits": list(jhits.values())}
    github = {"status": _status(gerr, len(terms)) if since else UNKNOWN, "reason": "; ".join(gerr)[:600] or None,
              "hits": list(ghits.values())}
    parts = [jira["status"], github["status"], git["status"], mrs["status"]]
    status = "OK" if all(p == "OK" for p in parts) else (UNKNOWN if all(p == UNKNOWN for p in parts) else "PARTIAL")
    return {"status": status, "reason": None if status == "OK" else "see jira/github/git/mrs", "terms": terms, "since": since,
            "jira": jira, "github": github, "git": git, "mrs": mrs, "excluded": excluded}


def scope_exclusions(m: dict) -> list[str]:
    """scope_constraints entries written as 'exclude: <term>' or 'out of scope: <term>' are sweep exclusions."""
    out = []
    for s in m.get("scope_constraints") or []:
        mm = re.match(r"\s*(?:exclude|out of scope)\s*:\s*(.+)$", str(s), re.I)
        if mm:
            out.append(mm.group(1).strip())
    return out


def obligations(facts: dict) -> list[list[str]]:
    """Sweep hits deduplicated by obligation: twin refs (a ticket and the issue that cites it) count once."""
    sw = facts.get("sweep") or {}
    refs = [h["ref"] for k in ("jira", "github") for h in (sw.get(k) or {}).get("hits") or []]
    parent = {r: r for r in refs}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    for p in facts.get("twins") or []:
        if p["jira"] in parent and p["gh"] in parent:
            parent[find(p["jira"])] = find(p["gh"])
    groups: dict[str, list[str]] = {}
    for r in refs:
        groups.setdefault(find(r), []).append(r)
    return sorted(groups.values())


# ---------------------------------------------------------------- record internals and UNKNOWN aggregation

DECISION_WORDS = re.compile(r"\b(decision|decided|resolved|resolution|destination reached|we chose|chosen)\b", re.I)


def record_internals(m: dict, gh: dict) -> dict:
    maps = [i for i in gh.get("issues") or [] if "wayfinder:map" in (i.get("labels") or []) and i.get("state") == "closed"]
    unknown = [i["ref"] for i in maps if not isinstance(i.get("comments"), list)]
    without = [i["ref"] for i in maps if isinstance(i.get("comments"), list)
               and not any(DECISION_WORDS.search(str((c or {}).get("body") or "")) for c in i["comments"])]
    return {"unratified_decisions": [d.get("id") for d in m.get("decisions") or [] if d.get("state") == "proposed"],
            "maps_closed_without_decision": without, "maps_decision_unknown": unknown,
            "orderings_without_edge": [x["ref"] for x in gh.get("blocking_mentions_without_edge") or []]}


def aggregate_unknowns(facts: dict) -> list[str]:
    """Every source, at any depth, whose status is UNKNOWN or PARTIAL. An UNKNOWN nested in a section is not a pass."""
    out = []

    def walk(node, path):
        if isinstance(node, dict):
            if node.get("status") in (UNKNOWN, "PARTIAL") and path:
                name = ("mrs" if path == ["branches", "mrs"] else f"wayfinder-telemetry {path[-1]}"
                        if path[:2] == ["github", "wayfinder_untraced_closes"] else ".".join(path))
                out.append(f"{name}: {node.get('reason') or node.get('status')}")
            for k, v in node.items():
                if isinstance(v, dict):
                    walk(v, path + [str(k)])
    walk({k: v for k, v in facts.items() if k not in ("scope", "unknown")}, [])
    return out


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
    gh = facts["github"]
    since = str(m.get("created") or a.since or "")[:10] or None
    tree_refs = set(all_keys) | {i["ref"] for i in gh.get("issues") or []}
    facts["sweep"] = gather_sweep(aliases, all_keys, since, a.repo or [], scope_exclusions(m) + split(a.exclude),
                                  tree_refs, a.offline, a.sweep_cap)
    facts["twins"] = twin_pairs(jira.get("tickets") or [], gh.get("issues") or [])
    facts["obligations"] = obligations(facts)
    facts["security_obligations"] = security_obligations(jira.get("tickets") or [], gh.get("issues") or [])
    facts["record"] = record_internals(m, gh)
    facts["unknown"] = aggregate_unknowns(facts)
    facts["unknown"] += field_unknowns(jira)
    unmarked = facts["drafts"].get("no_posted_marker") or []
    if unmarked:
        facts["unknown"].append(f"drafts: {len(unmarked)} draft(s) with no posted record; remote state not checked, "
                                "verify the target before calling any of them unsent")
    out = d / "closeout-facts.json"
    out.write_text(json.dumps(facts, indent=2, ensure_ascii=False, default=str))
    print(f"facts -> {out}")
    for k, st, reason in fact_sources(facts):
        print(f"  source {k}: {st}" + (f" ({reason})" if st != "OK" and reason else ""))
    for lbl, n in fact_counts(facts):
        print(f"  {lbl}: {n}")
    for u in facts["unknown"]:
        print(f"  UNKNOWN {u}")
    return 0


# ---------------------------------------------------------------- close-out record helpers

def load_closeout(d: pathlib.Path):
    import yaml
    f = d / "closeout.yaml"
    return yaml.safe_load(f.read_text()) if f.exists() else None


def save_closeout(d: pathlib.Path, co: dict) -> None:
    import yaml
    (d / "closeout.yaml").write_text(yaml.safe_dump(co, sort_keys=False, allow_unicode=True, width=120))


def named(who) -> bool:
    """A named human: not empty, not an agent or a placeholder."""
    return str(who or "").strip().lower() not in NOT_A_NAME


def has_link(x) -> bool:
    return isinstance(x, dict) and bool(x.get("url"))


def named_successor(s) -> bool:
    return isinstance(s, dict) and bool(s.get("url")) and bool(s.get("title"))


def accepted(s) -> bool:
    """The successor accepted the obligation (not only linked): a named person and a link to where they said it."""
    acc = (s or {}).get("accepted") if isinstance(s, dict) else None
    return isinstance(acc, dict) and named(acc.get("by")) and has_link(acc.get("link")) and not s.get("excludes")


def risk_decided(it: dict) -> bool:
    rr = it.get("residual_risk") or {}
    if isinstance(rr, dict) and named(rr.get("by")) and has_link(rr.get("link")) and str(rr.get("decision") or "").strip():
        return True
    s = it.get("successor") or {}
    return named_successor(s) and named(s.get("owner"))


def is_live(it: dict) -> bool:
    """live: false is the only proof of not-live. Missing or UNKNOWN counts as live."""
    return it.get("live") is not False


def has_evidence(it: dict) -> bool:
    return bool(it.get("evidence")) and str(it.get("evidence_state") or "present") not in ("missing", UNKNOWN)


def big_miss_reasons(it: dict) -> list[str]:
    """SYNTHESIS section 3, as predicates on a close-out item. Empty list = routine."""
    out = []
    if it.get("control") in CONTROL_KINDS and is_live(it) and (not has_evidence(it) or not risk_decided(it)):
        out.append("live-assurance-gap")
    s = it.get("successor") or {}
    if it.get("bucket") == "ORPHAN" or it.get("obligation_lost") or (isinstance(s, dict) and s.get("excludes")) \
            or (it.get("bucket") == "KEEP" and not accepted(s)):
        out.append("valid-obligation-uncovered")
    if it.get("bucket") == "FALSE-PREMISE" and set(it.get("affects") or []) & CONSEQUENTIAL_AFFECTS:
        out.append("consequential-false-record")
    if it.get("control_failure"):
        out.append("control-failure")
    return out


def needs_decision(it: dict) -> bool:
    return bool(big_miss_reasons(it)) and it.get("state") != "done" and not (it.get("decision") or {}).get("answer")


def unknown_key(u: str) -> str:
    return str(u).split(":", 1)[0].strip()


def entry_hash(a: dict) -> str:
    payload = json.dumps({k: a.get(k) for k in HASHED_FIELDS}, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def batch_hash(entries: dict) -> str:
    return hashlib.sha256("\n".join(f"{k}:{v}" for k, v in sorted(entries.items())).encode()).hexdigest()[:16]


def batch_problems(actions: list[dict]) -> list[str]:
    out = []
    closes = [a["id"] for a in actions if a.get("kind") in CLOSE_KINDS]
    if len(closes) > BATCH_CLOSE_CAP:
        out.append(f"{len(closes)} closes in one batch; the cap is {BATCH_CLOSE_CAP}. Split the batch.")
    solo = [a["id"] for a in actions if a.get("class", "routine") in PER_ITEM_CLASSES]
    if solo and len(actions) > 1:
        out.append(f"{solo} are security, cancellation or changed-commitment actions: per-item approval only, never in a batch")
    bad = [a["id"] for a in actions if a.get("class", "routine") not in ACTION_CLASSES]
    if bad:
        out.append(f"{bad}: class must be one of {sorted(ACTION_CLASSES)}")
    return out


def plan_batches(manifest: list[dict]) -> list[dict]:
    """Proposed actions, grouped for approval: per-item classes alone, routine actions in chunks of <= 15 closes."""
    todo = [a for a in manifest or [] if a.get("state", "proposed") == "proposed"]
    batches, cur = [], []
    for a in todo:
        if a.get("class", "routine") in PER_ITEM_CLASSES:
            batches.append([a])
            continue
        if a.get("kind") in CLOSE_KINDS and sum(1 for x in cur if x.get("kind") in CLOSE_KINDS) >= BATCH_CLOSE_CAP:
            batches.append(cur)
            cur = []
        cur.append(a)
    if cur:
        batches.append(cur)
    return [{"items": [a["id"] for a in b], "hash": batch_hash({a["id"]: entry_hash(a) for a in b})} for b in batches]


def approval_state(co: dict) -> dict:
    """Per action id: approved, changed (edited after approval), or unapproved. The latest approval of an id wins."""
    latest = {}
    for ap in co.get("approvals") or []:
        if not isinstance(ap, dict) or not named(ap.get("by")):
            continue
        hashes = ap.get("entry_hashes") or {}
        if batch_hash(hashes) != ap.get("hash"):
            continue
        for i in ap.get("items") or []:
            latest[i] = hashes.get(i)
    out = {}
    for a in co.get("manifest") or []:
        h = latest.get(a.get("id"))
        out[a.get("id")] = "unapproved" if h is None else ("approved" if h == entry_hash(a) else "changed")
    return out


# ---------------------------------------------------------------- gate

def mission_record_dir(d: pathlib.Path) -> pathlib.Path | None:
    """The mission folder for a close-out folder (itself, or missions/<slug> for missions/_closeout/<slug>)."""
    if (d / "mission.yaml").exists():
        return d
    if d.parent.name == "_closeout" and (MISSIONS_DIR / d.name / "mission.yaml").exists():
        return MISSIONS_DIR / d.name
    return None


def gate(d: pathlib.Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). An empty error list means the mission may close.
    For a mission with a record, every thread must also be resolved, dropped, or parked with an accepted home."""
    err, warn = [], []
    md = mission_record_dir(d)
    if md is not None:
        from mission_thread import gate_errors
        terr, twarn = gate_errors(load(md))
        err += [f"thread {e}" for e in terr]
        warn += twarn
        d = closeout_home(md)
    co = load_closeout(d)
    if co is None:
        return [f"no closeout.yaml in {d}: run /mission check --close first"] + err, warn
    facts = {}
    if not (d / "closeout-facts.json").exists():
        err.append("no closeout-facts.json: run mission closeout gather")
    else:
        facts = json.loads((d / "closeout-facts.json").read_text())
    if co.get("schema") != "mission-closeout/v2":
        err.append("closeout.yaml is not mission-closeout/v2: rewrite it with a manifest (references/closeout-procedure.md)")
    steps = {s.get("id"): s for s in co.get("checklist") or [] if isinstance(s, dict)}
    for sid in CHECKLIST_IDS:
        s = steps.get(sid)
        if not s or s.get("status") not in STEP_STATES:
            err.append(f"checklist step '{sid}' has no status ({'/'.join(sorted(STEP_STATES))})")
        elif s["status"] in ("open", "unknown"):
            warn.append(f"checklist step '{sid}' is {s['status']}")
    items = co.get("items") or []
    err += item_errors(items, warn)
    err += coverage_errors(items, load_coverage(d))
    err += manifest_errors(co)
    err += unknown_errors(co, facts, items)
    return err, warn


def item_errors(items: list[dict], warn: list[str]) -> list[str]:
    err = []
    for i, it in enumerate(items):
        where = f"items[{i}] {it.get('id', '?')}"
        b = it.get("bucket")
        if b not in BUCKETS:
            err.append(f"{where}: bucket '{b}' not in {BUCKETS}")
            continue
        succ = it.get("successor") or {}
        if b == "ORPHAN" and not (named_successor(succ) and named(it.get("parked_by"))):
            err.append(f"{where}: ORPHAN without a named successor and parked_by. Give it a home before close.")
        elif b == "ORPHAN" and not accepted(succ):
            err.append(f"{where}: ORPHAN successor is linked but has not accepted it (successor.accepted: by + link)")
        if b in NEEDS_SUCCESSOR and not named_successor(succ):
            err.append(f"{where}: KEEP needs successor with url and title")
        elif b in NEEDS_SUCCESSOR and not accepted(succ):
            err.append(f"{where}: KEEP successor has not accepted the obligation (successor.accepted: by + link)")
        if b == "HUMAN-ONLY" and it.get("state") != "done" and not (named_successor(succ) or named(it.get("owner"))):
            err.append(f"{where}: HUMAN-ONLY item still open without a named owner or successor. Give it a home before close.")
        if it.get("control") in CONTROL_KINDS and is_live(it) and not risk_decided(it):
            err.append(f"{where}: live {it['control']} risk (live: {it.get('live', UNKNOWN)}) without a residual-risk decision "
                       "by a named person (residual_risk: decision, by, link) or a successor with a named owner")
        if it.get("found_by") == "human" and it.get("miss_weight") != "routine" \
                and not (str(it.get("new_check") or "").strip() and str(it.get("eval_case") or "").strip()):
            err.append(f"{where}: found by the human, not the sweep: name the new_check and the eval_case "
                       "(or miss_weight: routine for friction that waits for a repeat)")
        if it.get("state", "proposed") == "proposed":
            warn.append(f"{where}: {b} still proposed")
    return err


def load_coverage(d: pathlib.Path) -> dict:
    f = d / "closeout-coverage.json"
    return (json.loads(f.read_text()).get("items") or {}) if f.exists() else {}


def coverage_errors(items: list[dict], cov: dict) -> list[str]:
    """A successor covers an item only if it was read and its out-of-scope lines do not name the item."""
    err = []
    for it in items:
        s = it.get("successor") or {}
        if it.get("bucket") not in ("KEEP", "ORPHAN") or not named_successor(s):
            continue
        c = cov.get(it.get("id"))
        if not c:
            err.append(f"{it.get('id')}: no coverage check of its successor; run mission closeout coverage")
        elif c.get("status") == UNKNOWN:
            err.append(f"{it.get('id')}: successor text unread (coverage UNKNOWN); read it before calling the item covered")
        elif c.get("status") == "excluded" and not has_link(s.get("exclusion_resolved")):
            err.append(f"{it.get('id')}: the successor excludes it ({'; '.join(c.get('excluded_by') or [])[:160]}). "
                       "Find another home, or link where the successor owner took it back in (exclusion_resolved)")
    return err


def successor_text(s: dict):
    """Description or body plus every comment of a successor, or UNKNOWN."""
    ref = str(s.get("ref") or "")
    if s.get("kind") == "jira" or re.fullmatch(JIRA_KEY_PATTERN, ref):
        desc, coms = jira_call("description", ref), jira_call("comments", ref)
        if not (isinstance(desc, dict) and "description" in desc) or not isinstance(coms, list):
            return UNKNOWN
        return "\n".join([str(desc.get("description") or "")] + [str(c.get("body") or "") for c in coms])
    try:
        repo, n = gh_ref(ref)
    except ValueError:
        return UNKNOWN
    i = gh_issue(repo, n)
    if i.get("error") or i.get("comments_truncated"):
        return UNKNOWN
    return "\n".join([i.get("title") or "", i.get("body") or ""] + [c.get("body") or "" for c in i.get("comments") or []])


def cmd_coverage(a) -> int:
    d, _ = closeout_dir(a.mission, a.scope)
    co = load_closeout(d) or {}
    out = {}
    for it in co.get("items") or []:
        s = it.get("successor") or {}
        if named_successor(s):
            out[it["id"]] = {**coverage_of(it, successor_text(s)), "successor": s.get("ref") or s.get("url")}
    f = d / "closeout-coverage.json"
    f.write_text(json.dumps({"fetched_at": now_utc(), "items": out}, indent=2, ensure_ascii=False))
    for k, v in out.items():
        print(f"  {k} -> {v['successor']}: {v['status']}" + (f" ({v['excluded_by'][0][:100]})" if v["excluded_by"] else ""))
    print(f"coverage -> {f}")
    return 0


def manifest_errors(co: dict) -> list[str]:
    err = []
    manifest = co.get("manifest")
    if manifest is None:
        return ["no action manifest: list every action (target, expected_state, action, evidence) under manifest"]
    approvals = [a for a in co.get("approvals") or [] if isinstance(a, dict)]
    if not manifest and not any(named(a.get("by")) and has_link(a.get("link")) for a in approvals):
        err.append("empty manifest with no approval: a named person approves the empty list (mission closeout approve --items '')")
    for ap in approvals:
        if not named(ap.get("by")) or not has_link(ap.get("link")):
            err.append(f"approval {ap.get('hash')}: needs a named person and a link to where they said it")
        acts = [a for a in manifest if a.get("id") in (ap.get("items") or [])]
        err += [f"approval {ap.get('hash')}: {p}" for p in batch_problems(acts)]
    state = approval_state(co)
    for a in manifest:
        aid = a.get("id", "?")
        st, s = state.get(aid), a.get("state", "proposed")
        if s == "skipped":
            if not str(a.get("skipped_reason") or "").strip():
                err.append(f"{aid}: skipped without a reason")
            continue
        if st == "unapproved":
            err.append(f"{aid}: not approved (approve the manifest entry by its hash)")
            continue
        if st == "changed":
            err.append(f"{aid}: changed after approval; the approval no longer covers it. Re-approve the new text.")
            continue
        if s == "unverified":
            err.append(f"{aid}: unverified: the action reported nothing. Verify the remote state before any retry, then record the read-back")
        elif s != "done":
            err.append(f"{aid}: approved, not done")
        else:
            rb = a.get("readback") or {}
            if not (str(rb.get("before") or "").strip() and str(rb.get("after") or "").strip() and rb.get("at")):
                err.append(f"{aid}: done without a read-back (before, after, at)")
    return err


def unknown_errors(co: dict, facts: dict, items: list[dict]) -> list[str]:
    err = []
    disp = {str(u.get("source")): u for u in co.get("unknowns") or [] if isinstance(u, dict)}
    control_refs = {k for it in items if it.get("control") in CONTROL_KINDS for k in it.get("unknowns") or []}
    for key in dict.fromkeys(unknown_key(u) for u in facts.get("unknown") or []):
        u = disp.get(key)
        if not u:
            err.append(f"UNKNOWN '{key}' has no disposition (unknowns: accepted by a named human, tracked, or not consequential with a reason)")
            continue
        consequential = u.get("consequential", True) is not False or key in control_refs
        if u.get("consequential") is False and key in control_refs:
            err.append(f"UNKNOWN '{key}' touches a security, access, safety or contract control: it is consequential")
        if not consequential:
            if not str(u.get("reason") or "").strip():
                err.append(f"UNKNOWN '{key}': not consequential needs a reason")
            continue
        if u.get("disposition") == "accepted" and named(u.get("by")) and has_link(u.get("link")):
            continue
        if u.get("disposition") == "tracked" and named_successor(u.get("successor")):
            continue
        err.append(f"UNKNOWN '{key}': consequential; needs disposition accepted by a named human with a link, "
                   "or tracked with a successor (url, title)")
    return err


def cmd_gate(a) -> int:
    d, _ = closeout_dir(a.mission, a.scope)
    err, warn = gate(d)
    for w in warn:
        print(f"WARN  {w}")
    for e in err:
        print(f"ERROR {e}")
    print("GATE OPEN: the mission may close" if not err else "GATE CLOSED: the mission may not close")
    return 1 if err else 0


# ---------------------------------------------------------------- approve and record (the executor's ledger)

def cmd_approve(a) -> int:
    d, _ = closeout_dir(a.mission, a.scope)
    co = load_closeout(d)
    if co is None:
        sys.exit("no closeout.yaml")
    if not named(a.by):
        sys.exit(f"--by '{a.by}' is not a named human; an agent never approves")
    if not a.link:
        sys.exit("--link is required: where the human said yes")
    ids = split(a.items)
    manifest = co.get("manifest") or []
    by_id = {x.get("id"): x for x in manifest}
    missing = [i for i in ids if i not in by_id]
    if missing:
        sys.exit(f"not in the manifest: {missing}")
    acts = [by_id[i] for i in ids]
    probs = batch_problems(acts)
    if probs:
        sys.exit("refused: " + "; ".join(probs))
    hashes = {i: entry_hash(by_id[i]) for i in ids}
    h = batch_hash(hashes)
    if a.hash and a.hash != h:
        sys.exit(f"refused: the approved hash {a.hash} does not match the current batch {h}; an entry changed")
    co.setdefault("approvals", [])
    co["approvals"] = (co["approvals"] or []) + [{"hash": h, "items": ids, "entry_hashes": hashes, "by": a.by, "at": now_utc(),
                                                   "link": {"kind": "url", "url": a.link, "title": a.link_title or "approval"}}]
    for x in acts:
        if x.get("state", "proposed") == "proposed":
            x["state"] = "approved"
    save_closeout(d, co)
    print(f"approved {len(ids)} action(s), hash {h}, by {a.by}")
    return 0


def cmd_record(a) -> int:
    d, _ = closeout_dir(a.mission, a.scope)
    co = load_closeout(d)
    if co is None:
        sys.exit("no closeout.yaml")
    act = next((x for x in co.get("manifest") or [] if x.get("id") == a.action), None)
    if act is None:
        sys.exit(f"{a.action} is not in the manifest")
    if a.skip:
        act.update(state="skipped", skipped_reason=a.skip)
        save_closeout(d, co)
        print(f"{a.action}: skipped ({a.skip})")
        return 0
    st = approval_state(co).get(a.action)
    if st != "approved":
        sys.exit(f"{a.action} is {st}, not approved: do not execute it")
    act["readback"] = {"before": a.before, "after": a.after, "at": now_utc()}
    if not str(a.after or "").strip():
        act["state"] = "unverified"
        save_closeout(d, co)
        print(f"STOP {a.action}: no read-back after the action. Stop and verify the remote state before any retry; "
              "a retry on a silent mutation makes duplicates.")
        return 2
    act["state"] = "done"
    save_closeout(d, co)
    print(f"{a.action}: done, read-back recorded")
    return 0


# ---------------------------------------------------------------- self-improvement log

def closeout_log_file() -> pathlib.Path:
    return MISSIONS_DIR / "_meta" / "closeout-log.jsonl"


def cmd_log(a) -> int:
    d, _ = closeout_dir(a.mission, a.scope)
    co = load_closeout(d) or {}
    items = co.get("items") or []
    human = [i for i in items if i.get("found_by") == "human"]
    line = {"at": now_utc(), "scope": a.mission or a.scope,
            "buckets": {b: sum(1 for i in items if i.get("bucket") == b) for b in BUCKETS},
            "big_misses_by_sweep": [{"id": i.get("id"), "reasons": big_miss_reasons(i), "found_by": i.get("found_by")}
                                    for i in items if big_miss_reasons(i) and i.get("found_by") != "human"],
            "human_found": [{"id": i.get("id"), "finding": i.get("finding") or i.get("title"), "weight": i.get("miss_weight", "consequential"),
                             "new_check": i.get("new_check"), "eval_case": i.get("eval_case")} for i in human],
            "checks_fired": sorted({i.get("found_by") for i in items if i.get("found_by") and i.get("found_by") != "human"})}
    f = closeout_log_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(f"logged -> {f}")
    for h in line["human_found"]:
        if h["weight"] != "routine" and not (h["new_check"] and h["eval_case"]):
            print(f"FOLLOW-UP {h['id']}: a human-found miss needs a new check and an eval case")
    return 0


def cmd_review_checks(a) -> int:
    f = closeout_log_file()
    lines = [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []
    recent = lines[-REVIEW_WINDOW:]
    if len(recent) < REVIEW_WINDOW:
        print(f"{len(recent)} of {REVIEW_WINDOW} close-outs logged: not enough to judge any check (UNKNOWN, keep all)")
        return 0
    fired = {c for x in recent for c in x.get("checks_fired") or []}
    for cid, spec in CHECK_REGISTRY.items():
        if cid in fired:
            print(f"{cid}: fired in the last {REVIEW_WINDOW}")
        else:
            print(f"{cid}: review for removal (no find in the last {REVIEW_WINDOW} close-outs; catches {spec['catches']})")
    return 0


# ---------------------------------------------------------------- render

def esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


def link(l) -> str:
    if not isinstance(l, dict):
        return esc(l)
    return f'<a href="{esc(l.get("url"))}">{esc(l.get("ref") or "")} {esc(l.get("title") or l.get("url"))}</a>'


def fact_counts(facts: dict) -> list[tuple[str, object]]:
    """One set of names and numbers for the gather output and the report."""
    j, g, h = facts.get("jira") or {}, facts.get("github") or {}, facts.get("handoffs") or {}
    dr, br = facts.get("drafts") or {}, facts.get("branches") or {}
    return [("Jira tickets", len(j.get("tickets") or [])), ("GitHub issues open", g.get("open", 0)),
            ("GitHub issues closed", g.get("closed", 0)), ("pending handoffs", len(h.get("pending") or [])),
            ("drafts with no posted record", len(dr.get("no_posted_marker") or [])), ("branches", len(br.get("branches") or [])),
            ("obligations found outside the tree", len(facts.get("obligations") or [])),
            ("twin pairs", len(facts.get("twins") or [])),
            ("security obligations without proof", len(facts.get("security_obligations") or [])),
            ("unratified decisions", len((facts.get("record") or {}).get("unratified_decisions") or [])),
            ("maps closed without a decision", len((facts.get("record") or {}).get("maps_closed_without_decision") or []))]


def fact_sources(facts: dict) -> list[tuple[str, str, str]]:
    out = []
    for k in ("jira", "github", "sweep", "handoffs", "drafts", "branches"):
        v = facts.get(k)
        if isinstance(v, dict):
            out.append((k, str(v.get("status")), str(v.get("reason") or "")))
    mrs = (facts.get("branches") or {}).get("mrs") or {}
    if mrs:
        out.append(("mrs", str(mrs.get("status")), str(mrs.get("reason") or "")))
    return out


CSS = """body{font:15px/1.5 -apple-system,Segoe UI,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}
h1{margin-bottom:.2rem}.muted{color:#666}.unknown{background:#fff4d6;border-left:4px solid #e0a800;padding:.6rem 1rem}
.gate-ok{background:#e5f6e8;border-left:4px solid #2e8b57;padding:.6rem 1rem}.gate-no{background:#fde8e8;border-left:4px solid #c0392b;padding:.6rem 1rem}
.need{border:1px solid #c0392b;border-radius:6px;padding:.6rem 1rem;margin:.6rem 0}.need h3{margin:.1rem 0}
table{border-collapse:collapse;width:100%;margin:.5rem 0 1.5rem}td,th{border-bottom:1px solid #ddd;padding:.35rem .5rem;text-align:left;vertical-align:top}
th{background:#f5f5f5}.b{font-weight:600}section{margin-top:1.5rem}code{background:#f3f3f3;padding:0 .2rem}"""


def item_label(i: dict) -> str:
    return link(i.get("ref")) if i.get("ref") else esc(i.get("title"))


def render_needs_you(items: list[dict]) -> list[str]:
    needs = [i for i in items if needs_decision(i)]
    h = [f"<section id=needs><h2>Needs you ({len(needs)})</h2>"]
    if not needs:
        h.append("<p>No big miss is open. The routine work is in the proposed batch below.</p>")
    for i in needs:
        dec = i.get("decision") or {}
        opts = dec.get("options") or []
        h.append(f"<div class=need><h3>{esc(i.get('id'))}: {item_label(i)}</h3>"
                 f"<p class=muted>Why it is big: {esc(', '.join(big_miss_reasons(i)))}</p><p>{esc(i.get('finding'))}</p>"
                 + (f"<p><b>Decision:</b> {esc(dec.get('question'))}</p>" if dec.get("question")
                    else "<p><b>Decision:</b> not written yet. The close-out is not complete until it is.</p>")
                 + ("<ol>" + "".join(f"<li>{esc(o if not isinstance(o, dict) else o.get('label', '') + ': ' + str(o.get('consequence', '')))}</li>" for o in opts) + "</ol>" if opts else "")
                 + "</div>")
    h.append("</section>")
    return h


def render_coverage(facts: dict, co: dict) -> list[str]:
    src = fact_sources(facts)
    full = [s for s, st, _ in src if st == "OK"]
    gaps = [(s, st, r) for s, st, r in src if st != "OK"]
    disp = {str(u.get("source")): u for u in co.get("unknowns") or [] if isinstance(u, dict)}
    h = ["<section id=coverage><h2>Coverage</h2>",
         f"<p>These sources were searched fully: <b>{esc(', '.join(full) or 'none')}</b>. "
         f"These gaps remain: <b>{esc(', '.join(s for s, _, _ in gaps) or 'none')}</b>. "
         "The claim is coverage of these sources, not completeness.</p>",
         "<ul>" + "".join(f"<li>{esc(lbl)}: {esc(n)}</li>" for lbl, n in fact_counts(facts)) + "</ul>"]
    sec = facts.get("security_obligations") or []
    if sec:
        h.append("<p><b>Security obligations without proof (always investigated, Done included):</b></p><ul>"
                 + "".join(f"<li>{esc(s['ref'])} ({esc(s.get('status'))}): {esc(s.get('reason'))}</li>" for s in sec) + "</ul>")
    if facts.get("unknown"):
        h.append('<div class="unknown"><b>Not checked (UNKNOWN, never PASS):</b><ul>' + "".join(
            f"<li>{esc(u)} <span class=muted>[disposition: "
            f"{esc((disp.get(unknown_key(u)) or {}).get('disposition') or ('not consequential' if (disp.get(unknown_key(u)) or {}).get('consequential') is False else 'none yet'))}]</span></li>"
            for u in facts["unknown"]) + "</ul></div>")
    h.append("</section>")
    return h


def render_batches(co: dict, slug_arg: str) -> list[str]:
    manifest = co.get("manifest") or []
    by_id = {a.get("id"): a for a in manifest}
    batches = plan_batches(manifest)
    h = [f"<section id=batch><h2>Proposed batch ({sum(len(b['items']) for b in batches)} action(s))</h2>"]
    if not batches:
        h.append("<p>No proposed action is waiting for approval.</p>")
    for n, b in enumerate(batches, 1):
        h.append(f"<p><b>Batch {n}</b>, hash <code>{esc(b['hash'])}</code>. Approve: "
                 f"<code>mission closeout approve {esc(slug_arg)} --items {esc(','.join(b['items']))} --hash {esc(b['hash'])} "
                 "--by &lt;name&gt; --link &lt;where you said yes&gt;</code></p>")
        h.append("<table><tr><th>ID</th><th>Target</th><th>Expected now</th><th>Exact action</th><th>Evidence</th><th>Class</th></tr>")
        for i in b["items"]:
            a = by_id[i]
            h.append(f"<tr><td>{esc(i)}</td><td>{link(a.get('target'))}</td><td>{esc(a.get('expected_state'))}</td>"
                     f"<td>{esc(a.get('action'))}</td><td>{' '.join(link(e) for e in a.get('evidence') or [])}</td>"
                     f"<td>{esc(a.get('class', 'routine'))}</td></tr>")
        h.append("</table>")
    h.append("</section>")
    return h


def render_appendix(co: dict, items: list[dict], warn: list[str]) -> list[str]:
    h = ["<section id=appendix><h2>Appendix</h2>"]
    counts = {b: sum(1 for i in items if i.get("bucket") == b) for b in BUCKETS}
    h.append("<table><tr>" + "".join(f"<th>{b}</th>" for b in BUCKETS) + "</tr><tr>"
             + "".join(f"<td class=b>{counts[b]}</td>" for b in BUCKETS) + "</tr></table>")
    state = approval_state(co)
    acts = [a for a in co.get("manifest") or [] if a.get("state") in ("done", "skipped", "unverified", "approved")]
    if acts:
        h.append("<h3>Actions taken, with read-back</h3><table><tr><th>ID</th><th>Target</th><th>Action</th><th>Approval</th>"
                 "<th>Before</th><th>After</th><th>State</th></tr>")
        for a in acts:
            rb = a.get("readback") or {}
            h.append(f"<tr><td>{esc(a.get('id'))}</td><td>{link(a.get('target'))}</td><td>{esc(a.get('action'))}</td>"
                     f"<td>{esc(state.get(a.get('id')))}</td><td>{esc(rb.get('before'))}</td><td>{esc(rb.get('after'))}</td>"
                     f"<td>{esc(a.get('state'))} {esc(a.get('skipped_reason') or '')}</td></tr>")
        h.append("</table>")
    for b in BUCKETS:
        rows = [i for i in items if i.get("bucket") == b]
        if not rows:
            continue
        h.append(f"<h3 id='{b}'>{b} ({len(rows)})</h3><table><tr><th>ID</th><th>Item</th><th>Finding</th>"
                 "<th>Proposed action</th><th>Successor</th><th>State</th></tr>")
        for i in rows:
            ev = " ".join(link(e) for e in i.get("evidence") or [])
            h.append(f"<tr><td>{esc(i.get('id'))}</td><td>{item_label(i)}</td>"
                     f"<td>{esc(i.get('finding'))} {ev}</td><td>{esc(i.get('action'))}</td>"
                     f"<td>{link(i.get('successor')) if i.get('successor') else ''}</td><td>{esc(i.get('state', 'proposed'))}</td></tr>")
        h.append("</table>")
    steps = {s.get("id"): s for s in co.get("checklist") or [] if isinstance(s, dict)}
    h.append("<h3>Checklist</h3><table><tr><th>Step</th><th>Status</th><th>Note</th></tr>")
    for sid, label in CHECKLIST:
        s = steps.get(sid) or {}
        h.append(f"<tr><td>{esc(label)}</td><td class=b>{esc(s.get('status', 'missing'))}</td><td>{esc(s.get('note'))}</td></tr>")
    h.append("</table>")
    guide = co.get("human_guide") or []
    if guide:
        h.append("<h3>Human-only guide</h3><ol>" + "".join(
            f"<li>{esc(g.get('step') if isinstance(g, dict) else g)}"
            + (f" <code>{esc(g.get('command'))}</code>" if isinstance(g, dict) and g.get("command") else "") + "</li>"
            for g in guide) + "</ol>")
    if warn:
        h.append("<h3>Warnings</h3><ul>" + "".join(f"<li>{esc(w)}</li>" for w in warn) + "</ul>")
    h.append("</section>")
    return h


def cmd_render(a) -> int:
    d, m = closeout_dir(a.mission, a.scope)
    co = load_closeout(d) or {}
    facts = json.loads((d / "closeout-facts.json").read_text()) if (d / "closeout-facts.json").exists() else {}
    err, warn = gate(d)
    items = co.get("items") or []
    title = m.get("title") or (co.get("scope") or {}).get("name") or a.scope
    slug_arg = a.mission or f"--scope {a.scope}"
    h = [f"<!doctype html><meta charset=utf-8><title>Close-out: {esc(title)}</title><style>{CSS}</style>",
         f"<h1>Close-out: {esc(title)}</h1>",
         f"<p class=muted>Facts fetched {esc(facts.get('fetched_at', 'never'))}. Report rendered {esc(now_utc())}.</p>",
         f'<div class="{"gate-ok" if not err else "gate-no"}"><b>Close gate: {"OPEN" if not err else "CLOSED"}.</b> '
         + (f"{len(err)} open condition(s), listed under Warnings and in <code>mission closeout gate</code>." if err
            else "The mission may close.") + "</div>"]
    h += render_needs_you(items)
    h += render_coverage(facts, co)
    h += render_batches(co, slug_arg)
    h += render_appendix(co, items, [f"gate: {e}" for e in err] + warn)
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
    for name in ("gather", "render", "gate", "approve", "record", "log", "coverage"):
        p = sub.add_parser(name)
        p.add_argument("mission", nargs="?")
        p.add_argument("--scope")
        if name == "gather":
            p.add_argument("--seed-jira")
            p.add_argument("--seed-gh")
            p.add_argument("--aliases")
            p.add_argument("--repo", action="append")
            p.add_argument("--depth", type=int, default=4)
            p.add_argument("--since", help="start date for the GitHub and git sweep when there is no mission record")
            p.add_argument("--exclude", help="comma-separated terms: sweep hits that match are listed as excluded")
            p.add_argument("--sweep-cap", type=int, default=SWEEP_CAP)
            p.add_argument("--offline", action="store_true")
        if name == "render":
            p.add_argument("--open", action="store_true")
        if name == "approve":
            p.add_argument("--items", required=True, help="comma-separated manifest ids ('' approves an empty manifest)")
            p.add_argument("--by", required=True)
            p.add_argument("--link")
            p.add_argument("--link-title")
            p.add_argument("--hash", help="the batch hash the human approved; refused if the batch changed")
        if name == "record":
            p.add_argument("--action", required=True)
            p.add_argument("--before", default="")
            p.add_argument("--after", default="")
            p.add_argument("--skip", help="reason: the action is skipped, not run")
    sub.add_parser("review-checks")
    a = ap.parse_args()
    return {"gather": cmd_gather, "render": cmd_render, "gate": cmd_gate, "approve": cmd_approve, "record": cmd_record,
            "log": cmd_log, "review-checks": cmd_review_checks, "coverage": cmd_coverage}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
