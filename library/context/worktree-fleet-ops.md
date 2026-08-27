# Worktree & Fleet Operations

Cross-org operational notes for running git worktrees, especially when many agents run git
concurrently (orchestrated fleets). Complements `superpowers:using-git-worktrees` (the how-to)
and the `pm-single-trunk-guard` hook (the safety block).

---

## Creating a worktree when dispatched from `project-management`

Agents are commonly dispatched with `cwd = project-management` (the standard orchestration
cwd). `project-management` is a single-trunk backup repo — no branches, no worktrees — and the
`pm-single-trunk-guard.sh` PreToolUse hook blocks worktree/branch *creation* whose target
resolves to it.

Git resolves the target from the current directory unless told otherwise. So a **bare**
`git worktree add …` (or `checkout -b` / `switch -c`) run from a `project-management` cwd
targets `project-management` and is correctly blocked.

**Rule: when creating a worktree for a CODE repo from a `project-management` cwd, target the
repo explicitly.** Never rely on a bare invocation.

```
git -C ~/Developer/<org>/.../<repo> worktree add <path> <branch>
```

(Or `cd` into the code repo first, then run the worktree command there.) The guard honors an
explicit `git -C <repo>` and will not block a target outside `project-management`. The bare
form staying blocked is intentional — it is the guard's whole purpose (see the 2026-06-16
incident where `project-management` drifted to 6 branches + 20 stray worktrees).

---

## `~/.gitconfig` lock contention in parallel fleets

*Doc-only note; the structural fix is deferred pending evidence of recurrence.*

When many agents run git concurrently in separate worktrees, you may see transient:

```
error: could not lock config file ~/.gitconfig: File exists
```

This is **contention on the single shared global-config lock (`~/.gitconfig.lock`), not
corruption.** Something in the parallel path is *writing* global config while agents run.
Recovery: **retry once or twice with a small backoff** — the lock is short-lived and the
operation is idempotent.

Structural fix (deferred): if this recurs across sessions or starts failing operations
mid-ship, investigate *what* writes `~/.gitconfig` per-worktree (candidates: a worktree-setup
step setting `user.name`/`user.email` globally, a credential-helper refresh, or gc/maintenance
logging) and redirect that write to **local** (`--worktree` / per-repo) config so parallel
agents stop contending on one file. Read-only git (status, log, ls-remote, worktree add of an
existing branch) should not touch global config at all. Do not blind-patch: one non-fatal
observation (2026-07) is not enough to justify changing where a skill writes git identity that
worktrees depend on.
