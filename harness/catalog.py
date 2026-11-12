#!/usr/bin/env python3
"""Local harness catalog CLI. No server, package installation or web framework."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import uuid

from store import Store, utc_now, stable_id


ROOT = Path(__file__).resolve().parent.parent


def resolve_skill(store, name):
    rows = store.rows("SELECT id,name,source_path FROM capabilities WHERE id=? OR name=?", (name,name))
    if len(rows) != 1:
        choices = "; ".join(r["id"]+" "+r["source_path"] for r in rows)
        raise ValueError("Capability must resolve uniquely; use its ID. " + (choices or "Run refresh first."))
    return rows[0]["id"]


def seed_preferences(store, root):
    """Import Gabriel's explicit selection, not inferred retirement decisions."""
    source = root / "docs/harness-skill-selection.md"
    if not source.is_file():
        return 0
    groups = {
        "prioritize": "bibliotheque-librarian bibliotheque-refresh context-audit operationalize operationalize-audit transcript-knowledge-miner vendor-api-ingest wiki-lint notion graphify dark-factory feedback-to-spec investigate sprint-estimation sprint-close sprint-factory",
        "keep": "tech-doc-review-flow push-adr pr-review index-context bmad-debrief archive create-tickets epic-reorganization leo-ac-scaffold status-index ticket-init ticket-to-pr-analyst to-issues to-prd triage setup-matt-pocock-skills spillover-scan",
        "promote": "agent-os:audit-docs",
        "review": "adversarial-cascade crawl-adversarial-review-cascade ralph-loop-preflight",
    }
    count=0
    for action,names in groups.items():
        for name in names.split():
            for cap in store.rows("SELECT id FROM capabilities WHERE name=?",(name,)):
                rationale = "Gabriel's explicit shared selection, 2026-10-26. See the original selection record."
                if name in ("adversarial-cascade","crawl-adversarial-review-cascade"):
                    rationale = "Gabriel reports non-use in both hosts. Review usefulness; no retirement authorized."
                if name == "ralph-loop-preflight":
                    rationale = "Gabriel reports long-term non-use. Dormant, review later; no retirement authorized."
                count += store.record("decision",{"id":stable_id("selection-2026-10-26",cap["id"],action),
                    "capability_id":cap["id"],"occurred_at":"2026-10-26","action":action,"status":"approved",
                    "rationale":rationale,"authority":"Gabriel, recorded selection 2026-10-26","evidence":str(source)},producer="maintainer")
    return count


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=Path(os.environ.get("HARNESS_ROOT",ROOT)))
    p.add_argument("--db",type=Path)
    p.add_argument("--view",type=Path)
    p.add_argument("--home",type=Path,default=Path.home())
    p.add_argument("--org",default="klever",choices=["klever"])
    sub=p.add_subparsers(dest="command",required=True)
    ref=sub.add_parser("refresh",help="Collect evidence and rebuild the static view; never run evals or workflows")
    ref.add_argument("--days",type=int,default=90)
    ref.add_argument("--project-root",type=Path)
    sub.add_parser("render",help="Rebuild HTML only")
    sub.add_parser("stats",help="Show domain record counts")
    show=sub.add_parser("show",help="Inspect one capability by exact name or ID")
    show.add_argument("capability")
    note=sub.add_parser("note",help="Append an observed friction, not a verdict or approval")
    note.add_argument("--skill",required=True)
    note.add_argument("--host",choices=["claude","codex","shared","unknown"],required=True)
    note.add_argument("--role",default="unknown")
    note.add_argument("--session",default="unknown")
    note.add_argument("--summary",required=True)
    note.add_argument("--impact",required=True)
    note.add_argument("--evidence",required=True)
    note.add_argument("--id",help="Stable observation ID for safe replay")
    record=sub.add_parser("record",help="Validated typed write; local ownership policy, not a filesystem security boundary")
    record.add_argument("kind",choices=["capability","availability","dependency","usage","friction","eval_suite","eval","outcome","decision","coverage","artifact"])
    record.add_argument("--input",type=Path,required=True,help="JSON object with only the selected domain's fields")
    record.add_argument("--producer",choices=["agent","collector","eval-runner","maintainer"],default="agent")
    backup=sub.add_parser("backup",help="Create a consistent SQLite snapshot")
    backup.add_argument("destination",type=Path)
    sub.add_parser("retry",help="Retry spooled producer records and rebuild the view")
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    root=args.root.expanduser().resolve()
    db=(args.db or root/"harness/data/harness.sqlite").expanduser().resolve()
    view=(args.view or root/"harness/view").expanduser().resolve()
    try:
        with Store(db) as store:
            if args.command=="refresh":
                if not 1 <= args.days <= 3650:
                    raise ValueError("--days must be between 1 and 3650")
                from bridges import refresh
                result=refresh(store,root,args.home.expanduser().resolve(),org=args.org,
                               project_root=args.project_root,days=args.days)
                result["selection_records_added"]=seed_preferences(store,root)
                from render import render
                result["view"]=render(store,view)
            elif args.command=="render":
                from render import render
                result=render(store,view)
            elif args.command=="stats":
                tables=["capabilities","availability","dependencies","usage_events","frictions","eval_suites","eval_runs","outcomes","decisions","coverage","artifacts"]
                result={t:store.rows(f"SELECT COUNT(*) AS count FROM {t}")[0]["count"] for t in tables}
            elif args.command=="show":
                cid=resolve_skill(store,args.capability)
                result={"capability":store.rows("SELECT * FROM capabilities WHERE id=?",(cid,))[0]}
                for table in ["availability","dependencies","usage_events","frictions","eval_suites","eval_runs","outcomes","decisions"]:
                    result[table]=store.rows(f"SELECT * FROM {table} WHERE capability_id=?",(cid,))
            elif args.command=="note":
                payload={"id":args.id or str(uuid.uuid4()),"capability_id":resolve_skill(store,args.skill),"host":args.host,
                    "role":args.role,"session_id":args.session,"occurred_at":utc_now(),"summary":args.summary,
                    "impact":args.impact,"evidence":args.evidence}
                # Replaying an explicit ID retains its original timestamp.
                previous=store.rows("SELECT occurred_at FROM frictions WHERE id=?",(payload["id"],))
                if previous:payload["occurred_at"]=previous[0]["occurred_at"]
                result={"inserted":store.record("friction",payload,producer="agent"),"id":payload["id"]}
                from render import render
                result["view"]=render(store,view)
            elif args.command=="record":
                payload=json.loads(args.input.read_text())
                result={"inserted":store.record(args.kind,payload,producer=args.producer)}
                from render import render
                result["view"]=render(store,view)
            elif args.command=="backup":
                store.backup(args.destination.expanduser().resolve());result={"backup":str(args.destination)}
            elif args.command=="retry":
                from producer import retry_pending
                result=retry_pending(root=root,db=db)
                from render import render
                result["view"]=render(store,view)
        print(json.dumps(result,indent=2,ensure_ascii=False,default=str))
        return 0
    except (ValueError,PermissionError,OSError) as error:
        print(f"harness: {error}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
