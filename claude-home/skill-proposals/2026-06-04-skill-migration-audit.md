# Skill Proposal: skill-migration-audit
Date: 2026-06-04
Source: tidy-mole — mapping ecosystem Phase 3 (erasing 5 loose skills into the mapping/adtech plugins)

## Trigger
Before deleting / archiving a skill that was "migrated" or "merged" into a new home (another skill, a plugin, a mode). Triggers on: "erase the old skill", "this was migrated, safe to delete?", "consolidate these skills", or any handoff whose checklist says "remove the superseded skill (content inlined ✓)".

## Scope
global (harness maintenance)

## Problem it solves
Migration notes routinely overclaim ("fully inlined ✓"). On the Phase 3 run, 4 of 5 supposedly-migrated skills had gaps and 2 were load-bearing (a literal `op://` 1Password token path; a skill's entire scraping-technique section). Deleting on trust would have silently lost knowledge that is hard to reconstruct.

## Draft Steps
1. Enumerate old skill's files vs the new home's files.
2. **Byte-diff bundled assets** (scripts, reference docs) old→new. Identical = that half is proven zero-loss.
3. **Prose-audit the SKILL.md** against the new home (dispatch a subagent): list any instruction, gotcha, env var, ticket/RCA ref, mode logic, or provenance present in old but absent in new. Be skeptical — this gates a destructive delete.
4. If gaps found: **backfill each into the new home**, then re-verify every item is present (grep the new files for each).
5. Safety net: confirm the skills dir is git-tracked AND tarball-backup to a durable (non-/tmp) location.
6. Only then delete, with per-skill confirmation. Report each deletion.

## Notes
Could be a mode of an existing skill-authoring tool rather than standalone. Pairs with the handoff-premise-verification rule (verify against current `dev` before executing destructive handoff steps).
