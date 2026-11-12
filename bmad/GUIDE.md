# BMAD loading and maintenance

## Activation

“Use BMAD” opens the metadata index. “Use BMAD Atlas” loads Atlas.
Claude supports `/bmad`; Codex supports `$bmad`. The same router serves both.
Legacy explicit `bmad-agent-*` commands resolve through this router. Generic role-related work leaves BMAD inactive.
An explicitly invoked existing workflow can load its declared role dependencies at the relevant step.

Run `python3 ~/.claude-shared-config/bmad/bmad.py list` for the current small roster.
Use `agent NAME` to read the entire selected definition, then follow its activation and menu instructions.
Read subsequent BMAD resources through `read PATH`, including configuration and the party-mode roster.
Dismissal ends the role's behavior; already-read text can remain in the conversation until compaction or a new session.

## Resource and project roots

Shared framework source lives in runtime/. The active working project supplies domain facts and output placement.
`bmad.py` renders `{project-root}/_bmad/...` resource references to the shared payload.
For module `config.yaml`, an existing active-project `_bmad/<module>/config.yaml` takes precedence.
Otherwise, neutral shared defaults render the active project name and output paths.
Configuration is read only; discovery and activation never provision files in another project.
Apply that project's ticket placement and architecture rules over generic `_bmad-output` examples.

Read only the relevant agent-os index, specs, contracts or standards when the selected task needs them.
Keep organization facts out of the portable personas. Avoid broad reads of entire documentation trees.

## Custom source and availability

Atlas (`data-engineer`), Leo (`spec-coach`) and Dexter (`debugger`) are preserved original files in custom/.
Runtime adapters reference those same files. The resolver includes all three in the effective party roster.
Dexter was recovered from a user-provided file on 2026-11-02. Its SHA-256 is recorded in runtime.lock.json.
The source is unchanged; a resolver alias repairs its obsolete Party Mode link. The global wrapper loads this original definition.
BMB's original agent/workflow/module builders are also unavailable. New persona creation requires an explicit request and an available builder.

The imported runtime lock records source hashes and versions. This installation does not upgrade to v6.12 or v7.
Keep source preservation separate from any later upgrade and preserve local customizations, including Bob's refinement-planning menu.

## Hosts and restoration

Claude uses the shared skills source through its existing directory link.
Codex's `~/.agents/skills/bmad` links to the same router. Its user AGENTS.md contains only the small loading rule.
`setup.py` preserves unrelated user instructions and refuses to overwrite conflicting skill paths.
`bootstrap.sh` calls setup after restoring the shared harness. Runtime and custom source must travel with this repository.
The user-level pointer is a conditional read instruction, not an eager `@file` import.

Claude model names, tool names, hook enforcement and Workflow execution are host-specific.
Use native supported tools, preserve review gates, and report unavailable executors rather than inventing equivalent enforcement.

## Recovery provenance

Payload source: Klever project-management `_bmad`, preserved 2026-10-27.
Atlas and Leo match Supervisr `fb962a9c0c10227063126124de5e2df5447a06d6` byte-for-byte.
The recovered Supervisr persona guide informed this guide. Its old absolute paths and broad role triggers were intentionally adapted.
The original guide and wiring note remain unmodified in the project's general/harness/recovered-bmad evidence folder.
