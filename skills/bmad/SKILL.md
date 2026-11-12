---
name: bmad
description: "Discover and run BMAD personas and workflows only when the user explicitly requests BMAD or a BMAD command."
---

# BMAD

Shared payload: `~/.claude-shared-config/bmad/`. Start with its `INDEX.md`.

For role questions, run `python3 ~/.claude-shared-config/bmad/bmad.py list`.
For a selected role, use `resolve NAME` for metadata, then `agent NAME` to read its full rendered definition.
Run `agent NAME` without `head`, slicing or truncation. These are activation instructions, not a bulk dataset. Read any remaining chunks if the host truncates output before adopting the role.
For a workflow, use `workflows QUERY` to find its path, then `read PATH` to load only that workflow.
For an explicit legacy `bmad-*` command, use `command NAME` for its exact target. A YAML workflow also requires its engine: read the full engine, pass the selected target as `workflow-config`, then follow its instructions and save at its prescribed boundaries.
Use `--project-root /active/project` before the subcommand when the shell is elsewhere.

Read framework files, including configs, through `bmad.py read PATH`. Raw `cat` of shared config leaves project placeholders unresolved. The reader renders portable runtime paths, uses the active project's module config when present, and supplies neutral defaults otherwise.
Keep the active project as the source of domain context and output placement. Its ticket, architecture and permission rules still apply.

An informational roster request does not activate a persona. Activate only selected roles; load sidecars and later workflow steps when needed.
An explicitly invoked existing workflow may load its declared persona dependencies without advertising all roles in ordinary conversations.
The original BMB builders remain unavailable. Report missing definitions without substitution. Dexter is available from recovered source.

Read `~/.claude-shared-config/bmad/GUIDE.md` for legacy commands, config behavior, multi-role work or maintenance.
Use the current host's native tools. Shared instructions do not install Claude's hooks or orchestration APIs in Codex.
