# Git-guard batch — eval report (2026-07-07)

Targets: `branch-guard.sh`, `worktree-guard.sh`, `deploy-identity-guard.sh` (hooks) and
`deploy-identity/probe.sh` (script). Built by the w1-gitguards agent; the agent hit a
session limit after all four suites were green, so this report was assembled by the lead
from the suites' inline documentation and verified by re-running everything.

## Suites and status (all green, re-verified by the lead)

| Suite | Cases | Runner |
|---|---|---|
| branch-guard | 11/11 (10 + wiring) | `run_hook_evals.py --hook branch-guard` |
| worktree-guard | 8/8 (7 + wiring) | `run_hook_evals.py --hook worktree-guard` |
| deploy-identity-guard | 10/10 (9 + wiring) | `run_hook_evals.py --hook deploy-identity-guard` |
| deploy-identity probe | 8/8 | `python3 ~/.claude-shared-config/skills/deploy-identity/evals/run_probe_evals.py` |

All three hooks are wired in settings.json; wiring assertions pass.

## Hermetic design (why no real repo is ever touched)

Every case overrides `HOME={tmp}`, so each hook's `$HOME/Developer/` path-scope check
resolves inside the per-case temp dir; the committed `code-repo` bundle is hydrated into
`{tmp}/Developer/repo`. deploy-identity cases symlink the real probe into
`{tmp}/.claude/skills/` and feed it a repo-local `.deploy-identity.yaml` fixture config,
so the real `~/.claude/deploy-identity/` registry is never read or written. Linked
worktrees and origin/dev refs are created in `setup:` from the hydrated clone.

## Coverage highlights

- branch-guard: protected branches (dev/main/master) block; feature branch ahead of dev
  allowed; branch already merged to origin/dev blocks; camelCase `filePath` input handled;
  non-repo files, paths outside ~/Developer, and project-management exempt.
- worktree-guard: main-worktree edit blocks (including nonexistent target file in main
  worktree); linked worktree allowed; pm exempt; non-repo file under ~/Developer allowed.
- deploy-identity-guard (KTP-688 spine): default-branch ≠ deploy-branch read blocks (the
  exact KTP-688 trap); feature branch + deployed-system transcript intent blocks; feature
  branch without intent allowed; reading the deploy branch allowed (VERIFIED);
  unregistered repo allowed; CANT_VERIFY on default branch still blocks.
- probe.sh: VERIFIED on deploy branch with resolvable sha; MISMATCH on default branch;
  no-registry, unresolvable-sha (CANT_VERIFY), no-repo, multi-deploy-branch, and
  listed-branch-missing-sha paths all pinned via DEPLOY_IDENTITY_JSON fields.

## Findings (pinned, hooks not modified)

1. **branch-guard blocks with exit 1, not exit 2.** Any non-zero exit blocks the tool, so
   the guard works, but it deviates from the exit-2 convention every other guard follows
   and from the PreToolUse "2 = block with stderr shown" contract. Cosmetic-to-low risk;
   fixtures pin exit 1 so a normalization to 2 will trip the suite deliberately.
2. **worktree-guard macOS symlink artifact (fixture-env only).** From a repo
   *subdirectory*, git returns an absolute `--git-dir` but relative `--git-common-dir`;
   under `/var`→`/private` symlinked temp dirs the hook's `cd && pwd` comparison then
   falsely allows. Real repos under `~/Developer` are not symlinked, so production is
   unaffected; block cases target repo-root files where detection is reliable. If the
   hook is ever hardened, use `pwd -P` on both sides.

## Manifest entries

Registered in `evals/manifest.yaml`: hooks/branch-guard, hooks/worktree-guard,
hooks/deploy-identity-guard, deploy-identity/probe — all layer A, last_green 2026-07-07.
