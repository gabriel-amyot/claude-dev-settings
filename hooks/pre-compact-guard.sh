#!/usr/bin/env bash
# Pre-Compaction Guard: Reminds the agent to persist critical state before context is compacted.
# This is the primary defense against agent drift after auto-compaction.

python3 -c "
import json, os
wd = os.getcwd()
msg = f'''COMPACTION IMMINENT — PERSIST STATE NOW

Before compaction proceeds, you MUST write a session state file to disk. This file is your memory across the compaction boundary.

Write to: {wd}/SESSION_STATE.md (or the ticket folder if one exists)

Include:
1. Current goal: What are you trying to accomplish? (ticket ID, AC being worked on)
2. Progress: What is done, what is in progress, what is remaining
3. Decisions made: Key decisions AND their rationale (the why drifts first)
4. Constraints: Things you must NOT do (spec boundaries, user instructions, architectural rules)
5. Blockers / open questions: Anything unresolved
6. Files modified: List of files you have touched this session

After compaction, READ THIS FILE BACK before continuing any work. Verify your next action aligns with the original plan.'''
print(json.dumps({'hookSpecificOutput': {'additionalContext': msg}}))"
