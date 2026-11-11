#!/bin/bash
D=/Users/gamyot/.claude-shared-config/docs/specs/2026-10-27-library-recall-review
codex exec --skip-git-repo-check -s read-only -C /tmp/codex-neutral-recall -c model_reasoning_effort="high" --output-last-message "$D/codex-review-r2.md" "$(cat "$D/codex-prompt-r2.md")" > "$D/codex-run-r2.log" 2>&1 < /dev/null
echo "exit=$?" >> "$D/codex-run-r2.log"
