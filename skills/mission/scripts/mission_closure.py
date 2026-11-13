"""Render the Closure tab of the mission report as static HTML (UX spec: missions/_meta/closure-ux/ux-spec.md).

render_closure(m, d) -> (html, summary). The HTML goes into the Closure panel of report.html. summary feeds the tab
counter and the Mission-tab tile. Levels: L0 verdict, phase, tiles, counts; L1 one <details> row per thread; L2 the
card body; L3 nested <details> (exact actions, history, raw checks). A thread renders as a full card exactly once,
in the highest block it qualifies for; every other block lists it as one line with "↑ in <block>".
Every text field goes through mission_links.linkify: no bare #N, KEY-N or !N outside an <a>.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re

from mission_lib import closeout_home, now_utc
from mission_links import Ctx, chip, e, linkify, repo_of
from mission_thread import BIG_REASONS, TERMINAL, accepted, view_state

MISSION_CMD = "~/.claude/skills/mission/scripts/mission"
WHY = {  # reason code -> (chip class, chip text, the fixed "why it needs you" sentence)
    "live_assurance_gap": ("crit", "Live security gap", "A production capability runs without proof that its control holds, and no named person accepted the risk."),
    "uncovered_obligation": ("warn", "No accepted home", "The work is still needed, but no owner has accepted it. If nobody takes it, it is lost after the close."),
    "false_record": ("warn", "False record", "A record says the opposite of what runs in production. A reader who trusts it gets the facts backwards."),
    "control_failure": ("crit", "Control failure", "A safeguard was skipped, and it happened before. A one-off fix does not stop the next time."),
    "your_call": ("neutral", "Your call", "Only you can make this call. Nothing in production is at risk while it waits."),
    "approval": ("neutral", "Approval", "An approval binds to the exact list of actions. If the list changes, the hash changes and the approval is void."),
}
GLYPH = {"open": ("◎", "g-open", "Open thread"), "needs_you": ("●", "g-needs", "Needs you"),
         "ready": ("◐", "g-act", "Ready: the agent acts after approval"), "parked": ("⤴", "g-home", "Parked with an accepted home"),
         "parked_unaccepted": ("⤴", "g-needs", "Parked, home not accepted"), "resolved": ("✓", "g-done", "Resolved"),
         "dropped": ("⊘", "g-drop", "Dropped")}
KIND_WORD = {"big_intent": "Big intent", "intent": "Intent", "rabbit_hole": "Rabbit hole", "open_door": "Open door", "handoff": "Handoff",
             "nugget": "Nugget", "ask": "Ask", "finding": "Finding"}
PHASES = ["Live capture", "Close-out review", "Approved actions", "Closed"]


def _num(tid: str) -> int:
    m = re.search(r"(\d+)$", str(tid or ""))
    return int(m.group(1)) if m else 0


def _days(v) -> int | None:
    try:
        t = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    t = t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
    return (dt.datetime.now(dt.timezone.utc) - t).days


def _load_json(f: pathlib.Path) -> dict:
    try:
        return json.loads(f.read_text()) if f.exists() else {}
    except (OSError, ValueError):
        return {}


def _load_yaml(f: pathlib.Path):
    import yaml
    try:
        return yaml.safe_load(f.read_text()) if f.exists() else None
    except (OSError, yaml.YAMLError):
        return None


class Closure:
    def __init__(self, m: dict, d: pathlib.Path | None):
        self.m, self.d = m, d
        self.slug = m.get("slug") or (d.name if d else "")
        self.threads = [t for t in m.get("threads") or [] if isinstance(t, dict)]
        cd = closeout_home(d) if d else None
        self.co = (_load_yaml(cd / "closeout.yaml") if cd else None) or {}
        self.facts = _load_json(cd / "closeout-facts.json") if cd else {}
        self.cd = cd
        self.manifest = {a.get("id"): a for a in self.co.get("manifest") or [] if isinstance(a, dict)}
        self.anchors = {t.get("id") for t in self.threads} | {(t.get("closeout") or {}).get("co_id") for t in self.threads} - {None}
        self.where: dict[str, str] = {}

    # ------------------------------------------------------------ helpers
    def ctx(self, t: dict) -> Ctx:
        text = " ".join(str(t.get(k) or "") for k in ("title", "finding", "about")) + " " + str((t.get("closeout") or {}).get("action") or "")
        return Ctx(repo=repo_of(text), anchors=self.anchors)

    def lk(self, text, t: dict | None = None) -> str:
        return linkify(text, self.ctx(t) if t else Ctx(anchors=self.anchors))

    def batches(self) -> list[dict]:
        from mission_closeout import plan_batches
        return plan_batches(list(self.manifest.values()))

    def approve_cmd(self, ids: list[str], h: str) -> str:
        return f"{MISSION_CMD} closeout approve {self.slug} --items {','.join(ids)} --hash {h} --by Gabriel --link <where you said yes>"

    def gate(self) -> tuple[list[str], list[str]]:
        if not self.d:
            return [], []
        from mission_closeout import gate
        try:
            return gate(self.d)
        except SystemExit as x:
            return [str(x)], []

    def phase(self) -> int:
        if self.m.get("status") == "done":
            return 3
        acted = any(a.get("state") in ("approved", "done", "skipped", "unverified") for a in self.manifest.values())
        if acted:
            return 2
        judged = self.co.get("items") or any((t.get("closeout") or {}).get("bucket") for t in self.threads)
        return 1 if judged else 0

    def is_big(self, t: dict) -> bool:
        return bool(set(t.get("reasons") or []) & BIG_REASONS) or view_state(t) == "parked_unaccepted"

    def block_of(self, t: dict) -> str:
        """The highest block a thread qualifies for (where its full card renders)."""
        vs, co = view_state(t), t.get("closeout") or {}
        if t.get("kind") == "big_intent" and not t.get("parent"):
            return "root"
        if vs == "open":
            return "open"
        if vs in ("needs_you", "parked_unaccepted"):
            if co.get("batch"):
                return "approval"
            return "big" if self.is_big(t) else "small"
        if vs == "ready":
            return {"SUPERSEDE": "replaced", "FALSE-PREMISE": "fixes"}.get(co.get("bucket"), "ready")
        if vs == "parked":
            return "parked"
        return vs  # resolved, dropped

    # ------------------------------------------------------------ the card
    def glyph(self, t: dict) -> str:
        g, cls, label = GLYPH.get(view_state(t), ("◎", "g-open", "Open"))
        return f'<span class="glyph {cls}" role="img" aria-label="{e(label)}" title="{e(label)}">{g}</span>'

    def summary_row(self, t: dict, needs: bool) -> str:
        chips = "".join(f'<span class="why {WHY[r][0]}">{e(WHY[r][1])}</span>' for r in t.get("reasons") or [] if r in WHY)
        if view_state(t) == "parked_unaccepted" and "uncovered_obligation" not in (t.get("reasons") or []):
            chips += f'<span class="why warn">{e(WHY["uncovered_obligation"][1])}</span>'
        drift = '<span class="why drift" title="Changed since it was captured or judged">⚠ changed</span>' if t.get("drift") else ""
        verb = (t.get("do_now") or {}).get("verb")
        do = f'<span class="do">{e(verb)}</span>' if needs and verb else ""
        if view_state(t) == "open":
            o = t.get("origin") or {}
            age = _days(o.get("at"))
            do = (f'<span class="kindw">{e(KIND_WORD.get(t.get("kind"), t.get("kind")))}</span>'
                  f'<span class="muted small">opened {age if age is not None else "?"}d ago'
                  f'{" in " + e(o.get("session")) if o.get("session") else ""}</span>')
        co = (t.get("closeout") or {}).get("co_id")
        ids = f'<span class="sid" title="Thread ID">{e(t.get("id"))}</span>' + (f'<span class="sid" title="Close-out item ID">{e(co)}</span>' if co else "")
        return f'<summary>{self.glyph(t)}<span class="ttl">{self.lk(t.get("title"), t)}</span>{chips}{drift}{do}{ids}</summary>'

    def do_now(self, t: dict) -> str:
        dn, tid = t.get("do_now") or {}, t.get("id")
        rec = dn.get("recommendation")
        lis = []
        for o in dn.get("options") or []:
            if not isinstance(o, dict):
                continue
            is_rec = o.get("label") == rec
            cons = f'<span class="cons">→ {self.lk(o.get("consequence"), t)}</span>' if o.get("consequence") else ""
            mark = ' <span class="st good">recommended</span>' if is_rec else ""
            lis.append(f'<li{" class=rec" if is_rec else ""}><b>{self.lk(o.get("label"), t)}</b>{cons}{mark}</li>')
        opts = "".join(lis)
        h = [f'<div class="donow"><h4>Do now</h4><p class="q">{self.lk(dn.get("question"), t)}</p>']
        if opts:
            h.append(f'<ol class="opts">{opts}</ol>')
        h.append(f'<p class="small"><b>Recommendation:</b> {self.lk(rec, t)}</p>' if rec
                 else '<p class="small muted">No recommendation recorded.</p>')
        for c in dn.get("commands") or []:
            h.append(self.cmd_block(c.get("label"), c.get("cmd"), t))
        h += self.approve_blocks(t)
        if dn.get("after_answer"):
            h.append(f'<p class="small"><b>Then the agent does:</b> {self.lk(dn["after_answer"], t)}</p>')
        ans = dn.get("answer")
        if isinstance(ans, dict) and ans.get("text"):
            h.append(f'<p class="small"><b>Answered</b> by {e(ans.get("by"))} {e(str(ans.get("at") or "")[:10])}: {self.lk(ans["text"], t)} {chip(ans.get("link"))}</p>')
        h.append(f'<button class="btn xs" data-copy="ANSWER {e(tid)}: ">Copy “ANSWER {e(tid)}:”</button> '
                 '<span class="small muted">Paste it in the terminal and add your choice.</span></div>')
        return "".join(h)

    def cmd_block(self, label, cmd, t=None) -> str:
        return (f'<div class="cmd"><div class="small">{self.lk(label, t)}</div><pre><code>{e(cmd)}</code></pre>'
                f'<button class="btn xs" data-copy="{e(cmd)}">Copy command</button></div>')

    def approve_blocks(self, t: dict) -> list[str]:
        co = t.get("closeout") or {}
        ids = co.get("actions") or []
        out = []
        for b in self.batches():
            if co.get("batch") and set(b["items"]) & set(ids) and len(b["items"]) > 1:
                out.append(self.cmd_block(f"Approve the {len(b['items'])} actions by their hash", self.approve_cmd(b["items"], b["hash"])))
            elif not co.get("batch") and len(b["items"]) == 1 and b["items"][0] in ids:
                a = self.manifest[b["items"][0]]
                if a.get("class", "routine") != "routine":
                    out.append(self.cmd_block(f"Approve action {a['id']} alone ({a.get('class')}): {a.get('action', '')[:90]}",
                                              self.approve_cmd(b["items"], b["hash"]), t))
        return out

    def actions(self, t: dict) -> str:
        co = t.get("closeout") or {}
        acts = [self.manifest[i] for i in co.get("actions") or [] if i in self.manifest]
        if not acts:
            return ""
        if co.get("batch"):
            rows = "".join(f'<tr><td class="sid">{e(a.get("id"))}</td><td>{chip(a.get("target"))}</td><td class="small">{self.lk(a.get("expected_state"), t)}</td>'
                           f'<td class="small">{self.lk(a.get("action"), t)}</td><td>{self.xref_link(a.get("item"))}</td><td>{e(a.get("state", "proposed"))}</td></tr>'
                           for a in acts)
            return (f'<details class="inner"><summary>The {len(acts)} actions</summary><table><thead><tr><th>Action</th><th>Target</th>'
                    f'<th>Expected now</th><th>Exact action</th><th>For</th><th>State</th></tr></thead><tbody>{rows}</tbody></table></details>')
        lis = "".join(f'<li><span class="sid">{e(a.get("id"))}</span> {self.lk(a.get("action"), t)} '
                      f'<span class="st {"warn" if a.get("class", "routine") != "routine" else "neutral"}">{e(a.get("class", "routine"))}</span> '
                      f'<span class="small muted">{e(a.get("state", "proposed"))}'
                      f'{" · read back: " + e((a.get("readback") or {}).get("after")) if (a.get("readback") or {}).get("after") else ""}</span></li>' for a in acts)
        return f'<div class="row"><span class="lbl">Exact action</span><ul class="acts">{lis}</ul></div>'

    def xref_link(self, co_id) -> str:
        t = next((x for x in self.threads if (x.get("closeout") or {}).get("co_id") == co_id), None)
        return f'<a href="#{e(t["id"])}">{e(t["id"])}</a>' if t else e(co_id)

    def home(self, t: dict) -> str:
        h = t.get("home")
        if not isinstance(h, dict) or not h.get("link"):
            return ""
        acc = h.get("accepted")
        if h.get("excludes"):
            st = '<span class="st crit">home excludes it</span>'
        elif accepted(h):
            st = f'<span class="st good">accepted by {e(acc.get("by"))}</span> {chip(acc.get("link"))}'
        else:
            st = '<span class="st warn">not accepted yet</span>'
        owner = f" · owner {e(h['owner'])}" if h.get("owner") else ""
        return f'<div class="row"><span class="lbl">Home</span><div>{chip(h["link"])} {st}{owner}</div></div>'

    def provenance(self, t: dict) -> str:
        o, co = t.get("origin") or {}, t.get("closeout") or {}
        ev = o.get("event")
        how = "imported from the record, not live" if ev == "imported" else "found at close, not live (a capture miss)" if ev == "closeout_sweep" else "live"
        bits = [f"Captured {e(str(o.get('at') or '?')[:10])}" + (f" by {e(o.get('session'))}" if o.get("session") else "") + f" ({e(ev)}), {how}"]
        if co.get("bucket"):
            bits.append(f"bucket {e(co['bucket'])}" + (f" ({e(co.get('found_by'))})" if co.get("found_by") else ""))
        bits.append(f"state {e(view_state(t))}")
        if t.get("control"):
            bits.append(f"control {e(t['control'])}")
        if "live" in t:
            bits.append(f"live {e(str(t['live']).lower())}")
        return f'<div class="hist">{" · ".join(bits)}</div>'

    def card(self, t: dict, open_: bool = False) -> str:
        block = self.block_of(t)
        needs = block in ("big", "small", "approval")
        reasons = [r for r in t.get("reasons") or [] if r in WHY]
        if view_state(t) == "parked_unaccepted" and "uncovered_obligation" not in reasons:
            reasons.append("uncovered_obligation")
        why = " ".join(WHY[r][2] for r in reasons) if needs else ""
        co = t.get("closeout") or {}
        res = t.get("resolution") or {}
        right = (f'<div><h4>Why it needs you</h4><p>{e(why)}</p></div>' if why else
                 f'<div><h4>Outcome</h4><p>{e(res.get("how"))}{" by " + e(res.get("by")) if res.get("by") else ""}: {self.lk(res.get("note"), t)} {chip(res.get("link"))}</p></div>' if res else
                 f'<div><h4>Outcome</h4><p>{self.lk(co.get("action"), t)}</p></div>' if co.get("action") else "")
        finding = t.get("finding") or (f"About: {t['about']}" if t.get("about") else "")
        body = [f'<div class="body"><div class="two"><div><h4>What is going on</h4><p>{self.lk(finding, t) or "<span class=muted>No finding written.</span>"}</p></div>{right}</div>']
        if t.get("drift"):
            body.append(f'<div class="driftbox">⚠ Changed since {e(str(t["drift"].get("at") or "")[:10])}: {self.lk(t["drift"].get("text"), t)}. '
                        'Re-read it before you act on the old evidence.</div>')
        if needs and (t.get("do_now") or {}).get("question"):
            body.append(self.do_now(t))
        elif (t.get("do_now") or {}).get("commands"):
            body.append('<div class="donow soft"><h4>One step left for you</h4>'
                        + "".join(self.cmd_block(c.get("label"), c.get("cmd"), t) for c in t["do_now"]["commands"]) + "</div>")
        if not needs:
            body += self.approve_blocks(t) and [f'<div class="donow soft"><h4>Its own approval</h4>{"".join(self.approve_blocks(t))}</div>']
        body.append(self.actions(t))
        if t.get("lives_in"):
            body.append(f'<div class="row"><span class="lbl">Lives in</span><div>{chip(t["lives_in"])}</div></div>')
        refs = [r for r in t.get("refs") or [] if r != t.get("lives_in")]
        if refs:
            body.append(f'<div class="row"><span class="lbl">About</span><div class="chips">{"".join(chip(r) for r in refs)}</div></div>')
        if t.get("evidence"):
            body.append(f'<div class="row"><span class="lbl">Evidence</span><div class="chips">{"".join(chip(x) for x in t["evidence"])}</div></div>')
        body.append(self.home(t))
        l3 = []
        dec = co.get("decision") or {}
        if dec.get("question") and dec.get("question") != (t.get("do_now") or {}).get("question"):
            opts = "".join(f"<li>{self.lk(o.get('label') if isinstance(o, dict) else o, t)}"
                           f"{' → ' + self.lk(o.get('consequence'), t) if isinstance(o, dict) and o.get('consequence') else ''}</li>" for o in dec.get("options") or [])
            l3.append(f'<details class="inner"><summary>The close-out reviewer\'s question</summary><p>{self.lk(dec["question"], t)}</p><ol>{opts}</ol></details>')
        if t.get("history"):
            l3.append('<details class="inner"><summary>History</summary><ul class="acts">' + "".join(
                f'<li><span class="mono small">{e(str(h.get("at"))[:16])}</span> {e(h.get("event"))}{" · " + e(h.get("session")) if h.get("session") else ""}'
                f'{": " + self.lk(h.get("note"), t) if h.get("note") else ""}</li>' for h in t["history"]) + "</ul></details>")
        body += l3
        body.append(self.provenance(t) + "</div>")
        anchor = f'<span id="{e(co["co_id"])}"></span>' if co.get("co_id") else ""
        return f'<details class="th" id="{e(t.get("id"))}"{" open" if open_ else ""}>{anchor}{self.summary_row(t, needs)}{"".join(body)}</details>'

    def line(self, t: dict, where: str | None) -> str:
        return (f'<li>{self.glyph(t)} <a href="#{e(t.get("id"))}">{self.lk(t.get("title"), t)}</a> <span class="sid">{e(t.get("id"))}</span>'
                f'{" <span class=\"muted small\">↑ in " + e(where) + "</span>" if where else ""}</li>')

    # ------------------------------------------------------------ blocks
    def bucket(self, title: str, n: int, sub: str, inner: str, sid: str | None = None, open_: bool = False) -> str:
        attr = (" open" if open_ else "") + (f' id="{e(sid)}"' if sid else "")
        return (f'<details class="bucket"{attr}>'
                f'<summary><span class="bt">{e(title)}</span><span class="ct">{n}</span><span class="sub">{sub}</span></summary>'
                f'<div class="bin">{inner}</div></details>')

    def coverage(self) -> str:
        from mission_closeout import CHECK_REGISTRY, fact_counts, fact_sources, unknown_key
        if not self.facts:
            return self.bucket("How we searched", 0, "sources, UNKNOWN sources and their disposition, the 15 checks",
                               '<div class="pad empty">Not searched yet. Coverage appears after <code>/mission check --close</code>.</div>', "cl-coverage")
        src = fact_sources(self.facts)
        full = [s for s, st, _ in src if st == "OK"]
        gaps = [(s, st, r) for s, st, r in src if st != "OK"]
        disp = {str(u.get("source")): u for u in self.co.get("unknowns") or [] if isinstance(u, dict)}
        unk = list(dict.fromkeys(unknown_key(u) for u in self.facts.get("unknown") or []))
        rows = []
        for k in unk:
            u = disp.get(k) or {}
            w = "not consequential" if u.get("consequential") is False else "consequential"
            d = u.get("disposition") or ("reason given" if u.get("reason") else "no disposition yet")
            rows.append(f'<tr><td class="small mono">{e(k)}</td><td><span class="st {"neutral" if w.startswith("not") else "crit"}">{w}</span></td>'
                        f'<td class="small">{e(d)}: {self.lk(u.get("reason") or u.get("note") or "")}</td></tr>')
        extra = [u for k, u in disp.items() if k not in unk]
        rows += [f'<tr><td class="small mono">{e(u.get("source"))}</td><td><span class="st {"neutral" if u.get("consequential") is False else "crit"}">'
                 f'{"not consequential" if u.get("consequential") is False else "consequential"}</span></td><td class="small">{self.lk(u.get("reason") or "")}</td></tr>' for u in extra]
        steps = {s.get("id"): s for s in self.co.get("checklist") or [] if isinstance(s, dict)}
        chk = "".join(f'<tr><td>{e(v["label"])} <span class="sid">{e(k)}</span></td><td><span class="st {"good" if (steps.get(k) or {}).get("status") == "done" else "warn"}">'
                      f'{e((steps.get(k) or {}).get("status", "missing"))}</span></td><td class="small">{self.lk((steps.get(k) or {}).get("note"))}</td></tr>'
                      for k, v in CHECK_REGISTRY.items())
        counts = "".join(f"<li>{e(lbl)}: {e(n)}</li>" for lbl, n in fact_counts(self.facts))
        inner = (f'<div class="pad"><p>These sources were searched fully: <b>{e(", ".join(full) or "none")}</b>. Gaps: <b>{e(", ".join(s for s, _, _ in gaps) or "none")}</b>. '
                 f'The claim is coverage of these sources, not completeness. Facts fetched {e(self.facts.get("fetched_at", "?"))}.</p><ul class="small">{counts}</ul>'
                 f'<h4>Sources the script could not read (UNKNOWN)</h4><p class="small muted">UNKNOWN is never a pass. Each one needs a disposition.</p>'
                 f'<table><thead><tr><th>Source</th><th>Weight</th><th>Disposition</th></tr></thead><tbody>{"".join(rows) or "<tr><td colspan=3>none</td></tr>"}</tbody></table>'
                 f'<h4>The {len(CHECK_REGISTRY)} checks</h4><table><thead><tr><th>Check</th><th>Status</th><th>Note</th></tr></thead><tbody>{chk}</tbody></table></div>')
        undisposed = sum(1 for k in unk if not (disp.get(k) or {}).get("disposition") and (disp.get(k) or {}).get("consequential") is not False)
        return self.bucket("How we searched", len(unk), f"{len(unk)} unread source(s), {undisposed} without a disposition · the {len(CHECK_REGISTRY)} checks", inner, "cl-coverage")

    def lens(self) -> str:
        groups: dict[str, list] = {}
        heads: dict[str, dict | None] = {}
        for t in self.threads:
            if t.get("kind") == "big_intent" and not t.get("parent"):
                continue
            home = t.get("lives_in") or (t.get("home") or {}).get("link")
            key = (home or {}).get("url") or "none"
            groups.setdefault(key, []).append(t)
            heads[key] = home
        items = sorted(groups.items(), key=lambda kv: (kv[0] == "none", -len(kv[1])))
        tree = "".join(f'<li><b>{chip(heads[k]) if heads[k] else "No tracker home"}</b><ul>{"".join(self.line(t, None) for t in ts)}</ul></li>' for k, ts in items)
        return self.bucket("Where each thread lives", len(groups), "the same threads grouped by their tracker home", f'<ul class="tree">{tree}</ul>')

    def capture(self) -> str:
        ts = [t for t in self.threads if not (t.get("kind") == "big_intent" and not t.get("parent"))]
        n = len(ts)
        ev = [(t.get("origin") or {}).get("event") for t in ts]
        imp, sweep = ev.count("imported"), ev.count("closeout_sweep")
        live = n - imp - sweep
        pct = (lambda x: round(100 * x / n) if n else 0)
        bar = (f'<div class="capbar" role="img" aria-label="{live} of {n} threads captured live, {imp} imported, {sweep} found at close">'
               + (f'<span class="cap-live" style="flex:{live}">{live} live</span>' if live else "")
               + (f'<span class="cap-imp" style="flex:{imp}">{imp} imported</span>' if imp else "")
               + (f'<span class="cap-sweep" style="flex:{sweep}">{sweep} found at close</span>' if sweep else "") + "</div>")
        note = ('<p class="small">Imported threads were seeded from the record by <code>mission threads import</code>. They are not live captures: '
                'nobody wrote them when they opened.</p>' if imp else "")
        inner = (f'<div class="pad">{bar}{note}<p class="small"><b>Target:</b> 80% or more of the threads captured live. Live now: {pct(live)}%. '
                 'Each thread found only at close is a capture miss in <code>missions/_meta/closeout-log.jsonl</code>.</p></div>')
        return self.bucket("How these threads were found", f"{live} of {n} live" if n else 0, "capture health: live capture against reconstruction", inner)

    # ------------------------------------------------------------ page
    def render(self) -> tuple[str, dict]:
        ts = self.threads
        by_block: dict[str, list] = {}
        for t in ts:
            by_block.setdefault(self.block_of(t), []).append(t)
        names = {"open": "Open threads", "big": "Needs you", "small": "Needs you", "approval": "Needs you", "ready": "Ready to close",
                 "replaced": "Replaced or obsolete", "fixes": "Record fixes", "parked": "Parked with an accepted home",
                 "resolved": "Resolved", "dropped": "Dropped"}
        for b, lst in by_block.items():
            for t in lst:
                self.where[t["id"]] = names.get(b, b)
        phase = self.phase()

        def sort_big(t):
            return (not t.get("drift"), "live_assurance_gap" not in (t.get("reasons") or []), _num(t.get("id")))

        big = sorted(by_block.get("big", []), key=sort_big)
        small = sorted(by_block.get("small", []), key=lambda t: (not t.get("drift"), _num(t.get("id"))))
        appr = by_block.get("approval", [])
        opn = sorted(by_block.get("open", []), key=lambda t: (not t.get("drift"), str((t.get("origin") or {}).get("at") or "")))
        needs_n = len(big) + len(small) + len(appr)
        live_risk = sum(1 for t in big if "live_assurance_gap" in (t.get("reasons") or []))
        gerr, _ = self.gate()
        root = (by_block.get("root") or [None])[0]

        if not ts:
            verdict = "Nothing captured yet. Threads appear when a session adds an intent, a handoff, or an open door."
        elif phase == 3:
            verdict = f"Closed on {e(str(self.m.get('updated') or '')[:10])}."
        elif phase == 0:
            verdict = (f"{len(opn)} open thread(s). {needs_n} need you." if opn or needs_n
                       else "No open threads. Run <code>/mission check --close</code> when the destination looks reached.")
        elif needs_n or gerr:
            verdict = (f"Not ready to close. {needs_n} item(s) need you." + (f" {live_risk} of them are live production risks." if live_risk else "")
                       + (f" {len(opn)} thread(s) are not judged yet." if opn else ""))
        else:
            verdict = "Ready to close."
        h = [f'<p class="verdict">{verdict}</p>',
             '<div class="phase" role="list" aria-label="Closure phase">' + "".join(
                 f'<span role="listitem" class="ph{" done" if i < phase else " on" if i == phase else ""}"{" aria-current=step" if i == phase else ""}>{p}</span>'
                 for i, p in enumerate(PHASES)) + "</div>"]
        if root:
            h.append(f'<p class="small root">Big intent {self.glyph(root)} <a href="#{e(root["id"])}">{self.lk(root.get("title"), root)}</a> '
                     f'<span class="sid">{e(root["id"])}</span> <span class="muted">{e(view_state(root))}</span></p>')
        ready_acts = [a for a in self.manifest.values() if a.get("state", "proposed") in ("proposed", "approved")]
        solo = sum(1 for b in self.batches() if len(b["items"]) == 1)
        in_batch = sum(len(b["items"]) for b in self.batches() if len(b["items"]) > 1)
        parked_ok = len(by_block.get("parked", []))
        unk = len({str(u).split(":", 1)[0] for u in self.facts.get("unknown") or []})
        h.append('<div class="tiles">'
                 f'<a class="tile{" hot" if needs_n else ""}" href="#cl-needs"><div class="v">{needs_n}</div><div class="l">Need you</div>'
                 f'<div class="s">{len(big)} big · {len(small)} smaller · {len(appr)} batch</div></a>'
                 + (f'<a class="tile{" warm" if ready_acts else ""}" href="#cl-else"><div class="v">{len(ready_acts)}</div><div class="l">Actions ready</div>'
                    f'<div class="s">{in_batch} in a batch · {solo} one by one</div></a>' if self.manifest else
                    f'<a class="tile{" warm" if opn else ""}" href="#cl-needs"><div class="v">{len(opn)}</div><div class="l">Open threads</div><div class="s">not judged yet</div></a>')
                 + f'<a class="tile" href="#cl-else"><div class="v">{parked_ok}</div><div class="l">Parked with a home</div><div class="s">an owner accepted each one</div></a>'
                 + f'<a class="tile" href="#cl-coverage"><div class="v">{unk if self.facts else "?"}</div><div class="l">Unread sources</div>'
                 f'<div class="s">{"UNKNOWN, see How we searched" if self.facts else "not searched yet"}</div></a></div>')
        counts = {}
        for t in ts:
            if t is root:
                continue
            counts[view_state(t)] = counts.get(view_state(t), 0) + 1
        order = [("needs_you", "need you", "m-needs"), ("parked_unaccepted", "home not accepted", "m-needs"), ("open", "open", "m-open"),
                 ("ready", "ready", "m-act"), ("parked", "homed", "m-home"), ("resolved", "resolved", "m-done"), ("dropped", "dropped", "m-drop")]
        label = ", ".join(f"{counts.get(k, 0)} {w}" for k, w, _ in order)
        h.append(f'<div class="mix" role="img" aria-label="{sum(counts.values())} threads: {e(label)}">' + "".join(
            f'<span style="flex:{counts[k]}" class="{c}">{counts[k]} {w}</span>' for k, w, c in order if counts.get(k)) + "</div>")
        h.append('<p class="legend small"><span><i class="glyph g-needs">●</i> needs you</span><span><i class="glyph g-open">◎</i> open thread</span>'
                 '<span><i class="glyph g-act">◐</i> ready, the agent acts after approval</span><span><i class="glyph g-home">⤴</i> parked, home accepted</span>'
                 '<span><i class="glyph g-done">✓</i> resolved</span><span><i class="glyph g-drop">⊘</i> dropped</span><span><i class="why drift">⚠ changed</i> changed since captured</span></p>')

        # Needs you
        first_big = big[0]["id"] if big else None
        nh = [f'<section id="cl-needs"><div class="sh"><h2>Needs you</h2><span class="n">{needs_n} · click a row to open it</span></div>']
        if phase == 0 and opn:
            nh.append(f'<h3 class="grp">Open threads <span class="n">{len(opn)} · oldest first</span></h3><div class="stack">{"".join(self.card(t) for t in opn)}</div>')
        if big:
            nh.append(f'<h3 class="grp">Big misses <span class="n">{len(big)} · live risk first</span></h3><div class="stack">'
                      + "".join(self.card(t, open_=t["id"] == first_big) for t in big) + "</div>")
        if appr:
            nh.append(f'<h3 class="grp">Approval <span class="n">{len(appr)}</span></h3><div class="stack">{"".join(self.card(t) for t in appr)}</div>')
        if small:
            nh.append(f'<h3 class="grp">Smaller calls <span class="n">{len(small)} · nothing live at risk</span></h3><div class="stack">{"".join(self.card(t) for t in small)}</div>')
        if phase != 0 and opn:
            nh.append(f'<h3 class="grp">Open threads, not judged yet <span class="n">{len(opn)} · oldest first · each needs a bucket before the close</span></h3>'
                      f'<div class="stack">{"".join(self.card(t) for t in opn)}</div>')
        if not needs_n and not opn:
            nh.append('<p class="good-note">Nothing needs you to close this mission.</p>')
        nh.append("</section>")
        h += nh

        # Everything else
        def xrefs(lst):
            return f'<ul class="xref">{"".join(self.line(t, self.where.get(t["id"])) for t in lst)}</ul>' if lst else ""

        needs_all = big + small
        eh = ['<section id="cl-else"><div class="sh"><h2>Everything else</h2><span class="n">collapsed · click to explore</span></div>']
        for key, title, sub in (("ready", "Ready to close with evidence", "the agent closes these after you approve"),
                                ("replaced", "Replaced or obsolete", "close with a pointer to what replaced them")):
            lst = by_block.get(key, [])
            if lst:
                eh.append(self.bucket(title, len(lst), sub, "".join(self.card(t) for t in lst)))
        fixes = by_block.get("fixes", [])
        fx_up = [t for t in needs_all if (t.get("closeout") or {}).get("bucket") == "FALSE-PREMISE"]
        if fixes or fx_up:
            eh.append(self.bucket("Record fixes", len(fixes) + len(fx_up), "text that is no longer true" + (f" · {len(fx_up)} more in Needs you" if fx_up else ""),
                                  "".join(self.card(t) for t in fixes) + xrefs(fx_up)))
        parked = by_block.get("parked", [])
        if parked:
            eh.append(self.bucket("Parked with an accepted home", len(parked), "nothing to do here: an owner took them", "".join(self.card(t) for t in parked)))
        homeless = [t for t in needs_all if "uncovered_obligation" in (t.get("reasons") or []) or view_state(t) == "parked_unaccepted"]
        if homeless:
            eh.append(self.bucket("Still needed, home not accepted", len(homeless), f"all {len(homeless)} are in Needs you", xrefs(homeless)))
        for key, title, sub in (("resolved", "Resolved", "done, with evidence or an answer"), ("dropped", "Dropped", "abandoned, with a reason and who dropped it")):
            lst = sorted(by_block.get(key, []), key=lambda t: _num(t.get("id")))
            if lst:
                eh.append(self.bucket(title, len(lst), sub, "".join(self.card(t) for t in lst)))
        if root:
            eh.append(self.bucket("The big intent", 1, "the mission destination as a thread; resolve it at close", self.card(root)))
        eh += [self.coverage(), self.lens(), self.capture()]
        if gerr:
            eh.append(self.bucket("Close gate", len(gerr), "CLOSED: the conditions that keep the mission open",
                                  '<ul class="xref">' + "".join(f"<li>{self.lk(x)}</li>" for x in gerr) + "</ul>", "cl-gate"))
        else:
            eh.append(f'<div class="gate-ok">Ready to close. {self.cmd_block("Close the mission", "/mission close " + self.slug)}</div>' if ts else "")
        eh.append("</section>")
        h += eh
        summary = {"needs": needs_n, "open": len(opn), "phase": PHASES[phase], "threads": len(ts), "live_risk": live_risk,
                   "gate": "open" if not gerr else "closed", "gate_conditions": len(gerr),
                   "counter": needs_n + (len(opn) if phase == 0 else 0)}
        return "\n".join(h), summary


def render_closure(m: dict, d: pathlib.Path | None) -> tuple[str, dict]:
    return Closure(m, d).render()


def closure_summary_line(s: dict) -> str:
    return f"Closure: {s['phase']}, {s['needs']} need you, {s['open']} open, gate {s['gate']}"


if __name__ == "__main__":
    import sys
    from mission_lib import load, mission_dir
    d = mission_dir(sys.argv[1])
    html, s = render_closure(load(d), d)
    print(closure_summary_line(s))
    print(f"generated {now_utc()}")
