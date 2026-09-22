# Skill Proposal: clean-room-feature-port
Date: 2026-06-10
Source: KTP-799 — porting proximity-explorer prototype features (PR #17/#18) into the portal Planning Map

## Trigger
"Port/migrate/merge feature X from <prototype or throwaway repo> into <production repo>." Especially when the prototype is prototype-grade code that must NOT be copy-pasted into production, but its data files and observable behavior should carry over.

## Scope
org (Klever-first; the pattern generalizes to any two-repo feature migration)

## Why a skill
The two-pass firewall is easy to get wrong: the natural instinct is to read the prototype component and copy it. Enforcing the separation (and the data-contract completeness that makes it possible) needs a checklist + agent-dispatch scaffolding, not memory.

## Draft Steps
1. **Scope + pin the source.** Identify the prototype repo, the merged PR(s), and the exact combined diff range. For stacked/merged PRs use `gh pr view N --json baseRefOid` for the true pre-feature base (NOT `git merge-base`, which collapses once master contains the merges). Combined diff = `<firstPR.baseRefOid>..<final-branch-tip>`.
2. **Create the worktree** off the production default branch (main checkout is usually hook-blocked). Both passes operate here.
3. **Pass 1 — spec extractor (firewalled agent).** ONE agent reads the prototype diff + data files and writes behavioral SBE specs (Given/When/Then) PLUS an exhaustive data-contracts spec (every key name, key format, reserved keys to strip, geometry types, units, lookup thresholds, distance method, fallback rules, value formatting). No implementation thinking. This is the only agent allowed to read prototype component code. Commit the specs.
4. **Human gate.** Present the specs (especially the data-contracts doc) for review before implementation.
5. **Orchestrator copies data files** verbatim into the worktree (`git show <branch>:public/foo > worktree/public/foo`), so the Pass-2 agent never touches the prototype repo. Validate the copied files parse.
6. **Pass 2 — implementer (firewalled agent).** A SEPARATE agent reads ONLY the approved specs + the production codebase. Explicitly forbidden from opening the prototype's component files. Build natively against the spec. Then `grep` the changed code for any prototype path/file refs to verify the firewall held.
7. **Verify + ship** through the normal repo pipeline (build, version bump, CHANGELOG, MR), watching for version/tag collisions if the base branch advanced.

## Notes
- The data-contracts spec is the firewall seam: if it's incomplete, Pass 2 hits an undocumented field. The fix is to extend Pass 1's spec, never to peek at the prototype.
- Companion captures in bibliothèque inbox: 2026-06-10-ktp799-clean-room-feature-port.md.
