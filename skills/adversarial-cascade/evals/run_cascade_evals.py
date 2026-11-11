#!/usr/bin/env python3
"""Layer A suite for the adversarial-cascade Codex loop scripts. No model calls, no codex calls.
Run: `python3 evals/run_cascade_evals.py`. Exit 1 on any failure.

Pins: the codex command shape that the SOP proved works (read-only, neutral cwd, explicit effort,
stdin closed, --output-last-message); the prompt's verdict contract and round-2 re-attack framing;
parsing that never eats a finding and treats BLOCK-with-no-findings as noise; and the loop rules
(fix CRITICAL+MAJOR only, provenance by defect, scope conflicts escalate, the cap reports unresolved).
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS)
import triage  # noqa: E402

passed = 0
failed = 0


def ok(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {name} {detail}", file=sys.stderr)


def run(*args):
    return subprocess.run(list(args), capture_output=True, text=True, stdin=subprocess.DEVNULL)


with tempfile.TemporaryDirectory() as tmp:
    # ---- command construction ----
    prompt = os.path.join(tmp, "prompt.txt")
    with open(prompt, "w") as f:
        f.write("review this\n")
    r = run("bash", os.path.join(SCRIPTS, "run_codex.sh"), prompt, os.path.join(tmp, "out.md"), "--dry-run")
    cmd = r.stdout
    ok("C1 dry-run succeeds", r.returncode == 0, r.stderr)
    ok("C2 read-only sandbox", "-s read-only" in cmd)
    ok("C3 --skip-git-repo-check + neutral -C dir", "--skip-git-repo-check" in cmd and "-C " in cmd and "codex-neutral-" in cmd)
    ok("C4 explicit reasoning effort (config default is low)", "model_reasoning_effort=high" in cmd)
    ok("C5 stdin closed", "< /dev/null" in cmd)
    ok("C6 --output-last-message to the out file", "--output-last-message" in cmd and "out.md" in cmd)
    ok("C7 positional prompt from the file, not stdin '-'", '"$(cat' in cmd and " - " not in cmd)
    r = run("bash", os.path.join(SCRIPTS, "run_codex.sh"), prompt, os.path.join(tmp, "o.md"), "--effort", "xhigh", "--dry-run")
    ok("C8 effort override", "model_reasoning_effort=xhigh" in r.stdout)
    empty = os.path.join(tmp, "empty.txt")
    open(empty, "w").close()
    r = run("bash", os.path.join(SCRIPTS, "run_codex.sh"), empty, os.path.join(tmp, "o.md"), "--dry-run")
    ok("C9 an empty prompt file is refused (the empty-positional-prompt hang)", r.returncode == 2)

    # ---- prompt construction ----
    p1 = os.path.join(tmp, "p1.txt")
    r = run(sys.executable, os.path.join(SCRIPTS, "build_codex_prompt.py"), "--out", p1, "--repo", "/r", "--files", "a.py,b.py")
    text = open(p1).read() if r.returncode == 0 else ""
    ok("P1 round-1 prompt written", r.returncode == 0, r.stderr)
    ok("P2 disprove stance + read-only rules", "DISPROVE" in text and "Read-only" in text)
    ok("P3 verdict contract", "VERDICT: PASS or VERDICT: BLOCK" in text)
    ok("P4 four-word rubric", all(w in text for w in ("CRITICAL:", "MAJOR:", "MINOR:", "NIT:")))
    ok("P5 UNVERIFIED labelling demanded", "UNVERIFIED" in text)
    ok("P6 files listed", "- a.py" in text and "- b.py" in text)
    r = run(sys.executable, os.path.join(SCRIPTS, "build_codex_prompt.py"), "--out", os.path.join(tmp, "p2.txt"), "--repo", "/r", "--round", "2")
    ok("P7 round 2 without previous triage + fix range is refused", r.returncode != 0)
    prev = os.path.join(tmp, "prev.md")
    with open(prev, "w") as f:
        f.write("F1 MAJOR fixed in abc123\n")
    p2 = os.path.join(tmp, "p2.txt")
    r = run(sys.executable, os.path.join(SCRIPTS, "build_codex_prompt.py"), "--out", p2, "--repo", "/r", "--round", "2",
            "--previous", prev, "--fix-range", "aaa..bbb")
    t2 = open(p2).read() if r.returncode == 0 else ""
    ok("P8 round 2 re-attacks what the fixes could break", "what each FIX could break" in t2 and "aaa..bbb" in t2)
    ok("P9 round 2 keeps unchanged context in view", "unchanged context" in t2)
    ok("P10 round 2 carries the previous triage", "F1 MAJOR fixed in abc123" in t2)

# ---- parse ----
REVIEW = """Some reasoning.
### F1 [CRITICAL] token logged in plain text
File: a.py:10
### F2 [HIGH] wrong default
File: b.py:3
### F3 [MEDIUM] empty list edge
### F4 [LOW] naming
VERDICT: BLOCK
"""
r = triage.parse(REVIEW)
ok("R1 four findings parsed", len(r["findings"]) == 4)
ok("R2 HIGH normalizes to MAJOR, MEDIUM to MINOR, LOW to NIT",
   [f["severity"] for f in r["findings"]] == ["CRITICAL", "MAJOR", "MINOR", "NIT"])
ok("R3 verdict BLOCK, 2 blocking listed", r["verdict"] == "BLOCK" and r["blocking_listed"] == 2)
ok("R4 clean parse has no warnings", r["warnings"] == [], json.dumps(r["warnings"]))
r = triage.parse("## Findings\n\nthe path fails closed.\n\nVERDICT: BLOCK\n")
ok("R5 BLOCK with no findings is noise", any("noise" in w for w in r["warnings"]) and r["findings"] == [])
r = triage.parse("### F1 [MAJOR] x\nalso **[CRITICAL]** buried in prose\nVERDICT: BLOCK\n")
ok("R6 raw severity tags beyond parsed findings raise a parse-gap warning", any("raw text holds" in w for w in r["warnings"]))
r = triage.parse("### F1 [MAJOR] x\n")
ok("R7 a missing VERDICT line is flagged", any("no VERDICT" in w for w in r["warnings"]))
r = triage.parse("### F1 [CRITICAL] x\nVERDICT: PASS\n")
ok("R8 PASS over a listed CRITICAL is flagged", any("trust the findings" in w for w in r["warnings"]))


# ---- decide ----
def F(i, sev, **kw):
    base = {"id": i, "severity": sev, "verified": True, "provenance": "introduced", "fixed": False}
    base.update(kw)
    return base


d = triage.decide([F("F1", "CRITICAL"), F("F2", "MINOR")], 1, 5)
ok("D1 fix CRITICAL only, log MINOR", d["next_action"] == "fix_and_recheck" and d["to_fix"] == ["F1"] and d["logged_only"] == ["F2"])
d = triage.decide([F("F1", "HIGH")], 1, 5)
ok("D2 HIGH counts as MAJOR and gets fixed", d["to_fix"] == ["F1"])
d = triage.decide([F("F1", "MAJOR", verified=False)], 1, 5)
ok("D3 an unverified finding blocks action until verified", d["next_action"] == "verify_findings")
d = triage.decide([F("F1", "MAJOR", verified="rejected")], 1, 5)
ok("D4 a rejection with no evidence is not a rejection", d["next_action"] == "verify_findings")
d = triage.decide([F("F1", "MAJOR", verified="rejected", rejection_evidence="git grep shows helper guards it: util.py:40")], 1, 5)
ok("D5 a rejection with evidence clears the finding", d["next_action"] == "stop_clean" and d["rejected"] == ["F1"])
d = triage.decide([F("F1", "MAJOR", provenance="unknown")], 1, 5)
ok("D6 unknown provenance must be determined by defect, not by file log", d["next_action"] == "determine_provenance")
d = triage.decide([F("F1", "MAJOR", provenance="pre-existing")], 1, 5)
ok("D7 pre-existing is filed, not fixed here", d["next_action"] == "stop_clean" and d["to_file"] == ["F1"] and d["to_fix"] == [])
d = triage.decide([F("F1", "MAJOR", provenance="pre-existing", filed="KTP-9")], 1, 5)
ok("D8 a filed pre-existing finding leaves nothing to file", d["to_file"] == [])
d = triage.decide([F("F1", "MAJOR", provenance="newly-reachable")], 1, 5)
ok("D9 newly reachable pre-existing behaviour is in scope", d["to_fix"] == ["F1"])
d = triage.decide([F("F1", "CRITICAL", scope_conflict=True)], 1, 5)
ok("D10 a scope conflict escalates at once, even in round 1", d["next_action"] == "escalate_scope")
d = triage.decide([F("F1", "MAJOR")], 5, 5)
ok("D11 the cap reports unresolved, never accepts", d["next_action"] == "stop_cap_unresolved" and d["ids"] == ["F1"])
d = triage.decide([F("F1", "MAJOR", fixed=True), F("F2", "NIT")], 2, 5)
ok("D12 all blocking fixed -> stop clean", d["next_action"] == "stop_clean")
d = triage.decide([], 1, 5)
ok("D13 nothing found -> stop clean", d["next_action"] == "stop_clean")

print(f"adversarial-cascade: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
