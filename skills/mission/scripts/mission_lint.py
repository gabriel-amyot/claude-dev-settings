"""Validate a mission.yaml against mission/v1. Exit 1 on any error.

Usage: mission_lint.py <slug|path> [--quiet]
"""
from __future__ import annotations

import datetime as dt
import re
import sys

from mission_lib import load, mission_dir

STATUS = {"active", "parked", "done", "abandoned"}
DEC_STATE = {"proposed", "ratified", "superseded", "reversed"}
ASK_STATE = {"open", "answered", "done", "deferred", "superseded", "blocked"}
MEMBER_ROLE = {"current", "done", "superseded", "parked"}
LINK_KIND = {"jira", "gh", "mr", "file", "folder", "session", "url", "slack"}
PARK_BUCKET = {"horizon", "tomorrow", "blocked_on_person"}
JOURNEY_KIND = {"session", "night_run", "commit_only", "gap"}
MSG_STATE = {"draft", "approved", "sent", "answered"}
PREFIX = {"deliverables": "D-", "decisions": "DEC-", "disproven": "X-", "needs_you": "N-",
          "asks": "A-", "parked": "P-", "messages": "M-", "artifacts": "ART-", "journey": "J-",
          "changes": "C-"}
RELITIGATE = re.compile(r"re-?litigat", re.I)


def _date(v):
    """Return a naive UTC datetime, or None."""
    if v in (None, ""):
        return None
    if isinstance(v, dt.datetime):
        d = v
    elif isinstance(v, dt.date):
        d = dt.datetime.combine(v, dt.time())
    else:
        try:
            d = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except ValueError:
            return None
    return d.astimezone(dt.timezone.utc).replace(tzinfo=None) if d.tzinfo else d


