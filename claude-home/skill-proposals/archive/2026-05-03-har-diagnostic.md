# Skill Proposal: har-diagnostic
Date: 2026-05-03
Source: KTP-130 dev smoke test session

## Trigger
User provides a HAR file path, says "analyze HAR", "check network", "what's wrong with the API responses", or is debugging frontend rendering issues where the data looks wrong.

## Scope
Global (works for any web app, not Klever-specific)

## Draft Steps
1. Parse HAR JSON, extract all API endpoints (exclude static assets, tiles, fonts)
2. Classify responses: success (2xx), error (4xx/5xx), empty, slow (>2s)
3. For each endpoint, check response quality: decimal precision on numeric fields, empty string fields, field name lengths, null vs missing fields
4. Produce an issue matrix: endpoint, issue type, severity (HIGH/MEDIUM/LOW), sample value, suggested fix location (backend vs frontend)
5. Output a structured report with priority-ordered findings
