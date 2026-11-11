#!/usr/bin/env python3
"""Layer A suite for meeting-to-action transcript-only mode.

Checks scripts/check_private_dest.sh, the gate that keeps a private recording's
transcript out of git, notes vaults and meetings/weekly-notes trees.
All fixtures are temp directories. Exit 0 = all pass, 1 = any failure.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path(__file__).resolve().parent.parent / "scripts" / "check_private_dest.sh"


def run_gate(dest: Path):
    res = subprocess.run(["bash", str(GATE), str(dest)], capture_output=True, text=True, timeout=30)
    return res.returncode, res.stdout.strip()


def build(root: Path) -> dict:
    repo = root / "repo"
    (repo / "general").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    vault = root / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / "Daily").mkdir()
    plain = root / "Movies" / "recs"
    plain.mkdir(parents=True)
    return {"repo": repo, "vault": vault, "plain": plain, "root": root}


CASES = [
    # (name, path builder, expected exit code, expected stdout prefix)
    ("refuse_inside_git_repo", lambda w: w["repo"] / "general" / "transcripts", 1, "REFUSED"),
    ("refuse_git_repo_root", lambda w: w["repo"], 1, "REFUSED"),
    ("refuse_inside_obsidian_vault", lambda w: w["vault"] / "Daily" / "transcripts", 1, "REFUSED"),
    ("refuse_meetings_path_outside_git", lambda w: w["root"] / "notes" / "meetings" / "2026-09-10", 1, "REFUSED"),
    ("refuse_weekly_notes_path", lambda w: w["root"] / "Weekly" / "2026-W37", 1, "REFUSED"),
    ("allow_transcripts_next_to_recording", lambda w: w["plain"] / "transcripts", 0, "SAFE"),
    ("allow_existing_plain_dir", lambda w: w["plain"], 0, "SAFE"),
]


def main() -> int:
    if not GATE.exists():
        print(f"FAIL  gate missing: {GATE}")
        return 1
    failures = 0
    with tempfile.TemporaryDirectory(prefix="mta-private-") as tmp:
        world = build(Path(tmp))
        for name, make_path, want_code, want_prefix in CASES:
            code, out = run_gate(make_path(world))
            ok = code == want_code and out.startswith(want_prefix)
            failures += 0 if ok else 1
            print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  -- exit={code} out={out!r}"))
        code, _ = subprocess.run(["bash", str(GATE)], capture_output=True, text=True).returncode, None
        ok = code == 2
        failures += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  usage_error_without_argument")
    total = len(CASES) + 1
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
