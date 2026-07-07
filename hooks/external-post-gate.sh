#!/usr/bin/env python3
"""External-Post Gate: PreToolUse hook for Bash (KTP-907 choke-point backstop).

The causal-claim and code-claim gates live inside the /post-comment pipeline — behavioral.
This hook enforces them mechanically at the irreversible step: any Bash command that CREATES
externally visible content (GitLab MR notes/discussions, GitHub PR/issue comments, Jira
comments, Slack posts) is blocked unless the post-comment gates ran recently and passed
(marker file /tmp/.pce-gate-pass, written by verify-causal-claims.py on exit 0, < 30 min old).

It deliberately does NOT block:
  - read-only API calls (GET/list/fetch — no POST/PUT write verb in the command)
  - non-posting API POSTs (pipeline triggers, MR creation — patterns anchor on
    comment/note/message endpoints specifically)
  - anything when a fresh gate marker exists (the legit /post-comment flow just ran)

Exit 0 = allow. Exit 2 = BLOCK (stderr shown to the agent as the reason).
"""
import json
import re
import sys
import time

BLOCK_MSG = """BLOCKED by external-post-gate (KTP-907 choke point): this command publishes externally visible
content (MR/PR/Jira/Slack comment), but no fresh post-comment gate pass was found.

External posts must go through /post-comment, whose verifiers (verify-code-claims.py +
verify-causal-claims.py) check code-location provenance and causal-claim epistemic status and
write the gate marker this hook looks for. Route the post through /post-comment. If you ARE the
post-comment agent seeing this: run the verifiers on the final draft first (they emit the marker
on pass), then retry the post within 30 minutes."""

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

MARKER = "/tmp/.pce-gate-pass"
FRESH_SECONDS = 1800


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

    try:
        with open(MARKER, encoding="utf-8") as fh:
            stamp = int(fh.read().split()[0])
        if time.time() - stamp < FRESH_SECONDS:
            return 0
    except Exception:
        pass

    print(BLOCK_MSG, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
