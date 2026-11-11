> ✅ BUILT 2026-09-01 → .claude/skills/observe-hermes-session/ (SKILL.md + scripts/observe_session.py, tested against Travis's live session). Moved out of the active queue.

# Skill Proposal: observe-hermes-session
Date: 2026-09-01
Source: Proxi — Travis first-session monitoring (2026-07-22 investigation)

## Trigger
Operator wants to watch a specific user's live/recent Proxi/Hermes session WITHOUT intervening —
"how is <user> doing", "surface any issues in their session", "did they get a good answer",
"is Travis still on", "did the canvas actually deliver". Also after any VIP/new-user onboarding
where feedback matters and the operator explicitly says "do not intervene".

## Scope
repo-local (Hermes/Proxi on this Mac) — read-only.

## Draft Steps
1. Resolve the user's Slack `user_id` (via `people/roster.json` name→id, or `hermes pairing list`).
2. Read-only session inventory from `state.db` (open `mode=ro`, host `~/.hermes/state.db`):
   `SELECT id,user_id,message_count,tool_call_count,started_at,ended_at FROM sessions
    WHERE user_id=? ORDER BY started_at DESC` — newest real session = highest message_count
   (0-message rows are empty thread artifacts). Container clock = truth for elapsed time.
3. Reconstruct what the user received: `SELECT role,tool_name,substr(content,1,220) FROM messages
   WHERE session_id=? ORDER BY id DESC` — surface the last assistant replies + any tool errors.
4. Health/issue scan (read-only): `docker logs --since Nm hermes` grep for `returned error`,
   `Traceback`, `Session is closed`, `credits are depleted`, `429`, `needed scope`; confirm
   canvas DELIVERY via a real `publish_canvas` `{"ok":true,"canvas_url":…}` (NOT the skill-load
   "success:true" line — see inbox nugget #16).
5. Report: who's active / idle-or-done (stable message_count), what they got (text vs canvas),
   and a ranked list of issues surfaced — WITHOUT touching the live chat. Optionally leave a
   launchd-based passive watcher (like `com.hermes.slack-watchdog`) rather than a background
   `docker logs -f` (those get reaped between turns).

## Notes
Companion to inbox nuggets #13–#17 (LLM-fallback SPOF, watchdog auto-heal, live-session read-only
inspection, canvas-delivery verification, scope header check). Strictly non-intervening by design.
