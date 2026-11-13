"""Threads: every intent, rabbit hole, open door, handoff, nugget, ask and finding of a mission, captured when it opens.

Usage:
  mission thread add <slug> --kind KIND --title "..." [--parent T-n] [--session S] [--event EVENT] [--state STATE]
                     [--ref "URL|title" ...] [--lives-in "URL|title"] [--finding "..."] [--reason R ...]
                     [--home "URL|title" --owner NAME [--accepted-by NAME --accepted-link URL]]
                     [--question "..." --option "label|consequence" ... --recommend "label" --verb "Decide"
                      --command "label|cmd" ... --after "..."] [--needs-you N-n] [--ask A-n] [--child "title" ...]
  mission thread set <slug> T-n [same fields] [--state STATE] [--clear-drift] [--answer "..." --by NAME --link URL]
                     [--json '{"field": value}'] [--note "..."] [--session S]
  mission thread resolve <slug> T-n --how evidence|superseded|ticket|dropped [--link "URL|title"] [--by NAME] [--note "..."]
  mission thread list <slug> [--state open,needs_you] [--session S] [--json]
  mission threads import <slug> [--session S] [--match N-1=CO-1,...] [--no-match N-4,...] [--dry-run]

Every write takes an flock on mission.yaml and replaces only the threads: block, so the rest of the
record keeps its layout. Every write appends one history entry. A thread ID (T-n) is never renumbered.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys

from mission_lib import MISSIONS_DIR, closeout_home, load, locked, mission_dir, now_utc, set_section
from mission_links import classify, link_tokens, tokens

KINDS = ["big_intent", "intent", "rabbit_hole", "open_door", "handoff", "nugget", "ask", "finding"]
STATES = ["open", "needs_you", "ready", "parked", "resolved", "dropped"]
REASONS = ["live_assurance_gap", "uncovered_obligation", "false_record", "control_failure", "your_call", "approval"]
BIG_REASONS = {"live_assurance_gap", "uncovered_obligation", "false_record", "control_failure"}
CONTROLS = {"security", "access", "safety", "contract"}
HOW = {"evidence", "superseded", "ticket", "dropped", "answered"}
EVIDENCE_STATES = {"present", "missing", "UNKNOWN"}
TERMINAL = {"resolved", "dropped"}
LIVE_EVENTS_HINT = ["mission_start", "session_init", "rabbit_hole_opened", "open_door_noticed", "handoff_written", "nugget_captured",
                    "ask_recorded", "needs_you_added", "parked", "ticket_created", "session_check", "closeout_sweep", "imported"]
BIG_MISS_MAP = {"live-assurance-gap": "live_assurance_gap", "valid-obligation-uncovered": "uncovered_obligation",
                "consequential-false-record": "false_record", "control-failure": "control_failure"}
NOT_A_NAME = {"", "agent", "claude", "assistant", "ai", "bot", "tbd", "unknown", "none", "n/a", "?", "someone"}
TITLE_MAX = 70


# ---------------------------------------------------------------- small helpers

def named(who) -> bool:
    return str(who or "").strip().lower() not in NOT_A_NAME


def has_url(x) -> bool:
    return isinstance(x, dict) and bool(x.get("url"))


def accepted(home) -> bool:
    """A home accepted the thread: a named person and a link to where they said it, and the home does not exclude it."""
    if not isinstance(home, dict) or home.get("excludes"):
        return False
    acc = home.get("accepted")
    return isinstance(acc, dict) and named(acc.get("by")) and has_url(acc.get("link"))


def view_state(t: dict) -> str:
    """The state the report shows: a parked thread whose home has not accepted it is parked_unaccepted."""
    s = t.get("state")
    return "parked_unaccepted" if s == "parked" and not accepted(t.get("home")) else s


def closable(t: dict) -> bool:
    return t.get("state") in TERMINAL or (t.get("state") == "parked" and accepted(t.get("home")))


def short_title(text, limit: int = TITLE_MAX) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    first = re.split(r"(?<=[.?!])\s", s, maxsplit=1)[0].rstrip(".")
    s = first if first else s
    if len(s) <= limit:
        return s
    cut = s[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def link_arg(v: str | None, default_title: str | None = None) -> dict | None:
    """'URL|title' (or a bare URL) -> a typed, titled link."""
    if not v:
        return None
    url, _, title = str(v).partition("|")
    c = classify({"kind": "url", "url": url.strip(), "title": title.strip() or default_title or url.strip()})
    if c.get("kind") == "url" and not re.match(r"^(https?|file)://", c["url"]):
        c["kind"] = "file"
    return c


def _date_str(v) -> str:
    if isinstance(v, dt.datetime):
        return v.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if v.tzinfo else v.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(v, dt.date):
        return v.strftime("%Y-%m-%dT00:00:00Z")
    s = str(v or "")
    return s if "T" in s or not s else s + "T00:00:00Z"


def next_id(threads: list[dict]) -> str:
    n = max([int(m.group(1)) for t in threads if (m := re.fullmatch(r"T-(\d+)", str(t.get("id"))))] + [0])
    return f"T-{n + 1}"


def history(t: dict, at: str, session: str | None, event: str, note: str | None = None) -> None:
    t.setdefault("history", [])
    t["history"].append({k: v for k, v in {"at": at, "session": session, "event": event, "note": note}.items() if v})


# ---------------------------------------------------------------- lint and gate

def _link_errors(link, where: str, err: list[str], warn: list[str]) -> None:
    if not isinstance(link, dict):
        err.append(f"{where}: link must be a mapping with kind, url, title")
        return
    if not link.get("url"):
        err.append(f"{where}: link missing 'url'")
    if not link.get("title"):
        warn.append(f"{where}: link has no title")


def lint_threads(m: dict) -> tuple[list[str], list[str]]:
    """Errors and warnings for the threads section. A record without threads passes."""
    err, warn = [], []
    threads = m.get("threads")
    if threads is None:
        return err, warn
    if not isinstance(threads, list):
        return ["threads must be a list"], warn
    ids = {t.get("id") for t in threads if isinstance(t, dict)}
    needs = {n.get("id") for n in m.get("needs_you") or []}
    for i, t in enumerate(threads):
        tid = (t or {}).get("id") or f"threads[{i}]"
        if not isinstance(t, dict):
            err.append(f"threads[{i}]: must be a mapping")
            continue
        if not re.fullmatch(r"T-\d+", str(t.get("id") or "")):
            err.append(f"{tid}: id must be T-<number>")
        if not str(t.get("title") or "").strip():
            err.append(f"{tid}: missing title")
        elif len(str(t["title"])) > TITLE_MAX:
            warn.append(f"{tid}: title is {len(str(t['title']))} characters; keep it at {TITLE_MAX} or less")
        if t.get("kind") not in KINDS:
            err.append(f"{tid}: kind '{t.get('kind')}' not in {KINDS}")
        if t.get("state") not in STATES:
            err.append(f"{tid}: state '{t.get('state')}' not in {STATES}")
        o = t.get("origin") or {}
        if not (isinstance(o, dict) and o.get("at") and o.get("event")):
            err.append(f"{tid}: origin needs at and event (when and how the thread was captured)")
        if t.get("parent") and t["parent"] not in ids:
            err.append(f"{tid}: parent '{t['parent']}' is not a thread id")
        if t.get("parent") == t.get("id"):
            err.append(f"{tid}: a thread cannot be its own parent")
        bad = [r for r in t.get("reasons") or [] if r not in REASONS]
        if bad:
            err.append(f"{tid}: reasons {bad} not in {REASONS}")
        if t.get("control") and t["control"] not in CONTROLS:
            err.append(f"{tid}: control '{t['control']}' not in {sorted(CONTROLS)}")
        if "live" in t and t["live"] not in (True, False, "UNKNOWN"):
            err.append(f"{tid}: live must be true, false or UNKNOWN")
        if t.get("evidence_state") and t["evidence_state"] not in EVIDENCE_STATES:
            err.append(f"{tid}: evidence_state '{t['evidence_state']}' not in {sorted(EVIDENCE_STATES)}")
        for j, ln in enumerate(t.get("refs") or []):
            _link_errors(ln, f"{tid}.refs[{j}]", err, warn)
        for j, ln in enumerate(t.get("evidence") or []):
            _link_errors(ln, f"{tid}.evidence[{j}]", err, warn)
        if t.get("lives_in"):
            _link_errors(t["lives_in"], f"{tid}.lives_in", err, warn)
        st = t.get("state")
        dn = t.get("do_now") or {}
        if st == "needs_you":
            if not str(dn.get("question") or "").strip():
                err.append(f"{tid}: needs_you needs do_now.question (what Gabriel must decide or do)")
            if not dn.get("recommendation"):
                warn.append(f"{tid}: needs_you without a recommendation (do_now.recommendation)")
        for o2 in dn.get("options") or []:
            if not isinstance(o2, dict) or not o2.get("label"):
                err.append(f"{tid}: each do_now option needs a label")
        if dn.get("recommendation") and dn.get("options") and dn["recommendation"] not in [o2.get("label") for o2 in dn["options"] if isinstance(o2, dict)]:
            warn.append(f"{tid}: recommendation is not one of the option labels")
        home = t.get("home")
        if st == "parked":
            if not isinstance(home, dict) or not has_url(home.get("link")):
                err.append(f"{tid}: parked needs home.link (where the work lives now)")
            elif not accepted(home):
                warn.append(f"{tid}: parked, but the home has not accepted it (home.accepted: by + link); it shows under Needs you")
        if isinstance(home, dict) and home.get("accepted") and not accepted(home) and not home.get("excludes"):
            err.append(f"{tid}: home.accepted needs a named person (by) and a link")
        res = t.get("resolution") or {}
        if st in TERMINAL:
            if res.get("how") not in HOW:
                err.append(f"{tid}: {st} needs resolution.how in {sorted(HOW)}")
            if not res.get("at"):
                err.append(f"{tid}: {st} needs resolution.at")
            if st == "dropped" and not (named(res.get("by")) and str(res.get("note") or "").strip()):
                err.append(f"{tid}: dropped needs resolution.by (a named person) and resolution.note (the reason)")
            if st == "resolved" and not (has_url(res.get("link")) or str(res.get("note") or "").strip()):
                err.append(f"{tid}: resolved needs resolution.link (evidence) or resolution.note")
        if t.get("drift") and not (isinstance(t["drift"], dict) and t["drift"].get("text")):
            err.append(f"{tid}: drift needs text (what changed)")
        if t.get("needs_you_id") and t["needs_you_id"] not in needs and st == "needs_you":
            warn.append(f"{tid}: needs_you_id {t['needs_you_id']} is not in needs_you")
    return err, warn


def gate_errors(m: dict) -> tuple[list[str], list[str]]:
    """The /mission close condition on threads: each one resolved, dropped, or parked with an accepted home, and none drifted."""
    threads = m.get("threads")
    if threads is None:
        return [], ["no threads in the record: run mission threads import, so the close checks every thread"]
    err = []
    for t in threads:
        tid = t.get("id")
        if t.get("drift"):
            err.append(f"{tid}: changed since it was judged ({(t['drift'] or {}).get('text', '')[:120]}). Re-judge it (thread set --clear-drift)")
        if closable(t):
            continue
        vs = view_state(t)
        why = {"parked_unaccepted": "parked, but its home has not accepted it", "open": "open, not judged yet",
               "needs_you": "waiting on a decision or an action by Gabriel", "ready": "an approved action is not done yet"}.get(vs, vs)
        err.append(f"{tid} ({vs}): {why}. Resolve it, drop it with a reason, or park it with an accepted home")
    return err, []


# ---------------------------------------------------------------- import (seed threads from an existing record)

def _co_tokens(it: dict) -> tuple[set[str], set[str]]:
    primary = link_tokens(it.get("ref"))
    text = " ".join(str(x or "") for x in (it.get("finding"), it.get("action"), (it.get("decision") or {}).get("question"), it.get("title")))
    allt = tokens(text) | primary | link_tokens(it.get("successor"))
    for ev in it.get("evidence") or []:
        allt |= link_tokens(ev)
    return primary, allt


def _src_tokens(text: str, links) -> set[str]:
    out = tokens(text)
    for ln in links or []:
        out |= link_tokens(ln)
    return out


def match_sources(sources: dict[str, set[str]], pool: dict[str, tuple[set[str], set[str]]],
                  forced: dict[str, str], blocked: set[str]) -> dict[str, str]:
    """Greedy one-to-one match of source records to close-out items by shared references.
    The item's own ref counts double. A pair needs the item's ref, or two shared references."""
    out = {k: v for k, v in forced.items() if k in sources}
    used = set(out.values())
    pairs = []
    for sid, st in sources.items():
        if sid in out or sid in blocked:
            continue
        for cid, (prim, allt) in pool.items():
            shared, ref_hit = st & allt, st & prim
            score = len(shared) + 2 * len(ref_hit)
            if ref_hit or len(shared) >= 2:
                pairs.append((score, sid, cid))
    for score, sid, cid in sorted(pairs, key=lambda x: (-x[0], x[1], x[2])):
        if sid in out or cid in used:
            continue
        rivals = [p for p in pairs if p[1] == sid and p[0] == score and p[2] not in used]
        if len(rivals) > 1:
            continue
        out[sid], _ = cid, used.add(cid)
    return out


def _options(opts) -> list[dict]:
    out = []
    for o in opts or []:
        if isinstance(o, dict) and o.get("label"):
            out.append({"label": str(o["label"]), "consequence": str(o.get("consequence") or "")})
        elif isinstance(o, str):
            label, _, cons = o.partition(":")
            out.append({"label": label.strip(), "consequence": cons.strip()})
    return out


def _keep_open(it: dict) -> bool:
    return bool(it.get("keep_open")) or bool(re.match(r"^\s*(keep open|none)\b", str(it.get("action") or ""), re.I))


def closeout_state(it: dict, big: list[str]) -> str:
    """Section 12 of the UX spec: close-out bucket -> thread state."""
    b, s = it.get("bucket"), it.get("successor") or {}
    if it.get("state") == "done":
        return "resolved"
    if it.get("state") == "dropped":
        return "dropped"
    if big:
        return "needs_you"
    if b == "HUMAN-ONLY":
        return "parked" if _keep_open(it) and (named(it.get("owner")) or named(s.get("owner"))) else "needs_you"
    if b == "KEEP":
        return "parked" if accepted(s) else "needs_you"
    if b == "ORPHAN":
        return "needs_you"
    return "ready"


def _home_from(it: dict) -> dict | None:
    s = it.get("successor")
    if isinstance(s, dict) and s.get("url"):
        home = {"link": classify({k: s[k] for k in ("kind", "ref", "url", "title") if s.get(k)}), "owner": s.get("owner"),
                "accepted": s.get("accepted"), "excludes": bool(s.get("excludes"))}
        return {k: v for k, v in home.items() if v not in (None, False) or k == "accepted"}
    if it.get("bucket") == "HUMAN-ONLY" and _keep_open(it) and named(it.get("owner")) and has_url(it.get("ref")):
        ref = classify(it["ref"])
        return {"link": ref, "owner": it["owner"],
                "accepted": {"by": it["owner"], "link": ref, "basis": "close-out owner: kept open as the record"}}
    return None


def thread_from_closeout(it: dict, co: dict, actions_by_item: dict, guide: list, at: str, session: str | None, event: str) -> dict:
    from mission_closeout import CLOSE_KINDS, PER_ITEM_CLASSES, big_miss_reasons
    big = [BIG_MISS_MAP[r] for r in big_miss_reasons(it) if r in BIG_MISS_MAP]
    state = closeout_state(it, big)
    acts = actions_by_item.get(it.get("id"), [])
    reasons = list(big)
    if state == "needs_you" and not reasons:
        reasons.append("your_call")
    if any(a.get("class", "routine") in PER_ITEM_CLASSES for a in acts):
        reasons.append("approval")
    ref = classify(it.get("ref")) if has_url(it.get("ref")) else None
    dec = it.get("decision") or {}
    title_src = it.get("title") or (dec.get("question") if state == "needs_you" else None) or (
        it.get("action") if not re.match(r"^\s*none\b", str(it.get("action") or ""), re.I) else None) or it.get("finding")
    t = {"title": short_title(title_src), "kind": "finding",
         "origin": {"at": _date_str(co.get("judged_at") or at), "session": session, "event": event, "source": f"closeout:{it.get('id')}"},
         "state": state, "refs": [ref] if ref else [], "lives_in": ref if ref and ref.get("kind") in ("gh", "jira", "mr") else None,
         "finding": str(it.get("finding") or "").strip(), "reasons": reasons}
    if not ref and isinstance(it.get("ref"), dict) and it["ref"].get("ref"):
        t["about"] = str(it["ref"]["ref"])
    for k in ("control", "evidence_state"):
        if it.get(k) is not None:
            t[k] = it[k]
    if "live" in it and it["live"] is not None:
        t["live"] = it["live"]
    t["evidence"] = [classify(e) for e in it.get("evidence") or [] if has_url(e)]
    home = _home_from(it)
    if home:
        t["home"] = home
    if state == "needs_you":
        verb = "Pick a home" if "uncovered_obligation" in reasons and it.get("bucket") in ("ORPHAN", "KEEP") else (
            f"Approve {len(acts)} edit{'s' if len(acts) != 1 else ''}" if "approval" in reasons and not dec.get("options") else
            "Decide" if dec.get("options") else "Act")
        t["do_now"] = {"actor": "Gabriel", "verb": verb, "question": str(dec.get("question") or it.get("action") or it.get("finding") or ""),
                       "options": _options(dec.get("options")), "recommendation": dec.get("recommendation"),
                       "commands": [], "after_answer": str(it.get("action") or ""), "answer": dec.get("answer")}
    cmds = []
    rt = link_tokens(it.get("ref"))
    for g in guide or []:
        if not isinstance(g, dict) or not g.get("command"):
            continue
        step = str(g.get("step") or "")
        if re.search(rf"\b{re.escape(str(it.get('id')))}\b", step) or (rt & tokens(step)):
            cmds.append({"label": step, "cmd": str(g["command"])})
    if cmds:
        t.setdefault("do_now", {"actor": "Gabriel", "verb": "Run 1 step", "question": cmds[0]["label"], "options": [],
                                "recommendation": None, "commands": [], "after_answer": str(it.get("action") or "")})
        t["do_now"]["commands"] = cmds
    cls = sorted({a.get("class", "routine") for a in acts}, key=lambda c: c == "routine")
    t["closeout"] = {"bucket": it.get("bucket"), "co_id": it.get("id"), "judged_at": _date_str(co.get("judged_at") or at),
                     "found_by": it.get("found_by"), "actions": [a.get("id") for a in acts], "class": cls[0] if cls else None,
                     "affects": it.get("affects") or None, "decision": dec or None, "action": it.get("action")}
    t["closeout"] = {k: v for k, v in t["closeout"].items() if v not in (None, [], "")}
    if state == "resolved":
        ev = t["evidence"][0] if t["evidence"] else None
        t["resolution"] = {"at": _date_str(co.get("judged_at") or at), "by": it.get("owner") or "close-out", "how": "evidence",
                           "link": ev, "note": str(it.get("action") or "")}
    if any(a.get("kind") in CLOSE_KINDS for a in acts) and state == "ready":
        t["closeout"]["closes"] = True
    return {k: v for k, v in t.items() if v not in (None, [], "")}


def batch_threads(co: dict, at: str, session: str | None, event: str) -> list[dict]:
    from mission_closeout import PER_ITEM_CLASSES, plan_batches
    by_id = {a.get("id"): a for a in co.get("manifest") or []}
    out = []
    for b in plan_batches(co.get("manifest") or []):
        if len(b["items"]) == 1 and by_id[b["items"][0]].get("class", "routine") in PER_ITEM_CLASSES:
            continue
        n = len(b["items"])
        out.append({"title": f"Approve {n} routine close-out action{'s' if n != 1 else ''} in one batch", "kind": "finding",
                    "origin": {"at": _date_str(co.get("judged_at") or at), "session": session, "event": event, "source": f"batch:{b['hash']}"},
                    "state": "needs_you", "reasons": ["approval"],
                    "finding": f"{n} small actions are ready: closing comments, closes with the fixing commit, moves and records. "
                               "Each one has evidence. The agent runs them only after your approval, then reads each target back.",
                    "do_now": {"actor": "Gabriel", "verb": "Approve batch", "question": "Read the list. If it is right, approve it by its hash.",
                               "options": [{"label": "Approve the batch", "consequence": f"The agent runs the {n} actions and reads each target back"},
                                           {"label": "Review item by item", "consequence": "Slower: each action is approved alone"}],
                               "recommendation": None, "commands": [], "after_answer": "The agent records each read-back and re-runs the gate."},
                    "closeout": {"batch": True, "actions": b["items"], "hash_at_import": b["hash"]}})
    return out


def import_threads(m: dict, co: dict | None, session: str | None, forced: dict[str, str] | None = None,
                   blocked: set[str] | None = None, at: str | None = None) -> tuple[list[dict], list[str]]:
    """Seed threads from the record (needs_you, asks, parked, journey findings and blockers, current members) and the
    close-out items. Each new thread has origin.event imported: imported is not live-captured. Idempotent by source key."""
    at = at or now_utc()
    forced, blocked = forced or {}, blocked or set()
    threads = [dict(t) for t in m.get("threads") or []]
    known = {k for t in threads for k in [(t.get("origin") or {}).get("source"), *(t.get("imported_from") or [])] if k}
    log: list[str] = []
    new: list[dict] = []

    def add(t: dict, sources: list[str]) -> dict:
        t["imported_from"] = sources
        history(t, at, session, "imported", "seeded from " + ", ".join(sources))
        new.append(t)
        known.update(sources)
        return t

    root = next((t for t in threads if t.get("kind") == "big_intent" and not t.get("parent")), None)
    if root is None and "mission:destination" not in known:
        root = add({"title": short_title(m.get("title") or m.get("slug")), "kind": "big_intent",
                    "origin": {"at": _date_str(m.get("created") or at), "session": session, "event": "imported", "source": "mission:destination"},
                    "state": "open", "finding": str(m.get("destination") or "").strip()}, ["mission:destination"])
    root_id = root.get("id") if root and root.get("id") else None

    items = (co or {}).get("items") or []
    acts: dict[str, list] = {}
    for a in (co or {}).get("manifest") or []:
        acts.setdefault(a.get("item"), []).append(a)
    guide = (co or {}).get("human_guide") or []
    pool = {it["id"]: _co_tokens(it) for it in items if it.get("id")}
    batches = batch_threads(co or {}, at, session, "imported") if co else []
    by_co: dict[str, dict] = {}
    for it in items:
        key = f"closeout:{it.get('id')}"
        if key in known:
            continue
        by_co[it["id"]] = add(thread_from_closeout(it, co, acts, guide, at, session, "imported"), [key])
    for b in batches:
        if b["origin"]["source"] not in known:
            by_co[b["origin"]["source"]] = add(b, [b["origin"]["source"]])

    needs = {n["id"]: n for n in m.get("needs_you") or [] if n.get("id") and f"needs_you:{n['id']}" not in known}
    n_src = {nid: _src_tokens(f"{n.get('question', '')} {n.get('why', '')}", n.get("links")) for nid, n in needs.items()}
    bpool = {k: (set(), set()) for k in by_co if k.startswith("batch:")}
    n_pool = {**{k: v for k, v in pool.items() if k in by_co}, **bpool}
    for nid, n in needs.items():
        txt = f"{n.get('question', '')} {n.get('why', '')}"
        for k in bpool:
            if k.split(":")[1][:8] in txt:
                forced.setdefault(nid, k)
    pairs = match_sources(n_src, n_pool, {k: v for k, v in forced.items() if k.startswith("N-")}, blocked)
    for nid, n in needs.items():
        dn = {"actor": "Gabriel", "verb": "Decide" if n.get("options") else "Answer", "question": str(n.get("question") or ""),
              "options": _options(n.get("options")), "recommendation": n.get("recommendation"),
              "commands": [], "after_answer": str(n.get("after_answer") or ""), "answer": None}
        target = by_co.get(pairs.get(nid))
        if target is not None:
            log.append(f"{nid} merged into close-out {pairs[nid]}")
            target["needs_you_id"] = nid
            target["imported_from"].append(f"needs_you:{nid}")
            known.add(f"needs_you:{nid}")
            old = target.get("do_now") or {}
            if old.get("question") and old.get("question") != dn["question"]:
                target.setdefault("closeout", {})["decision"] = target.get("closeout", {}).get("decision") or {
                    "question": old.get("question"), "options": old.get("options")}
            dn["commands"] = old.get("commands") or []
            dn["verb"] = old.get("verb") or dn["verb"]
            target["do_now"] = dn
            target["state"] = "needs_you"
            if not target.get("reasons"):
                target["reasons"] = ["your_call"]
            if len(str(n.get("question") or "")) <= TITLE_MAX and not str(target.get("closeout", {}).get("co_id", "")).startswith("batch"):
                target["title"] = str(n["question"]).rstrip(".")
            continue
        refs = [classify(ln) for ln in n.get("links") or [] if has_url(ln)]
        add({"title": short_title(n.get("question")), "kind": "finding",
             "origin": {"at": _date_str(n.get("since") or at), "session": session, "event": "imported", "source": f"needs_you:{nid}"},
             "state": "needs_you", "refs": refs, "finding": str(n.get("why") or "").strip(), "reasons": ["your_call"],
             "do_now": dn, "needs_you_id": nid}, [f"needs_you:{nid}"])

    parked = {p["id"]: p for p in m.get("parked") or [] if p.get("id") and f"parked:{p['id']}" not in known}
    p_src = {pid: _src_tokens(str(p.get("title") or ""), p.get("links")) for pid, p in parked.items()}
    ppairs = match_sources(p_src, {k: v for k, v in pool.items() if k in by_co}, {k: v for k, v in forced.items() if k.startswith("P-")}, blocked)
    for pid, p in parked.items():
        target = by_co.get(ppairs.get(pid))
        if target is not None:
            log.append(f"{pid} merged into close-out {ppairs[pid]}")
            target["imported_from"].append(f"parked:{pid}")
            target["parked_id"] = pid
            known.add(f"parked:{pid}")
            continue
        links = [classify(ln) for ln in p.get("links") or [] if has_url(ln)]
        add({"title": short_title(p.get("title")), "kind": "open_door",
             "origin": {"at": _date_str(p.get("since") or at), "session": session, "event": "imported", "source": f"parked:{pid}"},
             "state": "parked", "refs": links, "finding": str(p.get("reentry") or "").strip(),
             "home": {"link": links[0], "owner": p.get("owner"), "accepted": None} if links else None, "parked_id": pid},
            [f"parked:{pid}"])
        if not links:
            new[-1]["state"] = "open"
            new[-1].pop("home", None)

    for a in m.get("asks") or []:
        key = f"ask:{a.get('id')}"
        if key in known:
            continue
        st = a.get("state")
        link = classify(a["link"]) if has_url(a.get("link")) else None
        t = {"title": short_title(a.get("text")), "kind": "ask",
             "origin": {"at": _date_str(a.get("date") or at), "session": session, "event": "imported", "source": key},
             "state": "resolved" if st in ("answered", "done", "superseded") else "open", "ask_id": a.get("id"),
             "finding": str(a.get("text") or "").strip(), "refs": [link] if link else []}
        if t["state"] == "resolved":
            t["resolution"] = {"at": _date_str(a.get("date") or at), "by": a.get("asker"),
                               "how": "superseded" if st == "superseded" else "answered", "link": link, "note": str(a.get("answer") or "")}
        add(t, [key])

    for j in m.get("journey") or []:
        for field in ("findings", "blockers"):
            for k, text in enumerate(j.get(field) or []):
                key = f"journey:{j.get('id')}:{field}:{k}"
                if key in known:
                    continue
                add({"title": short_title(text), "kind": "finding",
                     "origin": {"at": _date_str(j.get("start") or at), "session": j.get("session") or session, "event": "imported", "source": key},
                     "state": "open", "finding": f"{'Blocker' if field == 'blockers' else 'Finding'} in {j.get('id')}: {text}",
                     "refs": [classify(ln) for ln in j.get("links") or [] if has_url(ln)][:3]}, [key])

    covered = set()
    for t in threads + new:
        covered |= tokens(t.get("finding")) | tokens(t.get("title"))
        for ln in (t.get("refs") or []) + (t.get("evidence") or []) + [t.get("lives_in"), (t.get("home") or {}).get("link")]:
            covered |= link_tokens(ln)
    for mem in m.get("members") or []:
        key = f"member:{mem.get('ref')}"
        if mem.get("role") != "current" or key in known or mem.get("kind") not in ("jira", "gh", "mr"):
            continue
        mt = link_tokens(classify({**mem}))
        if mt and mt <= covered:
            log.append(f"member {mem.get('ref')} already covered by a thread")
            continue
        link = classify({k: mem[k] for k in ("kind", "ref", "url", "title") if mem.get(k)})
        add({"title": short_title(mem.get("title") or mem.get("ref")), "kind": "intent",
             "origin": {"at": _date_str(m.get("created") or at), "session": session, "event": "imported", "source": key},
             "state": "open", "refs": [link], "lives_in": link, "finding": str(mem.get("note") or "").strip()}, [key])

    nxt = next_id(threads)
    for t in new:
        t["id"] = nxt
        nxt = f"T-{int(nxt[2:]) + 1}"
    root_id = root_id or (root.get("id") if root else None)
    for t in new:
        if root_id and t.get("id") != root_id and t.get("kind") != "big_intent":
            t.setdefault("parent", root_id)
    return [_order(t) for t in threads + new], log


FIELD_ORDER = ["id", "title", "kind", "parent", "origin", "state", "refs", "lives_in", "about", "finding", "reasons", "control", "live",
               "evidence_state", "evidence", "do_now", "home", "snapshot", "drift", "closeout", "resolution", "needs_you_id", "ask_id",
               "parked_id", "imported_from", "history"]


def _order(t: dict) -> dict:
    out = {k: t[k] for k in FIELD_ORDER if k in t and t[k] not in (None, [], "", {})}
    out.update({k: v for k, v in t.items() if k not in out and v not in (None, [], "", {})})
    if "home" in t and isinstance(t["home"], dict):
        out["home"] = {k: v for k, v in t["home"].items() if v is not None or k == "accepted"}
    return out


# ---------------------------------------------------------------- merge a close-out sweep into existing threads

def merge_closeout(m: dict, co: dict, session: str | None, at: str | None = None) -> tuple[list[dict], list[str]]:
    """After /mission check --close: update each thread that a close-out item judged, and add the items live capture missed
    (origin.event closeout_sweep, each one a capture miss). Threads with no close-out data are left as they are."""
    at = at or now_utc()
    if not m.get("threads"):
        return import_threads(m, co, session, at=at)
    threads = [dict(t) for t in m["threads"]]
    by_co = {(t.get("closeout") or {}).get("co_id"): t for t in threads if (t.get("closeout") or {}).get("co_id")}
    by_batch = {(t.get("origin") or {}).get("source"): t for t in threads if str((t.get("origin") or {}).get("source", "")).startswith("batch:")}
    acts: dict[str, list] = {}
    for a in co.get("manifest") or []:
        acts.setdefault(a.get("item"), []).append(a)
    log, new = [], []
    for it in co.get("items") or []:
        fresh = thread_from_closeout(it, co, acts, co.get("human_guide") or [], at, session, "closeout_sweep")
        t = by_co.get(it.get("id")) or next((x for x in threads if it.get("thread") == x.get("id")), None)
        if t is None:
            fresh["imported_from"] = [f"closeout:{it.get('id')}"]
            history(fresh, at, session, "closeout_sweep", "found at close, not captured live (capture miss)")
            new.append(fresh)
            log.append(f"capture miss: {it.get('id')} had no thread")
            continue
        t["closeout"] = fresh.get("closeout")
        for k in ("reasons", "control", "live", "evidence_state", "evidence"):
            if k in fresh:
                t[k] = fresh[k]
        if t.get("state") not in TERMINAL and not (t.get("do_now") or {}).get("answer"):
            t["state"] = fresh["state"]
            if fresh.get("do_now") and not t.get("do_now"):
                t["do_now"] = fresh["do_now"]
            if fresh.get("home") and not t.get("home"):
                t["home"] = fresh["home"]
            if fresh.get("resolution"):
                t["resolution"] = fresh["resolution"]
        history(t, at, session, "closeout_sweep", f"judged {it.get('bucket')} as {it.get('id')}")
    for b in batch_threads(co, at, session, "closeout_sweep"):
        src = b["origin"]["source"]
        old = next((t for s, t in by_batch.items() if t.get("state") not in TERMINAL), None)
        if old is not None:
            old["closeout"] = b["closeout"]
            old["title"], old["finding"] = b["title"], b["finding"]
            old.setdefault("origin", {})["source"] = src
            history(old, at, session, "closeout_sweep", "batch re-planned")
        elif src not in by_batch:
            new.append(b)
            history(b, at, session, "closeout_sweep", "batch planned")
    root = next((t.get("id") for t in threads if t.get("kind") == "big_intent" and not t.get("parent")), None)
    nxt = next_id(threads)
    for t in new:
        t["id"] = nxt
        nxt = f"T-{int(nxt[2:]) + 1}"
        if root:
            t.setdefault("parent", root)
    return [_order(t) for t in threads + new], log


# ---------------------------------------------------------------- CLI

def _write(d, threads: list[dict]) -> None:
    set_section(d, "threads", threads)


def _apply_fields(t: dict, a, at: str) -> None:
    if a.title:
        t["title"] = a.title
    if a.kind:
        t["kind"] = a.kind
    if getattr(a, "parent", None):
        t["parent"] = a.parent
    if a.finding:
        t["finding"] = a.finding
    if a.ref:
        t["refs"] = (t.get("refs") or []) + [link_arg(x) for x in a.ref]
    if a.lives_in:
        t["lives_in"] = link_arg(a.lives_in)
    if a.reason:
        t["reasons"] = sorted(set((t.get("reasons") or []) + a.reason), key=REASONS.index)
    if a.control:
        t["control"] = a.control
    if a.live:
        t["live"] = {"true": True, "false": False}.get(a.live.lower(), "UNKNOWN")
    if a.evidence:
        t["evidence"] = (t.get("evidence") or []) + [link_arg(x) for x in a.evidence]
    if a.home or a.owner or a.accepted_by:
        home = dict(t.get("home") or {})
        if a.home:
            home["link"] = link_arg(a.home)
        if a.owner:
            home["owner"] = a.owner
        if a.accepted_by:
            if not a.accepted_link:
                sys.exit("--accepted-by needs --accepted-link (where the owner said yes)")
            home["accepted"] = {"by": a.accepted_by, "link": link_arg(a.accepted_link, "accepted here")}
        home.setdefault("accepted", None)
        t["home"] = home
    if a.question or a.option or a.recommend or a.verb or a.command or a.after:
        dn = dict(t.get("do_now") or {"actor": "Gabriel"})
        if a.question:
            dn["question"] = a.question
        if a.option:
            dn["options"] = [{"label": o.partition("|")[0].strip(), "consequence": o.partition("|")[2].strip()} for o in a.option]
        if a.recommend:
            dn["recommendation"] = a.recommend
        if a.verb:
            dn["verb"] = a.verb
        if a.command:
            dn["commands"] = (dn.get("commands") or []) + [{"label": c.partition("|")[0].strip(), "cmd": c.partition("|")[2].strip()} for c in a.command]
        if a.after:
            dn["after_answer"] = a.after
        t["do_now"] = dn
    if a.needs_you:
        t["needs_you_id"] = a.needs_you
    if a.ask:
        t["ask_id"] = a.ask
    if getattr(a, "json", None):
        extra = json.loads(a.json)
        if not isinstance(extra, dict) or "id" in extra:
            sys.exit("--json must be an object and must not change the id")
        t.update(extra)


def _common(p) -> None:
    p.add_argument("mission")
    p.add_argument("--title")
    p.add_argument("--kind", choices=KINDS)
    p.add_argument("--parent")
    p.add_argument("--finding")
    p.add_argument("--ref", action="append", help="'URL|title', repeatable")
    p.add_argument("--lives-in")
    p.add_argument("--reason", action="append", choices=REASONS)
    p.add_argument("--control", choices=sorted(CONTROLS))
    p.add_argument("--live", choices=["true", "false", "UNKNOWN"])
    p.add_argument("--evidence", action="append")
    p.add_argument("--home")
    p.add_argument("--owner")
    p.add_argument("--accepted-by")
    p.add_argument("--accepted-link")
    p.add_argument("--question")
    p.add_argument("--option", action="append", help="'label|consequence', repeatable")
    p.add_argument("--recommend")
    p.add_argument("--verb")
    p.add_argument("--command", action="append", help="'label|command', repeatable")
    p.add_argument("--after")
    p.add_argument("--needs-you")
    p.add_argument("--ask")
    p.add_argument("--session")
    p.add_argument("--note")


def _validate_or_die(m: dict, threads: list[dict], tid: str | None = None) -> None:
    err, warn = lint_threads({**m, "threads": threads})
    mine = [e for e in err if tid is None or e.startswith(tid + ":") or e.startswith(tid + ".")]
    for w in warn:
        if tid is None or w.startswith(tid + ":"):
            print(f"WARN  {w}")
    if mine:
        for e in mine:
            print(f"ERROR {e}")
        sys.exit("refused: the thread would not lint (nothing written)")


def cmd_add(a) -> int:
    d = mission_dir(a.mission)
    at = now_utc()
    with locked(d):
        m = load(d)
        threads = list(m.get("threads") or [])
        if not a.kind or not a.title:
            sys.exit("add needs --kind and --title")
        tid = next_id(threads)
        t = {"id": tid, "title": "", "kind": a.kind, "origin": {"at": at, "session": a.session, "event": a.event or f"{a.kind}_opened"},
             "state": a.state or "open"}
        if a.origin_link:
            t["origin"]["link"] = link_arg(a.origin_link)
        if not a.parent and a.kind != "big_intent":
            root = next((x.get("id") for x in threads if x.get("kind") == "big_intent" and not x.get("parent")), None)
            if root:
                a.parent = root
        _apply_fields(t, a, at)
        history(t, at, a.session, t["origin"]["event"], a.note)
        threads.append(_order(t))
        made = [tid]
        for child in a.child or []:
            cid = next_id(threads)
            c = {"id": cid, "title": short_title(child), "kind": "intent", "parent": tid,
                 "origin": {"at": at, "session": a.session, "event": a.event or f"{a.kind}_opened"}, "state": "open"}
            if t.get("home"):
                c["home"] = t["home"]
            history(c, at, a.session, c["origin"]["event"], f"intent of {tid}")
            threads.append(_order(c))
            made.append(cid)
        for x in made:
            _validate_or_die(m, threads, x)
        _write(d, threads)
    print("added " + ", ".join(made))
    return 0


def _find(threads, tid):
    t = next((x for x in threads if x.get("id") == tid), None)
    if t is None:
        sys.exit(f"{tid} is not a thread")
    return t


def cmd_set(a) -> int:
    d = mission_dir(a.mission)
    at = now_utc()
    with locked(d):
        m = load(d)
        threads = list(m.get("threads") or [])
        t = _find(threads, a.id)
        before = t.get("state")
        _apply_fields(t, a, at)
        if a.state:
            t["state"] = a.state
        if a.clear_drift:
            t["drift"] = None
            t["snapshot"] = None
        if a.answer:
            if not named(a.by):
                sys.exit("--answer needs --by: a named person")
            t.setdefault("do_now", {})["answer"] = {"text": a.answer, "by": a.by, "at": at, "link": link_arg(a.link) if a.link else None}
        note = a.note or (f"state {before} -> {t.get('state')}" if t.get("state") != before else "updated")
        history(t, at, a.session, "rejudged" if a.clear_drift else "update", note)
        threads[threads.index(t)] = _order(t)
        _validate_or_die(m, threads, a.id)
        _write(d, threads)
    print(f"{a.id}: {before} -> {t.get('state')}")
    return 0


def cmd_resolve(a) -> int:
    d = mission_dir(a.mission)
    at = now_utc()
    with locked(d):
        m = load(d)
        threads = list(m.get("threads") or [])
        t = _find(threads, a.id)
        if a.how == "dropped" and not (named(a.by) and a.note):
            sys.exit("--how dropped needs --by (a named person) and --note (the reason)")
        if a.how != "dropped" and not (a.link or a.note):
            sys.exit("resolve needs --link (evidence, ticket, or what replaced it) or --note")
        if t.get("drift") and not a.rejudged:
            sys.exit(f"{a.id} changed since it was judged ({t['drift'].get('text')}). Re-read it, then pass --rejudged")
        t["state"] = "dropped" if a.how == "dropped" else "resolved"
        t["resolution"] = {k: v for k, v in {"at": at, "by": a.by, "how": a.how, "link": link_arg(a.link) if a.link else None,
                                             "note": a.note, "session": a.session}.items() if v}
        if a.rejudged:
            t["drift"] = None
        history(t, at, a.session, "resolved" if a.how != "dropped" else "dropped", a.note)
        threads[threads.index(t)] = _order(t)
        _validate_or_die(m, threads, a.id)
        _write(d, threads)
    print(f"{a.id}: {t['state']} ({a.how})")
    return 0


def cmd_list(a) -> int:
    m = load(mission_dir(a.mission))
    want = set((a.state or "").split(",")) - {""}
    rows = [t for t in m.get("threads") or [] if (not want or t.get("state") in want or view_state(t) in want)
            and (not a.session or (t.get("origin") or {}).get("session") == a.session)]
    if a.json:
        print(json.dumps(rows, indent=1, default=str, ensure_ascii=False))
        return 0
    for t in rows:
        dr = " DRIFT" if t.get("drift") else ""
        print(f"{t.get('id'):6} {view_state(t):17} {t.get('kind'):11} {t.get('title')}{dr}")
    print(f"{len(rows)} thread(s)")
    return 0


def load_closeout_for(d) -> dict | None:
    import yaml
    f = closeout_home(d) / "closeout.yaml"
    return yaml.safe_load(f.read_text()) if f.exists() else None


def cmd_import(a) -> int:
    d = mission_dir(a.mission)
    forced = dict(x.split("=", 1) for x in (a.match or "").split(",") if "=" in x)
    blocked = set(x.strip() for x in (a.no_match or "").split(",") if x.strip())
    with locked(d):
        m = load(d)
        co = load_closeout_for(d)
        before = len(m.get("threads") or [])
        threads, log = import_threads(m, co, a.session, forced, blocked)
        for line in log:
            print(f"  {line}")
        added = threads[before:]
        kinds: dict[str, int] = {}
        for t in added:
            kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
        print(f"{len(added)} thread(s) imported ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items())) or 'none'}); "
              f"origin.event = imported (not live-captured)")
        if co is None:
            print("  no closeout.yaml for this mission: close-out items not imported")
        _validate_or_die(m, threads)
        if a.dry_run:
            print("dry run: nothing written")
            return 0
        _write(d, threads)
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="mission thread")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    _common(p)
    p.add_argument("--state", choices=STATES)
    p.add_argument("--event", help=f"what opened it, for example {', '.join(LIVE_EVENTS_HINT[:6])}")
    p.add_argument("--origin-link", help="'URL|title' of where it opened (session folder, prompt file)")
    p.add_argument("--child", action="append", help="one child intent per value (handoffs: one per intent in the prompt)")
    p = sub.add_parser("set", aliases=["update"])
    _common(p)
    p.add_argument("id")
    p.add_argument("--state", choices=STATES)
    p.add_argument("--clear-drift", action="store_true", help="the thread was re-read and re-judged after a drift")
    p.add_argument("--answer")
    p.add_argument("--by")
    p.add_argument("--link")
    p.add_argument("--json", help="advanced: a JSON object merged into the thread")
    p = sub.add_parser("resolve")
    p.add_argument("mission")
    p.add_argument("id")
    p.add_argument("--how", required=True, choices=sorted(HOW))
    p.add_argument("--link")
    p.add_argument("--by")
    p.add_argument("--note")
    p.add_argument("--session")
    p.add_argument("--rejudged", action="store_true", help="the drift was read and the thread re-judged")
    p = sub.add_parser("list")
    p.add_argument("mission")
    p.add_argument("--state")
    p.add_argument("--session")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("import")
    p.add_argument("mission")
    p.add_argument("--session")
    p.add_argument("--match", help="force pairs: N-1=CO-1,P-1=CO-18")
    p.add_argument("--no-match", help="never merge these sources: N-4,P-2")
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    cmd = {"add": cmd_add, "set": cmd_set, "update": cmd_set, "resolve": cmd_resolve, "list": cmd_list, "import": cmd_import}[a.cmd]
    return cmd(a)


if __name__ == "__main__":
    sys.exit(main())
