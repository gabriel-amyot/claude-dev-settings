# Skill Proposal: colleague-message-draft
Date: 2026-11-03
Source: KTP-1216 spike session (agile-jackal), five rewrites of a Slack message to David

## Trigger
"Draft a message to <colleague>", "craft a response to him", "write a Slack/email to <vendor>". Internal Slack/email that Gabriel sends himself (not the /post-comment pipeline).

## Scope
Global (Gabriel's voice), org-agnostic.

## Draft Steps
1. Extract the ask (what Gabriel needs from this person) and put it in the first line; list context topics as "the kind of info I'm looking for", not questions.
2. Verify every quote and fact on the live source (WebFetch) and attach its link; re-check every line against the latest findings in the session.
3. Run ste_lint slop-subset (allow nominalizations inside verbatim quotes).
4. Render to a no-store HTML page with a Copy button (and mailto for email), serve locally, open with a cache-busting URL, and paste the text in chat too.
5. Save the draft under the ticket folder and log what was sent.
