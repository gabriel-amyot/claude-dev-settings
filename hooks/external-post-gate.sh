#!/usr/bin/env python3
"""External-Post Gate: PreToolUse hook for Bash (KTP-907 choke-point backstop).

The causal-claim, code-claim, and anti-slop gates live inside the /post-comment pipeline —
behavioral. This hook enforces them mechanically at the irreversible step: any Bash command
that CREATES externally visible content (GitLab MR notes/discussions, GitHub PR/issue comments,
Jira comments, Slack posts) is blocked unless the post-comment gates ran recently and passed.
Two fresh (< 30 min) markers are required:
  - /tmp/.pce-gate-pass  (verify-causal-claims.py — causal + code provenance)
  - /tmp/.ste-lint-pass  (ste_lint.py --gate-mode slop-subset — no AI-slop patterns)

It deliberately does NOT block:
  - read-only API calls (GET/list/fetch — no POST/PUT write verb in the command)
  - non-posting API POSTs (pipeline triggers, MR creation — patterns anchor on
    comment/note/message endpoints specifically)
  - anything when a fresh gate marker exists (the legit /post-comment flow just ran)

Exit 0 = allow. Exit 2 = BLOCK (stderr shown to the agent as the reason).
"""
import json
import os
import re
import sys
import time

BLOCK_MSG = """BLOCKED by external-post-gate (KTP-907 choke point): this command publishes externally visible
content (MR/PR/Jira/Slack comment), but a required post-comment gate marker is missing or stale.

External posts must go through /post-comment, whose gates write two markers this hook checks:
  - verify-causal-claims.py + verify-code-claims.py -> /tmp/.pce-gate-pass
  - ste_lint.py --gate-mode slop-subset --threshold 0 --marker /tmp/.ste-lint-pass
Route the post through /post-comment. If you ARE the post-comment agent seeing this: run the
verifiers AND the anti-slop lint on the final draft first (each emits its marker on pass), then
retry the post within 30 minutes. If the ste-lint gate blocked a legitimate term, the human adds
a `Lint-ack: <reason>` line to the draft and re-runs; the agent must not self-ack."""

POST_ENDPOINTS = re.compile(
    r'merge_requests/[^ ]*/(?:notes|discussions)'      # GitLab MR comments
    r'|issues/[^ ]*/(?:notes|comments)'                # GitLab/GitHub issue comments
    r'|pulls/[^ ]*/(?:comments|reviews)'               # GitHub PR review comments
    r'|repos/[^ ]*/issues/[^ ]*/comments'              # GitHub issue/PR comments
    r'|/rest/api/[23]/issue/[^ ]*/comment'             # Jira REST comment
    r'|chat\.postMessage',                             # Slack
    re.IGNORECASE)
WRITE_VERB = re.compile(
    r'-X\s*(?:POST|PUT)|--method\s*(?:POST|PUT)|method\s*=\s*["\']?(?:POST|PUT)'
    r'|requests\.(?:post|put)\b|\bcurl\b(?!.*(?:-X\s*GET|--get\b)).*(?:-d\s|--data|--json)',
    re.IGNORECASE)
SKILL_POSTERS = re.compile(
    r'jira_skill\.py[^\n]*\b(?:add-comment|comment)\b'
    r'|slack_skill\.py[^\n]*\b(?:reply|post|send)\b',
    re.IGNORECASE)

REQUIRED_MARKERS = ("/tmp/.pce-gate-pass", "/tmp/.ste-lint-pass")
FRESH_SECONDS = 1800


def _fresh(path):
    """A marker is fresh if written < FRESH_SECONDS ago. Prefer a leading epoch
    token (the marker convention); fall back to file mtime."""
    try:
        with open(path, encoding="utf-8") as fh:
            first = fh.read().split()
    except OSError:
        return False
    stamp = int(first[0]) if first and first[0].isdigit() else None
    if stamp is None:
        try:
            stamp = int(os.path.getmtime(path))
        except OSError:
            return False
    return time.time() - stamp < FRESH_SECONDS


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (d.get("tool_input", d) or {}).get("command") or ""

    posting = bool(SKILL_POSTERS.search(cmd)) or (
        bool(POST_ENDPOINTS.search(cmd)) and bool(WRITE_VERB.search(cmd)))
    if not posting:
        return 0

    if all(_fresh(m) for m in REQUIRED_MARKERS):
        return 0

    print(BLOCK_MSG, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
