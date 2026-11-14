#!/bin/bash
# PreToolUse Bash guard: block GitLab CI/CD variable writes.
#
# At Klever a runtime value has two paths only: a non-secret goes in the owning DAC's
# Terraform per-environment map, a secret goes in GCP Secret Manager, read at runtime.
# A GitLab CI/CD variable is never a third path (GitHub klever-project-management#672,
# KTP-1384: an agent routed the Foursquare key through a CI variable, then moved to
# create a prod one itself).
#
# Blocks: gitlab_skill.py ... vars ... --action set, glab variable set/create/update,
# and curl/http writes (POST/PUT/DELETE) on a GitLab /variables endpoint.
# Reads (vars list/get, GET on /variables) pass.
#
# Enforcement scope: Bash TOOL guard, Claude only. gitlab_skill.py refuses the same
# writes itself, which also covers Codex. Patterns mirror the eval grader at
# ~/.claude-shared-config/evals/rules/no-new-ci-var/grader.py.
#
# Kill-switch: export CI_VARIABLE_GUARD_OFF=1
# FAILS OPEN on any internal error.

[ -n "$CI_VARIABLE_GUARD_OFF" ] && exit 0

input="$(cat)"

hit="$(printf '%s' "$input" | python3 -c '
import sys, json, re
try:
    cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
except Exception:
    sys.exit(0)
PATTERNS = [
    (r"gitlab_skill\.py\b[^\n|;&]*\bvars\b[^\n|;&]*--action[ =]+set\b", "gitlab_skill.py vars --action set"),
    (r"\bglab\s+variable\s+(set|create|update)\b", "glab variable write"),
    (r"(?:^|\s)(-X|--request)\s*(POST|PUT|DELETE)\b[^\n]*/variables\b", "HTTP write on /variables"),
    (r"/variables\b[^\n]*\s(-X|--request)\s*(POST|PUT|DELETE)\b", "HTTP write on /variables"),
]
for pat, label in PATTERNS:
    if re.search(pat, cmd, re.I):
        print(label)
        break
' 2>/dev/null)"

[ -z "$hit" ] && exit 0

cat >&2 <<EOF
CI VARIABLE WRITE GUARD: blocked ($hit).
A GitLab CI/CD variable is not a value path at Klever.
  - Non-secret value: write it in the owning DAC's Terraform per-environment map.
  - Secret value: put it in GCP Secret Manager and read it at runtime.
"You have the tools, do it" authorizes the action, not this path. Ask Gabriel if unsure.
See documentation/bibliotheque/stack/ci-cd/dac-runtime-configuration-patterns.md
EOF
exit 2
