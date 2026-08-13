#!/usr/bin/env python3
"""
PMD Java quality gate. PostToolUse hook on Edit and Write.

WHY THIS EXISTS
    Java produced in the agent loop was landing with raw Object returns, null
    returns, duplicated literals and 16-branch controller methods. Those were
    caught by a human reading a merge request, which is the most expensive
    place to catch them. This moves the catch into the loop, one second after
    the file is written, while the agent still has the context to fix it.

PERFORMANCE NOTE  (read this before deciding to keep the hook)
    Measured on app-klever-media-api, 43 files, Apple Silicon:

        PMD on 1 file    0.97s
        PMD on 43 files  1.12s

    The cost is JVM startup, not analysis. PMD has no daemon mode, so there is
    a hard floor near one second per invocation and it does not warm up.
    Roughly 1s is added to every Java file edit.

    This was accepted with an explicit budget of about 2s per edit and an
    explicit agreement to revert if it feels heavy in practice. If edits start
    feeling sluggish, or the repo grows enough that whole-module linting drifts
    past the budget, the escape hatches in order of preference are:

        1. scope: "changed-lines"  (default) already limits REPORTED output,
           but PMD still parses the whole file. Cheap win only on noise.
        2. enabled: false in the config below. Instant off switch.
        3. Move the gate to pre-commit or CI, where a 1s cost is invisible.

    Do not try to fix this by trimming the ruleset. Rule count is not the cost.

CONFIGURATION  (no need to edit this script)
    Global defaults:  ~/.claude/pmd-java-gate.json
    Per-repo override: <repo>/.claude/pmd-gate.json   (merged over global)
    Rules + thresholds: <repo>/config/pmd/klever-java-rules.xml

    A repo opts in simply by having the ruleset file. No ruleset, no gate.
    That keeps this hook inert for every non-Java project on the machine.

SUPPRESSION
    @SuppressWarnings("PMD.NoNullReturn")   on the method or class
    // NOPMD  reason                        on the line
    Both leave a greppable, reviewable justification behind.

EXIT CODES
    0  clean, or advisory-only findings (printed, not blocking)
    2  blocking findings; stderr is fed back to the agent to self-correct
"""

import json
import os
import subprocess
import sys
import shutil
from pathlib import Path

DEFAULT_CONFIG = {
    "enabled": True,
    # "changed-lines": only report violations on lines this edit touched.
    #                  Legacy debt stays quiet, new code must be clean.
    # "whole-file":    report every violation in the file.
    "scope": "changed-lines",
    # Rules that report but never block. Everything else blocks.
    "advisory_rules": ["NoUncheckedThrow"],
    # Hard ceiling. If PMD exceeds this, the hook gives up silently rather
    # than stalling the loop.
    "timeout_seconds": 20,
    "ruleset_path": "config/pmd/klever-java-rules.xml",
    "pmd_binary": "/opt/homebrew/bin/pmd",
    # Skip generated and test sources. Tests legitimately break some rules.
    "exclude_path_fragments": ["/target/", "/generated-sources/", "/src/test/"],
    "max_reported": 25,
}

GLOBAL_CONFIG_PATH = Path.home() / ".claude" / "pmd-java-gate.json"


def load_config(repo_root):
    config = dict(DEFAULT_CONFIG)
    for path in (GLOBAL_CONFIG_PATH,
                 repo_root / ".claude" / "pmd-gate.json" if repo_root else None):
        if path and path.is_file():
            try:
                config.update(json.loads(path.read_text()))
            except (json.JSONDecodeError, OSError):
                pass  # A broken config must never block the user's edit.
    return config


USER_RULESET = Path.home() / ".claude" / "skills" / "java-quality" / "klever-java-rules.xml"


def resolve_ruleset(config, repo_root):
    """Repo ruleset wins, user ruleset is the default.

    These are one engineer's standards, not a ratified team standard. They live
    in personal config, not in a shared product repo, until the team agrees and
    CI consumes them. A repo-level file therefore means 'the team ratified
    this', and it takes precedence when it exists.
    """
    if repo_root:
        repo_rules = repo_root / config.get("ruleset_path", "")
        if repo_rules.is_file():
            return repo_rules
    user_rules = Path(config.get("user_ruleset_path", str(USER_RULESET))).expanduser()
    return user_rules if user_rules.is_file() else None


