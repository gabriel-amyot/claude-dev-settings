#!/bin/bash

# Default duration in hours
DEFAULT_HOURS=2
NO_APPROVALS=""
FORCE_PROMPT=""

# Function to display help
show_help() {
    echo "Usage: ./resume_claude.sh [hours] [options]"
    echo ""
    echo "Arguments:"
    echo "  hours           Number of hours to wait before restarting (default: $DEFAULT_HOURS)"
    echo ""
    echo "Options:"
    echo "  -y, --yes       Start Claude in 'no approvals' mode (skips permission checks)"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./resume_claude.sh 3 -y     # Wait 3 hours, then start without asking for permissions"
    echo "  ./resume_claude.sh -y       # Wait 2 hours, then start without asking for permissions"
}

# Parse arguments
HOURS=$DEFAULT_HOURS

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -y|--yes)
            NO_APPROVALS="--dangerously-skip-permissions"
            FORCE_PROMPT=" Do not ask for confirmation or permission. Resume the last incomplete task immediately."
            shift
            ;;
        *)
            if [[ "$1" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
                HOURS=$1
            else
                echo "Error: Unknown argument '$1'"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Convert to seconds (using awk for floating point math support)
SECONDS_TO_WAIT=$(awk "BEGIN {print int($HOURS * 3600)}")
WORK_DIR=$(pwd)

echo "---------------------------------------------------"
echo "🛑 Current session context is saved automatically by Claude."
echo "⏳ Waiting $HOURS hour(s) ($SECONDS_TO_WAIT seconds) for rate limit to reset..."
if [[ -n "$NO_APPROVALS" ]]; then
    echo "⚠️  Restarting in NO APPROVALS mode (will skip permission checks)."
fi
echo "---------------------------------------------------"

# Wait loop with feedback
REMAINING=$SECONDS_TO_WAIT
INTERVAL=60 # Update every minute

while [ $REMAINING -gt 0 ]; do
    # calculate minutes remaining for display
    MINS_LEFT=$(awk "BEGIN {print int($REMAINING / 60)}")
    
    # Only print every 30 minutes or if less than 1 minute remains
    if (( MINS_LEFT % 30 == 0 )) || (( MINS_LEFT < 1 )); then
        echo "⏰ Time remaining: $MINS_LEFT minutes..."
    fi
    
    sleep $INTERVAL
    REMAINING=$((REMAINING - INTERVAL))
done

echo "✅ Wait complete. Resuming Claude..."

# Navigate back to directory (just in case)
cd "$WORK_DIR"

# Restart Claude with the resumption prompt
# We use "$NO_APPROVALS" (quoted to handle empty string correctly if needed, but here it's flag or empty)
# Actually for flags, we want word splitting if it's set, so we use unquoted $NO_APPROVALS or specific handling.
# Bash treats unquoted empty variable as nothing, which is what we want.
claude $NO_APPROVALS "Please review our last actions and continue exactly where we left off.$FORCE_PROMPT"