#!/bin/bash
# Run ONE real Codex adversarial review round, the way the Codex SOP documents it works:
#   codex exec --skip-git-repo-check -s read-only -C <neutral dir> --output-last-message <out> "$(cat prompt.txt)" < /dev/null
#
#   run_codex.sh <prompt.txt> <out.md> [--effort high] [--model <m>] [--dry-run]
#
# - Neutral empty cwd: run from a project dir and Codex loads skills and goes agentic.
# - Positional prompt + stdin closed: without "< /dev/null" it hangs on "Reading additional input from stdin".
# - Effort is explicit: ~/.codex/config.toml defaults model_reasoning_effort to low, silently.
# - Exit 0 with an empty or missing out file is the known silent-failure signature, not a clean review.
#   This script exits 3 for it. Exit 2 = usage. Other non-zero = codex failed (see <out.md>.log).
# Run with the Bash tool's run_in_background, or foreground with timeout 600000. Never pipe it to tail.
set -u
prompt="${1:-}"; out="${2:-}"
[ -n "$prompt" ] && [ -n "$out" ] || { echo "usage: run_codex.sh <prompt.txt> <out.md> [--effort high] [--model m] [--dry-run]" >&2; exit 2; }
shift 2
effort="high"; model=""; dry=0
while [ $# -gt 0 ]; do
  case "$1" in
    --effort) effort="$2"; shift 2 ;;
    --model) model="$2"; shift 2 ;;
    --dry-run) dry=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -f "$prompt" ] || { echo "prompt file not found: $prompt" >&2; exit 2; }
[ -s "$prompt" ] || { echo "prompt file is empty: $prompt" >&2; exit 2; }

neutral="${TMPDIR:-/tmp}/codex-neutral-$$"
cmd=(codex exec --skip-git-repo-check -s read-only -C "$neutral" -c "model_reasoning_effort=$effort" --output-last-message "$out")
[ -n "$model" ] && cmd+=(-m "$model")

if [ "$dry" = 1 ]; then
  printf '%q ' "${cmd[@]}"; printf '"$(cat %q)" > %q 2>&1 < /dev/null\n' "$prompt" "$out.log"
  exit 0
fi

command -v codex >/dev/null || { echo "codex CLI not found: use the fallback reviewer (references/codex-loop.md)" >&2; exit 4; }
mkdir -p "$neutral" "$(dirname "$out")"
rm -f "$out"
"${cmd[@]}" "$(cat "$prompt")" > "$out.log" 2>&1 < /dev/null
rc=$?
rmdir "$neutral" 2>/dev/null
if [ $rc -ne 0 ]; then
  echo "codex exited $rc. Read $out.log (capacity, credits, hook block: see references/codex-loop.md fallback)" >&2
  exit $rc
fi
if [ ! -s "$out" ]; then
  echo "codex exited 0 but wrote no review to $out: silent-failure signature. Shrink the prompt or use the fallback." >&2
  exit 3
fi
echo "effort=$effort review=$out"
exit 0
