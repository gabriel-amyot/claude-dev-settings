---
name: ghostty-recover-sessions
description: "Recover Claude Code sessions that were open in terminal tabs when the computer crashed, lost power, or rebooted unexpectedly. Finds sessions clustered around the crash moment from ~/.claude/projects transcripts, and reopens chosen ones in new Ghostty tabs via `claude --resume`. Triggers on: 'my computer crashed/died/was killed', 'I lost my sessions', 'recover my tabs', 'reopen my claude sessions', 'power went out and I had sessions open'. macOS + Ghostty only."
nav:
  bay: ops
  when: "After an unexpected crash/reboot, recover Claude Code sessions that were open in terminal tabs and bring them back in Ghostty."
  when_not: "Normal session handoff/pickup (use /session:pickup). Sessions closed deliberately (they're just `claude --resume`-able directly, no crash forensics needed)."
---

# Ghostty Session Recovery

Recovers Claude Code sessions that were live in terminal tabs at the moment of
a crash/power-loss/unexpected reboot. Backed by `~/bin/ghostty-recover-sessions`
(already on `PATH`).

**Why this works:** Claude Code writes every session's transcript to
`~/.claude/projects/...` as it goes, independent of the terminal. A crash that
kills many tabs at once leaves those transcripts with near-identical
last-modified timestamps — a tight cluster in time, unlike the scattered
timestamps from sessions closed one at a time through a normal day. The tool
finds that cluster and lets you bring specific sessions back as new Ghostty
tabs, each resumed via `claude --resume <id>`.

**What it does NOT recover:** anything physically in-flight (a tool call
mid-execution) at the exact instant of the crash — only Claude Code's own
saved conversation history, same as running `claude --resume` by hand.

## Hard rule: never decide and open in one step

This tool has three subcommands. **Only `find` is safe to run freely.**
`open` fires real keystrokes into whatever app is frontmost — do not call it
without the user explicitly confirming which session IDs to open.

| Subcommand | Does | Who calls it |
|---|---|---|
| `find` | Read-only discovery. Prints candidates. Opens nothing, ever. | You, freely, any time |
| `open --session <id> ...` | Reopens exactly the given IDs. No auto-selection. | You, only after explicit user confirmation |
| `pick` | Interactive `find` + `fzf` multi-select + open. | The user directly at their keyboard — not you |