def lint(m: dict) -> tuple[list[str], list[str]]:
    err, warn = [], []

    def link_ok(link, where):
        if not isinstance(link, dict):
            err.append(f"{where}: link must be a mapping with kind, url, title")
            return
        for k in ("kind", "url", "title"):
            if not link.get(k):
                err.append(f"{where}: link missing '{k}'")
        if link.get("kind") and link["kind"] not in LINK_KIND:
            err.append(f"{where}: link kind '{link['kind']}' not in {sorted(LINK_KIND)}")

    for k in ("schema", "slug", "title", "status", "created", "destination", "root_issue"):
        if m.get(k) in (None, "", {}):
            err.append(f"missing required field '{k}'")
    if m.get("schema") not in (None, "mission/v1"):
        err.append(f"schema must be mission/v1, got {m.get('schema')}")
    if m.get("status") and m["status"] not in STATUS:
        err.append(f"status '{m['status']}' not in {sorted(STATUS)}")
    ri = m.get("root_issue") or {}
    if isinstance(ri, dict) and ri.get("number") is None:
        warn.append("root_issue.number is empty: create the GitHub root issue (mission_new.py does it)")

    ids = {}
    for section, prefix in PREFIX.items():
        for i, item in enumerate(m.get(section) or []):
            where = f"{section}[{i}]"
            iid = (item or {}).get("id")
            if not iid:
                err.append(f"{where}: missing id")
                continue
            if not str(iid).startswith(prefix):
                err.append(f"{where}: id '{iid}' must start with '{prefix}'")
            if iid in ids:
                err.append(f"{where}: duplicate id '{iid}' (also in {ids[iid]})")
            ids[iid] = section
            for j, link in enumerate(item.get("links") or []):
                link_ok(link, f"{iid}.links[{j}]")

    for i, mem in enumerate(m.get("members") or []):
        where = f"members[{i}]"
        for k in ("kind", "ref", "title", "role"):
            if not mem.get(k):
                err.append(f"{where}: missing '{k}'")
        if mem.get("role") and mem["role"] not in MEMBER_ROLE:
            err.append(f"{where}: role '{mem['role']}' not in {sorted(MEMBER_ROLE)}")
        if mem.get("kind") in ("jira", "gh", "mr") and not mem.get("url"):
            err.append(f"{where} ({mem.get('ref')}): {mem['kind']} member needs a url")

    for d in m.get("decisions") or []:
        did = d.get("id")
        if d.get("state") not in DEC_STATE:
            err.append(f"{did}: state '{d.get('state')}' not in {sorted(DEC_STATE)}")
        if not d.get("statement"):
            err.append(f"{did}: missing statement")
        rb = d.get("ratified_by") or {}
        if d.get("state") == "ratified":
            if not rb.get("who") or not rb.get("link"):
                err.append(f"{did}: ratified needs ratified_by.who and ratified_by.link (a place a human said it)")
            else:
                link_ok(rb["link"], f"{did}.ratified_by.link")
        if d.get("state") != "ratified" and RELITIGATE.search(str(d.get("statement", ""))):
            err.append(f"{did}: 're-litigate' wording is only allowed on a ratified decision")
        sup = d.get("supersedes")
        if sup and ids.get(sup) != "decisions":
            err.append(f"{did}: supersedes '{sup}' is not an existing decision id")

    superseded = {d.get("supersedes") for d in m.get("decisions") or [] if d.get("supersedes")}
    for d in m.get("decisions") or []:
        if d.get("id") in superseded and d.get("state") not in ("superseded", "reversed"):
            err.append(f"{d['id']}: another decision supersedes it, so its state must be superseded or reversed")

    for x in m.get("disproven") or []:
        for k in ("claim", "evidence", "signature"):
            if not x.get(k):
                err.append(f"{x.get('id')}: missing '{k}'")
        if x.get("evidence"):
            link_ok(x["evidence"], f"{x.get('id')}.evidence")

    for n in m.get("needs_you") or []:
        nid = n.get("id")
        if not n.get("question"):
            err.append(f"{nid}: missing question")
        if not n.get("options") and not n.get("free"):
            err.append(f"{nid}: needs options, or free: true for an open answer")
        for o in n.get("options") or []:
            if not isinstance(o, dict) or not o.get("label"):
                err.append(f"{nid}: each option needs a label")
        since = _date(n.get("since"))
        if since and (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - since).days > 14:
            warn.append(f"{nid}: waiting on Gabriel for {(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - since).days} days")

    for a in m.get("asks") or []:
        if a.get("state") not in ASK_STATE:
            err.append(f"{a.get('id')}: state '{a.get('state')}' not in {sorted(ASK_STATE)}")
        if a.get("state") in ("answered", "done") and not a.get("answer"):
            err.append(f"{a.get('id')}: state {a['state']} needs an answer")
        if not a.get("text"):
            err.append(f"{a.get('id')}: missing text")

    for p in m.get("parked") or []:
        if p.get("bucket") not in PARK_BUCKET:
            err.append(f"{p.get('id')}: bucket '{p.get('bucket')}' not in {sorted(PARK_BUCKET)}")
        rc = _date(p.get("recheck"))
        if p.get("bucket") == "tomorrow" and rc and rc < dt.datetime.now(dt.timezone.utc).replace(tzinfo=None):
            warn.append(f"{p.get('id')}: recheck date {p.get('recheck')} has passed")

    prev = None
    for j in m.get("journey") or []:
        if j.get("kind") not in JOURNEY_KIND:
            err.append(f"{j.get('id')}: kind '{j.get('kind')}' not in {sorted(JOURNEY_KIND)}")
        s = _date(j.get("start"))
        if s and prev and s < prev:
            err.append(f"{j.get('id')}: journey entries must be in time order")
        prev = s or prev
        for dref in j.get("decisions") or []:
            if ids.get(dref) != "decisions":
                err.append(f"{j.get('id')}: decision '{dref}' does not exist")

    for msg in m.get("messages") or []:
        if msg.get("state") not in MSG_STATE:
            err.append(f"{msg.get('id')}: state '{msg.get('state')}' not in {sorted(MSG_STATE)}")

    for section in ("needs_you", "asks", "decisions", "parked"):
        for item in m.get(section) or []:
            for k in ("question", "text", "statement", "title"):
                if len(str(item.get(k, ""))) > 400:
                    warn.append(f"{item.get('id')}.{k}: over 400 characters, write the high level and link the detail")
    dead = {d.get("id") for d in m.get("decisions") or [] if d.get("state") in ("superseded", "reversed")}
    live_texts = [(a.get("id"), a.get("answer")) for a in m.get("asks") or []] + \
                 [(n.get("id"), f"{n.get('question', '')} {n.get('why', '')}") for n in m.get("needs_you") or []] + \
                 [("scope_constraints", " ".join(map(str, m.get("scope_constraints") or []))), ("verdict", m.get("verdict"))]
    for where, text in live_texts:
        for ref in re.findall(r"DEC-\d+", str(text or "")):
            if ref in dead:
                warn.append(f"{where}: cites {ref}, which is superseded or reversed; point it at the decision that replaced it")
    asked = " ".join(f"{n.get('question', '')} {n.get('why', '')}" for n in m.get("needs_you") or [])
    for d in m.get("decisions") or []:
        if d.get("state") == "proposed" and d.get("id") not in asked:
            warn.append(f"{d.get('id')}: proposed but no needs_you item asks Gabriel to ratify it")
    return err, warn


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    m = load(mission_dir(sys.argv[1]))
    err, warn = lint(m)
    quiet = "--quiet" in sys.argv
    for w in warn:
        print(f"WARN  {w}")
    for e in err:
        print(f"ERROR {e}")
    if not err and not quiet:
        print(f"OK    {m.get('slug')}: {len(warn)} warning(s)")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
