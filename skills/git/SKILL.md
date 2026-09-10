---
name: git
description: "The positive procedure for git in this harness: how to clone a Klever GitLab repo, name a branch, shape a commit, and run a mutation safely. Owns the correct action, where the git guard hooks only block the wrong one. Carries a deterministic lint (scripts/git_lint.py) for the four rules no hook enforces: Klever clone scheme, history rewriting, DAC push targets, branch naming. Use when cloning a repo from cicd.prod.datasophia.com, starting a branch, force-pushing or rewriting history, pushing a grp-dac repo, after a worktree-guard/branch-guard/git-pipe-guard block, or when unsure which git command is correct here. Not for GitLab API calls (use gitlab) or merge requests (use klever-mr)."
nav:
  bay: build
  when: "About to run a git command in a Klever repo and unsure of the house form: cloning, branching, pushing a DAC repo, or anything that could rewrite history."
  when_not: "GitLab API queries (use gitlab). Creating an MR (use klever-mr). Worktree setup (use using-git-worktrees)."
---

# git

The harness enforces git with four hooks that block wrong actions. None of them tells
you the **right** action. This skill is that half.

## Quick start

Lint any git mutation before running it:

```bash
python3 ~/.claude-shared-config/skills/git/scripts/git_lint.py "git push --force origin dev"
```

Clean output means the four unhooked rules pass. It says nothing about worktree
placement or piping, which the hooks own.

## Cloning a Klever GitLab repo

Use plain `https://`, never `https+iap://`:

```bash
git clone https://cicd.prod.datasophia.com/<group-path>/<repo>.git
```

The IAP config loads through `includeIf hasconfig:remote.*.url:https://cicd.prod.datasophia.com/**`.
That glob matches the plain URL during clone and rewrites the remote to `https+iap://`
for you.

Gabriel's `~/.gitconfig` gained a second glob for the `https+iap://` scheme on
2026-09-10, so both forms clone on this machine. **Keep writing plain `https://`
anyway.** Any machine without that second glob still fails an `https+iap://` clone with
`ConfigGetURLMatch - could not read config 'http.cookieFile'`, and commands travel.

Do not reach for the `git init` + `remote add` + `fetch` fallback first. That workaround
got recorded seven times as if the plain clone were unreliable. It is not.

Root-cause fix, both verifications, and the IAP cookie refresh recipe:
`documentation/bibliotheque/stack/gitlab-iap-devtools.md`.

## Branch and commit

Branch: `{TICKET-ID}-short-description`, e.g. `KTP-571-zip-codec`. No `fix/`,
`feature/` or `chore/` prefixes, no folder separators. Repos with no Jira project
(e.g. `app-agent-skills`) use a plain descriptive name.

Commit subject: `{TICKET-ID}: {short imperative what}`. Body carries **why** first
(the problem or ask), then **what** changed as an outcome, not a file list. MR
descriptions are built from commits, so each commit must stand alone.

## Running a mutation

Run mutations unpiped. A pipe reports the last command's status, so `git push | tee log`
reads as success even when the push failed. Read-only queries pipe freely.

```bash
git push origin KTP-571-zip-codec     # unpiped, failure is visible
git log --oneline | head              # fine
```

## Branch targets

| Repo shape | Push to | Promote by |
|---|---|---|
| `grp-dac/*` (DAC) | `dev` only | merge request, dev → uat → main |
| Klever app repos | feature branch, MR to `dev` | `klever-mr` |
| `app-agent-skills` | descriptive branch | MR to `main` (no dev) |
| `project-management` | `main` directly | nothing, single trunk |

Confirm before assuming: `git branch -r | grep HEAD`. `main` being default does not mean
`main` deploys. `app-agent-hub` inverts it. Run `/deploy-identity` before any claim about
deployed code.

## Never rewrite published history

No force push, `filter-branch`, `reset --hard` to a pushed ref, or `--amend` on a pushed
commit. This holds even if Gabriel approves it. If he insists, hand him the exact command
with branch, remote and paths, and let him run it.

## Who enforces what

| Rule | Enforced by | Tested |
|---|---|---|
| Edits happen in a worktree, not a main checkout | `worktree-guard` hook | fixtures |
| No edits on a protected or already-merged branch | `branch-guard` hook | fixtures |
| No branches or worktrees in `project-management` | `pm-single-trunk-guard` hook | fixtures |
| Mutations are not piped | `git-pipe-guard` hook (warn-only) | fixtures |
| Klever clone scheme | `scripts/git_lint.py` | `git/lint` |
| No history rewriting | `scripts/git_lint.py` | `git/lint` |
| DAC push targets `dev` | `scripts/git_lint.py` | `git/lint` |
| Branch naming | `scripts/git_lint.py` | `git/lint` |

A hook that does not fire is not permission. The lint is advisory in the same way: it
covers four rules, not the whole policy.

## Evals

```bash
python3 ~/.claude-shared-config/skills/git/evals/run_git_evals.py
```

23 Layer A fixtures, registered as `git/lint`. Every rule family is mutation-tested, so a
rule that stops firing fails the suite instead of quietly becoming prose.
