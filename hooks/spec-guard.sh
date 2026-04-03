#!/usr/bin/env bash
# Spec Guard: PostToolUse hook for Edit and Write
# Checks if the edited file is covered by SBE specs and warns the agent.

MAPPING="$HOME/Developer/gabriel-amyot/tools/work-assistant/agent-os/spec-guard-mapping.yml"

if [ ! -f "$MAPPING" ]; then
  exit 0
fi

# Read tool input from stdin (correct API)
INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ti = data.get('tool_input', data)
print(ti.get('file_path', ti.get('filePath', '')))" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Normalize to relative path under work-assistant/
RELATIVE=$(echo "$FILE_PATH" | sed -n 's|.*/work-assistant/||p')
if [ -z "$RELATIVE" ]; then
  RELATIVE=$(echo "$FILE_PATH" | sed -n "s|$HOME/work-assistant/||p")
fi

if [ -z "$RELATIVE" ]; then
  exit 0
fi

# Check mapping for this file and output as JSON additionalContext
RESULT=$(python3 - "$MAPPING" "$RELATIVE" <<'PYEOF'
import sys, json, yaml

mapping_file = sys.argv[1]
edited_file = sys.argv[2]

with open(mapping_file) as f:
    mapping = yaml.safe_load(f)

for guard in mapping.get("guards", []):
    source = guard["source"]
    if edited_file == source or edited_file.endswith("/" + source):
        lines = []
        lines.append(f"SPEC GUARD: {source} is covered by specifications.")
        lines.append("Guarded behaviors:")
        for b in guard.get("behaviors", []):
            lines.append(f"  * {b}")
        lines.append("Linked specs:")
        for s in guard.get("specs", []):
            lines.append(f"  -> {s}")
        for a in guard.get("adrs", []):
            lines.append(f"  -> {a}")
        lines.append("Verify your change preserves these behaviors before proceeding.")
        msg = "\n".join(lines)
        print(json.dumps({"hookSpecificOutput": {"additionalContext": msg}}))
        break
PYEOF
)

if [ -n "$RESULT" ]; then
  echo "$RESULT"
fi
