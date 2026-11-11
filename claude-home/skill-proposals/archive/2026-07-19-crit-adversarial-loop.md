# Skill Proposal: crit-adversarial-loop
Date: 2026-07-19
Source: fierce-hawk — 3-round adversarial review of QC Gate docs against Codex over crit

## Trigger
User asks to adversarially review an artifact another agent (Codex, Gemini, teammate agent) proposed, served through a live crit session; or to "respond to / validate the peer's comment addressing".

## Scope
Global (crit is org-agnostic).

## Draft Steps
1. Discover the crit session (GET /api/session), identify the artifacts, read them fully.
2. Assumption audit: verify load-bearing empirical claims against code/data before design critique.
3. Post inline comments (crit comment path:line), release the round (POST /api/finish).
4. Watch for peer completion (background quiescence watcher on file mtimes + review.json).
5. Verify every peer reply against the actual text (grep the named mechanism), ack or counter per comment; new rounds target only new machinery.
6. Resolve comments only on the human's instruction; verify resolved counts in review.json, not crit status.
Gotchas baked in: no `crit comment --help`; bulk JSON transactional; ids recreated per round; active-session switching.
