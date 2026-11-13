# ticket-from-rca-pipeline — Pipeline Quick Reference

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DRAFT PHASE (Steps 1–3)                            │
├──────────────┬──────────────────────────────────────────────────────────────┤
│ Step 1       │ PARSE RCA FINDINGS                                           │
│              │ Consumes: RCA/incidental-findings markdown file              │
│              │ Produces: Structured findings list                           │
│              │   (title, context, observation, suspected cause,             │
│              │    related tickets, severity signal)                         │
│              │ Fails if: file missing, file empty → STOP, ask user         │
├──────────────┼──────────────────────────────────────────────────────────────┤
│ Step 2       │ DRAFT TICKETS                                                │
│              │ Consumes: Structured findings list                           │
│              │ Produces: Ticket drafts (Intent + ACs + Blockers + Refs)    │
│              │ Fails if: cannot produce testable ACs → flag as BLOCKED     │
├──────────────┼──────────────────────────────────────────────────────────────┤
│ Step 3       │ LEO AC GATE                                                  │
│              │ Consumes: Ticket drafts                                      │
│              │ Produces: PASS / NEEDS_REVISION / BLOCKED per ticket        │
│              │ Checks: vague outcomes, untestable conditionals,            │
│              │   task-list ACs, missing decision gates, fabricated numbers │
│              │ Fails if: ticket cannot pass without missing info           │
│              │   → mark BLOCKED, continue with others                      │
└──────────────┴──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          HUMAN GATE (Step 4)                                │
├──────────────┬──────────────────────────────────────────────────────────────┤
│ Step 4       │ USER CONFIRMATION                                            │
│              │ Consumes: Leo-reviewed drafts                                │
│              │ Produces: Approved final ticket list                        │
│              │ Shows: title, intent, AC count, Leo verdict, flags          │
│              │ BLOCKS until explicit user approval                         │
│              │ Asks: merge candidates, deferred items, project/epic,       │
│              │   assignees/labels                                           │
└──────────────┴──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         JIRA CREATION (Step 5)                              │
├──────────────┬──────────────────────────────────────────────────────────────┤
│ Step 5       │ CREATE IN JIRA                                               │
│              │ Consumes: Approved ticket list                               │
│              │ Produces: Key → finding mapping (e.g., SPV-143 → finding 2) │
│              │ Tool: /jira skill, create subcommand                        │
│              │ Fails if: creation error → log, continue others,           │
│              │   report in Step 9                                           │
└──────────────┴──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       ADVERSARIAL PHASE (Steps 6–8)                         │
├──────────────┬──────────────────────────────────────────────────────────────┤
│ Step 6       │ ADVERSARIAL CODEBASE VERIFICATION                           │
│              │ Consumes: Created tickets (keys + descriptions)             │
│              │ Produces: Per-ticket findings report                        │
│              │   Severities: CRITICAL / HIGH / MEDIUM / LOW / UNVERIFIED  │
│              │ Tool: Explore agents (one per ticket, parallel)             │
│              │ Verifies: entity names, schema fields, publisher behavior,  │
│              │   config semantics, cited file paths                        │
│              │ Fails if: repo not accessible → UNVERIFIED, do NOT fabricate│
├──────────────┼──────────────────────────────────────────────────────────────┤
│ Step 7       │ REWRITE WITH CORRECTIONS                                    │
│              │ Consumes: Adversarial findings from Step 6                  │
│              │ Produces: Corrected ticket bodies                           │
│              │ Fixes: all CRITICAL and HIGH findings                       │
│              │ Applies at discretion: MEDIUM                               │
│              │ Flags but does not block on: LOW                            │
│              │ Runs abbreviated Leo re-check on changed sections           │
├──────────────┼──────────────────────────────────────────────────────────────┤
│ Step 8       │ UPDATE JIRA                                                  │
│              │ Consumes: Corrected bodies + key mapping                    │
│              │ Produces: Updated Jira descriptions + audit comments        │
│              │ Tool: /jira skill, edit-description + add-comment           │
│              │ Fails if: update error → log, continue others,             │
│              │   report in Step 9                                           │
└──────────────┴──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            REPORT (Step 9)                                  │
├──────────────┬──────────────────────────────────────────────────────────────┤
│ Step 9       │ REPORT KEYS                                                  │
│              │ Consumes: Key mapping, failure log from Steps 5 and 8       │
│              │ Produces: Summary table of keys + adversarial outcomes      │
│              │ Format: table (key, title, Leo verdict, adversarial result) │
│              │ Includes: BLOCKED tickets requiring user decisions          │
│              │ Includes: any creation or update failures                  │
└──────────────┴──────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Failure Reference

| Step | What Can Fail | What to Do |
|------|---------------|------------|
| 1 | File not found / empty | STOP. Ask user for correct path. |
| 2 | Cannot produce testable ACs | Mark ticket BLOCKED. Continue with others. |
| 3 | Ticket cannot pass Leo without missing info | Mark BLOCKED. Flag to user in Step 4. |
| 4 | User requests changes | Apply changes, re-confirm before Step 5. |
| 5 | Jira creation error | Log failure. Continue. Report in Step 9. |
| 6 | Repo not accessible | Mark claim UNVERIFIED. Note which repo is needed. |
| 7 | Corrected text fails abbreviated Leo re-check | Revise further. Do not proceed with a failing ticket. |
| 8 | Jira update error | Log failure. Report in Step 9. Output corrections for manual application. |
| 9 | — | Terminal step. No failure mode. |

---

## Severity Legend (Step 6)

| Level | Meaning | Action in Step 7 |
|-------|---------|-----------------|
| CRITICAL | Claim is demonstrably false | Must fix before Step 8 |
| HIGH | Claim is probably wrong or seriously misleading | Must fix before Step 8 |
| MEDIUM | Claim is imprecise but approximately correct | Fix at discretion |
| LOW | Cosmetic wording issue | Flag only, do not block |
| UNVERIFIED | Could not check — repo inaccessible | Flag to user in Step 9 |
