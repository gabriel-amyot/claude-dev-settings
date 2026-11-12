"""Build a read-only, script-free view from a consistent SQLite snapshot."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import fcntl
import os
from pathlib import Path
import tempfile
import uuid

from store import utc_now


STYLE = """+:root{color-scheme:light;--ink:#182b3c;--muted:#526575;--line:#dbe2e8;--blue:#164b72}
*{box-sizing:border-box}body{margin:0;background:#f4f6f8;color:var(--ink);font:16px/1.55 system-ui,sans-serif}
header{background:#142e43;color:white;padding:2.5rem max(5%,calc((100% - 1300px)/2))}header p{max-width:900px;color:#d5e2ec}
main{max-width:1300px;margin:auto;padding:2rem 2rem 4rem}h1{font-size:2rem;margin:0}h2{margin-top:2.5rem}h3{margin-top:1.6rem}
nav{display:flex;gap:1rem;flex-wrap:wrap;margin-top:1.5rem}nav a{color:#d7edf9}a{color:var(--blue);overflow-wrap:anywhere}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem}.card{background:white;border:1px solid var(--line);border-radius:9px;padding:1.1rem}.number{display:block;font-size:1.9rem;font-weight:700}
.muted,small{color:var(--muted)}.notice{background:#fff4d6;padding:1rem 1.2rem;border-left:4px solid #bc8b29;border-radius:4px}.good{color:#1c6748}.bad{color:#9b3131}
.table-wrap{overflow:auto;background:white;border:1px solid var(--line);border-radius:8px}table{border-collapse:collapse;width:100%;font-size:.91rem}th,td{text-align:left;vertical-align:top;padding:.8rem;border-bottom:1px solid var(--line)}th{background:#eaf0f5;white-space:nowrap}td p{margin:0}
code{font-size:.88em;background:#eaf0f5;padding:.1rem .25rem;border-radius:3px;overflow-wrap:anywhere}.pill{display:inline-block;padding:.1rem .45rem;background:#eaf0f5;border-radius:10px;font-size:.8rem;margin:.1rem}
details{background:white;border:1px solid var(--line);padding:.7rem 1rem;margin:.5rem 0;border-radius:6px}summary{cursor:pointer;font-weight:600}.meta{display:grid;grid-template-columns:150px 1fr;gap:.4rem 1rem}.meta dt{color:var(--muted)}.meta dd{margin:0;overflow-wrap:anywhere}footer{margin-top:3rem;font-size:.85rem;color:var(--muted)}
@media(max-width:650px){main{padding:1rem}.meta{grid-template-columns:1fr}.meta dd{margin-bottom:.6rem}header{padding:1.5rem}th,td{padding:.6rem}}
"""


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def page_name(capability_id):
    return hashlib.sha256(capability_id.encode()).hexdigest()[:24] + ".html"


def source_link(path, label="Evidence"):
    if not path:
        return '<span class="muted">No source recorded</span>'
    try:
        raw, _, fragment = str(path).partition("#")
        target = Path(raw).expanduser()
        if not target.is_absolute():
            return esc(path)
        missing = " (missing)" if not target.exists() else ""
        # A line reference is kept as a label; local text files need no viewer script.
        suffix = " · " + fragment if fragment else ""
        return f'<a href="{esc(target.as_uri())}">{esc(label + missing + suffix)}</a>'
    except (ValueError, OSError):
        return esc(path)


def table(headers, rows):
    if not rows:
        return '<p class="muted">No records available for this view.</p>'
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def document(title, subtitle, content, nav=""):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{STYLE}</style></head>
<body><header><h1>{esc(title)}</h1><p>{esc(subtitle)}</p><nav>{nav}</nav></header><main>{content}
<footer>Generated from the shared harness database. Original reports remain authoritative. This view cannot edit data.</footer></main></body></html>'''


def newest_eval_status(row, capability):
    verdict = row["outcome"].upper()
    if "SIMULATED" in (row.get("summary") or ""):
        verdict = "SIMULATION · " + verdict
    if not row.get("revision"):
        return verdict + " · tested revision unknown"
    if row["revision"] != capability["revision"]:
        return verdict + " · different revision"
    return verdict + " · current source revision"


def instant(value):
    parsed=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed.astimezone(dt.timezone.utc)


def render(store, view_path):
    """Serialize snapshot capture and publication so an older writer cannot win."""
    view=Path(view_path)
    view.mkdir(parents=True,exist_ok=True)
    with (view/".render.lock").open("a") as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        try:
            return _render_locked(store,view)
        finally:
            fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def _render_locked(store, view_path):
    """Publish all detail pages first and atomically replace the overview last."""
    view = Path(view_path)
    build_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    snapshot = view / "snapshots" / build_id
    details_dir = snapshot / "skills"
    details_dir.mkdir(parents=True)
    generated = utc_now()
    # Query every table under one read transaction, then release the database.
    store.conn.execute("BEGIN")
    try:
        data = {name: store.rows(f"SELECT * FROM {name}") for name in (
            "capabilities", "availability", "dependencies", "usage_events", "frictions",
            "eval_suites", "eval_runs", "outcomes", "decisions", "coverage", "artifacts")}
    finally:
        store.conn.rollback()
    caps = sorted(data["capabilities"], key=lambda c: (c["kind"], c["name"].lower(), c["id"]))
    by_id = {c["id"]: c for c in caps}
    now=dt.datetime.now(dt.timezone.utc)
    since=now-dt.timedelta(days=30)
    def related(domain, cap_id):
        return [r for r in data[domain] if r.get("capability_id") == cap_id]
    def metrics(cap_id,days=30):
        events = related("usage_events", cap_id)
        cutoff=now-dt.timedelta(days=days)
        return {signal: sum(e.get("count", 1) for e in events if e["signal"] == signal and cutoff <= instant(e["occurred_at"]) <= now)
                for signal in ("invoked", "loaded")}
    def cap_link(cap_id, prefix=""):
        cap = by_id.get(cap_id)
        return (f'<a href="{prefix}skills/{page_name(cap_id)}">{esc(cap["name"])}</a>' if cap else esc(cap_id))
    def evidence(row):
        return source_link(row.get("source_path") or row.get("evidence"), "Original artifact")

    for cap in caps:
        cid = cap["id"]
        m = metrics(cid)
        fields = [("Kind", esc(cap["kind"])), ("Inventory state", "Present" if cap["active"] else "Source missing from latest inventory"), ("Source", source_link(cap["source_path"], cap["source_path"])),
                  ("Source fingerprint", f'<code>{esc(cap["revision"])}</code>'), ("Last discovered", esc(cap["discovered_at"]))]
        content = '<dl class="meta">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k,v in fields) + "</dl>"
        content += f'<p>{esc(cap["description"])}</p><p class="notice">30 days: {m["invoked"]} observed invocation(s), {m["loaded"]} observed instruction load(s). These are separate signals. Missing collection coverage is unknown usage.</p>'
        content += table(["Observed signal","7 days","30 days","90 days"],[[esc(signal),*[str(metrics(cid,days)[signal]) for days in (7,30,90)]] for signal in ("invoked","loaded")])
        content += "<h2>Availability</h2>" + table(["Host", "Role", "Status", "Observed", "Evidence"], [
            [esc(r[k]) for k in ("host", "role", "status", "observed_at")] + [evidence(r)] for r in related("availability",cid)])
        content += "<h2>Decisions and proposals</h2>" + table(["Date", "Action", "State", "Authority", "Rationale"], [
            [esc(r[k]) for k in ("occurred_at", "action", "status", "authority", "rationale")] for r in sorted(related("decisions",cid),key=lambda r:instant(r["occurred_at"]),reverse=True)])
        evaluations = sorted(related("eval_runs",cid),key=lambda r:instant(r["occurred_at"]),reverse=True)
        content += "<h2>Registered eval suites</h2>"+table(["Suite","Layer","Last recorded green","Registry"],[
            [esc(r["suite_id"]),esc(r["layer"]),esc(r.get("last_green") or "Unknown"),evidence(r)] for r in related("eval_suites",cid)])
        content += "<h2>Eval history</h2><p class=muted>Results retain their original revision and date. A historical pass does not validate the current skill.</p>" + table(["Date", "Suite", "Result", "Host", "Evidence"], [
            [esc(r["occurred_at"]),esc(r["suite_id"]),esc(newest_eval_status(r,cap)),esc(r["host"]),evidence(r)] for r in evaluations])
        owned_artifacts=[a for a in data["artifacts"] if str(a["source_path"]).startswith(str(Path(cap["source_path"]).parent)+os.sep)]
        content += "<h2>Related reports and definitions</h2>"+table(["Kind","Observed","Source"],[
            [esc(a["kind"]),esc(a["observed_at"]),source_link(a["source_path"],a["source_path"])] for a in owned_artifacts])
        content += "<h2>Friction history</h2>" + table(["Date", "Host / role", "Issue", "Impact", "State", "Evidence"], [
            [esc(r["occurred_at"]),esc(r["host"]+" / "+r["role"]),esc(r["summary"]),esc(r["impact"]),esc(r["status"]),evidence(r)] for r in sorted(related("frictions",cid),key=lambda r:instant(r["occurred_at"]),reverse=True)])
        content += "<h2>Observed activity</h2>" + table(["Date", "Host / role", "Signal", "Session", "Evidence"], [
            [esc(r["occurred_at"]),esc(r["host"]+" / "+r["role"]),esc(r["signal"]),esc(r["session_id"]),evidence(r)] for r in sorted(related("usage_events",cid),key=lambda r:instant(r["occurred_at"]),reverse=True)[:100]])
        content += "<h2>Workflow outcomes</h2>" + table(["Date", "Status", "Summary", "Evidence"], [
            [esc(r["occurred_at"]),esc(r["status"]),esc(r.get("summary")),evidence(r)] for r in sorted(related("outcomes",cid),key=lambda r:instant(r["occurred_at"]),reverse=True)])
        content += "<h2>Static references and dependencies</h2><p class=muted>A reference means an instruction mentions a capability. It does not prove execution.</p>" + table(["Relationship", "Target", "Evidence"], [
            [esc(r["relationship"]),cap_link(r["target_id"],"../"),evidence(r)] for r in related("dependencies",cid)])
        content += f'<p class="muted">Snapshot generated {esc(generated)}.</p>'
        (details_dir/page_name(cid)).write_text(document(cap["name"],"Capability details, observed activity and original evidence.",content,'<a href="../index.html">Snapshot overview</a><a href="../../../index.html">Latest overview</a>'),encoding="utf-8")

    invoked = sum(e.get("count",1) for e in data["usage_events"] if e["signal"] == "invoked" and since<=instant(e["occurred_at"])<=now)
    loaded = sum(e.get("count",1) for e in data["usage_events"] if e["signal"] == "loaded" and since<=instant(e["occurred_at"])<=now)
    resolved_ids = {f.get("resolves_id") for f in data["frictions"] if f["status"]=="resolved"}
    opened = [f for f in data["frictions"] if f["status"]=="open" and f["id"] not in resolved_ids]
    cards=[("Capabilities",len(caps)),("Invocations · 30d",invoked),("Instruction loads · 30d",loaded),("Open frictions",len(opened)),("Registered eval suites",len(data["eval_suites"])),("Eval results",len(data["eval_runs"]))]
    content='<div class="cards">'+"".join(f'<div class="card"><span class="number">{n}</span>{esc(label)}</div>' for label,n in cards)+"</div>"
    content += f'<p class="muted">Generated {esc(generated)}. Open a skill for its history and evidence. Use your browser’s Find command to search this catalog.</p>'
    content += '<p class="notice">Counts show observed evidence within collection coverage. Instruction loads, invocations, static references and historical estimates are kept separate. No observed activity does not prove non-use.</p>'
    content += '<h2 id="coverage">Collection coverage</h2>' + table(["Source", "Host", "Scope", "Window", "Status", "Last checked", "Detail"], [
        [esc(r["source"]),esc(r["host"]),esc(r["scope"]),esc((r.get("since") or "unknown")+" → "+(r.get("until") or "unknown")),esc(r["status"]),esc(r["observed_at"]),esc(r["detail"])] for r in sorted(data["coverage"],key=lambda r:r["source"])])
    catalog_rows=[]
    for c in caps:
        m=metrics(c["id"]);hosts=sorted({a["host"]+": "+a["status"] for a in related("availability",c["id"])})
        evals=sorted(related("eval_runs",c["id"]),key=lambda r:instant(r["occurred_at"]),reverse=True)
        decisions=sorted(related("decisions",c["id"]),key=lambda r:instant(r["occurred_at"]),reverse=True)
        catalog_rows.append([cap_link(c["id"]),esc(c["kind"]+(" · source missing" if not c["active"] else "")),esc(c["description"][:180]),"<br>".join(esc(h) for h in hosts) or "Unknown",str(m["invoked"]),str(m["loaded"]),esc(newest_eval_status(evals[0],c) if evals else "No result recorded"),esc(decisions[0]["action"]+" ("+decisions[0]["status"]+")" if decisions else "No decision")])
    content += '<h2 id="catalog">Capability catalog</h2>'+table(["Capability", "Kind", "Purpose", "Availability", "Invoked · 30d", "Loaded · 30d", "Latest eval", "Latest decision"],catalog_rows)
    content += '<h2 id="friction">Unresolved friction</h2>'+table(["Capability","Date","Issue","Impact","Evidence"],[
        [cap_link(r["capability_id"]),esc(r["occurred_at"]),esc(r["summary"]),esc(r["impact"]),evidence(r)] for r in sorted(opened,key=lambda r:instant(r["occurred_at"]),reverse=True)])
    content += '<h2 id="evals">Eval suite registry</h2><p class="muted">Last recorded green is historical metadata. Suite registration does not prove a current passing result.</p>'+table(["Suite","Capability","Layer","Last recorded green","Registry"],[
        [esc(r["suite_id"]),cap_link(r["capability_id"]),esc(r["layer"]),esc(r.get("last_green") or "Unknown"),evidence(r)] for r in sorted(data["eval_suites"],key=lambda r:r["suite_id"])])
    content += '<h2 id="artifacts">Reports and artifacts</h2>'+table(["Kind","Observed","Source","Summary"],[
        [esc(r["kind"]),esc(r["observed_at"]),source_link(r["source_path"],r["source_path"]),esc(r.get("summary"))] for r in sorted(data["artifacts"],key=lambda r:instant(r["observed_at"]),reverse=True)[:150]])
    nav='<a href="#coverage">Coverage</a><a href="#catalog">Catalog</a><a href="#friction">Friction</a><a href="#evals">Evals</a><a href="#artifacts">Evidence</a>'
    snapshot_html=document("Harness observatory","Skills, agents, usage and quality. One view over the original evidence.",content,nav)
    (snapshot/"index.html").write_text(snapshot_html,encoding="utf-8")
    # Identical content, links anchored to the immutable detail snapshot.
    overview=snapshot_html.replace('href="skills/',f'href="snapshots/{build_id}/skills/')
    with tempfile.NamedTemporaryFile("w",dir=view,prefix=".index-",suffix=".tmp",encoding="utf-8",delete=False) as out:
        out.write(overview);temp_path=out.name
    os.replace(temp_path,view/"index.html")
    return {"index":str(view/"index.html"),"snapshot":str(snapshot),"capabilities":len(caps),"generated_at":generated}
