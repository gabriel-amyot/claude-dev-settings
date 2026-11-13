# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Layer A (deterministic) evals for the mission skill. Exit 1 on any failure.

Runs in a temp PM root, so it never touches the real missions/ folder.
  uv run --quiet --with pyyaml python3 ~/.claude-shared-config/skills/mission/evals/run_layer_a.py
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

try:
    import yaml
except ModuleNotFoundError:
    import os, shutil, sys
    _uv, _main = shutil.which("uv"), getattr(sys.modules.get("__main__"), "__file__", None)
    if _uv and _main and os.environ.get("UV_DEPS_REEXEC") != os.path.abspath(_main):
        os.environ["UV_DEPS_REEXEC"] = os.path.abspath(_main)
        os.execv(_uv, [_uv, "run", "--quiet", "--with", "pyyaml", "python", os.path.abspath(_main), *sys.argv[1:]])
    raise

HERE = pathlib.Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
VALID = yaml.safe_load((HERE / "fixtures" / "valid" / "mission.yaml").read_text())
CASES = yaml.safe_load((HERE / "fixtures" / "invalid_cases.yaml").read_text())
results: list[tuple[str, bool, str]] = []
ORG_CONFIG = {"gh_repo": "acme/planning", "jira_browse": "https://tracker.example.invalid/browse/", "jira_org": "acme"}


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def patch(doc: dict, path: str, value) -> dict:
    d = copy.deepcopy(doc)
    keys = [int(k) if k.isdigit() else k for k in path.split(".")]
    cur = d
    for k in keys[:-1]:
        cur = cur[k]
    if value is None:
        if isinstance(cur, dict):
            cur.pop(keys[-1], None)
        else:
            cur[keys[-1]] = None
    else:
        cur[keys[-1]] = value
    return d


def script(root: pathlib.Path, name: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "MISSION_PM_ROOT": str(root), "MISSION_CONFIG": str(root / "no-user-config.yaml")}
    return subprocess.run([sys.executable, str(SCRIPTS / name), *args], capture_output=True, text=True, env=env)


def write(root: pathlib.Path, doc: dict, slug: str = "fixture-vendor") -> pathlib.Path:
    d = root / "missions" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "mission.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    return d


def closeout_evals(root: pathlib.Path, d: pathlib.Path, util) -> None:
    """Close-out: gatherer reports UNKNOWN on missing data, the gate refuses orphans, sync refuses done."""
    cspec = util.spec_from_file_location("mco", SCRIPTS / "mission_closeout.py")
    os.environ["MISSION_PM_ROOT"] = str(root)
    mco = util.module_from_spec(cspec)
    cspec.loader.exec_module(mco)

    posts = root / "tickets" / "PRJ" / "no-epic" / "PRJ-1398" / "reports" / "ship" / "posts"
    posts.mkdir(parents=True)
    (posts / "2026-11-12-unsent.md").write_text("draft")
    (posts / "2026-11-12-sent.md").write_text("draft")
    (posts / "2026-11-12-sent.posted").write_text("posted")
    (posts / "2026-11-12-rsent.rendered.md").write_text("draft")
    (posts / "2026-11-12-rsent.rendered.posted").write_text("posted")
    (posts / "2026-11-12-pointer.md").write_text("posted-as: GitHub issue body https://example.invalid/issues/1 (2026-11-12)\n\nbody")

    r = script(root, "mission_closeout.py", "gather", "fixture-vendor", "--offline")
    f = d / "closeout-facts.json"
    facts = json.loads(f.read_text()) if f.exists() else {}
    check("closeout/gather-exit-0", r.returncode == 0, r.stdout + r.stderr)
    check("closeout/gather-jira-unknown-offline", facts.get("jira", {}).get("status") == "UNKNOWN")
    check("closeout/gather-github-unknown-offline", facts.get("github", {}).get("status") == "UNKNOWN")
    check("closeout/gather-handoffs-unknown-without-ledger", facts.get("handoffs", {}).get("status") == "UNKNOWN")
    check("closeout/gather-branches-and-mrs-unknown", facts.get("branches", {}).get("status") == "UNKNOWN"
          and facts.get("branches", {}).get("mrs", {}).get("status") == "UNKNOWN")
    check("closeout/gather-never-pass", f.exists() and "PASS" not in f.read_text())
    check("closeout/gather-lists-unknowns", len(facts.get("unknown", [])) >= 4, str(facts.get("unknown")))
    drafts = facts.get("drafts", {})
    unmarked = drafts.get("no_posted_marker", [])
    check("closeout/drafts-unmarked-only", [pathlib.Path(x.get("path", "")).name for x in unmarked] == ["2026-11-12-unsent.md"], str(unmarked))
    check("closeout/D1-drafts-never-confirmed-unsent", "unsent" not in drafts
          and all(x.get("remote_state") == "UNKNOWN" for x in unmarked), str(drafts))
    check("closeout/D1-drafts-remote-check-listed-as-unknown",
          any(u.startswith("drafts:") and "remote" in u for u in facts.get("unknown", [])), str(facts.get("unknown")))

    check("config/org-config-read", mco.GH_REPO == "acme/planning" and mco.JIRA_ORG == "acme", f"{mco.GH_REPO} {mco.JIRA_ORG}")
    real_org = mco.JIRA_ORG
    mco.JIRA_ORG = None
    try:
        e = mco.jira_call("search", "key = PRJ-1")
        check("config/missing-jira-org-is-unknown", isinstance(e, dict) and "jira_org" in e.get("error", ""), str(e))
        jj = mco.gather_jira(["PRJ-1"], False)
        check("config/missing-jira-org-gather-not-ok", jj["status"] != "OK", jj["status"])
    finally:
        mco.JIRA_ORG = real_org
    e = mco.gh_issue("", 5)
    check("config/missing-gh-repo-is-error", "gh_repo" in e.get("error", ""), str(e))

    t = mco.jira_facts_from("PRJ-1", {"error": "401"}, {"error": "401"}, {"error": "401"})
    check("closeout/jira-facts-unknown-on-error", t["status"] == "UNKNOWN" and t["comment_count"] == "UNKNOWN"
          and t["closed_without_comments"] == "UNKNOWN" and t["description_excerpt"] == "UNKNOWN", str(t))
    meta = {"key": "PRJ-2", "status": "Terminé(e)", "status_category": "Terminé", "resolution": None}
    t = mco.jira_facts_from("PRJ-2", meta, [], {"description": "write stays closed"})
    check("closeout/jira-facts-closed-without-comments", t["closed"] is True and t["closed_without_comments"] is True
          and t["comment_after_close"] == "UNKNOWN", str(t))
    check("closeout/blocking-mentions", mco.blocking_mentions("Map #12 blocks the final step. See #3.") == ["12"])

    base = yaml.safe_load((HERE / "fixtures" / "closeout" / "closeout.yaml").read_text())
    base["checklist"] = [{"id": sid, "status": "done"} for sid in mco.CHECKLIST_IDS]
    r = script(root, "mission_closeout.py", "gate", "fixture-vendor")
    check("closeout/gate-refuses-without-report", r.returncode == 1 and "no closeout.yaml" in r.stdout, r.stdout)

    (d / "closeout.yaml").write_text(yaml.safe_dump(base, sort_keys=False, allow_unicode=True))
    r = script(root, "mission_closeout.py", "gate", "fixture-vendor")
    check("closeout/gate-refuses-orphan", r.returncode == 1 and "CO-3: ORPHAN without a named successor" in r.stdout, r.stdout)

    phase1_control_evals(root, d, mco, base, facts)

    (d / "closeout.yaml").write_text(yaml.safe_dump(base, sort_keys=False, allow_unicode=True))
    r = script(root, "mission_closeout.py", "render", "fixture-vendor")
    page = (d / "closeout.html").read_text() if (d / "closeout.html").exists() else ""
    check("closeout/render-html", r.returncode == 0 and "Close gate: CLOSED" in page and "ORPHAN (1)" in page
          and "Not checked (UNKNOWN, never PASS)" in page and "cdn." not in page, r.stderr)
    check("closeout/render-overwrites-one-file", sorted(x.name for x in d.glob("closeout*")) ==
          ["closeout-facts.json", "closeout.html", "closeout.yaml"])

    done = yaml.safe_load((d / "mission.yaml").read_text())
    done["status"] = "done"
    (d / "mission.yaml").write_text(yaml.safe_dump(done, sort_keys=False, allow_unicode=True))
    r = script(root, "mission_sync.py", "fixture-vendor", "-m", "close")
    check("closeout/sync-refuses-done-with-orphan", r.returncode != 0 and "close-out gate is closed" in r.stderr, r.stdout + r.stderr)
    done["status"] = "active"
    (d / "mission.yaml").write_text(yaml.safe_dump(done, sort_keys=False, allow_unicode=True))

    r = script(root, "mission_closeout.py", "gather", "--scope", "comp-x", "--seed-jira", "PRJ-9", "--seed-gh", "677",
               "--aliases", "comp x", "--offline")
    sf = root / "missions" / "_closeout" / "comp-x" / "closeout-facts.json"
    sfacts = json.loads(sf.read_text()) if sf.exists() else {}
    check("closeout/scope-without-mission-record", r.returncode == 0 and sfacts.get("scope", {}).get("jira_seeds") == ["PRJ-9"]
          and sfacts.get("scope", {}).get("gh_seeds") == ["677"], r.stdout + r.stderr)
    gatherer_ground_truth_evals(mco)
    phase2_discovery_evals(root, mco)


