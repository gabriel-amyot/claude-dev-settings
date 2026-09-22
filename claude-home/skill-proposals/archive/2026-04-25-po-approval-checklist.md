# Skill Proposal: po-approval-checklist
Date: 2026-04-25
Source: KTP-513 BMAD party decisions

## Trigger
"Generate PO checklist", "approval checklist for Amal", or after any BMAD party produces inferred decisions.

## Scope
org (Klever) — could be global

## Draft Steps
1. **Collect inferred decisions** — from BMAD party minutes or decision logs
2. **Format compact table** — one line per decision: topic, recommendation, approve checkbox
3. **Include question items** — binary questions where PO must choose between options
4. **Write to ticket reports folder** — `reports/po-approval-checklist.md`
5. **Optionally post via /post-comment** — to Jira ticket or Slack
