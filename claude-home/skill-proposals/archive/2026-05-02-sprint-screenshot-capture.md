# Skill Proposal: sprint-screenshot-capture
Date: 2026-05-02
Source: Sprint 3 review session — Gabriel challenged closing tickets without visual evidence

## Trigger
"capture screenshots for sprint", "screenshot evidence for KTP-XXX", "visual proof for frontend ACs", or automatically when posting a closing comment for a frontend ticket.

## Scope
org (Klever)

## Draft Steps
1. Read ticket AC from Jira or local ac.yaml
2. Classify each AC as frontend (needs screenshot) or backend (code/curl evidence sufficient)
3. For each frontend AC:
   a. Ensure local stack is running (frontend + dev tunnels via gcp-connect)
   b. Navigate to the relevant page with agent-browser
   c. Perform the AC's trigger action (select advertiser, open calendar, click play, etc.)
   d. Capture screenshot with descriptive filename: `{TICKET}-AC{N}-{slug}.png`
   e. Save to `tickets/{PREFIX}/{TICKET}/design/screenshots/`
4. Generate a summary table mapping ACs to screenshot files
5. Upload screenshots as Jira attachments (or reference in closing comment)

## Notes
- Depends on agent-browser skill (already available)
- Must handle LOCAL_MOCK_GOOGLE identity setup for demo advertiser access
- Should integrate with /sprint-close skill as a pre-step
