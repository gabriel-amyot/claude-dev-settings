#!/usr/bin/env python3
"""Layer A suite for batch-skill-pipeline triage mode (scripts/triage/).

Copies fixtures/triage/ (3 tiny proposals, fake Claude results, fake Codex outputs: one with
prose around the JSON, one missing) to a temp dir per case. Never touches the real
~/.claude/skill-proposals. Run: python3 run_triage_evals.py  (exit 0 = all pass)

Discriminating cases:
  - gamma: Claude ARCHIVE, Codex BUILD. Codex must win, so archive must NOT move gamma.
  - beta:  Claude UPDATE, Codex ARCHIVE (Codex JSON wrapped in prose). Archive moves only beta.
  - alpha: Codex output file missing. The Claude verdict must stand.
  - run_codex.sh: codex exits 0 but writes an empty or no output file (the known silent
    failure). The launcher must exit non-zero.
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures", "triage")
S = os.path.join(os.path.dirname(HERE), "scripts", "triage")
PY = sys.executable
PASS = FAIL = 0
ALPHA, BETA, GAMMA = "2026-01-01-alpha-tool.md", "2026-02-01-beta-check.md", "2026-03-01-gamma-sweep.md"


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def sh(args, env=None):
    p = subprocess.run(args, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=120)
    return p.returncode, p.stdout + p.stderr


def fresh():
    tmp = tempfile.mkdtemp(prefix="triage-eval-")
    shutil.copytree(os.path.join(FIX, "proposals"), os.path.join(tmp, "proposals"))
    shutil.copytree(os.path.join(FIX, "run"), os.path.join(tmp, "run"))
    run, props = os.path.join(tmp, "run"), os.path.join(tmp, "proposals")
    rc, out = sh([PY, f"{S}/split_batches.py", "--run-dir", run, "--proposals-dir", props, "--size", "2",
                  "--installed", "5", "--transcript-dir", "/nonexistent/transcripts"])
    if rc != 0:
        sys.exit(f"FATAL split_batches failed: {out}")
    return tmp, run, props


def lines(path):
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def case_split():
    print("split_batches")
    tmp, run, _ = fresh()
    check("batch-aa newest first", lines(f"{run}/batches/batch-aa.txt") == [GAMMA, BETA],
          lines(f"{run}/batches/batch-aa.txt"))
    check("batch-ab holds the oldest", lines(f"{run}/batches/batch-ab.txt") == [ALPHA])
    inv = lines(f"{run}/inventory.tsv")
    check("inventory newest first", inv[1].split("\t")[2] == GAMMA, inv[1:2])
    brief = open(f"{run}/brief.md").read()
    check("brief placeholders filled", "{{" not in brief and "/nonexistent/transcripts" in brief)
    st = json.load(open(f"{run}/STATE.json"))
    check("state records P1 done and the batches", st["phases"].get("P1") == "done" and set(st["batches"]) == {"batch-aa", "batch-ab"})
    shutil.rmtree(tmp)


def case_final():
    print("final_verdicts")
    tmp, run, _ = fresh()
    rc, out = sh([PY, f"{S}/final_verdicts.py", "--run-dir", run])
    fv = json.load(open(f"{run}/final-verdicts.json"))
    check("final_verdicts exits 0", rc == 0, out)
    check("Codex wins on conflict (gamma BUILD over Claude ARCHIVE)",
          fv[GAMMA]["verdict"] == "BUILD" and fv[GAMMA]["source"] == "codex", fv.get(GAMMA))
    check("Codex JSON wrapped in prose parses (beta ARCHIVE)", fv[BETA]["verdict"] == "ARCHIVE", fv.get(BETA))
    check("Claude stands when Codex is missing (alpha BUILD)",
          fv[ALPHA]["verdict"] == "BUILD" and fv[ALPHA]["source"] == "claude", fv.get(ALPHA))
    check("final score is the mean of both passes", fv[GAMMA]["final_score"] == 40, fv[GAMMA].get("final_score"))
    shutil.rmtree(tmp)


def case_render():
    print("render")
    tmp, run, props = fresh()
    sh([PY, f"{S}/final_verdicts.py", "--run-dir", run])
    rc, out = sh([PY, f"{S}/render.py", "--run-dir", run])
    page = open(f"{run}/triage.html").read()
    check("render exits 0", rc == 0, out)
    check("every proposal name present", all(n in page for n in ("alpha-tool", "beta-check", "gamma-sweep")))
    check("decision controls present", all(k in page for k in ('class="action"', 'value="override"', 'value="hold"',
                                                                 'class="note"', "Export decisions", "localStorage",
                                                                 "decisions.json", "clipboard")))
    check("no external URLs", not re.search(r"https?://", page))
    style = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    check("no external assets", not re.search(r"<link\b|<script\s+src|<img\b|<iframe\b", page, re.I)
          and not re.search(r"@import|url\(", style, re.I))
    check("toolbar: search, filters, disagreements, sort",
          all(k in page for k in ('id="q"', 'id="vf"', 'id="gf"', 'id="dis"', 'id="sort"')))
    check("disagreement flag set on conflicts", re.search(r'data-file="2026-03-01-gamma-sweep.md"[^>]*data-disagree="1"', page, re.S) is not None)
    check("overall review rendered as Markdown, not <pre>",
          "<h4>Top 15 actions</h4>" in page and "<ol>" in page and "<b>too harsh</b>" in page and "<pre" not in page)
    check("top actions panel present", "Top actions" in page and "BUILD gamma-sweep" in page)
    check("auto-refresh while running", 'http-equiv="refresh" content="30"' in page)
    check("light and dark schemes", "prefers-color-scheme:dark" in page)
    st = json.load(open(f"{run}/STATE.json"))
    st["status"] = "done"
    json.dump(st, open(f"{run}/STATE.json", "w"))
    sh([PY, f"{S}/render.py", "--run-dir", run])
    check("no auto-refresh when done", 'http-equiv="refresh"' not in open(f"{run}/triage.html").read())
    shutil.rmtree(tmp)


def case_archive():
    print("archive")
    tmp, run, props = fresh()
    sh([PY, f"{S}/final_verdicts.py", "--run-dir", run])
    log_before = open(f"{props}/archive/REJECTION-LOG.md").read()
    rc, out = sh([PY, f"{S}/archive.py", "--run-dir", run, "--proposals-dir", props])
    check("dry run exits 0 and lists beta", rc == 0 and BETA in out, out)
    check("dry run moves nothing", all(os.path.exists(f"{props}/{f}") for f in (ALPHA, BETA, GAMMA)))
    check("dry run leaves the log alone", open(f"{props}/archive/REJECTION-LOG.md").read() == log_before)
    rc, out = sh([PY, f"{S}/archive.py", "--run-dir", run, "--proposals-dir", props, "--apply"])
    check("apply exits 0", rc == 0, out)
    check("apply moves beta (final ARCHIVE)", os.path.exists(f"{props}/archive/{BETA}") and not os.path.exists(f"{props}/{BETA}"))
    check("apply keeps gamma (Claude ARCHIVE, Codex BUILD) and alpha",
          os.path.exists(f"{props}/{GAMMA}") and os.path.exists(f"{props}/{ALPHA}"))
    log = open(f"{props}/archive/REJECTION-LOG.md").read()
    check("REJECTION-LOG gains one audit section", log.startswith(log_before) and log.count("## Audit") == 1
          and "| 2026-02-01-beta-check |" in log and "gamma-sweep |" not in log, log[-400:])
    check("backup tarball written", any(f.endswith(".tgz") for f in os.listdir(f"{run}/backups")))
    shutil.rmtree(tmp)


def case_hold():
    print("decisions")
    tmp, run, props = fresh()
    json.dump({"run": run, "decisions": {BETA: {"action": "hold", "note": "wait"},
                                         ALPHA: {"action": "override", "verdict": "SOP"}}},
              open(f"{run}/decisions.json", "w"))
    sh([PY, f"{S}/final_verdicts.py", "--run-dir", run])
    fv = json.load(open(f"{run}/final-verdicts.json"))
    check("hold decision sets HOLD", fv[BETA]["verdict"] == "HOLD" and fv[BETA]["source"] == "human")
    check("override decision replaces the verdict", fv[ALPHA]["verdict"] == "SOP")
    sh([PY, f"{S}/archive.py", "--run-dir", run, "--proposals-dir", props, "--apply"])
    check("held proposal never moves", os.path.exists(f"{props}/{BETA}"))
    shutil.rmtree(tmp)


STUB = """#!/bin/bash
out=""
while [ $# -gt 0 ]; do
  if [ "$1" = "--output-last-message" ]; then out="$2"; shift; fi
  shift
done
case "$STUB_MODE" in
  empty) : > "$out" ;;
  blank) printf '  \\n\\n' > "$out" ;;
  missing) : ;;
  ok) printf 'prose [\\n{"file": "x.md"}\\n]\\n' > "$out" ;;
  fail) exit 7 ;;
