# Codex Hook Enforcement — Declared but Unverified

On-demand context: load before claiming any guard, gate or hook protects a Codex session, or
before wiring a new hook and calling the harness protected.

## Open question: no hook could be made to fire under `codex exec`

**Status: UNVERIFIED. This is a failed probe, not a proven absence.** Do not cite it as "Codex
guards are dead", and do not cite it as "Codex guards work."

`~/.codex/hooks.json` declares roughly 20 hook mappings, including six `PreToolUse` guards
(`pm-single-trunk-guard`, `worktree-guard`, `branch-guard`,
`session-close-operationalize-guard`, `deploy-identity-guard`, `library-stamp-guard`). On
2026-09-04 no probe could make any of them, or any hook of my own, actually run.

What was tried, all on Codex CLI 0.149.1:

1. A marker-writing probe appended to `~/.codex/hooks.json` `SessionStart`. Entries went from 4
   to 6; the logged `hook: SessionStart` count stayed at **6** and no marker file appeared.
2. A probe plugin shipping `hooks/hooks.json` with `${CLAUDE_PLUGIN_ROOT}`, matching the shape
   `session@local` uses. Listed in `.claude-plugin/marketplace.json` (the `source` needs a `./`
   prefix or `codex plugin add` reports "not found in marketplace"), installed with
   `codex plugin add guardprobe@local`, confirmed cached at
   `~/.codex/plugins/cache/local/<name>/local/` with an executable script. Still no marker.
3. Both of the above re-run with `--dangerously-bypass-approvals-and-sandbox`, in case
   `-s read-only` was blocking the hook's own `touch`. Still nothing.

Both probe scripts ran correctly when invoked by hand, so the scripts were not the problem.

**Why this is unverified rather than settled.** `codex exec` suppresses hook stdout/stderr, so a
firing hook and a dead one look identical. Interactive `codex` may honour hooks where `exec` does
not, and that was never tested. The binary does know the event names (`pre_tool_use`,
`post_tool_use`, `session_start`, `user_prompt_submit`, `subagent_start`, …) and references a
`hooks/hooks.json` path convention; `~/.codex/hooks/hooks.json` does not exist on this machine,
only `~/.codex/hooks.json`.

**How to apply:** treat Codex-side hook enforcement as unproven. Never state that a guard covers
Codex on the strength of a mapping existing in `~/.codex/hooks.json`. To settle it, run an
**interactive** Codex session and trigger a known guard, where hook output is visible. Until then,
a Klever guard is verified for Claude Code only.

## Definite, separate gap: `file-guard.sh` is not declared on the Codex side at all

Independent of the mechanism question, and verified:

```
grep -c file-guard ~/.codex/hooks.json      -> 0
grep -c file-guard ~/.claude/settings.json  -> 1
```

The adapter symlink `~/.codex/hooks/file-guard.sh` exists and resolves, which makes it *look*
wired. It is mapped to no event. So config-deletion protection on `CLAUDE.md`,
`.claude/settings.json` and `agent-os/sbe/` is a Claude-only guarantee, independent of the
`.protection-enabled` flag — that flag cannot affect a hook that was never mapped.

The old `harness-parity-check.sh` could not surface this because it verified a hardcoded
five-name hook allowlist that omitted `file-guard.sh`. The replacement derives the hook list from
`shared-config/hooks/` on disk, which is why it appeared. **A checker with a hardcoded allowlist
reports health for the names it knows and silence for everything else.**

## Related

- [[claude-config-filesystem-topology]] — which `~/.claude` paths are symlinks and which are
  git-backed; same class of error (a claim about config that nobody re-verified).
- Backups of `hooks.json`, `config.toml` and `marketplace.json` from the probe:
  `~/.claude/backups/codex-20260904/`.

---

**Source:** wayfinder integration session, 2026-09-03/04. Probe run and restored the same day.
