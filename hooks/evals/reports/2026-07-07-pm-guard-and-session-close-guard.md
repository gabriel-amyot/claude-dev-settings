# Hook eval report — pm-single-trunk-guard + session-close-operationalize-guard (2026-07-07)

Layer A deterministic regression suites for two catastrophe-class PreToolUse guards.
All exit codes pinned against the live hooks on 2026-07-07 by piping JSON to each hook
directly (the runner executes ONLY the hook, never the guarded command — no real repo or
session state is mutated).

## Suites

| Suite | Hook | Cases | Result | Runner command |
|---|---|---|---|---|
| pm-single-trunk-guard | `hooks/pm-single-trunk-guard.sh` | 20 + wiring | 21/21 PASS | `python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook pm-single-trunk-guard` |
| session-close-operationalize-guard | `hooks/session-close-operationalize-guard.sh` | 14 + wiring | 15/15 PASS | `python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook session-close-operationalize-guard` |

Both wiring assertions pass: each hook is registered under `PreToolUse` in
`~/.claude/settings.json` (pm-guard on Bash, session-close on Edit/Write).

## Coverage — pm-single-trunk-guard

True-positive blocks (exit 2): `checkout -b` via `-C <pm>`, `worktree add` with cwd=pm,
`switch -c` via `-C <pm>`, compound `cd <pm> && git checkout -b` with cwd=pm.
Allow (exit 0): `branch -D`/`worktree remove`/`worktree prune`/`branch -a`/`checkout main`
in pm (cleanup + listing + non-creating checkout), `echo` mentioning creation strings,
creation targeting a code repo (`-C {tmp}`).

## Coverage — session-close-operationalize-guard

Block (exit 2): close with stale manifest, close with no manifest ever, close fresh but
referenced inbox file missing, abandoned+stale.
Allow (exit 0): fresh + routed inbox file, fresh with no inbox dir (org unused),
non-ledger edit, ledger edit not closing, `.operationalize-skip` override.

## Red-team findings

### Caught (guard held)
- pm `rt-02`: `-C` path with `../` that resolves through `/project-management` → BLOCK
  (substring test sees the literal path component).
- pm `rt-04`: `git -C <pm> worktree add` → BLOCK.
- session `rt-01`: close via the Write tool `content` field (not `new_string`) → BLOCK.
- session `rt-02`: `status:closed` with no space → BLOCK (`[[:space:]]*` matches zero).
- session `rt-05`: fresh manifest living under `sessions/archive/done/*` → correctly ALLOW.

### KNOWN GAPs (evasions pinned as current behavior — need Gabriel's eyes)
- **pm GAP-1 `rt-01` — `git branch <name>` creates without checkout and is NOT blocked.**
  The CREATE regex only matches `branch\s+-b` (which is not even a real git form). Plain
  `git -C <pm> branch newname` creates a branch in pm and slips through (exit 0). This is
  the single most realistic evasion — `git branch <name>` is the ordinary way to create a
  branch. Recommend adding a `branch\s+(?!-)` (non-flag arg) clause.
- **pm GAP-2 `rt-03` — env-var indirection `git -C $PM checkout -b` evades.** `target_of`
  captures the literal unexpanded `$PM`, which lacks `/project-management` (exit 0). Hard
  to close without shell expansion; low practical risk (agents rarely `-C $VAR`).
- **pm GAP-3 `rt-05` — `git worktree add <pm>/wt` from a code repo evades.** `target_of`
  inspects only `-C`/cwd, never the worktree destination path, so a worktree whose *dir*
  lands inside pm is not caught (exit 0). Recommend also testing the `worktree add` path arg.
- **pm GAP-4 `case 12` — `cd <pm> && git checkout -b x` with cwd≠pm evades.** The hook reads
  the JSON `cwd`, not the in-command `cd`, so a subshell that changes directory first slips
  through (exit 0).
- **session GAP-5 `rt-03`/`rt-04` — quoted status value evades.** `status: 'closed'` and
  `status: "closed"` are not detected by `grep -E 'status:[[:space:]]*(closed|abandoned)'`
  (the bare-word match fails on the leading quote), so the close is allowed (exit 0). YAML
  writers that quote scalars would bypass the gate. Recommend allowing an optional quote:
  `status:[[:space:]]*["'\'']?(closed|abandoned)`.

### False positives (guard over-blocks — pinned; need Gabriel's eyes)
- **pm FP-1 `rt-06` — `git log --grep 'worktree add'` in pm is BLOCKED (exit 2).** A
  read-only history search is treated as creation because the CREATE regex matches
  `worktree add` inside the quoted argument. This is a plausible real command (searching
  history) and would be wrongly blocked in the pm repo.
- **pm FP-2 `rt-07` — `git commit -m "... checkout -b ..."` in pm is BLOCKED (exit 2).** A
  commit whose message text contains a creation phrase is over-blocked. Less common but real.

Both FPs stem from the CREATE regex scanning the whole `git`-led segment including quoted
argument text, rather than only the subcommand + flags. A fix would tokenize past quoted
strings (or require the create verb to be the first word after `git [-C <path>]`).

## Pins needing Gabriel's decision

The two FPs and five GAPs above are pinned as CURRENT behavior so the suite stays green and
any future hook change that alters them is caught. None were "fixed" — the task was pin,
not patch, and the hooks were not modified. If Gabriel wants the guards hardened (GAP-1 and
GAP-5 are the highest-value: real branch creation and quoted-YAML close), the corresponding
fixtures' `expected_exit` flip from the pinned value to the desired one, which will fail
until the hook is updated — exactly the regression signal wanted.