esac
echo "stub codex done"
exit 0
"""


def case_launcher():
    print("run_codex.sh")
    tmp, run, _ = fresh()
    bindir = os.path.join(tmp, "bin")
    os.makedirs(bindir)
    stub = os.path.join(bindir, "codex")
    with open(stub, "w") as fh:
        fh.write(STUB)
    os.chmod(stub, os.stat(stub).st_mode | stat.S_IEXEC)
    base = dict(os.environ, PATH=bindir + os.pathsep + os.environ["PATH"], CODEX_NEUTRAL_DIR=os.path.join(tmp, "neutral"))
    base.pop("CODEX_BIN", None)
    launcher = os.path.join(S, "run_codex.sh")
    for mode, want in (("empty", 4), ("blank", 4), ("missing", 3), ("fail", 7), ("ok", 0)):
        rc, out = sh(["/bin/bash", launcher, run, "batch", "batch-ab"], env=dict(base, STUB_MODE=mode))
        check(f"stub output {mode} -> exit {want}", rc == want, f"rc={rc} {out[-200:]}")
    prompt = open(f"{run}/codex/prompt-batch-ab.txt").read()
    check("prompt placeholders filled", "__RUN__" not in prompt and "__BATCH__" not in prompt and "results/batch-ab.json" in prompt)
    log = lines(f"{run}/codex/run.log")
    check("run.log has one line per call", len(log) == 5 and "status=empty-output" in log[0], log[:2])
    rc, out = sh(["/bin/bash", launcher, run, "nonsense"], env=base)
    check("bad kind exits 2", rc == 2, out)
    shutil.rmtree(tmp)


def main():
    for case in (case_split, case_final, case_render, case_archive, case_hold, case_launcher):
        case()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
