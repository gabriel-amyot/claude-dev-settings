#!/usr/bin/env bash
# PreToolUse guard: block direct reads of Notion mirror page bodies.
#
# Why this exists as a hook and not just a rule in SKILL.md:
# the `notion` skill's Layer B eval (run_behavior_evals.py, case no_raw_file_reads)
# showed that prose does NOT reliably stop it. Agents Read a file by reflex, because
# reading feels cheaper than running a command. It is the opposite here: one page body
# can be tens of thousands of tokens, and the mirror holds hundreds of them.
#
# Blocks: Read / Grep / Glob targeting <mirror>/pages/**
# Allows: anything going through nx.py (Bash), and reads of index/, LEDGER.yaml, docs.
#
# Wire as PreToolUse on Read|Grep|Glob.

set -uo pipefail

payload="$(cat)"

tool="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_name",""))' 2>/dev/null)"
case "$tool" in
  Read|Grep|Glob) ;;
  *) exit 0 ;;
esac

target="$(printf '%s' "$payload" | python3 -c '
import json, sys
data = json.load(sys.stdin).get("tool_input", {}) or {}
for key in ("file_path", "path", "pattern", "glob"):
    value = data.get(key)
    if isinstance(value, str) and value:
        print(value)
' 2>/dev/null)"

[ -z "$target" ] && exit 0

# Only guard paths that are actually inside a notion mirror: a `pages/` segment that
# sits beside an `index/catalog.jsonl`. Keeps this from firing on unrelated pages/ dirs.
printf '%s\n' "$target" | grep -q '/pages/' || exit 0

mirror="${target%%/pages/*}"
if [ ! -f "$mirror/index/catalog.jsonl" ] && [ ! -f "$mirror/CLAUDE.md" ]; then
  exit 0
fi

cat >&2 <<EOF
BLOCKED: direct read of a Notion mirror page body.

  $target

A mirrored Notion page can be tens of thousands of tokens. Reading one directly is the
context blowout the notion skill exists to prevent.

Use the bounded ladder instead:

  NX="python3 ~/.claude/skills/notion/nx.py"
  NOTION_CHECKOUT=$mirror \$NX search "<terms>"      # rung 1, ~40 tokens per hit
  NOTION_CHECKOUT=$mirror \$NX card <id>             # rung 2, ~200 tokens
  NOTION_CHECKOUT=$mirror \$NX get <id> --heading H  # rung 3, bounded slice

nx also stamps every read with freshness, which a raw file read does not.
EOF
exit 2
