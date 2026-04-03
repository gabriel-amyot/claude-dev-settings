#!/bin/bash
# PostToolUse hook: reminds agent to follow Librarian Protocol after writing to library/
# Fires on Write and Edit tools when the target is inside library/

# Read tool input from stdin
INPUT=$(cat)

# Extract the file path from the tool input
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty' 2>/dev/null)

# Only care about files in the library directory
if [[ "$FILE_PATH" == *"/library/"* ]] && [[ "$FILE_PATH" != *"/INDEX.md" ]] && [[ "$FILE_PATH" != *"/CATALOG.md" ]]; then
  # Determine which section this file is in
  SECTION=$(echo "$FILE_PATH" | sed 's|.*/library/||' | cut -d'/' -f1)

  cat << EOF

LIBRARIAN PROTOCOL REMINDER: You just wrote to library/${SECTION}/.
Complete these steps:
1. Update library/${SECTION}/INDEX.md with a one-liner for this file
2. If cross-cutting, add to library/CATALOG.md Topic Cross-Reference
3. Verify filename follows {domain}-{purpose}-{key-concepts}.md convention
EOF
fi