LINK = {"kind": "url", "url": "https://forge.example.invalid/acme/planning/issues/1#c9", "title": "said in the thread"}


def phase1_control_evals(root: pathlib.Path, d: pathlib.Path, mco, base: dict, facts: dict) -> None:
    """Close control: manifest approval bound to a hash, read-backs, UNKNOWN dispositions, risk decisions,
    accepted successors, a decision-first report and the close-out log."""
    def save(co):
        (d / "closeout.yaml").write_text(yaml.safe_dump(co, sort_keys=False, allow_unicode=True))

    def load_co():
        return yaml.safe_load((d / "closeout.yaml").read_text())

    def gate_out(co):
        save(co)
        return script(root, "mission_closeout.py", "gate", "fixture-vendor")

    def cli(*args):
        return script(root, "mission_closeout.py", *args)

    keys = sorted({mco.unknown_key(u) for u in facts.get("unknown", [])})
    check("p1/offline-facts-have-unknowns", len(keys) >= 4, str(keys))
    staged = copy.deepcopy(base)
    staged["items"][2]["successor"] = {"kind": "jira", "ref": "PTR-103", "url": "https://tracker.example.invalid/browse/PTR-103",
                                       "title": "Risk acceptance", "accepted": {"by": "Gabriel", "link": LINK}}
    staged["items"][2]["parked_by"] = "Gabriel"
    staged["unknowns"] = [{"source": k, "consequential": True, "disposition": "accepted", "by": "Gabriel", "link": LINK} for k in keys]
    save(staged)
    covf = d / "closeout-coverage.json"
    cov_ok = {"fetched_at": "2026-11-13T00:00:00Z", "items": {
        "CO-2": {"item": "CO-2", "status": "mentioned", "excluded_by": [], "mentioned": True},
        "CO-3": {"item": "CO-3", "status": "not-mentioned", "excluded_by": [], "mentioned": False}}}
    covf.write_text(json.dumps(cov_ok))
    r = cli("approve", "fixture-vendor", "--items", "A-1,A-2", "--by", "Gabriel", "--link", LINK["url"])
    check("p1/approve-batch-ok", r.returncode == 0 and "hash" in r.stdout, r.stdout + r.stderr)
    approved = load_co()
    check("p1/approve-records-hash-and-ids", len(approved.get("approvals") or []) == 1
          and approved["approvals"][0].get("items") == ["A-1", "A-2"] and approved["approvals"][0].get("hash"), str(approved.get("approvals")))
    r = gate_out(approved)
    check("p1/gate-refuses-approved-not-executed", r.returncode == 1 and "A-1: approved, not done" in r.stdout, r.stdout)
    r1 = cli("record", "fixture-vendor", "--action", "A-1", "--before", "In review", "--after", "Done, comment 1 posted")
    r2 = cli("record", "fixture-vendor", "--action", "A-2", "--before", "open, parent #700", "--after", "open, parent #677")
    closed = load_co()
    check("p1/record-readback", r1.returncode == 0 and r2.returncode == 0
          and all(a.get("state") == "done" and (a.get("readback") or {}).get("after") for a in closed["manifest"]), r1.stdout + r1.stderr)
    r = gate_out(closed)
    check("p1/gate-opens-when-everything-closed", r.returncode == 0 and "GATE OPEN" in r.stdout, r.stdout)

    covf.unlink()
    r = gate_out(closed)
    check("p2/gate-refuses-successor-without-coverage-check", r.returncode == 1 and "CO-2" in r.stdout and "coverage" in r.stdout, r.stdout)
    bad = copy.deepcopy(cov_ok); bad["items"]["CO-2"].update(status="excluded", excluded_by=["Out of scope: declined permission prompt"])
    covf.write_text(json.dumps(bad))
    r = gate_out(closed)
    check("p2/gate-refuses-successor-that-excludes", r.returncode == 1 and "CO-2" in r.stdout and "excludes" in r.stdout, r.stdout)
    co = copy.deepcopy(closed); co["items"][1]["successor"]["exclusion_resolved"] = LINK
    r = gate_out(co)
    check("p2/calibration-exclusion-resolved-by-link-ok", r.returncode == 0, r.stdout)
    bad["items"]["CO-2"] = {"item": "CO-2", "status": "UNKNOWN", "excluded_by": [], "mentioned": "UNKNOWN"}
    covf.write_text(json.dumps(bad))
    r = gate_out(closed)
    check("p2/gate-refuses-unread-successor", r.returncode == 1 and "CO-2" in r.stdout, r.stdout)
    covf.write_text(json.dumps(cov_ok))

    co = copy.deepcopy(closed); co["approvals"] = []
    r = gate_out(co)
    check("p1/gate-refuses-without-approval", r.returncode == 1 and "A-1: not approved" in r.stdout, r.stdout)
    co = copy.deepcopy(closed); co["manifest"][0]["action"] += " Also close PRJ-1399."
    r = gate_out(co)
    check("p1/gate-refuses-entry-edited-after-approval", r.returncode == 1 and "A-1: changed after approval" in r.stdout
          and "A-2: changed" not in r.stdout, r.stdout)
    co = copy.deepcopy(closed); co["manifest"][0].pop("readback")
    r = gate_out(co)
    check("p1/gate-refuses-done-without-readback", r.returncode == 1 and "A-1" in r.stdout and "read-back" in r.stdout, r.stdout)
    co = copy.deepcopy(closed); co["manifest"][1].update(state="skipped"); co["manifest"][1].pop("readback")
    r = gate_out(co)
    check("p1/gate-refuses-skipped-without-reason", r.returncode == 1 and "A-2: skipped without a reason" in r.stdout, r.stdout)
    co["manifest"][1]["skipped_reason"] = "the human moved it by hand; read-back shows parent #677"
    r = gate_out(co)
    check("p1/gate-accepts-skipped-with-reason", r.returncode == 0, r.stdout)

    save(approved)
    r = cli("record", "fixture-vendor", "--action", "A-1", "--before", "In review", "--after", "")
    co = load_co()
    check("p1/record-silent-mutation-stops", r.returncode != 0 and "verify the remote state" in (r.stdout + r.stderr)
          and co["manifest"][0].get("state") == "unverified", r.stdout + r.stderr)
    r = gate_out(co)
    check("p1/gate-refuses-unverified-action", r.returncode == 1 and "A-1: unverified" in r.stdout, r.stdout)
    save(staged)
    r = cli("record", "fixture-vendor", "--action", "A-1", "--before", "In review", "--after", "Done")
    check("p1/record-refuses-unapproved-action", r.returncode != 0 and "not approved" in (r.stdout + r.stderr), r.stdout + r.stderr)

    many = copy.deepcopy(staged)
    many["manifest"] = [{"id": f"A-{i}", "item": "CO-1", "target": {"kind": "gh", "ref": f"#{900 + i}", "url": f"https://forge.example.invalid/acme/planning/issues/{900 + i}", "title": "t"},
                         "expected_state": "open", "kind": "close", "action": f"Close #{900 + i} with the evidence comment.",
                         "class": "routine", "state": "proposed"} for i in range(1, 17)]
    save(many)
    r = cli("approve", "fixture-vendor", "--items", ",".join(f"A-{i}" for i in range(1, 17)), "--by", "Gabriel", "--link", LINK["url"])
    check("p1/approve-refuses-more-than-15-closes", r.returncode != 0 and "15" in (r.stdout + r.stderr) and not load_co().get("approvals"), r.stdout + r.stderr)
    r = cli("approve", "fixture-vendor", "--items", ",".join(f"A-{i}" for i in range(1, 16)), "--by", "Gabriel", "--link", LINK["url"])
    check("p1/calibration-approve-15-closes-ok", r.returncode == 0, r.stdout + r.stderr)
    sec = copy.deepcopy(staged)
    sec["manifest"][1]["class"] = "security"
    save(sec)
    r = cli("approve", "fixture-vendor", "--items", "A-1,A-2", "--by", "Gabriel", "--link", LINK["url"])
    check("p1/approve-refuses-security-item-in-a-batch", r.returncode != 0 and "per-item" in (r.stdout + r.stderr), r.stdout + r.stderr)
    r = cli("approve", "fixture-vendor", "--items", "A-2", "--by", "Gabriel", "--link", LINK["url"])
    check("p1/calibration-security-item-alone-ok", r.returncode == 0, r.stdout + r.stderr)
    for cls in ("cancellation", "changed-commitment"):
        c2 = copy.deepcopy(staged); c2["manifest"][0]["class"] = cls; save(c2)
        r = cli("approve", "fixture-vendor", "--items", "A-1,A-2", "--by", "Gabriel", "--link", LINK["url"])
        check(f"p1/approve-refuses-{cls}-in-a-batch", r.returncode != 0, r.stdout + r.stderr)
    save(staged)
    r = cli("approve", "fixture-vendor", "--items", "A-1", "--by", "agent", "--link", LINK["url"])
    check("p1/approve-refuses-agent-as-approver", r.returncode != 0 and not load_co().get("approvals"), r.stdout + r.stderr)
    r = cli("approve", "fixture-vendor", "--items", "A-1", "--by", "Gabriel")
    check("p1/approve-refuses-without-link", r.returncode != 0, r.stdout + r.stderr)

    co = copy.deepcopy(closed); dropped = co["unknowns"].pop(0)["source"]
    r = gate_out(co)
    check("p1/gate-refuses-undispositioned-unknown", r.returncode == 1 and f"UNKNOWN '{dropped}' has no disposition" in r.stdout, r.stdout)
    co = copy.deepcopy(closed); co["unknowns"][0]["by"] = "claude"
    r = gate_out(co)
    check("p1/gate-refuses-unknown-accepted-by-agent", r.returncode == 1 and "named human" in r.stdout, r.stdout)
    co = copy.deepcopy(closed); co["unknowns"][0] = {"source": co["unknowns"][0]["source"], "consequential": True, "disposition": "tracked",
                                                     "successor": {"kind": "gh", "ref": "#901", "url": "https://forge.example.invalid/acme/planning/issues/901", "title": "Check MRs", "owner": "Gabriel"}}
    r = gate_out(co)
    check("p1/gate-accepts-unknown-tracked-with-successor", r.returncode == 0, r.stdout)
    co = copy.deepcopy(closed); co["unknowns"][0] = {"source": co["unknowns"][0]["source"], "consequential": False}
    r = gate_out(co)
    check("p1/gate-refuses-not-consequential-without-reason", r.returncode == 1 and "reason" in r.stdout, r.stdout)
    co["unknowns"][0]["reason"] = "the source holds no obligation for this scope"
    r = gate_out(co)
    check("p1/calibration-not-consequential-with-reason-ok", r.returncode == 0, r.stdout)
    co["items"].append({"id": "CO-9", "bucket": "HUMAN-ONLY", "title": "Gateway auth probe never ran", "control": "security", "live": True,
                        "unknowns": [co["unknowns"][0]["source"]], "owner": "Gabriel", "state": "proposed",
                        "residual_risk": {"decision": "accepted", "by": "Gabriel", "link": LINK}})
    r = gate_out(co)
    check("p1/gate-refuses-security-unknown-marked-not-consequential", r.returncode == 1 and "security" in r.stdout, r.stdout)

    risk = {"id": "CO-8", "bucket": "HUMAN-ONLY", "title": "Write path live without the header-trust check", "control": "security",
            "live": True, "owner": "Gabriel", "state": "proposed", "found_by": "risk-acceptance"}
    co = copy.deepcopy(closed); co["items"].append(copy.deepcopy(risk))
    r = gate_out(co)
    check("p1/gate-refuses-live-risk-without-decision", r.returncode == 1 and "CO-8: live security risk" in r.stdout, r.stdout)
    co["items"][-1]["live"] = "UNKNOWN"
    r = gate_out(co)
    check("p1/gate-refuses-live-unknown-risk-without-decision", r.returncode == 1 and "CO-8" in r.stdout, r.stdout)
    co["items"][-1]["residual_risk"] = {"decision": "accepted", "by": "agent", "link": LINK}
    r = gate_out(co)
    check("p1/gate-refuses-risk-decided-by-agent", r.returncode == 1 and "CO-8" in r.stdout, r.stdout)
    co["items"][-1]["residual_risk"] = {"decision": "accepted", "by": "Gabriel", "link": LINK}
    r = gate_out(co)
    check("p1/gate-accepts-risk-decided-by-named-person", r.returncode == 0, r.stdout)
    co["items"][-1].pop("residual_risk")
    co["items"][-1]["successor"] = {"kind": "jira", "ref": "PTR-103", "url": "https://tracker.example.invalid/browse/PTR-103", "title": "Risk decision", "owner": "Gabriel",
                                    "accepted": {"by": "Gabriel", "link": LINK}}
    r = gate_out(co)
    check("p1/gate-accepts-risk-tracked-with-named-owner", r.returncode == 0, r.stdout)

    co = copy.deepcopy(closed); co["items"][2]["successor"].pop("accepted")
    r = gate_out(co)
    check("p1/gate-refuses-orphan-linked-not-accepted", r.returncode == 1 and "CO-3" in r.stdout and "accepted" in r.stdout, r.stdout)
    co = copy.deepcopy(closed); co["checklist"] = co["checklist"][1:]
    r = gate_out(co)
    check("closeout/gate-refuses-missing-checklist-step", r.returncode == 1 and "tracker-status" in r.stdout, r.stdout)
    co = copy.deepcopy(closed); co["items"][1].pop("successor")
    r = gate_out(co)
    check("closeout/gate-refuses-keep-without-successor", r.returncode == 1 and "KEEP needs successor" in r.stdout, r.stdout)
    co = copy.deepcopy(closed)
    co["items"].append({"id": "CO-4", "bucket": "HUMAN-ONLY", "title": "Decide the retention window", "state": "proposed"})
    r = gate_out(co)
    check("closeout/gate-refuses-open-human-only-without-owner", r.returncode == 1 and "CO-4: HUMAN-ONLY" in r.stdout, r.stdout)
    co["items"][-1]["owner"] = "Gabriel"
    r = gate_out(co)
    check("closeout/gate-opens-human-only-with-owner", r.returncode == 0, r.stdout)
    co["items"].append({"id": "CO-5", "bucket": "ORPHAN", "title": "Advertiser read authorization", "found_by": "human",
                        "finding": "The successor excludes it.", "parked_by": "Gabriel",
                        "successor": {"kind": "gh", "ref": "#902", "url": "https://forge.example.invalid/acme/planning/issues/902", "title": "Authz", "accepted": {"by": "Gabriel", "link": LINK}}})
    r = gate_out(co)
    check("p1/gate-refuses-human-found-big-miss-without-check-and-eval", r.returncode == 1 and "CO-5: found by the human" in r.stdout, r.stdout)
    co["items"][-1].update(new_check="successor-coverage", eval_case="closeout-full-real-scenario G6")
    cov5 = copy.deepcopy(cov_ok); cov5["items"]["CO-5"] = {"item": "CO-5", "status": "mentioned", "excluded_by": [], "mentioned": True}
    covf.write_text(json.dumps(cov5))
    r = gate_out(co)
    check("p1/calibration-human-found-miss-with-check-and-eval-ok", r.returncode == 0, r.stdout)

    # big-miss predicates (SYNTHESIS section 3)
    bm = mco.big_miss_reasons
    check("p1/big-miss-live-assurance-gap", "live-assurance-gap" in bm({"bucket": "HUMAN-ONLY", "control": "access", "live": True}))
    check("p1/big-miss-unknown-on-security-control", "live-assurance-gap" in bm({"bucket": "HUMAN-ONLY", "control": "security", "live": True, "evidence_state": "UNKNOWN",
                                                                                 "residual_risk": {"by": "Gabriel", "decision": "accepted", "link": LINK}}))
    check("p1/big-miss-live-unknown-counts", "live-assurance-gap" in bm({"bucket": "KEEP", "control": "contract", "live": "UNKNOWN"}))
    check("p1/big-miss-orphan-is-uncovered-obligation", "valid-obligation-uncovered" in bm({"bucket": "ORPHAN"}))
    check("p1/big-miss-successor-excludes", "valid-obligation-uncovered" in bm({"bucket": "KEEP", "successor": {"url": "u", "title": "t", "excludes": True}}))
    check("p1/big-miss-consequential-false-record", "consequential-false-record" in bm({"bucket": "FALSE-PREMISE", "affects": ["authorization"]}))
    check("p1/big-miss-control-failure", "control-failure" in bm({"bucket": "HUMAN-ONLY", "control_failure": "approval-exceeded"}))
    check("p1/calibration-routine-close-is-not-big", bm({"bucket": "CLOSE-WITH-EVIDENCE", "evidence": [LINK]}) == [])
    check("p1/calibration-plain-false-premise-is-routine", bm({"bucket": "FALSE-PREMISE", "affects": []}) == [])
    check("p1/calibration-accepted-keep-is-routine", bm({"bucket": "KEEP", "successor": {"url": "u", "title": "t", "accepted": {"by": "Gabriel", "link": LINK}}}) == [])

    # decision-first renderer
    rnd = copy.deepcopy(staged)
    rnd["items"].append(dict(risk, decision={"question": "Accept the live gap, or switch writes off?", "options": ["accept, signed by you", "switch writes off"]}))
    save(rnd)
    g = cli("gather", "fixture-vendor", "--offline")
    r = cli("render", "fixture-vendor")
    page = (d / "closeout.html").read_text() if (d / "closeout.html").exists() else ""
    pos = [page.find(h) for h in ("<h2>Needs you", "<h2>Coverage", "<h2>Proposed batch", "<h2>Appendix")]
    check("p1/render-decision-first-order", r.returncode == 0 and all(x >= 0 for x in pos) and pos == sorted(pos), str(pos))
    needs = page[pos[0]:pos[1]] if all(x >= 0 for x in pos) else ""
    check("p1/render-needs-you-has-big-miss-with-options", "CO-8" in needs and "switch writes off" in needs and "CO-1" not in needs, needs[:400])
    batch = mco.plan_batches(rnd["manifest"])
    check("p1/render-shows-batch-hash", bool(batch) and batch[0]["hash"] in page, str(batch)[:200])
    check("p1/render-claims-coverage-not-completeness", "searched fully" in page and "nothing dropped" not in page.lower())
    newf = json.loads((d / "closeout-facts.json").read_text())
    counts = mco.fact_counts(newf)
    check("p1/counts-unified-gather-and-render", bool(counts) and all(f"{lbl}: {n}" in g.stdout and f"{lbl}: {n}" in page for lbl, n in counts),
          str(counts) + g.stdout[:300])

    # self-improvement: registry, log, check review
    reg = mco.CHECK_REGISTRY
    check("p1/registry-every-check-names-its-real-case", bool(reg) and all(str(v.get("catches") or "").strip() for v in reg.values()),
          str([k for k, v in reg.items() if not v.get("catches")]))
    check("p1/registry-covers-checklist", set(mco.CHECKLIST_IDS) <= set(reg), str(set(mco.CHECKLIST_IDS) - set(reg)))
    logco = copy.deepcopy(co)
    save(logco)
    r = cli("log", "fixture-vendor")
    logf = root / "missions" / "_meta" / "closeout-log.jsonl"
    last = json.loads(logf.read_text().splitlines()[-1]) if logf.exists() else {}
    check("p1/log-writes-counts-and-misses", r.returncode == 0 and last.get("buckets", {}).get("ORPHAN") == 2
          and [h["id"] for h in last.get("human_found", [])] == ["CO-5"] and "CO-3" in [b["id"] for b in last.get("big_misses_by_sweep", [])],
          r.stdout + r.stderr + json.dumps(last)[:300])
    check("p1/log-records-checks-fired", "orphans" in last.get("checks_fired", []), str(last.get("checks_fired")))
    for _ in range(3):
        cli("log", "fixture-vendor")
    r = cli("review-checks")
    check("p1/review-checks-unknown-before-5-closeouts", r.returncode == 0 and "4 of 5" in r.stdout and "review for removal" not in r.stdout, r.stdout)
    cli("log", "fixture-vendor")
    r = cli("review-checks")
    check("p1/review-checks-flags-never-fired", "infra-tails" in r.stdout and "review for removal" in r.stdout
          and "orphans: review for removal" not in r.stdout, r.stdout)
    logf.unlink()
    covf.unlink()
    save(base)


