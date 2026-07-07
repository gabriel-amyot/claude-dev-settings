# Hook eval report — cheap hook sweep (2026-07-07)

Layer A deterministic regression suites for six low-complexity hooks. Every exit
code and needle was pinned by piping JSON (or setting env vars, per each hook's
actual stdin/env contract) to the live hook before encoding; no hook script or
`settings.json` was modified.

Runner: `python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook <name>`

## Overall status

**Suites 1–4 fully green. Suites 5–6 green except their designed wiring failure.**

| Suite | Cases | Wiring | Runner exit |
|---|---|---|---|
| claude-md-guard | 6/6 PASS | PASS (wired under PostToolUse) | 0 |
| screenshot-placement-guard | 6/6 PASS | PASS (wired under PostToolUse) | 0 |
| proposal-backlog-check | 6/6 PASS | PASS (wired under SessionStart) | 0 |
| spec-guard | 6/6 PASS | PASS (wired under PostToolUse) | 0 |
| file-guard | 5/5 PASS | FAIL (by design — not registered) | 1 |
| config-protect | 6/6 PASS | FAIL (by design — not registered) | 1 |

The two non-zero runner exits are solely the intentional wiring assertions for
file-guard.sh and config-protect.sh, confirmed absent from `~/.claude/settings.json`
by grep against the live file before writing either fixture. Do not flip
`expected:` or touch settings.json to green them — see the TODO comments in each
YAML for the actual decision needed.

## Stdin/env contract per hook (load-bearing — get this wrong and cases silently
no-op)

| Hook | Reads | Notes |
|---|---|---|
| claude-md-guard.sh | `$CLAUDE_TOOL_INPUT` env var | NOT stdin. Correctly-quoted extraction. |
| screenshot-placement-guard.sh | stdin JSON (`tool_input.name`/`fileName`) | PostToolUse on Playwright screenshot tool. |
| proposal-backlog-check.sh | filesystem only, no tool_input | SessionStart; gated on `$HOME/.claude/skill-proposals`. Isolated via `HOME` override. |
| spec-guard.sh | stdin JSON (`tool_input.file_path`/`filePath`, or top-level if no `tool_input` wrapper) | MAPPING file check short-circuits before stdin is even read. |
| file-guard.sh | stdin JSON (`tool_input.file_path`/`filePath`) | Gated on `$HOME/.claude/hooks/.protection-enabled`. Isolated via `HOME` override. |
| config-protect.sh | `$CLAUDE_TOOL_INPUT` env var | NOT stdin. **Extraction is broken — see bug below.** |

## TARGET 1 — claude-md-guard.sh (PostToolUse: Edit\|Write)

Injects the CLAUDE.md authoring standards as context whenever a file whose
basename is `CLAUDE.md` is edited/written. Always exits 0; silent for any other
file. 6 cases: basename match at a nested path, non-match silent, `filePath`
camelCase fallback, empty env var silent, malformed JSON fails closed silent
(caught by `2>/dev/null`), and a content check that the injected context actually
includes the real standards file body, not just the header line.

## TARGET 2 — screenshot-placement-guard.sh (PostToolUse:
`browser_take_screenshot`)

Advisory-only (never blocks, always exit 0). Warns when a Playwright screenshot
`name` is a bare filename that will land at the repo root. 6 cases including the
`tickets/*` and generic `*/*` good-placement paths, the bare-filename warning, a
`fileName` camelCase fallback, missing-name silence, and one pinned gap:

- **PINNED GAP (not a bug, a design edge case):** `./foo.png` contains a `/`, so it
  matches the generic `*/*` "probably OK" branch even though it still resolves to
  the repo root exactly like a bare filename would. Case
  `06-dot-slash-bypasses-warning-pinned-gap` documents this so a future tightening
  has a case to update deliberately rather than discovering it live.

## TARGET 3 — proposal-backlog-check.sh (SessionStart)

Fires a `systemMessage` nudge only when pending proposal count > 5 **and** the
last audit is ≥7 days old (or the audit marker file is missing entirely). Every
case overrides `HOME` to an isolated tmp dir with a fabricated
`.claude/skill-proposals/` tree — the real backlog (41 `.md` files today) was never
read or touched by this suite. 6 cases: under-threshold silent, at-threshold
boundary (5, exactly `-le 5`) silent even with a stale audit date — pins the
short-circuit ORDER (count check before date check), over-threshold with a recent
audit silent, over-threshold with a stale audit firing, over-threshold with the
audit marker file missing entirely firing (exercises the `date -r ... || echo 0`
fallback distinctly from "old file"), and no-proposals-dir-at-all silent.

## TARGET 4 — spec-guard.sh (PostToolUse: Edit\|Write)

Warns when an edited file (relative to a hardcoded `work-assistant/` mapping) is
covered by an SBE spec, per real content in
`~/Developer/gabriel-amyot/tools/work-assistant/agent-os/spec-guard-mapping.yml`.
6 cases: the MAPPING-file-missing short-circuit (isolated `HOME`, exits 0 before
stdin is even parsed — this is the highest-value case since it proves the hook
fails closed rather than crashing if the mapping ever goes missing), a real guarded
source match (`bin/process-meeting.sh`), a path with no `work-assistant/` segment,
a `work-assistant/` path with an unmapped source, a `filePath` camelCase fallback
against a different real guard (`lib/find-config.sh`), and a payload with no
`tool_input` wrapper at all — pins that the script falls back to treating the
whole top-level JSON as the params dict (`bin/extract-action-items.sh`).

