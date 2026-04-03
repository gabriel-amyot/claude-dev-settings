# Autopilot Session State

## Feature
`supervisr-autopilot` — autonomous dev lifecycle orchestrator (Jira ticket → deployed code)

## Location
- Branch: `autopilot-v0.2` at `~/.claude-shared-config/`
- Files:
  - `agents/supervisr-autopilot.md` (1119 lines) — main agent definition
  - `agents/autopilot-config.yaml` (179 lines) — tunable config
  - `library/archive/superpowers-plugin/supervisr-autopilot-guide.md` (642 lines) — documentation + roadmap

## Commit History
```
0b65627 autopilot v0.2.1: address 15 adversarial findings
a981e86 autopilot v0.2: address all 13 adversarial findings
8ab0f62 autopilot v0.1: initial agent, config, and guide
```

## Architecture (10 Phases)
Intake → PRD → Architecture → Task Breakdown → Implementation → Quality Gates → Ship → Integration → Deploy → Closeout

Key design decisions:
- SendMessage for runtime agent comms, Jira comments as write-only audit trail
- Human gates: Phase 0 (if gaps found), Phase 8 (deploy, always)
- All workers on opus, observer on sonnet
- Stakeholder proxy removed — Mary absorbs business perspective
- Wave splitting enforces concurrency cap
- Handoff files in `reports/status/` (not ticket root)
- On-demand responders (not persistent listeners)
- Bug path: synthetic Phase 3 handoff, reclassify to feature if 2+ services

## Status: REVIEW PENDING
- Two adversarial reviews completed and addressed
- Not merged to main, not pushed to origin
- Never tested on a real ticket
- Recommended next: editorial review for structural consistency, then merge or test

## Roadmap (from GUIDE.md)
- v0.1 ✅ MVP
- v0.2 ✅ Adversarial hardening (current)
- v0.3: Installer skill (`/autopilot-init`), resume-from-phase, dry-run mode
- v0.4: Pre-existing test detection, rollback, gate caching
- v0.5: Cost tracking, pipeline analytics, observer v2
- v1.0: Multi-ticket pipelines, auto-deploy, cloud deployment
