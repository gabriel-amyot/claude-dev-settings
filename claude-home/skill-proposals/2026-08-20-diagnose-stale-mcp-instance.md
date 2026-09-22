# Skill Proposal: diagnose-stale-mcp-instance
Date: 2026-08-20
Source: session keen-kestrel — KTP-1130 trader install of the ttd-trading-mcp .mcpb

## Trigger

An MCP tool fails from inside a desktop client while the same call succeeds from a terminal, or
fails identically on retry, or started failing right after an extension was upgraded or
reconfigured. Also: any error naming a config variable whose value on disk is already correct.

The tell is a mismatch between what the file says and what the process does. Configuration is
injected at process launch and never re-read, so a surviving process holds whatever it was born
with.

## Scope

Global. Applies to any locally-installed MCP server, not just Klever's. The Klever-specific parts
are the log paths and the `~/.klever/ttd-mcp-oplog.jsonl` example.

## Draft Steps

1. **Count the processes before theorising.**
   `ps -eo pid,ppid,lstart,command | grep <server module> | grep -v grep`
   More than one server line is the diagnosis. Note each start time.

2. **Read each process's actual environment, not the config file.**
   `ps eww -p <pid> | tr ' ' '\n' | grep <YOUR_ENV_PREFIX>`
   Compare against the installed manifest. A divergence between a live process and the file on
   disk proves the process predates the edit, and the start time confirms it.

3. **Correlate pid to outcome in the server's own log.** The client's log is often useless here: a
   process whose stderr is `/dev/null` writes nothing to it, and the client does not log tool
   invocations at all. The application's own operational log is where the pid lives.
   Tally pid against status; a pid with all failures and no successes is the stale one.

4. **Check timing to rule the network in or out.** A 2-8 ms connect failure never touched the
   network, it is a cached negative DNS answer. A real connect to a cloud gateway is tens of
   milliseconds. Distinguish `ConnectError` from `ReadTimeout` before blaming an environment.

5. **Do not trust the client's shutdown log.** A client can log "intentional shutdown" for a
   process that is still alive and still attached. `ps` is the authority.

6. **Fix by killing the stale pid, then quit the client with Cmd-Q and reopen.** Toggling the
   extension off and on may not be enough. Confirm exactly one process afterwards.

## Why this is worth a skill rather than a CLAUDE.md line

It is a five-step procedure with a specific ordering (count, then read env, then correlate, then
time), and each step has a trap attached that a one-line rule cannot carry. The failure it
diagnoses cost ninety minutes and produced two confident wrong diagnoses along the way: "start the
local media-api service" (nothing runs locally) and "the httpx client is bound to a dead event
loop" (there is no long-lived client). Both were plausible and both were wrong, and the procedure
above would have refuted each in one command.
