# Skill Proposal: Post-MR Dev Checkout
Date: 2026-05-16
Source: KTP-669 wrong-branch incident RCA

## Trigger
After `/klever-mr` completes (branch pushed, MR URL presented). Also at `/session-check` close phase, for all repos touched during the session.

## Scope
org (Klever)

## Draft Steps
1. Detect repos touched during session (git status scan across ~/Developer/grp-beklever-com/)
2. For each repo with a pushed feature branch: `git checkout dev && git pull origin dev`
3. Report which repos were switched back
4. Could be integrated as a final step in `/klever-mr` and as a step in `/session-check` Phase S1

## Rationale
On 2026-05-16, an entire session's work (30 files, 2 review gates) was wasted because the previous session left a merged feature branch checked out. The next session started coding on that stale branch without checking. Switching to dev after MR creation prevents this class of error.