**`find` has two output shapes depending on whether you gave it an exact window:**
- No `--since`/`--until`: lists **every distinct cluster** found in the lookback window (`--days`, default 30) as a *summary* — time range, session count, cwd(s), and a ready-to-copy `--since`/`--until` drill-in command. It deliberately does NOT pick "the biggest" and expand it — a wide window can contain more than one real crash-like event (today's, plus one from weeks ago), and collapsing to a single winner would hide the others.
- With `--since`/`--until`: full detail for exactly that window — cwd, first/last message preview, per session. This is what you actually read to decide which sessions matter.

**The flow, every time:**
1. Run `ghostty-recover-sessions find` (no window args) to see what clusters exist. If exactly one, drill in with the printed `--since`/`--until` command to get full detail. If several, show the user the cluster list and ask which time range they mean before drilling in.
2. Show the user the drilled-in detail: cwd, first/last message preview, timestamp. Help them recognize which ones matter (some may already be naturally wrapped up).
3. **Ask which specific sessions to reopen.** Wait for an explicit answer (session IDs, "all of them", "just the KTP-719 one", etc.).
4. Call `ghostty-recover-sessions open --session <id1> --session <id2> ...` with exactly the confirmed IDs (8-char prefix is enough; the tool prefix-matches against every session under `~/.claude/projects` and errors if a prefix is ambiguous).

## Do NOT do this

- **Do not call `open` without an explicit session ID the user confirmed in this conversation.** There is no "open everything found" shortcut — that was removed on purpose. If you find yourself about to pass every ID from a `find` result into `open` without having asked, stop.
- **Do not treat a plain `find` (no window) summary as if it were session detail.** It has no message previews at that point — you have not actually looked at what's in those sessions yet, so you cannot meaningfully summarize them to the user. Drill in first.
- **Do not assume the default 30-day window covers an old event, and do not assume the first/only cluster shown is the one the user means.** If `find` shows multiple clusters, ask which one, don't guess from recency or size.
- **Do not call `pick` yourself.** It launches an interactive `fzf` prompt meant for the user's own fingers at their own keyboard — an LLM calling it either hangs waiting for input it can't provide, or (worse) an agent might try to script fake input into it. Use `find` + `open` instead; that pairing *is* the LLM-safe path.
- **Do not retry `open` in a loop if a session fails to open.** `open` reports `FAILED to open <id>: ...` per session with the reason (commonly missing Accessibility permission). Surface that message to the user rather than re-attempting — repeated keystroke injection attempts compound the risk of hitting the wrong app if focus is unstable.

## Usage reference

```
ghostty-recover-sessions find                     # list every cluster in the last 30 days (summary only)
ghostty-recover-sessions find --json               # same, machine-readable
ghostty-recover-sessions find --days 60            # widen lookback to catch an older event
ghostty-recover-sessions find --cluster-gap 5      # minutes between sessions to count as one cluster (default 2)
ghostty-recover-sessions find --since 2026-08-01T05:00:00 --until 2026-08-01T05:10:00
                                                    # drill in: full detail for one exact window
ghostty-recover-sessions find --dir /path/to/project
ghostty-recover-sessions find --include-non-cli   # also show eval/SDK-harness sessions (noise by default)

ghostty-recover-sessions open --session 061ebde8 --session 4b8cb136
```

**Worked example — the whole flow:**
```
$ ghostty-recover-sessions find
Found 2 distinct cluster(s):

  2026-08-01 05:07:45 -> 05:08:18 UTC   21 session(s)
    dir(s): ~/Developer/grp-beklever-com/project-management, ~/Developer/gabriel-amyot/project-management
    drill in: ghostty-recover-sessions find --since 2026-08-01T05:07:45 --until 2026-08-01T05:08:18

  2026-06-28 02:14:00 -> 02:15:40 UTC   6 session(s)
    dir(s): ~/Developer/grp-beklever-com/project-management
    drill in: ghostty-recover-sessions find --since 2026-06-28T02:14:00 --until 2026-06-28T02:15:40
```
→ Ask the user which event they mean (or if it's obvious from context, say so and confirm). Say they pick the first one:
```
$ ghostty-recover-sessions find --since 2026-08-01T05:07:45 --until 2026-08-01T05:08:18
Found 21 session(s):
  ... cwd, first message, last message per session ...
```
→ Show that to the user, ask which of the 21 to bring back. Say they answer "just the dark-factory KTP-719 one and the Placer API one":
```
$ ghostty-recover-sessions open --session 7654d361 --session 061ebde8
```
→ That's the only step that touches Ghostty, and it only runs because the user named those two IDs.

`find` auto-detection filters out `entrypoint != "cli"` sessions by default —
these are eval/SDK-harness test runs, not real terminal tabs, and can
otherwise dominate the clustering with false positives (observed: 135
synthetic sessions from one eval batch outsized a real 21-session crash
cluster). Use `--include-non-cli` only if you're deliberately looking for
those.

## Known constraints (macOS + Ghostty specific)

- **Ghostty is single-instance on macOS** with no CLI/IPC way to open an
  independent new window or tab in an already-running instance (`+new-window`
  is explicitly unsupported on macOS). `open` drives it via AppleScript/System
  Events instead: activate, verify Ghostty is actually frontmost (polling with
  retries), Cmd+T, type a short launch command, Enter.
- **Requires Accessibility permission** for whatever app is running this
  script (System Settings → Privacy & Security → Accessibility). Without it,
  AppleScript's keystroke simulation is silently refused (error 1002).
- **`activate` racing user input is real** — if the user is actively typing in
  another app at the exact moment a keystroke fires, it can land in the wrong
  app. `open` verifies frontmost-ness before every keystroke and aborts that
  one session rather than risk a misfire, but it still asks the user to keep
  hands off keyboard/mouse for a few seconds before it starts (this recovery
  flow runs rarely — a printed warning + short pause was judged sufficient;
  no need to propose a more bulletproof mechanism unless asked).
- **Typed strings are kept short** — a full `cd <path> && claude --resume
  <uuid>` string is long enough that AppleScript's `keystroke` can silently
  drop a character mid-string (observed once). `open` writes a tiny temp
  launch script instead and types only `zsh <short-path>`.
