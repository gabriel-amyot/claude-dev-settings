---
title: MCP Server Scoping and Isolation in Claude Code
type: concept
created: 2026-08-12
tags: [mcp, claude-code, scoping, isolation, tooling]
aliases: [mcp-scoping, mcp-isolation, strict-mcp-config]
---

# MCP Server Scoping and Isolation in Claude Code

**Source:** Session keen-shrike, Notion checkout build (2026-08-10).

Four mechanics that matter whenever an MCP server should load in only one project or one
headless process, not every interactive session.

---

## `claude mcp add` From a Project Root Registers at Local Scope and Loads Everywhere

Scoping an MCP server to a folder via `.mcp.json` is defeated if the same server is also
registered at **local** scope for another project. Local-scope registration loads the server's
tool definitions into every session started from that working root, including sessions with no
relation to the server's purpose.

**How to apply:** After scoping any MCP server to a folder, verify from both directories with
`claude mcp get <name>`. `Scope: Local config` means it loads everywhere in that project, not
only in the folder you intended. Remove the leak with `claude mcp remove <name> -s local`. A
heavy MCP server costs tokens in every unrelated session it loads into.

## `--mcp-config <path> --strict-mcp-config` Is the Real Isolation Mechanism

Directory scoping alone still loads the MCP server in any interactive session started in that
directory. Passing `--mcp-config .mcp.json --strict-mcp-config` to a headless `claude -p`
invocation loads only that server, for only that process.

**How to apply:** For a heavy MCP server used only by a batch or sync operation, do not rely on
cwd scoping. Invoke headless with `--strict-mcp-config` and never register the server at user or
local scope. Combined with removing local-scope registration, no interactive session ever loads
the server; it exists only for the seconds a fetch runs.

## `.mcp.json` Approval Is Per-Directory and Separate from OAuth

A project-scoped `.mcp.json` server requires a one-time interactive trust approval per directory
(`Pending approval (run claude to approve)`), which is distinct from the OAuth flow. Approving or
authenticating in one folder does not carry to another folder. Removing a local-scope
registration also drops the OAuth token attached to it, which breaks any dependent headless path.

**How to apply:** Expect two separate one-time steps per folder: approve the `.mcp.json` trust
prompt, then run `/mcp` to authenticate. Budget for re-authentication after moving a server
between scopes.

## The `!` Prefix Shell Is Non-Interactive — `claude` Cannot Be Launched From It

Running `claude` via a session's `!` bash-prefix shortcut fails with `Error: Input must be
provided either through stdin or as a prompt argument when using --print`. Any step needing
interactive Claude (MCP OAuth, `/mcp`, trust prompts) needs a real terminal window.

**How to apply:** When handing a user a step that requires interactive Claude, say "open a real
terminal" explicitly. Do not suggest the `!` prefix for it.

---

## There Are TWO MCP Surfaces, and a Config-Only Audit Misses One

**Source:** Klever session `deft-pike`, MCP surface audit (2026-08-13).

An earlier audit found the Notion MCP registered at **local scope** in a project directory, loading
into every session there, and removed it. That fix held and was re-verified: no `.mcp.json` in the
project, no `mcpServers` under any project in `~/.claude.json`, only one server at user scope.

The config files said clean. The session's tool list did not.

A second surface exists that **no Claude Code config controls**: the claude.ai **account
connector**, which appears as `mcp__claude_ai_<Name>__*` — 29 tools in the Notion case, in *every*
session regardless of directory.

| Surface | Registered in | Scope |
|---|---|---|
| `mcp__notion__*` | a project's `.mcp.json` | that project only |
| `mcp__claude_ai_Notion__*` | claude.ai account connectors | every session, everywhere |

**What makes the second one tolerable:** those tools arrive **deferred**, so only the tool *names*
load, not the schemas. A name list is far cheaper than 29 full definitions, and cheaper than the
local-scope registration that was actually costing tokens.

**How to apply:** When auditing "is this MCP properly scoped," check both. Grep `~/.claude.json` and
every `.mcp.json`, **then also read the session's own tool list** for `mcp__claude_ai_*` entries.
The config files alone will tell you it is clean when it is not.

## claude.ai Connectors Cannot Be Disabled From Claude Code Settings

Verified: no connector- or MCP-related key exists in `~/.claude/settings.json` or
`settings.local.json`, and the servers are absent from `enabledMcpjsonServers` and
`disabledMcpjsonServers`.

They are account-side. Disable at **claude.ai → Settings → Connectors → disconnect**.

**The trade-off is total.** Disconnecting removes the connector from claude.ai chats *and* from
every Claude Code session. A project-scoped `.mcp.json` then becomes the only remaining path to that
service.

**How to apply:** Before disconnecting a connector to cut tool-name bloat, list everything that
reaches that service through it. See the sequencing rule in
[long-running-process-pattern.md](long-running-process-pattern.md): prove the dependent job works on
its other credential path first.