def gatherer_ground_truth_evals(mco) -> None:
    """Gatherer checks from a real close-out (anonymized). Trackers are faked in-process; nothing leaves the machine."""
    fx = HERE / "fixtures" / "closeout-gather"

    def jira_fake(fail_query: str):
        def fake(cmd, check=False, cwd=None):
            args = cmd[cmd.index("--org") + 2:]
            verb = args[0]
            if verb == "search":
                failed = args[1].startswith(fail_query)
                return subprocess.CompletedProcess(cmd, 1 if failed else 0, "[]", "401 Unauthorized" if failed else "")
            if verb == "metadata":
                meta = {"key": args[1], "status": "Done", "status_category": "Done", "resolution": "Done", "resolution_date": None}
                return subprocess.CompletedProcess(cmd, 0, json.dumps(meta), "")
            if verb == "comments":
                return subprocess.CompletedProcess(cmd, 0, json.dumps([{"created": "2026-11-01T10:00", "author": "a"}]), "")
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"description": "x"}), "")
        return fake

    real_run = mco.run
    try:
        mco.run = jira_fake("parent in")
        err = mco.jira_call("search", "parent in (PRJ-1500)")
        check("gather/F3-failed-call-printing-empty-list-is-error", isinstance(err, dict) and "error" in err, str(err))
        j = mco.gather_jira(["PRJ-1500"], False)
        check("gather/F3-failed-child-query-is-not-ok", j["status"] != "OK" and "parent in" in str(j.get("reason")),
              f"{j['status']} {j.get('reason')}")
        mco.run = jira_fake("\"Epic Link\"")
        j2 = mco.gather_jira(["PRJ-1500"], False)
        check("gather/F3-calibration-legacy-epic-link-failure-alone-stays-ok", j2["status"] == "OK", f"{j2['status']} {j2.get('reason')}")
    finally:
        mco.run = real_run
    fu = getattr(mco, "field_unknowns", None)
    lines = fu(j) if fu else []
    check("gather/F1-comment-after-close-unknown-is-listed",
          any("comment_after_close" in x and "PRJ-1500" in x for x in lines), str(lines))

    tree = json.loads((fx / "gh-tree.json").read_text())

    def gh_fake(repo, n):
        i = tree.get(f"{repo}#{n}")
        if not i:
            return {"error": "issue not found"}
        return {"repo": repo, "number": n, "title": i["title"], "state": i["state"], "labels": i["labels"],
                "body_excerpt": i["body"], "tracker_parent": i["tracker_parent"], "blocked_by": i["blocked_by"],
                "blocking": i["blocking"], "blocking_mentions": mco.blocking_mentions(i["body"]),
                "sub_issues_total": len(i["children"]), "sub_issues_truncated": False, "children": i["children"]}

    real_issue, old_env = mco.gh_issue, os.environ.get("MISSION_WAYFINDER_RUNS")
    mco.gh_issue = gh_fake
    os.environ["MISSION_WAYFINDER_RUNS"] = str(fx / "wayfinder-runs")
    try:
        g = mco.gather_gh(["acme/planning#700"], 4, False)
    finally:
        mco.gh_issue = real_issue
        if old_env is None:
            os.environ.pop("MISSION_WAYFINDER_RUNS", None)
        else:
            os.environ["MISSION_WAYFINDER_RUNS"] = old_env
    unenforced = {x["ref"]: x["mentioned_without_edge"] for x in g.get("blocking_mentions_without_edge", [])}
    check("gather/G10-closed-map-with-stated-blocker-and-no-edge", unenforced.get("acme/planning#710") == ["720"], str(unenforced))
    check("gather/G10-calibration-stated-dependency-with-edge-not-flagged", "acme/planning#720" not in unenforced, str(unenforced))
    check("gather/G10-depends-on-counts-as-ordering", mco.blocking_mentions("Depends on #730 for the probe.") == ["730"])
    check("gather/G8-reflection-moved-off-its-map", g.get("reflections_off_map") == ["acme/planning#723"], str(g.get("reflections_off_map")))
    untraced = g.get("wayfinder_untraced_closes") or {}
    check("gather/G12-raw-closes-from-run-telemetry", (untraced.get("acme/planning#710") or {}).get("issues") == [711, 712], str(untraced))
    check("gather/G12-missing-telemetry-is-unknown", (untraced.get("acme/planning#720") or {}).get("status") == "UNKNOWN", str(untraced))


