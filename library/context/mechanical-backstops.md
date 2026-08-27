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

### Rules with NO hook coverage

- **"Never pipe git commands"** has no backstop. Measured 2026-08-27 across 1,642 transcripts: git-as-command piped in **431 sessions (26%)**, `git ... && git ...` chained in 271 (17%). Highest-violation rule in either CLAUDE.md. The rule text is also ambiguous — it prohibits "pipe" but its example shows `&&` — so the count mixes probably-harmless piping (`git log | head`) with the chaining the example targets. Disambiguate before mechanising.

A hook that does not fire is not permission.
