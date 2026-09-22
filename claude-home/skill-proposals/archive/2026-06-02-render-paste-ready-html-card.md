# Skill Proposal: render-paste-ready-html-card
Date: 2026-06-02
Source: lucid-lynx session (KTP-754) — drafting a Slack message to Mohammed; user asked for "the same output as the klever 3Ps" so he could copy-paste cleanly.

## Trigger
When content has been drafted that the USER must paste manually into an external surface (Slack thread/DM they own, a channel /post-comment can't auto-send to, an email), and they need it formatted + copy-pasteable rather than dumped in the terminal. Phrases: "open this as HTML", "I can't copy paste this from the terminal", "give me the 3Ps-style output", "render it so I can paste it".

## Scope
Global (any org). Complements /post-comment (which auto-posts); this is for human-sent content.

## Draft Steps
1. Take the drafted message (from a `.md` draft on disk) + any ticket/links context.
2. Generate a self-contained HTML file: styled reading view with clickable links (Jira keys → browse URL, BQ console, repos), a "Copy" button backed by a readonly `<textarea>` holding the platform-formatted plain text (Slack mrkdwn for Slack), with `navigator.clipboard.writeText` + `execCommand('copy')` fallback, and a reference-links panel.
3. Keep the message prose human (no em-dashes, no AI-tell filler) per feedback_human_voice_external_messages.
4. Save to `tickets/{TICKET}/reports/ship/posts/{date}-{slug}.html` (alongside the `.md` draft) and `open` it in the default browser.
5. On edit requests, rewrite the HTML + reopen.

## Notes
Reference implementation exists: `tickets/KTP/KTP-559/KTP-754/reports/ship/posts/2026-06-01-mo-pipeline-questions.html`. Could be a thin mode of /post-comment ("render-only / manual-send") rather than a standalone skill.
