#!/bin/bash
# Monthly Layer A eval sweep — invoked by launchd (com.harness.skill-evals-monthly).
# Deterministic fixture runners only: zero model calls, safe unattended.
# Failures land in evals/reports/ and as a decision item in the Mission Control inbox.
set -u

LOG_DIR="$HOME/.claude-shared-config/evals/monthly-sweep/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/sweep-$(date +%Y-%m-%d).log"

{
  echo "=== monthly skill-evals sweep $(date '+%Y-%m-%d %H:%M:%S') ==="
  python3 "$HOME/.claude-shared-config/skills/skill-evals/scripts/run_sweep.py" --source monthly
  echo "=== exit $? ==="
} >> "$LOG" 2>&1
