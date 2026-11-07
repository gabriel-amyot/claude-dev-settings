#!/usr/bin/env python3
"""Layer A suite for scripts/mutation_check.py. Real files, real subprocess test runs, real SIGTERM.
Run: `python3 evals/run_mutation_evals.py`. Exit 1 on any failure.
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "mutation_check.py")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
PY = sys.executable

SRC = """def pad(code):
    return code.zfill(5)


def label(code):
    return "ZIP " + code
"""
TEST = """from calc import pad
assert pad("501") == "00501", pad("501")
print("1 passed")
"""
BASELINE = """from calc import label
assert label("x").startswith("ZIP")
print("baseline passed")
"""

passed = 0
failed = 0


def ok(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {name} {detail}", file=sys.stderr)


def digest(path):
    with open(path, "rb") as h:
        return hashlib.sha256(h.read()).hexdigest()


def mc(*args, cwd):
    p = subprocess.run([PY, SCRIPT, *args], cwd=cwd, capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL)
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        out = {"raw": p.stdout, "err": p.stderr}
    return p.returncode, out


def fixture(root):
    d = tempfile.mkdtemp(dir=root)
    for name, body in (("calc.py", SRC), ("test_calc.py", TEST), ("test_base.py", BASELINE)):
        with open(os.path.join(d, name), "w") as h:
            h.write(body)
    subprocess.run(["git", "init", "-q"], cwd=d, env=ENV)
    subprocess.run(["git", "add", "."], cwd=d, env=ENV)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=d, env=ENV)
    return d


with tempfile.TemporaryDirectory() as root:
    d = fixture(root)
    calc = os.path.join(d, "calc.py")
    before = digest(calc)
    test = f"{PY} test_calc.py"

    code, out = mc("run", "--file", calc, "--find", "zfill(5)", "--replace", "zfill(4)", "--test", test,
                   "--baseline", f"{PY} test_base.py", "--out", os.path.join(root, "r.json"), cwd=d)
    ok("M1 the re-applied defect is KILLED", code == 0 and out.get("verdict") == "KILLED", json.dumps(out)[:300])
    ok("M2 restored byte-identical", digest(calc) == before and out.get("restore", {}).get("restored") is True)
    ok("M3 untouched-side baseline stayed green under the mutant", out.get("baseline_exit_under_mutant") == 0 and out.get("notes") == [])
    ok("M4 no backup or journal left behind", not os.path.exists(calc + ".mutation-backup") and not os.path.exists(calc + ".mutation-journal.json"))
    ok("M5 result written to --out", os.path.exists(os.path.join(root, "r.json")))

    code, out = mc("run", "--file", calc, "--find", "zfill(5)", "--replace", "zfill(5)", "--test", test, cwd=d)
    ok("M6 a no-op substitution is refused", code == 2 and "no-op" in out.get("detail", ""))
    code, out = mc("run", "--file", calc, "--find", "padStart", "--replace", "x", "--test", test, cwd=d)
    ok("M7 an absent --find is refused (the silent str.replace no-op)", code == 2 and "occurs 0" in out.get("detail", ""))
    code, out = mc("run", "--file", calc, "--find", "code", "--replace", "c", "--test", test, cwd=d)
    ok("M8 an ambiguous --find (many sites) is refused", code == 2 and "expected 1" in out.get("detail", ""))
    ok("M9 refusals leave the file untouched", digest(calc) == before)

    code, out = mc("run", "--file", calc, "--find", '"ZIP "', "--replace", '"POSTAL "', "--test", test, cwd=d)
    ok("M10 an untested change SURVIVES and is reported, not rationalised",
       code == 1 and out.get("verdict") == "SURVIVED" and any("redundant" in n for n in out.get("notes", [])))
    ok("M11 restored after a surviving mutant", digest(calc) == before)

    code, out = mc("run", "--file", calc, "--find", '"ZIP "', "--replace", '"POSTAL "', "--test", test,
                   "--baseline", f"{PY} test_base.py", cwd=d)
    ok("M12 baseline going red under the mutant is flagged as too broad / too coupled",
       any("too broad" in n for n in out.get("notes", [])))

    code, out = mc("run", "--file", calc, "--find", "return code.zfill(5)", "--replace", "return code.zfill(5", "--test", test, cwd=d)
    ok("M13 a mutant that breaks the runner's import (syntax error) still restores", digest(calc) == before and out.get("restore", {}).get("restored") is True)

    code, out = mc("run", "--file", calc, "--find", "zfill(5)", "--replace", "zfill(4)", "--test", "definitely-not-a-command-xyz", cwd=d)
    ok("M14 a broken runner is refused BEFORE mutation (cannot pose as a kill)", code == 2 and "not green before" in out.get("detail", ""))

    with open(os.path.join(d, "test_red.py"), "w") as h:
        h.write("raise SystemExit(1)\n")
    code, out = mc("run", "--file", calc, "--find", "zfill(5)", "--replace", "zfill(4)", "--test", f"{PY} test_red.py", cwd=d)
    ok("M15 a suite red before mutation is refused", code == 2)

    with open(calc, "a") as h:
        h.write("# local edit\n")
    code, out = mc("run", "--file", calc, "--find", "zfill(5)", "--replace", "zfill(4)", "--test", test, cwd=d)
    ok("M16 uncommitted changes are refused (isolate mutants from shared work)", code == 2 and "uncommitted" in out.get("detail", ""))
    code, out = mc("run", "--file", calc, "--find", "zfill(5)", "--replace", "zfill(4)", "--test", test, "--allow-dirty", cwd=d)
    ok("M17 --allow-dirty opts in explicitly", code == 0 and out.get("verdict") == "KILLED")
    subprocess.run(["git", "checkout", "--", "calc.py"], cwd=d, env=ENV)

    # ---- interruption: a hard kill leaves a journal; the next run refuses; recover restores ----
    with open(os.path.join(d, "test_slow.py"), "w") as h:
        h.write("import time, calc\nif calc.pad('1') != '00001':\n    time.sleep(30)\n")
    subprocess.run(["git", "add", "."], cwd=d, env=ENV)
    subprocess.run(["git", "commit", "-qm", "slow"], cwd=d, env=ENV)
    before = digest(calc)
    proc = subprocess.Popen([PY, SCRIPT, "run", "--file", calc, "--find", "zfill(5)", "--replace", "zfill(4)",
                             "--test", f"{PY} test_slow.py"], cwd=d, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    journal = calc + ".mutation-journal.json"
    for _ in range(100):
        if os.path.exists(journal):
            break
        time.sleep(0.1)
    time.sleep(0.5)
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=60)
    ok("M18 SIGTERM mid-run restores the original byte-identical", digest(calc) == before and not os.path.exists(journal), f"rc={proc.returncode}")

    # simulate a hard kill (SIGKILL cannot be caught): leave mutant + backup + journal on disk
    import shutil
    shutil.copyfile(calc, calc + ".mutation-backup")
    with open(journal, "w") as h:
        json.dump({"file": calc, "original_sha256": before}, h)
    with open(calc, "w") as h:
        h.write(SRC.replace("zfill(5)", "zfill(4)"))
    code, out = mc("run", "--file", calc, "--find", "zfill(5)", "--replace", "zfill(4)", "--test", test, cwd=d)
    ok("M19 a run after a hard kill refuses and points to recover", code == 2 and "recover" in out.get("detail", ""))
    code, out = mc("recover", "--file", calc, cwd=d)
    ok("M20 recover restores byte-identical and clears the journal", code == 0 and digest(calc) == before and not os.path.exists(journal))
    code, out = mc("recover", "--file", calc, cwd=d)
    ok("M21 recover with nothing to recover is a clear non-success", code == 3 and "nothing to restore" in out.get("detail", ""))

print(f"mutation-check: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
