#!/usr/bin/env python3
"""P5 of the skill-proposal triage: render the review page (one self-contained HTML file).

Reads whatever exists in the run directory (each input is optional, so the page also works as
a live progress view while the passes run):
  STATE.json, inventory.tsv or batches/*.txt (or flat batch-* files), groups.json (or
  codex/groups.json), results/*.json, codex/out-batch-*.json, codex/out-groups.json,
  codex/out-overall.md, final-verdicts.json
No external assets: works offline from file://. Decisions persist in localStorage and export to
decisions.json (download plus clipboard). Save that file into the run directory.

Usage: render.py --run-dir DIR [--out FILE] [--proposals-dir DIR] [--budget N] [--installed N]
"""
import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage_common as tc  # noqa: E402
from final_verdicts import merge  # noqa: E402

e = lambda s: html.escape(str(s if s is not None else ""), quote=True)


# --------------------------------------------------------------------------- markdown
def inline_md(text):
    t = e(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<i>\1</i>", t)
    return t


def md_to_html(md):
    """Small Markdown subset: headings, ordered and unordered lists, tables, paragraphs."""
    out, para, list_tag, table = [], [], None, []

    def flush():
        nonlocal para, list_tag, table
        if para:
            out.append("<p>" + inline_md(" ".join(para)) + "</p>")
            para = []
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None
        if table:
            rows = [r for r in table if not re.fullmatch(r"[\s|:\-]+", r)]
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            if cells:
                head = "".join(f"<th>{inline_md(c)}</th>" for c in cells[0])
                body = "".join("<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in r) + "</tr>" for r in cells[1:])
                out.append(f"<table class=md><tr>{head}</tr>{body}</table>")
            table = []

    for raw in md.splitlines():
        line = raw.rstrip()
        h = re.match(r"^(#{1,6})\s+(.*)", line)
        ol = re.match(r"^\s*\d+[.)]\s+(.*)", line)
        ul = re.match(r"^\s*[-*+]\s+(.*)", line)
        if not line.strip():
            flush()
        elif line.lstrip().startswith("|"):
            if para or list_tag:
                flush()
            table.append(line)
        elif h:
            flush()
            level = min(len(h.group(1)) + 2, 6)
            out.append(f"<h{level}>{inline_md(h.group(2))}</h{level}>")
        elif ol or ul:
            tag = "ol" if ol else "ul"
            if para or table or (list_tag and list_tag != tag):
                flush()
            if not list_tag:
                out.append(f"<{tag}>")
                list_tag = tag
            out.append("<li>" + inline_md((ol or ul).group(1)) + "</li>")
        elif list_tag and raw.startswith(("  ", "\t")):
            out[-1] = out[-1][:-5] + " " + inline_md(line.strip()) + "</li>"
        else:
            if list_tag or table:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(out)


def md_section(md, pattern):
    """Return the body of the first heading section whose title matches pattern."""
    lines, grab, level, body = md.splitlines(), False, 0, []
    for ln in lines:
        h = re.match(r"^(#{1,6})\s+(.*)", ln)
        if h and grab and len(h.group(1)) <= level:
            break
        if grab:
            body.append(ln)
        elif h and re.search(pattern, h.group(2), re.I):
            grab, level = True, len(h.group(1))
    return "\n".join(body).strip()


# --------------------------------------------------------------------------- data
def inventory(run, claude, codex, final):
    files = []
    inv = os.path.join(run, "inventory.tsv")
    if os.path.exists(inv):
        with open(inv) as fh:
            files = [ln.split("\t")[2] for ln in fh.read().splitlines()[1:] if ln.count("\t") >= 2]
    for fs in tc.batch_files(run).values():
        files += fs
    files += list(claude) + list(codex) + list(final)
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return sorted(out, reverse=True)


def chip(verdict, extra=""):
    if not verdict:
        return '<span class="chip v-PENDING">pending</span>'
    return f'<span class="chip v-{e(tc.verdict_class(verdict))}{extra}">{e(verdict)}</span>'


def build_rows(run, proposals, files, claude, codex, final, groups, moves):
    group_of = {n: g for g, ns in groups.items() for n in (ns if isinstance(ns, list) else str(ns).split())}
    rows = []
    for fn in files:
        c, x, f = claude.get(fn, {}), codex.get(fn, {}), final.get(fn, {})
        name = c.get("name") or f.get("name") or tc.proposal_name(fn)
        group = group_of.get(name, "Ungrouped")
        fverdict = f.get("verdict") or x.get("codex_verdict") or c.get("verdict")
        scores = [s for s in (c.get("score"), x.get("codex_score")) if isinstance(s, (int, float))]
        fscore = f.get("final_score")
        if fscore is None and scores:
            fscore = round(sum(scores) / len(scores))
        disagree = bool(x) and bool(c) and (x.get("agree") is False or
                                            tc.verdict_class(x.get("codex_verdict")) != tc.verdict_class(c.get("verdict")))
        in_inbox = os.path.exists(os.path.join(proposals, fn))
        path = os.path.join(proposals, fn) if in_inbox else os.path.join(proposals, "archive", fn)
        hi, ev = c.get("harness_impact", {}) or {}, c.get("evidence", {}) or {}
        target = hi.get("target") or ""
        if not target and tc.verdict_class(fverdict) == "UPDATE" and ":" in (fverdict or ""):
            target = fverdict.split(":", 1)[1].strip() + "/SKILL.md"
        verdict_opts = []
        for v in ["BUILD", c.get("verdict"), x.get("codex_verdict"), "SOP", "ARCHIVE"]:
            if v and v not in verdict_opts:
                verdict_opts.append(v)
        search = " ".join([name, c.get("one_line", ""), group, str(c.get("verdict")), str(x.get("codex_verdict")),
                           " ".join(c.get("overlap", []) or [])]).lower()
        ease = c.get("eval_ease")
        examples = "".join(f"<li><code>{e(str(i.get('file', ''))[-70:])}</code> {e(i.get('quote', ''))}</li>"
                           for i in ev.get("examples", []) or [])
        findings = "".join(f"<li><b>{e(i.get('label', ''))}</b> {e(i.get('text', ''))}</li>"
                           for i in x.get("findings", []) or [])
        move = moves.get(name)
        move_html = (f'<div class="sub">Codex: move to <b>{e(move.get("to"))}</b>. {e(move.get("why"))}</div>'
                     if move else "")
        status = "" if in_inbox else '<span class="tag">archived</span>'
        agree_mark = ("" if not x else ('<span class="ok">agree</span>' if not disagree
                                         else '<span class="bad">disagree</span>'))
        claude_cell = (f"<b>{e(c.get('score', ''))}</b> {chip(c.get('verdict'))}"
                       f"<div class=sub>{e(c.get('invocation', ''))}</div>") if c else '<span class="sub">pending</span>'
        codex_cell = (f"<b>{e(x.get('codex_score', ''))}</b> {chip(x.get('codex_verdict'))} {agree_mark}"
                      f"<div class=sub>{e(x.get('codex_invocation', ''))}</div>") if x else '<span class="sub">pending</span>'
        detail = f"""<div class="grid">
<div><h4>Claude first pass</h4><p><b>Against:</b> {e(c.get('adversarial_case', ''))}</p>
<p><b>Overlap:</b> {e(', '.join(c.get('overlap', []) or []))}</p>
<p><b>Why this score:</b> {e(c.get('rationale', ''))}</p>
<p><b>Invocation:</b> {e(c.get('invocation', ''))}. {e(c.get('invocation_why', ''))}</p>
<p><b>Eval idea:</b> {e(c.get('eval_idea', ''))}</p></div>
<div><h4>Evidence</h4><p>{e(ev.get('sessions_before', '?'))} sessions before, {e(ev.get('sessions_after', '?'))} after.
Keywords: {e(', '.join(ev.get('keywords', []) or []))}</p><ul>{examples}</ul>
<h4>Harness impact</h4><p>{e(hi.get('slot', ''))}. {e(hi.get('summary', ''))}</p>
<p><b>Collisions:</b> {e(', '.join(hi.get('collisions', []) or []))}</p></div>
<div><h4>Codex second pass</h4><p>{e(x.get('summary', '')) or 'pending'}</p><ul>{findings}</ul></div></div>"""
        rows.append(f"""<tbody class="item" data-file="{e(fn)}" data-final="{fscore if fscore is not None else -1}"
 data-date="{e(fn[:10])}" data-ease="{ease if isinstance(ease, int) else 9}" data-verdict="{e(tc.verdict_class(fverdict))}"
 data-group="{e(group)}" data-disagree="{1 if disagree else 0}" data-search="{e(search)}">
<tr class="main">
<td class="num">{'' if fscore is None else fscore}</td>
<td><a href="file://{e(path)}">{e(name)}</a> {status}<div class="sub">{e(fn[:10])} · {e(group)}</div>
<div class="sub">{e(c.get('one_line', ''))}</div>{move_html}</td>
<td>{chip(fverdict, ' big')}<div class="sub">{e(f.get('source', 'codex' if x else 'claude'))}</div></td>
<td>{claude_cell}</td><td>{codex_cell}</td>
<td class="num">{e(ease if ease is not None else '')}</td>
<td><span class="sub">{e(hi.get('slot', ''))}</span><div class="sub">{e(target)}</div></td>
<td class="decide"><select class="action" aria-label="decision for {e(name)}">
<option value="accept">Accept</option><option value="override">Override verdict</option><option value="hold">Hold</option></select>
<select class="override" hidden aria-label="override verdict">{''.join(f'<option>{e(v)}</option>' for v in verdict_opts)}</select>
<input class="note" type="text" placeholder="note" aria-label="note">
<button class="more" type="button">Details</button></td></tr>
<tr class="detail" hidden><td colspan="8">{detail}</td></tr></tbody>""")
    return rows


# --------------------------------------------------------------------------- page
CSS = """
:root{--bg:#fff;--fg:#1d1f23;--mut:#5d6470;--line:#e3e5e8;--card:#f6f7f9;--head:#fbfbfc;--acc:#3767d6;
--build:#e3f4e5;--build-b:#2e8540;--update:#e5edfb;--update-b:#3767d6;--merge:#fbf3dc;--merge-b:#a77b00;
--sop:#f0e9fa;--sop-b:#7a4bc2;--archive:#fbe6e6;--archive-b:#b3261e;--hold:#eceff1;--hold-b:#5d6470}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--fg:#e7e9ec;--mut:#9aa1ab;--line:#2c3036;--card:#1f2227;
--head:#1b1e22;--acc:#7ea2f2;--build:#1d3324;--build-b:#7fd38f;--update:#1d2940;--update-b:#8fb0f5;--merge:#3a3016;
--merge-b:#e3c25c;--sop:#2d2340;--sop-b:#c3a3f2;--archive:#3d1f1f;--archive-b:#f19a93;--hold:#26292e;--hold-b:#a3aab4}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--head);border-bottom:1px solid var(--line);padding:10px 16px}
h1{font-size:17px;margin:0 0 8px}main{padding:12px 16px}a{color:var(--acc)}.decide select[hidden]{display:none}
.cards{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 10px;min-width:92px}
.card b{display:block;font-size:17px}.card span{color:var(--mut);font-size:11px}
.progress{height:8px;background:var(--card);border:1px solid var(--line);border-radius:4px;overflow:hidden;margin:4px 0 8px}
.progress div{height:100%;background:var(--acc)}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
input,select,button{font:inherit;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:3px 6px}
button{cursor:pointer}button.primary{background:var(--acc);color:#fff;border-color:var(--acc)}
#q{min-width:220px}table{border-collapse:collapse;width:100%}
th{text-align:left;font-weight:600;color:var(--mut);border-bottom:2px solid var(--line);padding:6px}
td{vertical-align:top;border-bottom:1px solid var(--line);padding:6px}td.num{text-align:right;font-weight:600}
.sub{color:var(--mut);font-size:12px}.tag{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 4px;color:var(--mut)}
.chip{display:inline-block;border-radius:10px;padding:0 7px;font-size:12px;font-weight:600;border:1px solid}
.chip.big{font-size:13px;padding:1px 9px}
.v-BUILD{background:var(--build);color:var(--build-b)}.v-UPDATE{background:var(--update);color:var(--update-b)}
.v-MERGE{background:var(--merge);color:var(--merge-b)}.v-SOP{background:var(--sop);color:var(--sop-b)}
.v-ARCHIVE{background:var(--archive);color:var(--archive-b)}.v-HOLD,.v-PENDING{background:var(--hold);color:var(--hold-b)}
.ok{color:var(--build-b);font-size:12px}.bad{color:var(--archive-b);font-size:12px;font-weight:600}
.decide{min-width:190px}.decide select,.decide input{display:block;width:100%;margin-bottom:3px}
tbody.item.changed .main{box-shadow:inset 3px 0 0 var(--acc)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.grid h4{margin:4px 0}
details.panel{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin-bottom:10px}
details.panel summary{cursor:pointer;font-weight:600}table.md td,table.md th{border:1px solid var(--line)}
#toast{position:fixed;bottom:16px;right:16px;background:var(--fg);color:var(--bg);padding:8px 12px;border-radius:6px;display:none;max-width:420px}
#exportbox{width:100%;height:120px;display:none;margin-top:6px}
"""

JS = """
const KEY='skill-triage:'+document.body.dataset.run;
const items=[...document.querySelectorAll('tbody.item')];
const load=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch(_){return {}}};
let store=load();
function apply(tb){const d=store[tb.dataset.file]||{};const a=tb.querySelector('.action'),o=tb.querySelector('.override'),n=tb.querySelector('.note');
 a.value=d.action||'accept';if(d.verdict)o.value=d.verdict;n.value=d.note||'';o.hidden=a.value!=='override';
 tb.classList.toggle('changed',a.value!=='accept'||!!n.value)}
function save(tb){const a=tb.querySelector('.action').value,o=tb.querySelector('.override'),n=tb.querySelector('.note').value;
 o.hidden=a!=='override';store[tb.dataset.file]={action:a,verdict:a==='override'?o.value:null,note:n};
 localStorage.setItem(KEY,JSON.stringify(store));tb.classList.toggle('changed',a!=='accept'||!!n);count()}
items.forEach(tb=>{apply(tb);tb.querySelectorAll('.action,.override,.note').forEach(el=>el.addEventListener('input',()=>save(tb)));
 tb.querySelector('.action').addEventListener('change',()=>save(tb));
 tb.querySelector('.more').onclick=()=>{const d=tb.querySelector('tr.detail');d.hidden=!d.hidden}});
function count(){const n=Object.values(store).filter(d=>d.action!=='accept'||d.note).length;
 document.getElementById('nchanged').textContent=n+' changed'}
function flt(){const q=document.getElementById('q').value.toLowerCase().trim(),v=document.getElementById('vf').value,
 g=document.getElementById('gf').value,dis=document.getElementById('dis').checked;let shown=0;
 items.forEach(tb=>{const ok=(!q||tb.dataset.search.includes(q))&&(!v||tb.dataset.verdict===v)&&(!g||tb.dataset.group===g)&&(!dis||tb.dataset.disagree==='1');
  tb.hidden=!ok;if(ok)shown++});document.getElementById('nshown').textContent=shown+' shown'}
function srt(){const k=document.getElementById('sort').value,t=document.getElementById('t');
 const val={final:tb=>-parseFloat(tb.dataset.final),date:tb=>tb.dataset.date,ease:tb=>parseFloat(tb.dataset.ease)};
 const f=val[k];const s=[...items].sort((a,b)=>{let x=f(a),y=f(b);if(k==='date'){return x<y?1:x>y?-1:0}return x-y});
 s.forEach(tb=>t.appendChild(tb))}
['q','vf','gf','dis'].forEach(id=>document.getElementById(id).addEventListener('input',flt));
document.getElementById('sort').addEventListener('change',srt);
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.style.display='block';setTimeout(()=>t.style.display='none',6000)}
document.getElementById('export').onclick=()=>{const out={run:document.body.dataset.run,exported:new Date().toISOString(),decisions:{}};
 items.forEach(tb=>{const d=store[tb.dataset.file]||{action:'accept'};out.decisions[tb.dataset.file]={action:d.action||'accept',
  verdict:d.action==='override'?d.verdict:null,note:d.note||'',merged_verdict:tb.querySelector('.chip.big').textContent}});
 const txt=JSON.stringify(out,null,1);const a=document.createElement('a');
 a.href=URL.createObjectURL(new Blob([txt],{type:'application/json'}));a.download='decisions.json';a.click();
 const box=document.getElementById('exportbox');box.value=txt;
 const done=m=>toast(m+' Save decisions.json into '+document.body.dataset.run+' or paste it into the chat.');
 if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(txt).then(()=>done('Downloaded and copied.'),
  ()=>{box.style.display='block';box.select();done('Downloaded. Clipboard blocked: copy from the box.')})}
 else{box.style.display='block';box.select();done('Downloaded. Copy from the box.')}};
document.getElementById('reset').onclick=()=>{if(confirm('Clear all decisions on this page?')){store={};localStorage.removeItem(KEY);items.forEach(apply);count()}};
flt();count();
"""


def summary_cards(files, claude, codex, final_rows, state, budget, installed, overall_line):
    both = [f for f in files if f in claude and f in codex]
    agree = sum(1 for f in both if codex[f].get("agree") is not False and
                tc.verdict_class(claude[f].get("verdict")) == tc.verdict_class(codex[f].get("codex_verdict")))
    counts = {}
    for f in files:
        counts[final_rows[f]] = counts.get(final_rows[f], 0) + 1
    cards = [("Proposals", len(files)), ("Reviewed", len(claude)), ("Codex-checked", len(codex)),
             ("Agree", f"{round(100 * agree / len(both))}%" if both else "n/a"),
             ("Skills / budget", f"{installed} / {budget}")]
    cards += [(k, counts[k]) for k in tc.VERDICT_CLASSES + ["PENDING"] if counts.get(k)]
    html_cards = "".join(f'<div class="card"><b>{e(v)}</b><span>{e(k)}</span></div>' for k, v in cards)
    m = re.search(r"OVERALL:\s*(SOUND|NEEDS REWORK)", overall_line or "", re.I)
    if m:
        html_cards += (f'<div class="card" title="{e(overall_line)}"><b>{e(m.group(1).upper())}</b>'
                       f'<span>Codex overall</span></div>')
    return html_cards


def progress_html(state, n_batches):
    if not state:
        return ""
    phases = state.get("phases", {})
    done = sum(1 for p in tc.PHASES if phases.get(p) == "done")
    cur = state.get("phase", "")
    b = state.get("batches", {}) or {}
    cl = sum(1 for v in b.values() if v.get("claude") == "done")
    cx = sum(1 for v in b.values() if v.get("codex") == "done")
    pct = round(100 * done / len(tc.PHASES))
    label = (f"Phase {e(cur)} {e(tc.PHASE_NAMES.get(cur, ''))} · status {e(state.get('status', '?'))} · "
             f"Claude batches {cl}/{n_batches} · Codex batches {cx}/{n_batches} · updated {e(state.get('updated', ''))}")
    return f'<div class="sub">{label}</div><div class="progress" title="{pct}%"><div style="width:{pct}%"></div></div>'


def groups_panel(cg):
    if not cg:
        return '<details class="panel"><summary>Codex review of the groups: pending</summary></details>'
    li = lambda items: "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else "<p class=sub>none</p>"
    mis = [f"Move <b>{e(m.get('proposal'))}</b>: {e(m.get('from'))} to {e(m.get('to'))}. {e(m.get('why'))}"
           for m in cg.get("misattributions", [])]
    new = [f"<b>{e(n.get('name'))}</b>: {e(', '.join(n.get('members', [])))}. {e(n.get('why'))}" for n in cg.get("new_clusters", [])]
    cov = [f"{e(c.get('proposal'))}: {e(c.get('covered_by'))} ({e(c.get('label'))})"
           for c in cg.get("coverage", cg.get("group_F_coverage", []))]
    mrg = [f"<b>{e(d.get('group'))}</b> ({'merge' if d.get('merge') else 'keep separate'}): {e(d.get('design'))}"
           for d in cg.get("merge_designs", [])]
    return (f'<details class="panel"><summary>Codex review of the groups</summary><p>{e(cg.get("summary", ""))}</p>'
            f"<h4>Misattributions</h4>{li(mis)}<h4>New clusters</h4>{li(new)}<h4>Coverage</h4>{li(cov)}"
            f"<h4>Merge designs</h4>{li(mrg)}</details>")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out")
    ap.add_argument("--proposals-dir")
    ap.add_argument("--budget", type=int)
    ap.add_argument("--installed", type=int)
    args = ap.parse_args()
    run = os.path.abspath(os.path.expanduser(args.run_dir))
    state = tc.load_state(run)
    proposals = os.path.abspath(os.path.expanduser(args.proposals_dir or state.get("proposals_dir") or tc.DEFAULT_PROPOSALS))
    budget = args.budget or state.get("budget") or 120
    installed = args.installed if args.installed is not None else (state.get("skills_installed") or tc.count_installed_skills())

    problems = []
    claude, codex = tc.load_claude(run), tc.load_codex(run, problems)
    final = tc.read_json(os.path.join(run, "final-verdicts.json"), {}) or {}
    merged = merge(claude, codex, {})
    for fn, row in merged.items():
        final.setdefault(fn, row)
        final[fn].setdefault("final_score", row.get("final_score"))
    files = inventory(run, claude, codex, final)
    groups = tc.load_groups(run)
    cg = tc.load_codex_groups(run)
    moves = {m.get("proposal"): m for m in cg.get("misattributions", [])}
    for n in cg.get("new_clusters", []):
        for mem in n.get("members", []):
            moves.setdefault(mem, {"to": n.get("name"), "why": "new cluster: " + str(n.get("why", ""))})
    overall = ""
    op = os.path.join(run, "codex", "out-overall.md")
    if os.path.exists(op):
        overall = open(op).read()
    overall_line = next((ln.strip() for ln in overall.splitlines() if ln.strip().upper().startswith("OVERALL:")), "")
    top = md_section(overall, r"top\s*\d*\s*actions?")

    final_class = {f: tc.verdict_class((final.get(f) or {}).get("verdict") or (codex.get(f) or {}).get("codex_verdict")
                                       or (claude.get(f) or {}).get("verdict")) for f in files}
    rows = build_rows(run, proposals, files, claude, codex, final, groups, moves)
    group_names = list(groups) + ["Ungrouped"]
    n_batches = len(tc.batch_files(run)) or len((state.get("batches") or {}))
    refresh = '<meta http-equiv="refresh" content="30">' if state.get("status") == "running" else ""
    top_panel = (f'<details class="panel" open><summary>Top actions (Codex overall review)</summary>{md_to_html(top)}</details>'
                 if top else "")
    overall_panel = (f'<details class="panel"><summary>Codex overall review</summary>{md_to_html(overall)}</details>'
                     if overall else '<details class="panel"><summary>Codex overall review: pending</summary></details>')
    warn = "".join(f'<p class="sub">WARN {e(p)}</p>' for p in problems)

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">{refresh}
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Skill proposal triage</title>
<style>{CSS}</style></head><body data-run="{e(run)}">
<header><h1>Skill proposal triage</h1>
<div class="cards">{summary_cards(files, claude, codex, final_class, state, budget, installed, overall_line)}</div>
{progress_html(state, n_batches)}
<div class="toolbar"><input id="q" type="search" placeholder="Search name, summary, overlap" aria-label="search">
<select id="vf" aria-label="verdict filter"><option value="">All verdicts</option>{''.join(f'<option>{v}</option>' for v in tc.VERDICT_CLASSES + ['PENDING'])}</select>
<select id="gf" aria-label="group filter"><option value="">All groups</option>{''.join(f'<option>{e(g)}</option>' for g in group_names)}</select>
<label><input id="dis" type="checkbox"> Disagreements only</label>
<select id="sort" aria-label="sort"><option value="date">Newest first</option><option value="final">Final score</option><option value="ease">Eval ease</option></select>
<span class="sub" id="nshown"></span><span class="sub" id="nchanged"></span>
<button id="export" class="primary" type="button">Export decisions</button><button id="reset" type="button">Reset</button></div>
<textarea id="exportbox" readonly aria-label="exported decisions"></textarea></header>
<main>{warn}{top_panel}{groups_panel(cg)}{overall_panel}
<p class="sub">Final = mean of the Claude and Codex scores. The final verdict is the Codex verdict on conflict, the Claude verdict when Codex is missing. Evidence = distinct transcript sessions before and after the proposal date. Eval ease: 1 trivial, 5 needs a live environment. Decisions save in this browser; Export writes decisions.json for the apply phase.</p>
<table id="t"><thead><tr><th>Final</th><th>Proposal</th><th>Verdict</th><th>Claude</th><th>Codex</th><th>Eval ease</th><th>Impact / target</th><th>Decision</th></tr></thead>
{''.join(rows)}</table></main><div id="toast"></div>
<script>{JS}</script></body></html>"""
    out = args.out or os.path.join(run, "triage.html")
    with open(out, "w") as fh:
        fh.write(page)
    print(f"{len(files)} proposals, {len(claude)} reviewed, {len(codex)} codex-checked -> {out}")
    for p in problems:
        print("WARN " + p)


if __name__ == "__main__":
    main()
