#!/usr/bin/env bash
# Spec Guard: PostToolUse hook for Edit and Write
# Checks if the edited file is covered by SBE specs and warns the agent.

MAPPING="$HOME/Developer/gabriel-amyot/tools/work-assistant/agent-os/spec-guard-mapping.yml"

if [ ! -f "$MAPPING" ]; then
  exit 0
fi

# Extract file path from tool input JSON
FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('file_path', data.get('filePath', '')))" 2>/dev/null)

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

# Check mapping for this file
python3 - "$MAPPING" "$RELATIVE" <<'PYEOF'
import sys, yaml

mapping_file = sys.argv[1]
edited_file = sys.argv[2]

with open(mapping_file) as f:
    mapping = yaml.safe_load(f)

for guard in mapping.get("guards", []):
    source = guard["source"]
    if edited_file == source or edited_file.endswith("/" + source):
        print(f"\nSPEC GUARD: {source} is covered by specifications\n")
        print("Guarded behaviors:")
        for b in guard.get("behaviors", []):
            print(f"  * {b}")
        print("\nLinked specs:")
        for s in guard.get("specs", []):
            print(f"  -> {s}")
        for a in guard.get("adrs", []):
            print(f"  -> {a}")
        print("\nVerify your change preserves these behaviors before proceeding.\n")
        break
PYEOF
