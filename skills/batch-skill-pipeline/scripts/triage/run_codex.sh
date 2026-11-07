#!/bin/bash
# One launcher for every Codex pass of the skill-proposal triage.
#
# Usage:
#   run_codex.sh <run-dir> smoke              P0: tiny prompt, expects the answer OK
#   run_codex.sh <run-dir> batch <batch-id>   P3: attack results/<batch-id>.json
#   run_codex.sh <run-dir> groups             P4: attack groups.json
#   run_codex.sh <run-dir> overall            P4: attack the whole triage
#
# Writes <run>/codex/prompt-<tag>.txt, out-<tag>.{json,md}, run-<tag>.log, and one summary
# line per call to <run>/codex/run.log.
#
# Invocation discipline (each item fixes a known silent failure):
#   - read-only sandbox, neutral empty cwd: a project cwd makes Codex go agentic
#   - prompt passed positionally, never through stdin: large stdin prompts produce no output
#   - stdin from /dev/null: without it, exec hangs on "Reading additional input from stdin"
#   - --output-last-message: capture only the answer, not the transcript
#   - exit 0 with a missing or empty output file is the known failure signature, so this
#     script exits non-zero in that case instead of reporting success
#
# Exit codes: 0 ok, 2 usage, 3 output missing, 4 output empty, 5 no JSON in output,
#             6 smoke answer wrong, otherwise the codex exit code.
# Env: CODEX_BIN (default codex), CODEX_NEUTRAL_DIR (default $TMPDIR/codex-neutral).

usage() { sed -n '4,8p' "$0" >&2; exit 2; }
[ $# -ge 2 ] || usage
[ -d "$1" ] || { echo "run dir not found: $1" >&2; exit 2; }
RUN=$(cd "$1" && pwd)
KIND=$2
BATCH=${3:-}
HERE=$(cd "$(dirname "$0")" && pwd)

case "$KIND" in
  smoke)   TAG=smoke;   OUT="$RUN/codex/smoke.txt" ;;
  batch)   [ -n "$BATCH" ] || usage
           TAG=$BATCH;  OUT="$RUN/codex/out-$BATCH.json"; TPL=batch.md ;;
  groups)  TAG=groups;  OUT="$RUN/codex/out-groups.json"; TPL=groups.md ;;
  overall) TAG=overall; OUT="$RUN/codex/out-overall.md";  TPL=overall.md ;;
  *) usage ;;
esac

mkdir -p "$RUN/codex"
NEUTRAL=${CODEX_NEUTRAL_DIR:-${TMPDIR:-/tmp}/codex-neutral}
mkdir -p "$NEUTRAL"
PROMPT="$RUN/codex/prompt-$TAG.txt"
LOG="$RUN/codex/run-$TAG.log"

if [ "$KIND" = smoke ]; then
  printf 'Reply with exactly the two letters OK and nothing else.\n' > "$PROMPT"
else
  sed -e "s|__RUN__|$RUN|g" -e "s|__BATCH__|$BATCH|g" "$HERE/codex_prompts/$TPL" > "$PROMPT"
fi

# A stale output from an earlier call must never pass the checks below.
[ -f "$OUT" ] && mv -f "$OUT" "$OUT.prev"

START=$(date +%s)
"${CODEX_BIN:-codex}" exec --skip-git-repo-check -s read-only -C "$NEUTRAL" \
  --output-last-message "$OUT" "$(cat "$PROMPT")" > "$LOG" 2>&1 < /dev/null
RC=$?
SECS=$(( $(date +%s) - START ))

STATUS=ok
if [ $RC -ne 0 ]; then STATUS="codex-exit-$RC"
elif [ ! -f "$OUT" ]; then STATUS=missing-output; RC=3
elif ! grep -q '[^[:space:]]' "$OUT"; then STATUS=empty-output; RC=4
elif [ "$KIND" = batch ] && ! grep -q '\[' "$OUT"; then STATUS=no-json-array; RC=5
elif [ "$KIND" = groups ] && ! grep -q '{' "$OUT"; then STATUS=no-json-object; RC=5
elif [ "$KIND" = smoke ] && ! grep -qx '[[:space:]]*OK[[:space:]]*' "$OUT"; then STATUS=smoke-wrong-answer; RC=6
fi

echo "$(date '+%Y-%m-%dT%H:%M:%S') $TAG rc=$RC status=$STATUS secs=$SECS out=$OUT" >> "$RUN/codex/run.log"
echo "$TAG: $STATUS (rc=$RC, ${SECS}s) $OUT"
if [ $RC -ne 0 ]; then
  echo "See $LOG. Exit 0 with no output file is the known silent-failure signature." >&2
fi
exit $RC