Cases 2, 5, 6 read the REAL mapping file (read-only) since MAPPING's path isn't
overridable independent of the guard content; this is safe because the hook only
reads it.

## TARGET 5 — file-guard.sh (intended PreToolUse: Edit\|Write)

Gated on `$HOME/.claude/hooks/.protection-enabled`; every case overrides `HOME` to
an isolated tmp dir so this suite never touches the real flag file. Blocks
(`exit 2`) edits to files basenamed `CLAUDE.md`, containing `.claude/settings.json`,
or under `agent-os/sbe/`. 5 behavioral cases all pass: protection-disabled silent
regardless of target, and each of the three protected-path branches individually,
plus one unrelated-file pass-through.

**Wiring assertion fails by design.** Confirmed via `grep -n "file-guard" ~/.claude/settings.json`
before writing the fixture: zero hits. Nothing dispatches this hook today, despite
its own header comment claiming it "Replaces: config-protect.sh, prompt hook,
claude-md-guard.sh" — that claim is not true in the live config; both
config-protect.sh's would-be role and claude-md-guard.sh remain separately
relevant (claude-md-guard.sh is itself registered and green, see Target 1).

## TARGET 6 — config-protect.sh (intended PreToolUse: Edit\|Write)

**CONFIRMED BUG, found while running this suite — needs Gabriel's eyes.** The
inline python JSON extraction is corrupted:

```
data.get('"'"'file_path'"'"', data.get('"'"'filePath'"'"', '"'"''"'"'))
```

The repeated `'"'"'` sequence is the shell idiom for embedding a literal single
quote inside a *single-quoted* string — but this script's `python3 -c "..."` call
is wrapped in DOUBLE quotes, so bash never processes that escaping and it lands in
the python source verbatim. The effective python becomes:

```python
data.get('"file_path"', data.get('"filePath"', '""'))
```

i.e. it looks up a dict key literally named `"file_path"` (quote characters
included), which never exists in real JSON. Both lookups miss, and it falls to
the default value `'""'` — a 2-character string, not empty — so the script's own
`[ -z "$FILE_PATH" ]` empty-guard never trips either. `BASENAME` then never
matches `CLAUDE.md` or `settings.json`, `PROTECTED` stays `false`, and the script
exits 0.

**Net effect: config-protect.sh never blocks anything, for any input, regardless
of the `.protection-enabled` flag.** Verified directly with `bash -x
config-protect.sh` against a fabricated `.protection-enabled` flag and
`CLAUDE_TOOL_INPUT='{"file_path": "/repo/CLAUDE.md"}'` — trace showed
`FILE_PATH='""'`, `PROTECTED=false`, exit 0. For contrast, `claude-md-guard.sh`
performs the equivalent extraction correctly with plain, unescaped single quotes
and works as intended (Target 1, 6/6 green).

The fixture pins this **actual (broken)** behavior rather than the intended one,
with cases named `0N-bug-...` where the bug is what makes the case pass. If
someone fixes the escaping, those cases should start failing — that's the signal
to flip their `expected_exit` to `2` and needle to `"BLOCKED"`.

**Wiring assertion also fails by design** — confirmed via grep, config-protect.sh
is not registered under `PreToolUse` either. Even after fixing the extraction bug,
nothing currently dispatches this hook.

## Recommended manifest entries (for the lead to add — not written here per this
task's "write only under hooks/evals/" constraint)

```yaml
  - target: hooks/claude-md-guard
    layer: A
    runner: python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook claude-md-guard
    owner_skill: harness
    last_green: 2026-07-07

  - target: hooks/screenshot-placement-guard
    layer: A
    runner: python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook screenshot-placement-guard
    owner_skill: harness
    last_green: 2026-07-07

  - target: hooks/proposal-backlog-check
    layer: A
    runner: python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook proposal-backlog-check
    owner_skill: harness
    last_green: 2026-07-07

  - target: hooks/spec-guard
    layer: A
    runner: python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook spec-guard
    owner_skill: harness
    last_green: 2026-07-07

  - target: hooks/file-guard
    layer: A
    runner: python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook file-guard
    owner_skill: harness
    last_green: null   # runner exits 1 by design (wiring assertion) — do not mark green
                        # until the file-guard wiring decision is made

  - target: hooks/config-protect
    layer: A
    runner: python3 ~/.claude-shared-config/hooks/evals/run_hook_evals.py --hook config-protect
    owner_skill: harness
    last_green: null   # runner exits 1 by design (wiring assertion) — do not mark green
                        # until the config-protect wiring AND extraction-bug decisions are made
```

## Pinned behaviors needing Gabriel's eyes

1. **config-protect.sh extraction bug (above).** Currently non-functional as a
   guard. One-line fix (mirror claude-md-guard.sh's extraction) or retire in favor
   of file-guard.sh.
2. **file-guard.sh and config-protect.sh are both unregistered**, and their
   header comments contradict the live config (file-guard.sh's header claims it
   "replaces" config-protect.sh and claude-md-guard.sh; neither replacement holds
   today). Worth resolving which of the two protection-flag hooks (if either)
   should actually be wired, rather than carrying both dead.
3. **screenshot-placement-guard.sh's `./foo.png` gap** — dot-relative bare
   filenames slip past the warning. Low severity (advisory-only hook), flagged as
   a pinned case rather than a fix.