def find_repo_root(file_path):
    try:
        out = subprocess.run(
            ["git", "-C", str(file_path.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return Path(out.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def is_tracked(repo_root, file_path):
    """True if git already knows this file at HEAD."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", str(file_path)],
            capture_output=True, text=True, timeout=5,
        )
        return out.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def changed_line_numbers(repo_root, file_path):
    """Lines added or modified versus HEAD.

    Returns a set, possibly empty when the file is tracked and unmodified.
    Returns None only when git itself failed, which the caller treats as
    'cannot tell, so check everything'. An empty set and None mean opposite
    things and must not be conflated: that confusion caused the gate to flag
    pre-existing debt in files the edit never touched.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--unified=0", "HEAD", "--", str(file_path)],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return None
    except (subprocess.SubprocessError, OSError):
        return None

    lines = set()
    for raw in out.stdout.splitlines():
        if not raw.startswith("@@"):
            continue
        # @@ -old,count +new,count @@
        try:
            new_part = raw.split("+")[1].split("@@")[0].strip()
            start, _, count = new_part.partition(",")
            start = int(start)
            count = int(count) if count else 1
            lines.update(range(start, start + count))
        except (IndexError, ValueError):
            continue
    return lines


def run_pmd(config, ruleset, file_path):
    """Returns (report, error_message). Exactly one is non-None.

    A broken ruleset must never read as 'code is clean'. PMD exits 0 for no
    violations and 4 when it finds some. Anything else is a real failure and
    is surfaced, because a silently dead gate is worse than no gate: it prints
    a green check over code nobody checked.
    """
    cmd = [
        config["pmd_binary"], "check",
        "-d", str(file_path),
        "-R", str(ruleset),
        "-f", "json",
        "--no-cache",
        "--no-progress",
    ]
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=config["timeout_seconds"],
        )
    except subprocess.TimeoutExpired:
        return None, f"PMD exceeded {config['timeout_seconds']}s and was killed."
    except (subprocess.SubprocessError, OSError) as exc:
        return None, f"PMD could not be executed: {exc}"

    if out.returncode not in (0, 4):
        detail = "\n".join(
            line for line in (out.stderr or "").splitlines()
            if "[ERROR]" in line or "Cannot" in line or "Unable" in line
        )
        return None, (
            f"PMD failed to run (exit {out.returncode}). The gate is NOT checking "
            f"your code until this is fixed.\n{detail[:1200]}"
        )

    if not out.stdout.strip():
        return None, "PMD produced no output."
    try:
        return json.loads(out.stdout), None
    except json.JSONDecodeError:
        return None, "PMD output was not valid JSON."


def collect_violations(report, allowed_lines):
    found = []
    for file_entry in report.get("files", []):
        for v in file_entry.get("violations", []):
            line = v.get("beginline", 0)
            if allowed_lines is not None and line not in allowed_lines:
                continue
            found.append({
                "line": line,
                "rule": v.get("rule", "?"),
                "message": (v.get("description") or "").strip(),
            })
    found.sort(key=lambda x: x["line"])
    return found


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_input = payload.get("tool_input", payload)
    raw_path = tool_input.get("file_path") or tool_input.get("filePath") or ""
    if not raw_path.endswith(".java"):
        return 0

    file_path = Path(raw_path)
    if not file_path.is_file():
        return 0

    repo_root = find_repo_root(file_path)
    config = load_config(repo_root)

    if not config.get("enabled", True):
        return 0
    if any(frag in str(file_path) for frag in config["exclude_path_fragments"]):
        return 0
    if not repo_root:
        return 0

    ruleset = resolve_ruleset(config, repo_root)
    if ruleset is None:
        return 0
    if not shutil.which(config["pmd_binary"]) and not Path(config["pmd_binary"]).is_file():
        return 0  # PMD absent. Never punish the user for a missing tool.

    report, error = run_pmd(config, ruleset, file_path)
    if error:
        # Loud, but never blocking. A tooling fault is not the author's fault,
        # and blocking edits on it would make the gate hated within a day.
        print(f"PMD quality gate DEGRADED: {error}", file=sys.stderr)
        return 0
    if report is None:
        return 0

    allowed_lines = None  # None means "no filter, report everything".
    if config["scope"] == "changed-lines":
        if not is_tracked(repo_root, file_path):
            # Brand new file. All of it is new code, so all of it is in scope.
            allowed_lines = None
        else:
            allowed_lines = changed_line_numbers(repo_root, file_path)
            if allowed_lines is None:
                # git failed. Fail toward checking rather than toward silence.
                pass

    violations = collect_violations(report, allowed_lines)
    if not violations:
        return 0

    advisory = set(config["advisory_rules"])
    blocking = [v for v in violations if v["rule"] not in advisory]
    advisories = [v for v in violations if v["rule"] in advisory]

    rel = file_path.relative_to(repo_root) if repo_root in file_path.parents else file_path
    cap = config["max_reported"]

    def render(items):
        out = []
        for v in items[:cap]:
            out.append(f"  {rel}:{v['line']}  [{v['rule']}] {v['message']}")
        if len(items) > cap:
            out.append(f"  ... and {len(items) - cap} more")
        return "\n".join(out)

    if blocking:
        msg = [
            f"PMD quality gate: {len(blocking)} violation(s) in code you just wrote.",
            "",
            render(blocking),
        ]
        if advisories:
            msg += ["", f"Advisory, not blocking ({len(advisories)}):", render(advisories)]
        msg += [
            "",
            "Fix these now. If a rule is genuinely wrong here, suppress it at the",
            "site with a reason: @SuppressWarnings(\"PMD.<Rule>\") or // NOPMD <why>.",
            f"Rules: {ruleset}",
        ]
        print("\n".join(msg), file=sys.stderr)
        return 2

    print(f"PMD advisory ({len(advisories)}):\n{render(advisories)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
