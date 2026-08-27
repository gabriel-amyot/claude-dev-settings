# Long-Running Process Pattern

How to run multi-hour jobs from Claude Code without them being killed by tool timeouts.

## Problem

The Bash tool has a max timeout of 600,000ms (10 minutes). Background tasks (`run_in_background: true`) are also subject to this limit. Any process exceeding 10 minutes will be killed.

## Solution: nohup Launcher Script

1. Write a self-contained launcher script to `/tmp/`:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd /path/to/workdir

# Get credentials inside the script (they expire)
export TOKEN=$(gcloud auth print-identity-token)
export API_KEY=$(gcloud secrets versions access latest --secret="..." --project="...")

# Run the actual work, logging to a file
python3 my-script.py --args >> /path/to/log.log 2>&1

echo "[$(date)] === FINISHED ===" >> /path/to/log.log
```

2. Launch it detached:
```bash
chmod +x /tmp/launcher.sh
nohup /tmp/launcher.sh &
echo $! > /tmp/process-pid.txt
```

3. Monitor via log file:
```bash
tail -f /path/to/log.log
grep -c 'some_progress_marker' /path/to/log.log  # count progress
```

## Key Rules

- **Credentials inside the script:** GCP identity tokens and Auth0 M2M tokens expire (24h). Get them at script start, not before launch.
- **Log to a file, not stdout:** `nohup` redirects stdout to `nohup.out` by default, but explicit logging is more reliable.
- **Save PID:** Write `$!` to a file so you can check/kill the process later.
- **Use `flush=True` in Python:** Without explicit flushing, Python buffers stdout and logs appear empty for long periods.
- **`disown` may fail in zsh:** The `disown` command sometimes errors in the Claude Code shell. `nohup` alone is sufficient.

## Monitoring Commands

```bash
ps aux | grep my-script | grep -v grep     # is it running?
tail -5 /path/to/log.log                    # latest progress
grep -c 'success_marker' /path/to/log.log   # count completions
wc -l /path/to/log.log                      # total log lines
```

---

## A Headless `claude -p` Subprocess Inherits the Parent's PreToolUse Hooks

A headless subprocess is not a fresh permission environment. It inherits the parent session's
hooks from `settings.json`, including a repo's `worktree-guard.sh`.

During a Notion checkout crawl, this silently lost 3 pages. Shards that wrote their JSON via a
Bash heredoc succeeded. The one shard that reached for the Write tool was blocked by
`worktree-guard.sh` (main-worktree edits are blocked; a project-management-style docs repo is
typically exempt), and its pages never landed. The failure was invisible in the aggregate
progress counter. It surfaced only when the staged-file count came up 3 short of the target
list. Source: session deft-pike, Klever Notion checkout first sync (2026-08-12).

**How to apply:** When a headless prompt must write files into a hook-guarded repo, mandate the
write mechanism explicitly, for example "use Bash with a python3 heredoc, do not use the Write
tool." Leaving the tool choice to the model makes success non-deterministic. A guard firing
inside a headless subprocess is not itself evidence of a false positive; check whether the
artifact being written is shaped wrong before reaching for an exemption.

## A Killed Foreground `claude -p` May Have Already Finished Its Work

The Bash tool's 10-minute ceiling can kill a foreground `claude -p` process after it has already
completed. In one case the subprocess had written both its output file and its
`--output-format json` result before the kill signal landed.

**How to apply:** On a timeout or a kill, check the artifacts on disk before concluding the run
failed. Re-running a job that already succeeded doubles the spend for nothing.

Related counter trap: shell redirection with `>` creates the target file immediately, at 0
bytes, before any content is written. Counting shard result files by existence alone overstates
progress. An in-flight shard shows up as a 0-byte file. Count with `find -size +1c` instead of a
bare file-existence count.

## Detached Background Work: the Launch Notification Refers to the Launcher, Not the Job

`nohup ... &` inside a backgrounded Bash call reports "completed" as soon as the launcher process
exits, while the real work continues running detached. The completion notification is about the
launcher, not the job it started.

**How to apply:** Poll the artifact count or `pgrep` for the actual worker process. Do not treat
a backgrounded launch's own completion message as proof the job it started is done.

---

## Cowork Runs Locally and Has File Access — a Cloud/Local Split Is the Wrong Model

**Source:** Klever session `deft-pike`, designing a scheduled mirror refresh (2026-08-13).

Cowork recurring tasks execute through the **Claude desktop app on the machine**, so they can read
and write local files. Evidence on disk, confirmed 2026-08-13:

```
~/Library/Application Support/Claude/cowork-enabled-cli-ops.json
~/Library/Application Support/Claude/Partitions/cowork-*
```

This corrects an intuitive but wrong assumption: that anything "scheduled on Anthropic's side"
cannot touch a local repo and would therefore need a git remote as a bridge. It does not.

**Where the schedule lives is the surprising part: not on disk.** A project's
`.claude/scheduled_tasks.json` reads `{"tasks": []}` even when Cowork tasks exist. Cowork's
recurring-task definitions are **account-side**. You cannot enumerate, create, or edit them from a
Claude Code session. They are configured in the Cowork UI only.

**How to apply:** An agent can write the *prompt* for a recurring task. The human must install the
schedule. Do not plan a design around an agent creating or reading its own Cowork schedule.

## Three Scheduling Substrates, With Different Guarantees

| Substrate | Runs when | Survives | Use for |
|---|---|---|---|
| `CronCreate` | only while a REPL is **idle** | dies on exit; recurring jobs **auto-expire after 7 days** | "watch this while I work today" |
| Cowork recurring task | desktop app, local file access | account-side schedule | agentic recurring work needing judgment |
| `launchd` | a real scheduler, survives reboot | plist on disk | deterministic scripts |

**`CronCreate` is the trap.** It reads like a scheduler and cannot do unattended recurring work.

**Prefer `launchd` plus a deterministic script whenever the task has no judgment in it.** The
working example on this machine: `com.gabriel.bibliotheque-surface-reconcile.plist` fires
`tools/bibliotheque/surface_reconcile.py` daily at 06:00. No model in the loop, no token cost, and
it survives a reboot.

**How to apply:** Pick the substrate from the guarantee you need, not from which one is easiest to
create. If the job must run unattended and repeat past a week, `CronCreate` is disqualified.

## Prove the Scheduled Task Before Removing the Credential It Might Depend On

A scheduled task can reach a service through more than one credential path — a project-scoped
`.mcp.json`, or an account-side connector. Which one it actually uses may be unverified.

If it is the connector, then disabling that connector for an unrelated reason (tool-name bloat, say)
**silently breaks the scheduled job**. Two changes that each look independently correct combine into
a broken job with an ambiguous cause.

**Rule: get the scheduled task running and confirm it works, then remove the credential path you
suspect is redundant.** If it breaks, you have your answer and can restore it.

The reverse order gives you a failure with two candidate causes and no signal to separate them.

**How to apply:** Order every credential cleanup after the dependent job has one confirmed green
run. This generalizes past MCP: the same shape applies to rotating a key, narrowing an IAM binding,
or deleting a service account a cron job might still use.