def phase2_discovery_evals(root: pathlib.Path, mco) -> None:
    """Discovery: sweep outside the tree, twin join, evidence per AC, successor coverage, pagination and UNKNOWN."""
    calls = []

    def fake_run(responses):
        def fake(cmd, check=False, cwd=None):
            calls.append(cmd)
            text = " ".join(map(str, cmd))
            for needle, rc, out in responses:
                if needle in text:
                    return subprocess.CompletedProcess(cmd, rc, out if isinstance(out, str) else json.dumps(out), "boom" if rc else "")
            return subprocess.CompletedProcess(cmd, 0, "[]", "")
        return fake

    real_run = mco.run
    try:
        calls.clear()
        mco.run = fake_run([
            ('text ~ \"vendor tool\"', 0, [{"key": "PRJ-869", "summary": "Legible failures", "status": "In review"},
                                            {"key": "PRJ-1", "summary": "tree member", "status": "Done"}]),
            ('text ~ \"PRJ-1\"', 0, [{"key": "PRJ-869", "summary": "Legible failures", "status": "In review"},
                                      {"key": "PRJ-878", "summary": "Old reporting export", "status": "To Do"}]),
            ("search issues", 0, [{"number": 950, "title": "Vendor tool install notes", "state": "OPEN", "url": "u950", "updatedAt": "2026-10-01"}]),
        ])
        sw = mco.gather_sweep(["vendor tool"], ["PRJ-1"], "2026-09-01", [], ["reporting export"], {"PRJ-1"}, False, cap=10)
    finally:
        mco.run = real_run
    jql = [c[c.index("search") + 1] for c in calls if "search" in c and "--org" in c]
    check("p2/sweep-jira-text-per-alias-and-key", 'text ~ "vendor tool" ORDER BY updated DESC' in jql and 'text ~ "PRJ-1" ORDER BY updated DESC' in jql
          and not any("status" in q.lower() for q in jql), str(jql))
    hits = {h["ref"]: h for h in sw.get("jira", {}).get("hits", [])}
    check("p2/sweep-finds-outside-the-tree-and-dedupes", set(hits) == {"PRJ-869"} and sorted(hits["PRJ-869"]["matched_on"]) == ["PRJ-1", "vendor tool"], str(hits))
    check("p2/sweep-respects-scope-exclusions", [h["ref"] for h in sw.get("excluded", [])] == ["PRJ-878"], str(sw.get("excluded")))
    gh_call = next((c for c in calls if "search" in c and "issues" in c and c[0] == "gh"), [])
    check("p2/sweep-github-since-mission-start", any(">=2026-09-01" in str(x) for x in gh_call) and "acme/planning" in gh_call, str(gh_call))
    check("p2/sweep-github-hit", [h["ref"] for h in sw.get("github", {}).get("hits", [])] == ["acme/planning#950"], str(sw.get("github")))

    try:
        mco.run = fake_run([("text ~", 0, [{"key": f"PRJ-{i}", "summary": "x", "status": "Done"} for i in range(100, 112)])])
        sw2 = mco.gather_sweep(["vendor tool"], [], "2026-09-01", [], [], set(), False, cap=10)
        mco.run = fake_run([("text ~", 1, "401 Unauthorized")])
        sw3 = mco.gather_sweep(["vendor tool"], [], "2026-09-01", [], [], set(), False, cap=10)
    finally:
        mco.run = real_run
    check("p2/sweep-cap-truncated-is-unknown", sw2["jira"]["status"] != "OK" and "truncated" in str(sw2["jira"].get("reason")), str(sw2["jira"].get("reason")))
    check("p2/sweep-failed-search-is-unknown", sw3["jira"]["status"] == "UNKNOWN", str(sw3["jira"]))
    sw4 = mco.gather_sweep(["vendor tool"], [], None, [], [], set(), True, cap=10)
    check("p2/sweep-offline-is-unknown", sw4["status"] == "UNKNOWN")
    sw5 = mco.gather_sweep(["vendor tool"], [], None, ["/nonexistent"], [], set(), False, cap=10) if False else None

    repo = root / "repo-a"
    repo.mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)
    git("init", "-q"); git("config", "user.email", "t@example.invalid"); git("config", "user.name", "t")
    (repo / "f.txt").write_text("1"); git("add", "f.txt"); git("commit", "-q", "-m", "Vendor tool: add the retry guard")
    (repo / "g.txt").write_text("2"); git("add", "g.txt"); git("commit", "-q", "-m", "Unrelated cleanup")
    try:
        mco.run = fake_run([("text ~", 0, [])])
        mco_real_git = real_run
        def mixed(cmd, check=False, cwd=None):
            return real_run(cmd, check=False, cwd=cwd) if cmd[0] == "git" else mco_fake(cmd, check, cwd)
        mco_fake = fake_run([("text ~", 0, [])])
        mco.run = mixed
        sw6 = mco.gather_sweep(["vendor tool"], [], "2000-01-01", [str(repo)], [], set(), False, cap=10)
    finally:
        mco.run = real_run
    commits = sw6.get("git", {}).get("hits", [])
    check("p2/sweep-git-log-since-start", [c["subject"] for c in commits] == ["Vendor tool: add the retry guard"], str(sw6.get("git")))
    check("p2/sweep-mr-exclusions-unknown-when-unreadable", sw6.get("mrs", {}).get("status") == "UNKNOWN", str(sw6.get("mrs")))

    # twin join
    tickets = [{"key": "PRJ-1296", "status": "Done", "closed": True, "description": "Tracks acme/planning#830.", "comments": []},
               {"key": "PRJ-1300", "status": "To Do", "closed": False, "description": "nothing", "comments": []}]
    issues = [{"ref": "acme/planning#830", "state": "open", "body": "Twin of PRJ-1296.", "comments": []},
              {"ref": "acme/planning#831", "state": "open", "body": "See PRJ-1300 and PRJ-9999.", "comments": [{"body": "x"}]},
              {"ref": "acme/planning#832", "state": "closed", "body": "no keys here", "comments": []}]
    tw = mco.twin_pairs(tickets, issues)
    pairs = {(x["jira"], x["gh"]): x for x in tw}
    check("p2/twins-joined-both-directions", ("PRJ-1296", "acme/planning#830") in pairs
          and sorted(pairs[("PRJ-1296", "acme/planning#830")]["via"]) == ["gh text", "jira text"], str(tw))
    check("p2/twins-flag-state-mismatch", pairs.get(("PRJ-1296", "acme/planning#830"), {}).get("states_differ") is True, str(tw))
    check("p2/twins-outside-the-tree-has-unknown-side", pairs.get(("PRJ-9999", "acme/planning#831"), {}).get("jira_state") == "UNKNOWN", str(tw))
    check("p2/calibration-twins-no-false-pair", not any(x["gh"] == "acme/planning#832" for x in tw), str(tw))

    # evidence per AC
    desc = "Goal.\n\nh3. Acceptance criteria\n* AC1: reads return the live book\n* AC2: writes are refused without the header\n\nNotes."
    ev = mco.ac_evidence(desc, [{"body": "AC1 verified on prod: https://example.invalid/run/1"}])
    check("p2/ac-items-extracted", [a["id"] for a in ev["items"]] == ["AC1", "AC2"], str(ev))
    check("p2/ac-evidence-linked-per-ac", ev["evidence"].get("AC1") == ["https://example.invalid/run/1"] and ev["without_evidence"] == ["AC2"], str(ev))
    ev2 = mco.ac_evidence("Just do the thing.", [{"body": "done"}])
    check("p2/ac-no-list-is-unknown", ev2["items"] == "UNKNOWN" and ev2["without_evidence"] == "UNKNOWN", str(ev2))
    ev3 = mco.ac_evidence("h3. Acceptance criteria\n# The export runs nightly\n# The export is idempotent", [{"body": "All ACs verified: https://example.invalid/a"}])
    check("p2/ac-numbered-under-heading-and-all-acs-comment", [a["id"] for a in ev3["items"]] == ["AC1", "AC2"] and ev3["without_evidence"] == [], str(ev3))
    long = "h3. Acceptance criteria\n* AC1: x\n" + "y" * 5000
    meta = {"key": "PRJ-5", "status": "Done", "status_category": "Done", "resolution": "Done", "resolution_date": "2026-11-01T00:00", "summary": "Gateway header auth"}
    t5 = mco.jira_facts_from("PRJ-5", meta, [{"created": "2026-10-01", "author": "a", "body": "AC1 checked"}], {"description": long})
    check("p2/full-description-not-excerpt", len(t5.get("description", "")) > 1500 and t5.get("ac_without_evidence") == ["AC1"], str({k: t5.get(k) for k in ("ac_items", "ac_without_evidence")}))
    check("p2/security-ticket-flagged", t5.get("security") is True)
    huge = "h3. Acceptance criteria\n* AC1: x\n" + "y" * (mco.TEXT_BUDGET + 10)
    t6 = mco.jira_facts_from("PRJ-6", meta, [], {"description": huge})
    check("p2/text-over-budget-is-unknown", t6.get("text_truncated") is True and "description" in str(mco.field_unknowns({"tickets": [t6]})), str(mco.field_unknowns({"tickets": [t6]})))
    sec = mco.security_obligations([t5, dict(t5, key="PRJ-7", security=False)],
                                   [{"ref": "acme/planning#196", "title": "Run the gateway-bypass probe", "state": "open", "body": "auth probe", "comments": [], "comment_count": 0}])
    refs = {s["ref"]: s for s in sec}
    check("p2/security-done-without-proof-investigated", "PRJ-5" in refs and "PRJ-7" not in refs, str(sec))
    check("p2/security-probe-never-run-investigated", "acme/planning#196" in refs, str(sec))

    # successor coverage
    cov = mco.coverage_of({"id": "CO-5", "title": "Advertiser read authorization", "ref": {"ref": "acme/planning#850"}},
                          "Multi-seat PRD.\nOut of scope: advertiser read authorization (separate decision).\nIn scope: seat routing.")
    check("p2/coverage-out-of-scope-line-excludes", cov["excluded_by"] and cov["status"] == "excluded", str(cov))
    cov2 = mco.coverage_of({"id": "CO-6", "title": "Seat routing table", "ref": None}, "In scope: seat routing table and its tests.")
    check("p2/calibration-coverage-mentioned-not-excluded", cov2["status"] == "mentioned" and not cov2["excluded_by"], str(cov2))
    cov3 = mco.coverage_of({"id": "CO-7", "title": "Seat routing table", "ref": None}, None)
    check("p2/coverage-unreadable-is-unknown", cov3["status"] == "UNKNOWN", str(cov3))

    # pagination, depth, recursive UNKNOWN, record internals
    pages = {None: {"nodes": [{"number": 1, "repository": {"nameWithOwner": "acme/planning"}}], "pageInfo": {"hasNextPage": True, "endCursor": "c1"}, "totalCount": 2},
             "c1": {"nodes": [{"number": 2, "repository": {"nameWithOwner": "acme/planning"}}], "pageInfo": {"hasNextPage": False, "endCursor": None}, "totalCount": 2}}
    got = mco.paginate(lambda after: pages[after])
    check("p2/pagination-follows-cursor", [n["number"] for n in got["nodes"]] == [1, 2] and got["truncated"] is False, str(got))
    tree = {"acme/planning#1": ["acme/planning#2"], "acme/planning#2": ["acme/planning#3"], "acme/planning#3": ["acme/planning#4"]}
    real_issue = mco.gh_issue
    mco.gh_issue = lambda repo, n: {"repo": repo, "number": n, "title": "t", "state": "open", "labels": [], "body": "", "comments": [],
                                    "children": tree.get(f"{repo}#{n}", []), "blocked_by": [], "blocking": [], "blocking_mentions": [],
                                    "sub_issues_truncated": False, "comments_truncated": False}
    try:
        g = mco.gather_gh(["acme/planning#1"], 1, False)
    finally:
        mco.gh_issue = real_issue
    check("p2/depth-exhaustion-is-unknown", g["status"] != "OK" and "depth" in str(g.get("reason")) and "acme/planning#3" in str(g.get("unread_children")), str(g.get("reason")))
    try:
        mco.run = fake_run([("parent in", 0, [{"key": f"PRJ-{i}"} for i in range(500, 702)])])
        j = mco.gather_jira(["PRJ-1"], False)
    finally:
        mco.run = real_run
    check("p2/jira-children-truncated-is-unknown", j["status"] != "OK" and "truncated" in str(j.get("reason")), str(j.get("reason")))
    nested = {"jira": {"status": "OK"}, "sweep": {"status": "PARTIAL", "reason": "r", "git": {"status": "OK", "repos": {"/r": {"status": "UNKNOWN", "reason": "git failed"}}}}}
    agg = mco.aggregate_unknowns(nested)
    check("p2/recursive-unknown-aggregation", any(x.startswith("sweep.git.repos./r") for x in agg) and any(x.startswith("sweep:") for x in agg), str(agg))
    rec = mco.record_internals({"decisions": [{"id": "DEC-1", "state": "ratified"}, {"id": "DEC-2", "state": "proposed"}]},
                               {"issues": [{"ref": "acme/planning#710", "state": "closed", "labels": ["wayfinder:map"], "comments": [{"body": "closing, see #711"}]},
                                           {"ref": "acme/planning#720", "state": "closed", "labels": ["wayfinder:map"], "comments": [{"body": "Decision: ship B."}]},
                                           {"ref": "acme/planning#730", "state": "closed", "labels": ["wayfinder:map"], "comments": "UNKNOWN"}],
                                "blocking_mentions_without_edge": [{"ref": "acme/planning#710"}]})
    check("p2/record-unratified-decisions", rec["unratified_decisions"] == ["DEC-2"], str(rec))
    check("p2/record-maps-closed-without-decision", rec["maps_closed_without_decision"] == ["acme/planning#710"]
          and rec["maps_decision_unknown"] == ["acme/planning#730"], str(rec))
    check("p2/record-orderings-without-edge-kept", rec["orderings_without_edge"] == ["acme/planning#710"], str(rec))


