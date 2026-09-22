# Skill Proposal: skill-self-containment-audit

Date: 2026-07-20
Source: session swift-wren — made /service-factory self-contained + version-wired (dark-factory model)

## Trigger

"Is this skill self-contained?", "wire version to self-improvement", "audit the factory skills",
or after building/refactoring any factory-style skill (dark-factory, sprint-factory,
sprint-crawl, service-factory).

## Scope

global (skills live in `~/.claude-shared-config/skills/`)

## Problem

The self-containment + version↔self-improvement pattern was just built by hand for
service-factory (carried spec in `docs/spec/`, `CHANGELOG.md` bump law, `runs/INDEX.md`
telemetry ledger, `gates/version_guard.py` + SFE-60). dark-factory has most of it by
discipline (CHANGELOG + runs + contracts) but NO mechanical `version_guard`. sprint-factory
/ sprint-crawl have neither. Nothing enforces that a skill's spec is carried in-house
(single source of truth) or that a change bumps the version + CHANGELOG.

## Draft Steps

1. Given a skill dir, check for the four self-containment artifacts: version-stamped spec in
   `docs/spec/`, `CHANGELOG.md` with the bump law, `runs/INDEX.md` (if it's a run-producing
   factory), and extracted execution laws (`contracts/` or `laws-of-execution.md`).
2. Scan the authoritative spec surface for external tethers (`session-retros`,
   cross-repo paths) that would create a drift-prone second copy.
3. Report gaps; offer to port `service-factory/gates/version_guard.py` (parameterized by
   skill dir) + a seeded CHANGELOG as the mechanical backstop.
4. For skills that produce runs, confirm the close/retro phase appends to `runs/INDEX.md`.

## Notes

`version_guard.py` is already a pure, reusable function taking `<skill-dir>` — it can be
lifted almost verbatim. The reference model + full rationale are in the inbox nugget
`2026-07-20-skill-self-containment-version-wiring.md`.
