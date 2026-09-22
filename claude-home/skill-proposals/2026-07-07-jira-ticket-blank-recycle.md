# Skill Proposal: jira-ticket-blank-recycle
Date: 2026-07-07
Source: prime-otter — KTP-853 (Proxi) epic restructure

## Trigger
User over-created Jira tickets (or a batch is superseded) and wants them off a board/epic WITHOUT losing the ticket numbers — "blank these", "recycle these tickets", "empty them for reuse", "don't delete, I'll reuse them".

## Scope
org (Klever KTP; pattern generalizes to any company-managed Jira project)

## Draft Steps
1. Confirm the target keys and that the user wants recycle-not-delete (irreversible-ish; verify reporters are the user's own).
2. For each key, REST PUT to blank + orphan:
   `{"fields":{"summary":"TODO","description":null,"labels":[],"parent":null,"customfield_10014":null}}`
   (both `parent` and `customfield_10014`/Epic Link must be nulled; `update:{parent:[{set:null}]}` is a no-op.)
3. Leave status in TO DO; do not delete.
4. Verify: `search "parent = {EPIC}"` shows only the intended survivors; blanked keys are orphan "TODO" stories.
5. Record the reusable pool (keys) in memory / ticket docs so future ticket creation reuses them before creating new (see memory `project_reusable_ktp_ticket_pool`).

## Notes
Complements /create-tickets (reuse pool as a source). Uses raw REST + keychain auth (`claude-jira`/`jira_klever`) since jira_skill.py has no blank/unlink command.