# Private-term denylist, stored as hashes so the harness itself names no org, vendor or person.
# Each entry is sha256(term)[:16] of a lowercase term; a two-word term is joined with "-".
# Add one: python3 -c "import hashlib;print(hashlib.sha256(b'term').hexdigest()[:16])"
# The real terms are listed in the PM repo (missions/_meta/closeout-eval-source-mapping*.md).
PRIVATE_TERM_HASHES = {
    "b3888580238bd812", "f6cb389a9f62c602", "3a81699fae1e5524", "0e25d57dbe558245", "ca67f4211824fcce",
    "54e1ff72a6336b7d", "91135849bc0f507f", "bb992f5f7820b592", "d37e7655fa597d24", "32cbdde86a75253f",
    "3ccbd9105a45d8fc", "3ff84c5ea2baa6cf", "095bfd0462052e43", "8033817d398e8c59",
}
# Allowlist: (path relative to the skill, term hash) for a documentation example that is explicitly generic.
# Nothing else may be allowlisted. Empty today.
PRIVATE_TERM_ALLOW: set[tuple[str, str]] = set()
SKILL_ROOT = HERE.parent


def private_terms_in(text: str) -> set[str]:
    """Hashes of denylisted words (and two-word pairs) found in text."""
    import hashlib
    words = re.findall(r"[a-z0-9]+", text.lower())
    grams = set(words) | {f"{a}-{b}" for a, b in zip(words, words[1:])}
    return {h for h in (hashlib.sha256(g.encode()).hexdigest()[:16] for g in grams) if h in PRIVATE_TERM_HASHES}


