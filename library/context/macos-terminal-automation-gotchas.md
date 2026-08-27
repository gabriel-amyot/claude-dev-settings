# macOS Terminal Automation Gotchas (AppleScript + Ghostty)

Cross-project knowledge for any tool that drives a macOS terminal app via `open` or
AppleScript keystroke injection. Learned 2026-08-03 building a Ghostty-based session-recovery
tool.

---

## 1. Ghostty is single-instance on macOS — `open -na` does not open independent windows

`open -na Ghostty.app --args ...` does not create a new, independent window each time you
call it. Ghostty runs as a single instance on macOS. A repeated `open -na` call recycles that
one instance. It tears down the previous window. It orphans the previous shell process, which
keeps running headless instead of shutting down cleanly. The visible symptom looks like a
window that opens and immediately crashes. The window does not crash. The next invocation
replaces it.

Ghostty's own `+new-window` CLI action is unsupported on macOS. Running
`ghostty +new-window` returns `"+new-window is not supported on this platform."` There is no
config key to disable single-instance mode (checked via `ghostty +show-config`).

**How to apply:** to open a genuine additional window or tab in an already-running Ghostty
instance, drive the app's own in-app keybind. Use Cmd+T for a new tab or Cmd+N for a new
window, through simulated keystrokes (AppleScript + System Events). Do not rely on `open -na`
or `+new-window` for multi-window automation against Ghostty.

## 2. AppleScript `keystroke` can silently drop characters on long strings

Typing a long string via
`tell application "System Events" to keystroke "..."` can silently drop a chunk of characters
mid-string under real-world conditions. One observed case involved a full path plus a UUID,
over 100 characters. The drop produced a garbled command and left the shell stuck at a
`quote>` continuation prompt.

**How to apply:** write the actual long command to a small temporary shell script on disk, and
type only a short invocation of that script (`zsh /tmp/foo.sh`) instead of the full command
inline. Keep every simulated keystroke short.

## 3. `tell application "X" to activate` does not guarantee X is frontmost for the next keystroke

There is a real race condition. `activate` returns before macOS has necessarily finished
switching focus. The user may be actively interacting with another app, typing or clicking, at
that moment. Focus can then bounce back to that app before the next `keystroke` command fires.
This caused a real misfire: a keystroke sequence meant for a new Ghostty tab landed in the
user's live iTerm2 session instead. It executed a real command in the user's active shell
without their intent.

**How to apply:** after `activate`, poll for the frontmost app with retries: six attempts,
0.3s delay, re-issuing `activate` each time. Use
`tell application "System Events" to get name of first application process whose frontmost is true`
to confirm the target app is actually frontmost before you send any keystroke. If the target
app never becomes frontmost, abort that action instead of risking the wrong target. This
confirm-before-keystroke check is the single most important safety property for any
keystroke-simulation automation.

For low-frequency personal tools, used monthly or less, add a printed disclaimer plus a short
pause: "hands off the keyboard for 3 seconds" before firing keystrokes. Treat this as a
reasonable complement to the frontmost check, not a substitute for it.

## 4. macOS Accessibility permission belongs to the controlling app, not the target

When macOS denies AppleScript/System Events keystroke injection, the error reads
`"osascript is not allowed to send keystrokes (1002)"`. The Accessibility permission you must
grant, under System Settings → Privacy & Security → Accessibility, belongs to whatever app
actually runs the `osascript` call. That is often the terminal emulator hosting the session.
It does not belong to the app that the keystrokes control or target.

**How to apply:** when you hit error 1002, grant Accessibility to the controlling terminal
app, not the app you are trying to automate. This is a common source of confusion. Verify
which process actually issues the `osascript` call before you grant permission.
