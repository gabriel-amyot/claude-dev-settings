# Skill Proposal: demo-data-forge
Date: 2026-04-12
Source: SPV-141 emergency demo data session

## Trigger
When the user needs to populate a demo environment with realistic data across the lead lifecycle pipeline. "Forge demo data", "populate dashboard", "seed demo environment", "fake data for demo."

## Scope
org (Supervisr) — applicable to any partner's demo environment

## Draft Steps
1. **Load existing leads** from a create-leads results JSON (UUIDs + phones)
2. **Assign scenarios** based on a configurable distribution table (outcome buckets + interaction counts)
3. **Generate interaction events** matching each scenario's realistic pattern (voicemail, no-answer, connected calls)
4. **Fire interactions** to ERS `/Interaction/update` in parallel (proven DreamPipe payload builder)
5. **Record dispositions** via LLS `recordDisposition` for terminal leads (sequential, paced)
6. **Spot-check** via EQS Gateway query to confirm data landed

## Existing Implementation
`tickets/SPV-141/tools/mass-forge-interactions.py` — first instance. Imports helpers from `tracer.py`. Supports `--dry-run`, `--limit N`, `--workers N`, `--skip-interactions`, `--skip-dispositions`, `--seed N`.

## Generalization Notes
- Distribution table should be configurable (not hardcoded)
- Should accept any partner's org ID and source name (not just clarifying/Remix Dynamix)
- Should support multiple lead sources in one run
- Consider adding `--resume` for interrupted runs (persist progress to state file)