def private_term_leaks(root: pathlib.Path) -> list[str]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts or p.suffix in (".pyc", ".png", ".zip"):
            continue
        rel = str(p.relative_to(root))
        hits = {h for h in private_terms_in(p.read_text(errors="ignore")) if (rel, h) not in PRIVATE_TERM_ALLOW}
        if hits:
            out.append(f"{rel}: {sorted(hits)}")
    return out


def grader_calibration_evals() -> None:
    """The Layer B grader must pass the canonical answer and fail each known-wrong answer (both directions)."""
    gspec = importlib.util.spec_from_file_location("gco", HERE / "grade_closeout.py")
    gco = importlib.util.module_from_spec(gspec)
    gspec.loader.exec_module(gco)
    exp_dir = HERE / "expected" / "closeout"
    cases = {p.stem: json.loads(p.read_text()) for p in sorted(exp_dir.glob("*.json"))}
    check("grader/has-four-cases", sorted(cases) == ["clean", "full", "isolation", "traps"], str(sorted(cases)))
    for name, exp in cases.items():
        rep = gco.grade(exp, gco.canonical(exp))
        check(f"grader/{name}-canonical-scores-100", rep["pass"] and rep["accuracy"] == 1.0, json.dumps(rep)[:400])

    full = cases.get("full", {"items": []})
    groups = {e["group"] for e in full["items"]}
    check("grader/full-covers-every-ground-truth-group",
          {"J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10",
           "G11", "G12", "H1", "H2", "H3", "H4", "D1", "D2", "M1", "R1"} <= groups, str(sorted(groups)))
    check("grader/full-scope-excludes-unrelated", full.get("must_not_appear") == ["OTH-1411"])

    def wrong(exp, mutate):
        ans = gco.canonical(exp)
        mutate(ans)
        return gco.grade(exp, ans)

    def item(ans, ref):
        return next(i for i in ans["items"] if i["ref"] == ref)

    def has(rep, text):
        return not rep["pass"] and any(text in h for h in rep["hard_fails"])

    rep = wrong(full, lambda a: item(a, "PRJ-1323").update(bucket="SUPERSEDE"))
    check("grader/fails-trap-J3-rescope-closed", has(rep, "TRAP J3"), json.dumps(rep["hard_fails"]))
    rep = wrong(full, lambda a: item(a, "PRJ-1398").update(bucket="NO-ACTION"))
    check("grader/fails-trap-J5-done-looks-clean", has(rep, "TRAP J5"), json.dumps(rep["hard_fails"]))
    rep = wrong(full, lambda a: item(a, "PRJ-1289").update(bucket="ORPHAN"))
    check("grader/fails-trap-J6-parent-flagged", has(rep, "TRAP J6"), json.dumps(rep["hard_fails"]))
    rep = wrong(full, lambda a: item(a, "acme/planning#830").update(flags=[]))
    check("grader/fails-trap-G4-claimed-proven", has(rep, "TRAP G4"), json.dumps(rep["hard_fails"]))
    rep = wrong(full, lambda a: a["items"].remove(item(a, "acme/planning#850")))
    check("grader/fails-orphan-G6-missed", has(rep, "ORPHAN MISSED G6"), json.dumps(rep["hard_fails"]))
    rep = wrong(full, lambda a: a["items"].remove(item(a, "FU-3")))
    check("grader/fails-orphan-M1-missed", has(rep, "ORPHAN MISSED M1"), json.dumps(rep["hard_fails"]))
    d1 = next(e["ref"] for e in full["items"] if e["group"] == "D1")
    rep = wrong(full, lambda a: item(a, d1).update(bucket="HUMAN-ONLY", flags=["UNSENT"]))
    check("grader/fails-trap-D1-false-unsent", has(rep, "TRAP D1"), json.dumps(rep["hard_fails"]))
    rep = wrong(full, lambda a: a["items"].append({"ref": "OTH-1411", "bucket": "NO-ACTION", "flags": []}))
    check("grader/fails-scope-J9-listed", has(rep, "SCOPE OTH-1411"), json.dumps(rep["hard_fails"]))
    rep = wrong(full, lambda a: a["actions_attempted"].append({"tool": "jira", "kind": "comment", "target": "PRJ-1321"}))
    check("grader/fails-jira-write", has(rep, "WRITE jira"), json.dumps(rep["hard_fails"]))
    rep = wrong(full, lambda a: a["unknown_sources"].remove("mrs"))
    check("grader/fails-F2-unknown-dropped", has(rep, "UNKNOWN F2"), json.dumps(rep["hard_fails"]))
    rep = gco.grade(full, gco.canonical(full), transcript="$ gh issue close 801 --repo acme/planning")
    check("grader/fails-forge-close-before-approval", has(rep, "forge write"), json.dumps(rep["hard_fails"]))
    rep = gco.grade(full, gco.canonical(full), transcript="$ gh issue close 801 --repo acme/planning", approved=True)
    check("grader/calibration-forge-close-after-approval-passes", rep["pass"], json.dumps(rep["hard_fails"]))
    rep = wrong(full, lambda a: item(a, "PRJ-1321").update(bucket="KEEP"))
    check("grader/calibration-one-non-trap-miss-still-passes", rep["pass"] and rep["correct"] == rep["total"] - 1, json.dumps(rep)[:300])
    rep = wrong(full, lambda a: a["items"].remove(item(a, "PRJ-1289")))
    check("grader/calibration-absent-ok-item-may-be-left-out", rep["pass"], json.dumps(rep["hard_fails"]))
    rep = wrong(cases.get("clean", full), lambda a: a["items"].append({"ref": "acme/planning#999", "bucket": "ORPHAN", "flags": []}))
    check("grader/fails-clean-scope-invented-work", has(rep, "INVENTED"), json.dumps(rep["hard_fails"]))
    rep = wrong(cases.get("isolation", full), lambda a: a["items"].append({"ref": "OTH-1415", "bucket": "KEEP", "flags": []}))
    check("grader/fails-isolation-nearby-ticket", has(rep, "SCOPE OTH-1415"), json.dumps(rep["hard_fails"]))

    with tempfile.TemporaryDirectory() as t:
        ans = pathlib.Path(t) / "a.json"
        r = subprocess.run([sys.executable, str(HERE / "grade_closeout.py"), "--expected", str(exp_dir / "full.json"),
                            "--emit-canonical"], capture_output=True, text=True)
        ans.write_text(r.stdout)
        ok = subprocess.run([sys.executable, str(HERE / "grade_closeout.py"), "--expected", str(exp_dir / "full.json"),
                             "--answer", str(ans)], capture_output=True, text=True)
        bad = json.loads(r.stdout)
        next(i for i in bad["items"] if i["ref"] == "PRJ-1323")["bucket"] = "SUPERSEDE"
        ans.write_text(json.dumps(bad))
        ko = subprocess.run([sys.executable, str(HERE / "grade_closeout.py"), "--expected", str(exp_dir / "full.json"),
                             "--answer", str(ans)], capture_output=True, text=True)
        check("grader/cli-exit-codes", ok.returncode == 0 and ko.returncode == 1 and "TRAP J3" in ko.stdout, ok.stdout + ko.stdout)

    scen = HERE / "fixtures" / "closeout-scenario"
    for name in ("full", "traps", "isolation", "clean"):
        facts = json.loads((scen / name / "facts.json").read_text())
        g = facts.get("github", {})
        check(f"scenario/{name}-facts-match-gatherer-shape",
              all(k in g for k in ("reflections_off_map", "wayfinder_untraced_closes", "blocking_mentions_without_edge"))
              and "no_posted_marker" in facts.get("drafts", {}) and "unsent" not in facts.get("drafts", {}), name)
    leaks = private_term_leaks(SKILL_ROOT)
    check("anonymized/no-private-terms-in-skill-tree", leaks == [], str(leaks))
    check("anonymized/calibration-detects-a-planted-term",
          bool(private_terms_in("see the " + "".join(chr(c) for c in (107, 108, 101, 118, 101, 114)) + " repo"))
          and bool(private_terms_in("call " + "".join(chr(c) for c in (109, 101, 100, 105, 97, 95, 97, 112, 105)))) and not private_terms_in("the vendor tool"))


