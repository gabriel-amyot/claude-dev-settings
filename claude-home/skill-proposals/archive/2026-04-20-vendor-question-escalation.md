# Skill Proposal: vendor-question-escalation
Status: BUILT (2026-04-21 — functional test: PASS)
Date: 2026-04-20
Source: KTP-130 Placer API architecture session

## Trigger
When internal research contradicts vendor documentation or when a go/no-go blocker depends on a vendor's confirmation. User says "ask the vendor", "email Nick", "check with [external person]", or when a blocker is tagged as "vendor response needed."

## Scope
global (applies to any vendor interaction: Placer, TTD, Mapbox, Auth0, etc.)

## Draft Steps
1. Identify the exact binary question(s) that unblock progress (max 3)
2. Strip all internal context, analysis, and architecture debate from the message
3. Provide only: what was tested, what was observed, what needs clarification
4. Draft the message in direct, no-fluff style
5. Present for user approval before sending (via /post-comment if Jira, or draft-to-clipboard if email)

## Why
Vendors don't need our internal architecture debates. They need clear questions they can answer in 2 lines. Bundling context causes delays because the vendor has to parse what you actually want to know. Learned from KTP-130: first draft had full pre-flight findings and architecture assumptions. Final email was 3 questions, got a response same day.
