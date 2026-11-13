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
import json
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
    env = {**os.environ, "MISSION_PM_ROOT": str(root)}
    return subprocess.run([sys.executable, str(SCRIPTS / name), *args], capture_output=True, text=True, env=env)


def write(root: pathlib.Path, doc: dict, slug: str = "fixture-ttd") -> pathlib.Path:
    d = root / "missions" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "mission.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    return d


def main() -> int:
    root = pathlib.Path(tempfile.mkdtemp(prefix="mission-evals-"))
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
        check("render/data-slot-filled", "/*__DATA__*/null" not in html and '"slug": "fixture-ttd"' in html)
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
        check("index/lists-mission", "fixture-ttd" in idx)
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

        r = script(root, "mission_log.py", "use", "--command", "report", "--mission", "fixture-ttd")
        r2 = script(root, "mission_log.py", "feedback", "--rating", "-1", "--text", "what is N-2?", "--command", "report")
        r3 = script(root, "mission_log.py", "summary")
        check("log/use-feedback-summary", all(x.returncode == 0 for x in (r, r2, r3)) and "what is N-2?" in r3.stdout and "net rating: -1" in r3.stdout, r3.stdout)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    fails = [x for x in results if not x[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {detail.strip()[:400]}" if not ok and detail else ""))
    print(f"\n{len(results) - len(fails)}/{len(results)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