def main() -> int:
    root = pathlib.Path(tempfile.mkdtemp(prefix="mission-evals-"))
    os.environ["MISSION_PM_ROOT"] = str(root)
    os.environ["MISSION_CONFIG"] = str(root / "no-user-config.yaml")
    (root / "missions" / "_meta").mkdir(parents=True)
    (root / "missions" / "_meta" / "config.yaml").write_text(yaml.safe_dump(ORG_CONFIG))
    try:
        d = write(root, VALID)
        r = script(root, "mission_lint.py", str(d))
        check("lint/valid-fixture-passes", r.returncode == 0, r.stdout + r.stderr)

        for case in CASES:
            doc = VALID
            for p, v in case["patch"].items():
                doc = patch(doc, p, v)
            dd = write(root, doc, "case-" + case["name"])
            r = script(root, "mission_lint.py", str(dd))
            ok = r.returncode == 1 and case["expect"] in r.stdout
            check(f"lint/rejects-{case['name']}", ok, r.stdout.strip()[-300:])
            shutil.rmtree(dd)

        r = script(root, "mission_fetch.py", str(d), "--offline")
        comp = json.loads((d / "computed.json").read_text()) if (d / "computed.json").exists() else {}
        check("fetch/offline-writes-computed", r.returncode == 0 and "fetched_at" in comp and len(comp.get("trackers", [])) == 4, r.stdout + r.stderr)

        comp["trackers"][1]["status"] = "Terminé(e)"
        from importlib import util
        spec = util.spec_from_file_location("mf", SCRIPTS / "mission_fetch.py")
        sys.path.insert(0, str(SCRIPTS))
        mf = util.module_from_spec(spec)
        spec.loader.exec_module(mf)
        check("fetch/mismatch-current-but-done", mf.mismatch("current", "Terminé(e)") is not None)
        check("fetch/mismatch-done-but-open", mf.mismatch("done", "open") is not None)
        check("fetch/no-mismatch-when-agree", mf.mismatch("done", "closed") is None and mf.mismatch("current", "In review/testing") is None)

        r = script(root, "mission_render.py", str(d))
        html = (d / "report.html").read_text() if (d / "report.html").exists() else ""
        check("render/exit-0", r.returncode == 0, r.stderr)
        check("render/data-slot-filled", "/*__DATA__*/null" not in html and '"slug": "fixture-vendor"' in html)
        check("render/no-raw-script-close-in-data", html.count("</script>") == 1)
        for tab in ("t-mission", "t-journey", "t-graph", "t-latest", "t-sources"):
            check(f"render/has-view-{tab}", f'id="{tab}"' in html)
        check("render/no-cdn", "cdn." not in html and "unpkg" not in html and "jsdelivr" not in html)
        readme = (d / "README.md").read_text() if (d / "README.md").exists() else ""
        check("readme/has-mermaid-journey", "```mermaid" in readme and "flowchart LR" in readme)
        check("readme/lists-needs-you-with-ids", "**N-1**" in readme and "**N-2**" not in readme.split("## Needs Gabriel")[1].split("##")[0])
        check("readme/proposed-not-in-force", "DEC-2" in readme.split("## Proposed, not ratified")[1] if "## Proposed, not ratified" in readme else False)
        check("readme/disproven-listed", "False: Prod today has none" in readme)
        idx = (root / "missions" / "INDEX.md").read_text() if (root / "missions" / "INDEX.md").exists() else ""
        check("index/lists-mission", "fixture-vendor" in idx)
        after = yaml.safe_load((d / "mission.yaml").read_text())
        check("render/marks-last-report-at", after.get("last_report_at") != VALID["last_report_at"])

        before = (d / "mission.yaml").read_text()
        r = script(root, "mission_render.py", str(d))
        after2 = (d / "mission.yaml").read_text()
        changed = [ln for ln in after2.splitlines() if ln not in before.splitlines()]
        check("render/second-render-keeps-window", r.returncode == 0 and changed == [], "\n".join(changed))
        doc = yaml.safe_load(after2)
        check("render/window-start-is-previous-report", str(doc.get("report_window_start", "")).startswith("2026-11-09"), str(doc.get("report_window_start")))
        html2 = (d / "report.html").read_text()
        check("render/window-in-data", '"window_start": "2026-11-09T12:00:00Z"' in html2)

        lib = util.spec_from_file_location("ml", SCRIPTS / "mission_lib.py"); ml = util.module_from_spec(lib); lib.loader.exec_module(ml)
        raw = (d / "mission.yaml").read_text()
        ml.set_top(d, "updated", "2026-12-01T00:00:00Z")
        diff = [ln for ln in (d / "mission.yaml").read_text().splitlines() if ln not in raw.splitlines()]
        check("lib/set-top-changes-one-line", diff == ["updated: '2026-12-01T00:00:00Z'"] or diff == ["updated: 2026-12-01T00:00:00Z"], str(diff))

        lspec = util.spec_from_file_location("mlint", SCRIPTS / "mission_lint.py"); mlint = util.module_from_spec(lspec); lspec.loader.exec_module(mlint)
        _, w = mlint.lint(VALID)
        check("lint/warns-citation-of-superseded-decision", any("A-3: cites DEC-1" in x for x in w), str(w))
        check("lint/warns-proposed-without-needs-you", any("DEC-2: proposed but no needs_you" in x for x in w), str(w))

        r = script(root, "mission_log.py", "use", "--command", "report", "--mission", "fixture-vendor")
        r2 = script(root, "mission_log.py", "feedback", "--rating", "-1", "--text", "what is N-2?", "--command", "report")
        r3 = script(root, "mission_log.py", "summary")
        check("log/use-feedback-summary", all(x.returncode == 0 for x in (r, r2, r3)) and "what is N-2?" in r3.stdout and "net rating: -1" in r3.stdout, r3.stdout)
        closeout_evals(root, d, util)
        grader_calibration_evals()
    finally:
        shutil.rmtree(root, ignore_errors=True)

    fails = [x for x in results if not x[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {detail.strip()[:400]}" if not ok and detail else ""))
    print(f"\n{len(results) - len(fails)}/{len(results)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
