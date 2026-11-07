#!/usr/bin/env python3
"""Layer A suite for scripts/find_prior_work.py.

Origin: KTP-1403 (Campaign Health empty response). Its cause had been found in October
under KTT-48 and KTT-54. A search by the new key found nothing.

Cases:
  different key       prior work under another key is found by symptom terms
  misleading match    a folder that matches one generic term ranks below the real one
  key still searched  a folder that names the new key is found too
  bounded output      file bodies never reach stdout
  no hits             exit 1, says so; bad input exits 2

Run:  python3 run_prior_work_evals.py [-v]
Exit: 0 all green, 1 any failure
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "find_prior_work.py"
VERBOSE = "-v" in sys.argv
RESULTS: list[tuple[str, bool, str]] = []
BODY_CANARY = "CANARY-BODY-LINE-never-printed"


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(condition), detail))
    if VERBOSE or not condition:
        print(f"  [{'PASS' if condition else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not condition else ""))


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_world() -> Path:
    root = Path(tempfile.mkdtemp(prefix="prior-work-eval-"))
    write(root, "tickets/KTT/no-epic/KTT-48/reports/rca.md",
          f"# Campaign Health returns an empty response\n{BODY_CANARY}\nCause: stale BQ view.\n")
    write(root, "tickets/KTT/no-epic/KTT-54/STATE.md", "Campaign Health fix attempt, empty response persists.\n")
    write(root, "tickets/KTP/no-epic/KTP-900/notes.md", "Service health dashboard for the portal.\n")
    write(root, "tickets/KTP/no-epic/KTP-1403/jira/description.md", "Campaign Health shows nothing.\n")
    write(root, "sessions/archive/agile-wren/reports/summary.md", "Looked at campaign health empty response again.\n")
    write(root, "sessions/active/steady-ibis/reports/diag.md", "Campaign Health empty response diagnostic.\n")
    write(root, "sessions/active/other-slug/state.yaml", "campaign health\n")
    write(root, "documentation/bibliotheque/ALIASES.md", "| campaign health | products/campaign-health.md |\n")
    write(root, "tickets/KTP/no-epic/KTP-1/big.bin", "campaign health empty response")
    return root


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def main() -> int:
    if not SCRIPT.exists():
        print(f"FATAL: {SCRIPT} missing. NOT-RUN, not a pass.")
        return 1
    root = build_world()
    try:
        result = run("--root", str(root), "--key", "KTP-1403",
                     "--term", "campaign health", "--term", "empty response", "--term", "health")
        out = result.stdout
        lines = [l for l in out.splitlines() if l.startswith("[")]
        check("found:exit 0", result.returncode == 0, out + result.stderr)
        check("found:older key KTT-48 by symptom", any("KTT-48" in l for l in lines), out)
        check("found:older key KTT-54 by symptom", any("KTT-54" in l for l in lines), out)
        check("found:session report", any("sessions/archive/agile-wren" in l for l in lines), out)
        check("grouping:active sessions are one unit per session",
              any(l.endswith("sessions/active/steady-ibis  (latest " + l.split("(latest ")[-1]) for l in lines)
              and not any(l.split("] ")[1].startswith("sessions/active  ") for l in lines), out)
        rank = {name: next((i for i, l in enumerate(lines) if name in l), 99)
                for name in ("KTT-48", "KTP-900")}
        check("misleading:one generic term ranks lower", rank["KTT-48"] < rank["KTP-900"], out)
        check("misleading:shows term coverage", any(l.startswith("[1/3 terms]") and "KTP-900" in l for l in lines), out)
        check("key:new key folder still found", any("KTP-1403" in l and "+key" in l for l in lines), out)
        check("bounded:no body text printed", BODY_CANARY not in out, out)
        check("bounded:non-text files skipped", "big.bin" not in out, out)

        result = run("--root", str(root), "--term", "nothing matches this phrase")
        check("none:exit 1 and says so", result.returncode == 1 and "no prior work" in result.stdout, result.stdout)
        result = run("--root", str(root))
        check("input:no term exits 2", result.returncode == 2, result.stdout)
        result = run("--root", str(root), "--key", "KTP-1403")
        check("input:key alone is refused", result.returncode == 2, result.stdout)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    failed = [(n, d) for n, ok, d in RESULTS if not ok]
    print(f"prior-work evals: {len(RESULTS) - len(failed)}/{len(RESULTS)} assertions passed")
    for name, detail in failed:
        print(f"  - {name}\n      {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
