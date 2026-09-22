# Skill Proposal: disk-management (UPDATE, not new)
Date: 2026-09-21
Source: interactive `/disk-management` run on Gabriel's Mac — 100% full data volume → 28 GiB free
Target: `~/.claude/skills/disk-management/` (SKILL.md + scripts/scan.sh)

## Trigger
Applies every time the skill runs. These are three defects found in live use, not enhancements.

## Scope
Global (the skill is user-level, macOS).

## Proposed changes

### 1. `scripts/scan.sh` line 6 — wrong volume (HIGH: false negative)
The before-shot reads the sealed read-only system volume, which reports a healthy capacity while
the machine is full.

```diff
  echo "=== Overall disk usage ==="
- df -h /
+ df -h / /System/Volumes/Data
```

Observed this run: `/` said `3.7Gi avail, 73% capacity`. `/System/Volumes/Data` said
`404Gi used, 100% capacity`. A reader trusting the `73%` concludes there is no problem.

Same fix belongs in SKILL.md's "Quick start" and "Reporting" sections, which both say
`df -h /`. The after-shot and the before/after table must use the Data volume too, or the delta is
computed against a number that never moves.

### 2. SKILL.md Tier A — `brew cleanup` is too weak
Tier A currently lists `brew cleanup`. Change to `brew cleanup --prune=all`. Plain cleanup leaves
stale `portable-ruby` vendor copies in `/opt/homebrew`; `--prune=all` freed 5.2 GB this run, the
largest single Tier A win.

Note for the skill body: `~/Library/Caches/Homebrew` is a poor proxy for brew's reclaimable bytes
(74M in the scan vs 5.2 GB actually freed), because the waste is in `/opt/homebrew`, which `scan.sh`
never inspects.

### 3. SKILL.md Tier B/C — measure the item, not its parent (HIGH: cost a real decision)
Add to the Tier B paragraph and the Tier C bullets:

> Before putting any item into an `AskUserQuestion`, run `du -sh` on each individual deletion
> target and state its size in the option label. Never let a parent-folder total stand in for the
> items being offered.

What happened: the scan reported `Steam` = 23 GiB; `steamapps/common` listed two games. The question
offered "delete both (22 GiB)" / "DRL Simulator only" / "Liftoff only" with no per-title sizes. The
real split was Liftoff 21 GiB, DRL Simulator ~1 GiB. Gabriel picked DRL Simulator, which recovered
roughly 1 GiB of a 22 GiB opportunity. His call stands, but the menu hid the deciding number.

### 4. SKILL.md — add two known non-cache reclaimable paths
Worth naming under Tier B examples, since routine `Caches/` sweeps never reach them:
- `~/Library/Application Support/Claude/vm_bundles` — Claude Desktop local agent-mode VM (~11 GiB
  observed). Re-provisions on next use.
- `~/Library/Application Support/<streaming app>/*-cache` — e.g. `stremio-server/stremio-cache`
  (7.5 GiB observed). Distinguish from the sibling `downloads/`, which is user content.

## Draft steps to apply
1. Patch `scripts/scan.sh` line 6.
2. Patch the three `df -h /` references in SKILL.md (Quick start step 1, step 4, Reporting).
3. Patch Tier A brew line to `--prune=all`.
4. Insert the `du -sh` per-item rule into Tier B and Tier C.
5. Add the two paths to Tier B examples.
6. Re-run `scan.sh` on this machine to confirm the before-shot now reports 94%, not 73%.
