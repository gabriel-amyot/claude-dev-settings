"""Lint, regenerate README/INDEX, commit and push a mission. Optionally post a status comment on the root issue.

Usage: mission_sync.py <slug|path> -m "what changed" [--session slug] [--status-comment]

Stops on a lint error. Commits only the mission folder and missions/INDEX.md (explicit paths,
so other agents' uncommitted files are never captured). Pushes main unpiped and checks the result.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile

from mission_lib import GH_REPO, MISSIONS_DIR, PM_ROOT, gh_url, load, load_computed, mission_dir, now_utc, run, set_top
from mission_lint import lint
from mission_render import index, readme


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return run(["git", "-C", str(PM_ROOT), *args], check=check)


def status_comment(m: dict, msg: str, session: str, commit: str, d) -> str:
    needs = [n for n in m.get("needs_you") or [] if n.get("blocking", True)]
    nm = m.get("next_milestone") or {}
    lines = ["<!-- issue-status v1 -->",
             f"**Status:** {m.get('verdict') or msg}",
             f"**Change:** {msg}",
             f"**Next milestone:** {nm.get('title', 'not set')}",
             f"**Needs Gabriel:** {'; '.join(n['id'] + ' ' + n['question'] for n in needs) or 'nothing'}",
             f"**Session:** {session}, {now_utc()}",
             f"**Record:** [mission.yaml @ {commit[:8]}]({gh_url(d / 'mission.yaml').replace('/blob/main/', '/blob/' + commit + '/')})"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mission")
    ap.add_argument("-m", "--message", required=True)
    ap.add_argument("--session", default="none")
    ap.add_argument("--status-comment", action="store_true")
    a = ap.parse_args()
    d = mission_dir(a.mission)
    m = load(d)
    err, warn = lint(m)
    for w in warn:
        print(f"WARN  {w}")
    if err:
        for e in err:
            print(f"ERROR {e}")
        sys.exit("lint failed: fix mission.yaml before sync")
    m["updated"] = now_utc()
    set_top(d, "updated", m["updated"])
    (d / "README.md").write_text(readme(m, load_computed(d), m["updated"]))
    (MISSIONS_DIR / "INDEX.md").write_text(index())

    rel = str(d.relative_to(PM_ROOT))
    git("add", "--", rel, "missions/INDEX.md")
    if git("diff", "--cached", "--quiet", "--", rel, "missions/INDEX.md", check=False).returncode == 0:
        print("nothing to commit")
    else:
        git("commit", "-q", "-m", f"mission({m['slug']}): {a.message}", "--", rel, "missions/INDEX.md")
    git("pull", "-q", "--no-rebase", "--no-edit", "origin", "main")
    push = git("push", "-q", "origin", "main", check=False)
    if push.returncode != 0:
        sys.exit(f"push failed, the commit is local only:\n{push.stderr}")
    commit = git("rev-parse", "HEAD").stdout.strip()
    print(f"pushed {commit[:8]}: {gh_url(d / 'mission.yaml')}")

    ri = m.get("root_issue") or {}
    if a.status_comment and ri.get("number"):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(status_comment(m, a.message, a.session, commit, d))
        url = run(["gh", "issue", "comment", str(ri["number"]), "-R", GH_REPO, "--body-file", f.name]).stdout.strip()
        print(f"status comment: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
