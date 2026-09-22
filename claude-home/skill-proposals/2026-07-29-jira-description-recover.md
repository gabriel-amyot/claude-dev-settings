# Skill Proposal: jira-description-recover
Date: 2026-07-29
Source: Q3-Sprint-2 AC rework — restored 3 overwritten Amal-reported tickets from Jira changelog

## Trigger
"restore the Jira description", "recover the previous ticket text", "I overwrote a ticket / undo the description change", or any need to read a ticket's description history.

## Scope
org (Klever + Supervisr — both use the jira skill + Atlassian Cloud)

## Draft Steps
1. Resolve the issue's changelog via Atlassian REST API v3: `GET /rest/api/3/issue/{KEY}?expand=changelog`, reusing the jira skill's `jira_config.json` base URL + the keychain token. (The skill's own `metadata`/`get --full` choke on `customfield_10028` for newer tickets, so go direct.)
2. urllib needs a certifi SSL context to connect.
3. Walk `histories[]` newest-first; collect `items[]` where `field == "description"`. The most recent item's `fromString` is the text that existed immediately before the last edit; `toString` is the current value. For an N-edits-ago restore, walk further back.
4. Print the recovered text verbatim (it is Jira wiki markup) and optionally re-apply it via `jira update KEY --description <text>` — but first check the reporter and honor the "don't overwrite others' tickets" rule.

## Notes
- Also file a jira-skill bug: `metadata`/`get --full` raise `'PropertyHolder' object has no attribute 'customfield_10028'` on tickets lacking the sprint field.
- Pairs with the deferred "reporter-aware write guard" (block description overwrite when reporter != operator without explicit prompt).
