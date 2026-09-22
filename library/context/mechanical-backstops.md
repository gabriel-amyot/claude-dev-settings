# Mechanical Backstops

Hooks enforce these rules. They are defense-in-depth, not a substitute for following the rule: each has known gaps, and a hook that does not fire is not permission.

| Rule | Hook | Blocks |
|---|---|---|
| No edits on protected or already-merged branches | `branch-guard.sh` | Edit/Write |
| No edits in a main worktree | `worktree-guard.sh` | Edit/Write |
| No branches or worktrees in `project-management` | `pm-single-trunk-guard.sh` | Bash (blind to skill-internal worktrees) |
| `sessions/ledger.yaml` written via the helper only | `ledger-write-guard.sh` | Edit/Write (Bash passes silently) |
| No reading a non-deploy branch during deployed-code reasoning | `deploy-identity-guard.sh` | Read/Grep |
| Owner pushback triggers falsification | `challenge-detect.sh` | injects directive |
| Library checked before declaring a mechanism unknown | `library-stamp-guard.sh` | Agent/Task dispatch |
| Config files not deleted | `file-guard.sh` | Edit/Write, Bash `rm`/`mv` |
| `project-management` file placement | `ticket-path-guard.sh` | warns |
| CLAUDE.md holds rules, not origins | `claude-md-tier-lint.sh` | warns |
| AGENTS.md mirrors CLAUDE.md | `agents-md-mirror.sh` (PostToolUse) + `agents-md-mirror-startup.sh` (SessionStart) | regenerates |
| Library pointers surfaced by topic | `bibliotheque-recall.sh` | injects pointers |
| A piped git mutation hides its own failure | `git-pipe-guard.sh` | warns |
| CLAUDE.md authoring standards | `claude-md-guard.sh` | injects `claude-md-authoring.md` on any CLAUDE.md edit |
| Spec fidelity on edits | `spec-guard.sh` | injects |
| Screenshot placement | `screenshot-placement-guard.sh` | warns |
| Unscoped investigation drift | `rabbit-hole-guard.sh` | injects |
| Session capture before compaction | `pre-compact-guard.sh`, `auto-operationalize-cmd.sh` | injects |
| Session close capture | `session-close-operationalize-guard.sh` | blocks |
| Harness drift at session start | `harness-parity-check.sh` | reports |
| Unread proposals at session start | `proposal-backlog-check.sh` | reports |

Session-lifecycle plumbing (`session-start.sh`, `session-init-reminder.sh`, `prompt-submit.sh`, `post-tool-use.sh`, `on-exit.sh`) is not rule enforcement and is not listed.

## Known gaps

- `pm-single-trunk-guard.sh` is blind to worktrees created inside a `Workflow` run or a skill. Three stray worktrees existed in `project-management/.claude/worktrees/` while the rule was in force.
- `ledger-write-guard.sh` blocks Edit/Write but deliberately allows Bash, because the helper needs Bash. A raw Bash write to the ledger passes silently. Silence is not approval.
- `ticket-path-guard.sh` and `claude-md-tier-lint.sh` warn only. They do not stop a write.
- The PostToolUse mirror fires only on `Edit`/`Write`. A CLAUDE.md changed by Bash, `git checkout`, or an external editor leaves AGENTS.md stale until the SessionStart resync runs, so a mirror can be stale for the remainder of a session.
- `bibliotheque-recall.sh` skips prompts under 10 characters, fires each pointer at most once per session, and needs a score of 2. A prompt naming one topic that many pages match (`liquibase` matches 10 rows) surfaces nothing rather than guessing.
- `pm-single-trunk-guard.sh` keys on the shell **cwd**, not the repo named in the command. A bare
  `git worktree add` issued while cwd is `project-management` targets `project-management`, even
  when the surrounding conversation is entirely about another repo. The Bash tool's cwd also
  resets between calls, so a `cd` earlier in the session does not protect a later command. Fix:
  always run `git -C <absolute-repo-path> worktree add ...`. The guard's own error message says
  this. Learned 2026-08-27 (session `crisp-pike`). **Confirmed 2026-09-01 (session
  `deft-wolf`): the gap also holds inside a single compound command.** A `cd <repo> && git
  worktree add ...` chain run as ONE Bash call still gets blocked, even though the `cd` moves
  into the target repo before the worktree command runs in the same string. The guard checks
  the shell's resting cwd, not the compound command's effective cwd at execution time. Same
  fix applies: `git -C <repo-path> worktree add ...`.
- `file-guard.sh` blocks Edit/Write on **any file named `CLAUDE.md`**, not only agent-config ones.
  A vendor-documentation page that happens to be named `CLAUDE.md` (e.g. a bibliothèque skill
  quick-start) is protected identically to a real config file. The escape hatch is explicit: hand
  the user a ready-to-run command. The guard covers Edit/Write but not a Bash-based write, so
  routing around it is possible — doing so after being told to hand over the command defeats a
  control the user installed on purpose. Learned 2026-08-27 (session `crisp-pike`).

### Retired rule: "never pipe git commands"

Replaced 2026-08-27 after measurement, not after an incident. The old blanket rule was
violated in **431 of 1,642 sessions (26%)** with no demonstrable harm, and its own example
(`git fetch && git status`) prohibited chaining rather than piping.

The obvious hazard was tested and failed. Sessions piping git hit the `~/.gitconfig` lock
error 27.1% of the time versus 7.7% without, but controlling for git-command volume the gap
collapses (14.2% vs 11.8% at 1-5 commands; the high-volume non-piper cells have n=7 and
n=0). Volume drives the lock error, not piping, and the real cause is already documented in
[[worktree-fleet-ops]] as parallel-fleet contention on the shared global-config lock, with
retry as the recovery.

The one real hazard is exit-status masking: a pipe reports the LAST command's status, so
`git push | tee log` reads as success when the push failed. The rule now targets exactly
that, and `git-pipe-guard.sh` enforces it on mutating subcommands only. Read-only pipes are
explicitly fine.

**Rule-design lesson:** the old rule was retired, not merely narrowed, because it was
self-contradictory before it was ever wrong — it prohibited "piping" while its own example
(`git fetch && git status`) prohibited chaining, a different operation, with no rationale
recorded anywhere for either. An unenforceable rule is usually an ambiguous rule: if a guard
cannot be written for it, the rule needs rewriting before it needs a hook.

A hook that does not fire is not permission.
